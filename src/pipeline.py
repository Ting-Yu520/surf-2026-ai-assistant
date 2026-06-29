"""
端到端流水线 v6 — 二人转科普 + ffmpeg 视频剪辑

让 AI 生成双口相声风格的角球科普解说，逐句 TTS 获取时间轴，
用 ffmpeg 按时间轴叠加彩色边框、角色角标，输出最终视频。
"""

import time, logging, re, requests, json
from html import unescape
from typing import Optional
from anthropic import Anthropic
from config import (
    DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_API_KEY,
    API_TIMEOUT, MAX_TOKENS, TEMPERATURE, OUTPUT_DIR,
)
from tts_client import generate_audio, generate_timeline_audio, concat_audio_segments
from prompts.corner_kick import DUO_SYSTEM_PROMPT, DUO_USER_TEMPLATE
from phase_bridge import get_real_or_sample, build_field_mapping, tacticai_to_phase2, format_for_prompt
from mg_renderer import render_all_mg_clips

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_corner_kick(
    video_path: str = None,
    article_url: str = None,
    formatted: Optional[dict] = None,
    output_prefix: str = "",
    corner_entry: Optional[dict] = None,
    tacticai_predictions: Optional[list] = None,
) -> dict:
    """处理角球视频——二人转科普 + 视频剪辑版本。"""

    t0 = time.time()
    result = {}
    prefix = output_prefix + "_" if output_prefix else ""

    # ====== Step 0: 获取真实预测数据 ======
    predictions_data = None
    mapping = None
    if corner_entry:
        predictions_data = get_real_or_sample(corner_entry)
        if predictions_data and predictions_data.get("predictions"):
            mapping = build_field_mapping(predictions_data["predictions"])
            logger.info(f"Step 0 ✓: {len(predictions_data['predictions'])} real player positions loaded")

    # Make predictions available for the prompt formatting
    if predictions_data:
        # Pass predictions into the formatted data for LLM prompt context
        phase2_input = tacticai_to_phase2(predictions_data)
        formatted_from_real = format_for_prompt(phase2_input, corner_entry)
        if not formatted:
            formatted = formatted_from_real
        # Also augment the tactic_section with real probability data
        if formatted and predictions_data.get("predictions"):
            top_preds = sorted(predictions_data["predictions"],
                              key=lambda p: p.get("probability", 0), reverse=True)[:3]
            extra = "\nTacticAI 真实预测数据:\n"
            for p in top_preds:
                role = p.get("role", "球员")
                prob = p.get("probability", 0)
                pos = p["position"]
                extra += f"- {role}#{p['player_index']}: 接球概率 {prob*100:.1f}%, 位置({pos[0]:.0f},{pos[1]:.0f})\n"
            formatted["tactic_section"] = formatted.get("tactic_section", "") + extra

    # Store for later use
    result["predictions_data"] = predictions_data
    result["mapping"] = mapping

    # ====== Step 1: 获取输入数据 ======
    if formatted:
        section_text = (
            f"## 比赛事实\n{formatted.get('fact_section', '')}\n\n"
            f"## 战术彩蛋（可选）\n{formatted.get('tactic_section', '')}"
        )
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
        formatted = {"fact_section": f"标题：{title}", "tactic_section": body}
        section_text = f"## 比赛事实\n{formatted['fact_section']}\n\n## 战术彩蛋\n{formatted['tactic_section']}"
        result['article'] = {'title': title, 'body': body}
    else:
        raise ValueError("需要 formatted 或 article_url")

    result['formatted'] = formatted
    logger.info(f"Step 1 ✓")

    # ====== Step 2: 二人转生成 ======
    logger.info("Step 2: 生成双口相声脚本...")
    client = Anthropic(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=float(API_TIMEOUT))
    response = client.messages.create(
        model=DEEPSEEK_MODEL, max_tokens=MAX_TOKENS, temperature=0.85,
        system=DUO_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": DUO_USER_TEMPLATE.format(
                fact_section=formatted.get("fact_section", ""),
                tactic_section=formatted.get("tactic_section", ""),
            ),
        }],
    )
    script = '\n'.join(b.text for b in response.content if hasattr(b, 'text'))
    result['script'] = script
    logger.info(f"Step 2 ✓: {len(script)} chars")

    # ====== Step 3: 解析脚本为 A/B 逐句段 ======
    from video_overlay import parse_script
    segments = parse_script(script)
    if not segments:
        # 如果 LLM 输出格式不对，加退路
        segments = [{"speaker": "A", "text": script}]
    logger.info(f"Step 3 ✓: 解析出 {len(segments)} 句对话")

    # ====== Step 4: 逐句 TTS ======
    audio_seg_dir = OUTPUT_DIR / f"{prefix}audio_segs"
    audio_seg_dir.mkdir(exist_ok=True)

    tts_segments = generate_timeline_audio(
        [{"narration": seg["text"]} for seg in segments],
        str(audio_seg_dir),
    )

    # 合并音频
    audio_path = str(OUTPUT_DIR / f"{prefix}narration.mp3")
    concat_audio_segments(tts_segments, audio_path)
    result['audio_path'] = audio_path
    logger.info(f"Step 4 ✓: {len(tts_segments)} 段 TTS")

    # ====== Step 4b: 组装时间轴 ======
    from video_overlay import build_timeline
    timeline = build_timeline(segments, [s["actual_duration_sec"] for s in tts_segments])
    result['timeline'] = timeline
    logger.info(f"Step 4b ✓: 时间轴 {timeline[-1]['end']:.1f}s" if timeline else "Step 4b ✓: 空时间轴")

    # ====== Step 4c: 渲染 MG 动画 ======
    # Auto-upgrade: A 段的非 clear visual → ai_scene（确保 MG 动画覆盖懂哥解说）
    for seg in segments:
        if seg["speaker"] == "A" and seg.get("visual_type") != "ai_scene" and seg.get("visual_type") != "clear":
            seg["visual"] = "ai_scene"
            seg["visual_type"] = "ai_scene"

    predictions_list = predictions_data.get("predictions", []) if predictions_data else []
    ai_scene_segments = [
        {**seg, "actual_duration_sec": d, "orig_index": i}
        for i, (seg, d) in enumerate(zip(segments, [s["actual_duration_sec"] for s in tts_segments]))
        if seg.get("visual_type") == "ai_scene"
    ]

    mg_clips = {}
    if ai_scene_segments and predictions_list and mapping:
        logger.info(f"Step 4c: Rendering {len(ai_scene_segments)} MG animation segments...")
        mg_clips = render_all_mg_clips(
            ai_scene_segments, predictions_list, mapping, corner_entry or {}, prefix
        )
        ok = sum(1 for v in mg_clips.values() if v)
        logger.info(f"Step 4c ✓: {ok}/{len(mg_clips)} MG clips rendered")
    else:
        reason = "no ai_scene segments" if not ai_scene_segments else \
                 "no predictions data" if not predictions_list else \
                 "no field mapping"
        logger.info(f"Step 4c ⏭: Skipped ({reason})")

    result["mg_clips"] = mg_clips

    # ====== Step 5: 视频合成 ======
    if video_path:
        from video_overlay import create_titled_video
        match_info = ""
        if corner_entry:
            match_info = f"{corner_entry.get('match','')} — {corner_entry.get('goal_scorer','')} ({corner_entry.get('minute','')}')"
        output_video = str(OUTPUT_DIR / f"{prefix}corner_story.mp4")
        total_dur = timeline[-1]["end"] if timeline else None
        create_titled_video(
            video_path=video_path,
            audio_path=audio_path,
            timeline=timeline,
            output_path=output_video,
            match_info=match_info or "⚽ AI 角球战术解说",
            total_dur=total_dur,
            tacticai_predictions=tacticai_predictions,
            mg_clips=mg_clips,
        )
        result['output_video'] = output_video
        logger.info(f"Step 5 ✓: {output_video}")
    else:
        logger.info("Step 5 ⏭: 无视频源，跳过")

    result['elapsed'] = time.time() - t0
    return result


# 保持与旧版兼容
SYSTEM_PROMPT = DUO_SYSTEM_PROMPT
