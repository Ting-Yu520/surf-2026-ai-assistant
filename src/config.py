"""
SURF-2026-0154 全局配置

管理 VLM、LLM、TTS、视频输出全部配置。
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ============================================================
# VLM 配置 — Gemini 1.5 Flash (免费)
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT = 120

# ============================================================
# LLM 配置 — DeepSeek V4 Pro (文本生成)
# ============================================================
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_TIMEOUT = 60
MAX_TOKENS = 2048
TEMPERATURE = 0.7

# ============================================================
# TTS 配置 — Edge TTS (免费)
# ============================================================
TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")  # 中文女声，自然
TTS_SPEED = os.getenv("TTS_SPEED", "+10%")  # 稍快，保持节奏感

# ============================================================
# 视频输出配置
# ============================================================
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================
# 场景数据 (保留兼容旧的 text-only demo)
# ============================================================
def load_scenarios() -> dict:
    scenarios_path = Path(__file__).parent / "data" / "scenarios.json"
    if scenarios_path.exists():
        try:
            with open(scenarios_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return {s.get("scenario", s.get("match","?")): s for s in data}
            return data
        except (json.JSONDecodeError, KeyError):
            pass
    return {}
