"""
VLM 客户端 — Gemini 1.5 Flash

功能：从角球视频关键帧中提取结构化战术数据 (JSON)。
设计原则：输出 Schema 固定，确保 LLM 下游 Prompt 的一致性。

使用方法：
    from vlm_client import analyze_corner_kick
    json_data = analyze_corner_kick("path/to/corner.mp4")
"""

import json
import time
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT

# ============================================================
# 角球 JSON Schema — VLM 必须遵守的输出格式
# ============================================================
CORNER_KICK_SCHEMA = """
{
  "scenario": "corner_kick",
  "match_context": {
    "teams": "",
    "score_at_time": "",
    "minute": "",
    "tournament": "2026 FIFA World Cup"
  },
  "corner_setup": {
    "corner_side": "left / right",
    "kick_taker_position": {"x": 0-100, "y": 0-100},
    "kick_taker_foot": "left / right",
    "players_in_box": { "attacking": int, "defending": int },
    "formation_visible": "e.g. zonal marking, man-to-man, mixed"
  },
  "key_action": {
    "type": "in-swing / out-swing / short_corner / near_post / far_post / direct_shot",
    "trajectory_description": "describe ball path",
    "receiving_player_position": {"x": 0-100, "y": 0-100},
    "defenders_near_ball": int,
    "shot_attempt": true/false,
    "goal_scored": true/false
  },
  "tactical_analysis": {
    "defensive_vulnerability": "describe the gap or error",
    "attacking_creativity": "describe what made this corner special",
    "difficulty_score_1_to_10": int,
    "why_difficult": "numbers / positioning / timing"
  }
}
"""

VLM_PROMPT = """Analyze this corner kick video frame(s) from a 2026 FIFA World Cup match.

Your task: extract structured tactical data in JSON format.

Focus on:
1. How many players are in the penalty box? How are they positioned?
2. What type of corner is it? (in-swinging, out-swinging, short corner, near post, far post, direct shot)
3. Where does the ball go? Who receives it?
4. What is the defensive setup? Is there a gap the attacking team exploited?
5. Was a shot attempted? Was a goal scored?
6. Rate the difficulty of this corner kick action (1-10) and explain why.

IMPORTANT:
- Use approximate coordinates (x,y from 0-100%)
- If you can't determine something, mark it as "unclear" rather than guessing
- Output ONLY the JSON, no extra text

Return JSON following this schema:
""" + CORNER_KICK_SCHEMA


def analyze_corner_kick(video_path: str) -> dict:
    """
    使用 Gemini 1.5 Flash 分析角球视频，返回结构化 JSON。

    Args:
        video_path: 角球视频文件路径（支持 mp4, mov, avi）

    Returns:
        dict: 结构化角球战术数据

    Raises:
        ValueError: API Key 未配置
        RuntimeError: VLM 调用失败
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 未设置。请在 .env 中添加 GEMINI_API_KEY=your-key")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # 上传视频
    video_file = client.files.upload(
        file=video_path,
        config=types.UploadFileConfig()
    )

    # 等待视频处理完成
    while video_file.state == types.FileState.PROCESSING:
        time.sleep(2)
        video_file = client.files.get(name=video_file.name)

    if video_file.state == types.FileState.FAILED:
        raise RuntimeError(f"视频处理失败: {video_file.error}")

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_uri(
                            file_uri=video_file.uri,
                            mime_type=video_file.mime_type or "video/mp4"
                        ),
                        types.Part(text=VLM_PROMPT)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,  # 低温度 = 更准确的结构化输出
                max_output_tokens=2048,
            )
        )

        raw_text = response.text.strip()

        # 清理可能的 markdown 代码块包裹
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        return json.loads(raw_text)

    except json.JSONDecodeError as e:
        raise RuntimeError(f"VLM 返回内容无法解析为 JSON: {e}\n\n返回文本:\n{raw_text[:500]}")
    except Exception as e:
        raise RuntimeError(f"VLM 调用失败: {e}")


def analyze_corner_kick_from_frame(image_path: str) -> dict:
    """
    从单张关键帧图片（而非视频）分析角球场景。
    用于没有完整视频时，用手动截取的关键帧。

    Args:
        image_path: 关键帧图片路径

    Returns:
        dict: 结构化角球战术数据
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 未设置。")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # 读取图片
    import PIL.Image
    img = PIL.Image.open(image_path)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[VLM_PROMPT, img],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2048,
            )
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        return json.loads(raw_text)

    except json.JSONDecodeError as e:
        raise RuntimeError(f"VLM 返回内容无法解析为 JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"VLM 调用失败: {e}")
