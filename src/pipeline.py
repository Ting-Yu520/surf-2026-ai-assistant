"""
端到端流水线 v5 — 二人转科普版本

让 AI 生成双口相声风格的角球科普解说。
"""

import time, logging, re, requests, json
from html import unescape
from anthropic import Anthropic
from config import (
    DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_API_KEY,
    API_TIMEOUT, MAX_TOKENS, TEMPERATURE, OUTPUT_DIR,
)
from tts_client import generate_audio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_corner_kick(
    video_path: str = None,
    article_url: str = None,
    article_text: str = None,
    output_prefix: str = "",
) -> dict:
    """处理角球视频——二人转科普版本。"""
    from prompts.corner_kick import DUO_SYSTEM_PROMPT, DUO_USER_TEMPLATE

    t0 = time.time()
    result = {}
    prefix = output_prefix + "_" if output_prefix else ""

    # ====== Step 1: 获取文章描述 ======
    if article_text:
        facts = article_text
    elif article_url:
        r = requests.get(article_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        r.encoding = 'utf-8'
        text = r.text
        title_m = re.search(r'<title>([^<]+)</title>', text)
        title = unescape(title_m.group(1)).strip() if title_m else ''
        paras = re.findall(r'<p[^>]*>([^<]{20,})</p>', text)
        body = ''
        for p in paras:
            clean = re.sub(r'<[^>]+>', '', p)
            clean = unescape(clean).strip()
            if clean: body += clean + '\n'
        facts = f"标题：{title}\n内容：{body}"
        result['article'] = {'title': title, 'body': body}
    else:
        raise ValueError("需要 article_url 或 article_text")

    result['facts'] = facts
    logger.info(f"Step 1 ✓")

    # ====== Step 2: 二人转生成 ======
    logger.info("Step 2: 生成双口相声脚本...")
    client = Anthropic(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=float(API_TIMEOUT))
    response = client.messages.create(
        model=DEEPSEEK_MODEL, max_tokens=MAX_TOKENS, temperature=0.85,
        system=DUO_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": DUO_USER_TEMPLATE.format(article=facts)}],
    )
    script = '\n'.join(b.text for b in response.content if hasattr(b, 'text'))
    result['script'] = script
    logger.info(f"Step 2 ✓: {len(script)} chars")

    # ====== Step 3: 合成完整解说（A+B对话合并为叙事） ======
    # 把对话转成自然语音解说文本（二人转对白）
    lines = [l for l in script.split('\n') if l.strip()]
    # 改写成叙事式解说（用于 TTS 单声道）
    narration = "你听我来给你讲讲这个角球啊！\n"
    for l in lines:
        if l.startswith('A:'):
            narration += l[2:].strip() + " "
        elif l.startswith('B:'):
            pass  # B 的话省略，让叙事保持连贯

    result['narration'] = narration
    logger.info(f"Step 3 ✓: 对话合成叙事 {len(narration)} chars")

    # ====== Step 4: TTS ======
    audio_path = str(OUTPUT_DIR / f"{prefix}narration.mp3")
    generate_audio(narration, audio_path)
    result['audio_path'] = audio_path
    logger.info(f"Step 4 ✓")

    # ====== Step 5: 视频合成 ======
    if video_path:
        from video_overlay import create_simple_video
        output_video = str(OUTPUT_DIR / f"{prefix}corner_story.mp4")
        create_simple_video(video_path, audio_path, output_video)
        result['output_video'] = output_video
        logger.info(f"Step 5 ✓: {output_video}")

    result['elapsed'] = time.time() - t0
    return result


# 保持与旧版兼容
SYSTEM_PROMPT = DUO_SYSTEM_PROMPT
