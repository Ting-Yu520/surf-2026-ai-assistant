"""
端到端流水线 — SURF-2026 核心流程

流程：角球视频 → VLM 提取 JSON → LLM 生成通俗叙事 → TTS 配音 → 视频合成

使用方法：
    from pipeline import process_corner_kick
    result = process_corner_kick("corner.mp4")
    print(result["output_video"])  # 最终视频路径
"""

import time
import json
import logging
from pathlib import Path
from anthropic import Anthropic

from config import (
    DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_API_KEY,
    API_TIMEOUT, MAX_TOKENS, TEMPERATURE, OUTPUT_DIR,
)
from vlm_client import analyze_corner_kick, analyze_corner_kick_from_frame
from prompts.corner_kick import CORNER_KICK_SYSTEM_PROMPT, build_corner_kick_prompt
from tts_client import generate_audio
from video_overlay import create_narrated_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_corner_kick(
    video_path: str = None,
    image_path: str = None,
    scenario_json: dict = None,
) -> dict:
    """
    端到端处理一个角球场景。

    输入至少提供一种：
    - video_path: 角球视频
    - image_path: 角球关键帧
    - scenario_json: 手工编写的 JSON (跳过 VLM 步骤)

    Returns:
        {
            "json_data": dict,          # VLM 提取或手工的 JSON
            "narration_text": str,      # LLM 生成的通俗叙事
            "audio_path": str,          # TTS 音频文件路径
            "output_video": str,        # 最终合成视频路径
            "elapsed": float,           # 总耗时
        }
    """
    t0 = time.time()
    result = {}

    # ====== Step 1: 获取 JSON 数据 ======
    if scenario_json:
        json_data = scenario_json
        logger.info("Step 1: 使用手工提供的 JSON")
    elif video_path:
        logger.info(f"Step 1: VLM 分析视频 → {video_path}")
        json_data = analyze_corner_kick(video_path)
    elif image_path:
        logger.info(f"Step 1: VLM 分析关键帧 → {image_path}")
        json_data = analyze_corner_kick_from_frame(image_path)
    else:
        raise ValueError("必须提供 video_path、image_path 或 scenario_json 之一")

    result["json_data"] = json_data
    logger.info(f"Step 1 ✓: JSON 提取完成 ({len(json.dumps(json_data))} chars)")

    # ====== Step 2: LLM 生成通俗叙事 ======
    logger.info("Step 2: LLM 生成叙事...")
    system_prompt, user_prompt = build_corner_kick_prompt(json_data)

    client = Anthropic(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=float(API_TIMEOUT),
    )
    response = client.messages.create(
        model=DEEPSEEK_MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    narration_text = '\n\n'.join(
        b.text for b in response.content if hasattr(b, 'text')
    )
    result["narration_text"] = narration_text
    logger.info(f"Step 2 ✓: 叙事生成完成 ({len(narration_text)} chars)")

    # ====== Step 3: TTS 配音 ======
    logger.info("Step 3: TTS 配音...")
    audio_path = str(OUTPUT_DIR / "narration.mp3")
    generate_audio(narration_text, audio_path)
    result["audio_path"] = audio_path
    logger.info(f"Step 3 ✓: 音频生成完成 → {audio_path}")

    # ====== Step 4: 视频合成 ======
    output_video = str(OUTPUT_DIR / "corner_story.mp4")

    if video_path:
        logger.info("Step 4: 视频合成 (原视频 + 配音 + 字幕)...")
        create_narrated_video(video_path, audio_path, narration_text, "corner_story.mp4")
        result["output_video"] = output_video
        logger.info(f"Step 4 ✓: 视频合成完成 → {output_video}")
    else:
        logger.info("Step 4: 跳过 (无原视频，仅输出音频)")
        result["output_video"] = None

    result["elapsed"] = time.time() - t0
    logger.info(f"全部完成，总耗时 {result['elapsed']:.1f}s")

    return result
