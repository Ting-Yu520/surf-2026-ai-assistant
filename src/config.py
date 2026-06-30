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
# VLM 配置 — 已迁移至 DeepSeek (2026-06-30)
# ⚠️ LEGACY: 这些变量保留用于 src/pipeline.py 向后兼容
# 新代码使用 agents/video_analyzer/config.yaml + core/llm_client.py
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "deepseek-v4-flash")
GEMINI_TIMEOUT = 60

# ============================================================
# LLM 配置 — DeepSeek (Anthropic 兼容端点)
# ⚠️ LEGACY: 新 agent 架构优先使用 agents/*/config.yaml
# 此文件仅供 src/pipeline.py 等旧代码路径使用
# ============================================================
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_TIMEOUT = 60
# max_tokens per model:
#   deepseek-v4-flash: 2048 (no thinking chain)
#   deepseek-v4-pro:   4096 (thinking + output)
# Override via DEEPSEEK_MAX_TOKENS env var
MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "2048"))
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
