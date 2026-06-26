"""
端到端流水线 v4 — 文章底本版本

不做 VLM 看图猜。用 CCTV 记者报道做准确底本 → LLM 改写为科普解说。
"""

import time, logging, re, requests
from html import unescape
from anthropic import Anthropic
from config import (
    DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_API_KEY,
    API_TIMEOUT, MAX_TOKENS, TEMPERATURE, OUTPUT_DIR,
)
from tts_client import generate_audio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 教育科普 System Prompt
SYSTEM_PROMPT = """你是一个足球科普作者。你要把一条足球比赛新闻改写成一段45秒的科普解说词。

观众是完全不懂足球的新手。他们不知道角球是什么。

结构（3段）：
第1段（15秒）：「这是什么？」— 用1句话解释角球（生活比喻），然后说"现在你看到的是..."
第2段（20秒）：「发生了什么？」— 把新闻里的内容变成生动的描述。指出场上发生了什么，为什么这个动作厉害
第3段（10秒）：「为什么这很酷？」— 用1个生活比喻总结，让观众"哦，原来如此"

规则：
- 口语化，像朋友在旁边解说
- 绝对不用足球术语，每个概念用比喻解释
- 告诉观众看哪里："注意看...""你看到...了吗？"
- 纯文本输出，不要标题，不要标记"""


def fetch_cctv_article(url: str) -> dict:
    """从CCTV页面抓取标题和正文。"""
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    r.encoding = 'utf-8'
    text = r.text
    # 标题
    title_m = re.search(r'<title>([^<]+)</title>', text)
    title = unescape(title_m.group(1)).strip() if title_m else ''
    # 正文
    paras = re.findall(r'<p[^>]*>([^<]{20,})</p>', text)
    body = ''
    for p in paras:
        clean = re.sub(r'<[^>]+>', '', p)
        clean = unescape(clean).strip()
        if clean: body += clean + '\n'
    return {'title': title, 'body': body.strip()}


def process_corner_kick(
    video_path: str = None,
    article_url: str = None,
    article_text: str = None,
    output_prefix: str = "",
) -> dict:
    """处理角球视频——文章底本版。"""
    t0 = time.time()
    result = {}
    prefix = output_prefix + "_" if output_prefix else ""

    # ====== Step 1: 获取准确描述 ======
    if article_text:
        facts = article_text
    elif article_url:
        article = fetch_cctv_article(article_url)
        facts = f"标题：{article['title']}\n内容：{article['body']}"
        result['article'] = article
    else:
        raise ValueError("需要 article_url 或 article_text")

    result['facts'] = facts
    logger.info(f"Step 1 ✓: {len(facts)} chars from article")

    # ====== Step 2: LLM 改写 ======
    logger.info("Step 2: LLM 科普改写...")
    client = Anthropic(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=float(API_TIMEOUT))
    response = client.messages.create(
        model=DEEPSEEK_MODEL, max_tokens=MAX_TOKENS, temperature=0.8,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"请把这条足球新闻变成45秒的科普解说：\n\n{facts}"}],
    )
    narration = '\n'.join(b.text for b in response.content if hasattr(b, 'text'))
    result['narration'] = narration
    logger.info(f"Step 2 ✓: {len(narration)} chars")

    # ====== Step 3: TTS ======
    logger.info("Step 3: TTS 配音...")
    audio_path = str(OUTPUT_DIR / f"{prefix}narration.mp3")
    generate_audio(narration, audio_path)
    result['audio_path'] = audio_path
    logger.info(f"Step 3 ✓")

    # ====== Step 4: 视频合成 ======
    if video_path:
        from video_overlay import create_simple_video
        output_video = str(OUTPUT_DIR / f"{prefix}corner_story.mp4")
        create_simple_video(video_path, audio_path, output_video)
        result['output_video'] = output_video
        logger.info(f"Step 4 ✓: {output_video}")

    result['elapsed'] = time.time() - t0
    return result
