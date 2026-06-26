"""
端到端流水线 — 时间线感知版本

流程：
  视频 → VLM (时间线+JSON) → LLM (分段叙事) → TTS (逐段配音+精确时长) → Video (字幕精确对齐)
"""

import time, json, logging
from pathlib import Path
from anthropic import Anthropic

from config import (
    DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_API_KEY,
    API_TIMEOUT, MAX_TOKENS, TEMPERATURE, OUTPUT_DIR,
)
from vlm_client import analyze_corner_kick
from prompts.corner_kick import build_timeline_prompt, parse_timeline_narrative
from tts_client import generate_timeline_audio, concat_audio_segments
from video_overlay import create_synced_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_corner_kick(video_path: str = None, scenario_json: dict = None) -> dict:
    """
    端到端处理角球视频。

    Returns:
        {
            "vlm_data": dict,           # VLM 含时间线
            "segments": list[dict],     # LLM 分段叙事
            "full_audio_path": str,     # 合并后的完整音频
            "output_video": str,        # 最终合成视频
            "elapsed": float,
        }
    """
    t0 = time.time()
    result = {}

    # ====== Step 1: VLM 提取时间线 + JSON ======
    if scenario_json:
        vlm_data = scenario_json
    elif video_path:
        logger.info("Step 1: VLM 分析视频 + 提取时间线...")
        vlm_data = analyze_corner_kick(video_path)
    else:
        raise ValueError("需要 video_path 或 scenario_json")

    result["vlm_data"] = vlm_data
    logger.info(f"Step 1 ✓: {len(vlm_data.get('timeline',[]))} 个时间线事件")

    # ====== Step 2: LLM 按时间线分段生成叙事 ======
    logger.info("Step 2: LLM 按时间线分段生成叙事...")
    system_prompt, user_prompt = build_timeline_prompt(vlm_data)

    client = Anthropic(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, timeout=float(API_TIMEOUT))
    response = client.messages.create(
        model=DEEPSEEK_MODEL, max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    llm_output = '\n'.join(b.text for b in response.content if hasattr(b, 'text'))
    segments = parse_timeline_narrative(llm_output)
    result["segments"] = segments
    logger.info(f"Step 2 ✓: {len(segments)} 段叙事")

    # ====== Step 3: TTS 逐段配音 + 记录精确时长 ======
    logger.info("Step 3: TTS 逐段配音 + 精确计时...")
    segments = generate_timeline_audio(segments, str(OUTPUT_DIR))
    result["segments"] = segments

    # 合并为完整音频
    full_audio = str(OUTPUT_DIR / "narration_full.mp3")
    concat_audio_segments(segments, full_audio)
    result["full_audio_path"] = full_audio

    total_audio = sum(s["actual_duration_sec"] for s in segments)
    logger.info(f"Step 3 ✓: {len(segments)} 段音频, 总时长 {total_audio:.1f}s")

    # ====== Step 4: 视频合成 ======
    if video_path:
        logger.info("Step 4: 视频合成 (精准时间轴对齐)...")
        output_video = create_synced_video(video_path, full_audio, segments, "corner_story.mp4")
        result["output_video"] = output_video
        logger.info(f"Step 4 ✓: {output_video}")
    else:
        result["output_video"] = None

    result["elapsed"] = time.time() - t0
    logger.info(f"完成! 总耗时 {result['elapsed']:.1f}s")
    return result
