"""
VLM 客户端 — Gemini 视频分析

功能：从角球视频中提取结构化战术数据 + 事件时间线
"""

import json
import time
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT

TIMELINE_PROMPT = """Analyze this corner kick video from the 2026 FIFA World Cup.

Your task: extract BOTH the tactical data AND a precise event timeline.

## Output Schema (JSON only, no extra text):

{
  "scenario": "corner_kick",
  "match_context": {
    "teams": "Team A vs Team B",
    "score_at_time": "score before this corner",
    "minute": "match minute",
    "tournament": "2026 FIFA World Cup"
  },
  "corner_setup": {
    "corner_side": "left or right",
    "players_in_box": {"attacking": N, "defending": N},
    "kick_taker_foot": "left or right",
    "formation_visible": "describe defensive setup"
  },
  "timeline": [
    {
      "start_sec": 0,
      "end_sec": 3,
      "phase": "setup",
      "visual_description": "What is visible on screen: players positioning, referee placing ball, kicker preparing"
    },
    {
      "start_sec": 3,
      "end_sec": 6,
      "phase": "delivery",
      "visual_description": "The kick: ball trajectory, where it's heading, first contact"
    },
    {
      "start_sec": 6,
      "end_sec": 12,
      "phase": "action",
      "visual_description": "What happens with the ball: header, deflection, scramble, shot"
    },
    {
      "start_sec": 12,
      "end_sec": 18,
      "phase": "outcome",
      "visual_description": "Result: goal celebration, save, clearance. Player reactions."
    }
  ],
  "tactical_analysis": {
    "key_moment": "what made this corner special",
    "defensive_error": "what went wrong for defenders",
    "attacking_success": "what the attackers did right"
  }
}

IMPORTANT:
- Use approximate timestamps (seconds from video start)
- Each timeline entry should describe what is VISIBLY happening on screen at that moment
- Keep visual_descriptions concise (1-2 sentences)
- Output ONLY valid JSON, no markdown code blocks, no extra text
"""


def analyze_corner_kick(video_path: str) -> dict:
    """使用 Gemini 分析角球视频，返回含时间线的结构化 JSON。"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 未设置。")

    client = genai.Client(api_key=GEMINI_API_KEY)

    video_file = client.files.upload(file=video_path, config=types.UploadFileConfig())
    while video_file.state == types.FileState.PROCESSING:
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)

    if video_file.state == types.FileState.FAILED:
        raise RuntimeError(f"视频处理失败: {video_file.error}")

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Content(role="user", parts=[
                    types.Part.from_uri(file_uri=video_file.uri, mime_type="video/mp4"),
                    types.Part(text=TIMELINE_PROMPT)
                ])
            ],
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=4096)
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"): raw = raw[4:]
        return json.loads(raw)

    except json.JSONDecodeError as e:
        raise RuntimeError(f"VLM 返回无效 JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"VLM 调用失败: {e}")


def analyze_corner_kick_from_frame(image_path: str) -> dict:
    """从单张关键帧图片分析角球场景。"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 未设置。")

    import PIL.Image
    client = genai.Client(api_key=GEMINI_API_KEY)
    img = PIL.Image.open(image_path)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[TIMELINE_PROMPT, img],
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=4096)
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"): raw = raw[4:]
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"VLM 返回无效 JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"VLM 调用失败: {e}")
