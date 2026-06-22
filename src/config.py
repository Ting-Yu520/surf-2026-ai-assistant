"""
SURF-2026-0154 全局配置

管理 LLM 端点、模型选择、和场景数据加载。
所有硬编码集中在此文件，方便 Phase 2 替换为真实 API 配置。
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（项目根目录）
load_dotenv(Path(__file__).parent.parent / ".env")

# ============================================================
# LLM 配置
# ============================================================

# DeepSeek OpenAI 兼容端点
DEEPSEEK_BASE_URL = os.getenv(
    "DEEPSEEK_BASE_URL",
    "https://api.deepseek.com/v1"
)

# 模型名称：deepseek-chat (V3) 或 deepseek-reasoner (R1)
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# API Key 优先级：环境变量 > .env 文件
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# API 调用超时（秒）
API_TIMEOUT = 60

# 最大 Token 数（留给 LLM 回复的空间）
MAX_TOKENS = 1024

# 生成温度（0.7 = 有创意但不离谱）
TEMPERATURE = 0.7


# ============================================================
# 场景数据
# ============================================================

def load_scenarios() -> dict:
    """
    从 scenarios.json 加载所有战术场景。

    Returns:
        dict: {场景名称: 场景JSON数据}

    如果文件不存在或格式错误，返回内置的默认场景。
    """
    scenarios_path = Path(__file__).parent / "data" / "scenarios.json"

    if scenarios_path.exists():
        try:
            with open(scenarios_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 转换为 {名称: 数据} 的字典格式
            if isinstance(data, list):
                return {s["scenario"]: s for s in data}
            elif isinstance(data, dict):
                return data
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️ 场景文件解析失败: {e}，使用默认场景")

    # 内置默认场景（兜底）
    return _get_default_scenarios()


def _get_default_scenarios() -> dict:
    """内置默认场景——即使 scenarios.json 丢失也能运行 Demo。"""
    return {
        "The Impossible Pass": {
            "scenario": "Through pass in the final third",
            "game_time": "88:42",
            "score": "Team A 0 - 0 Team B",
            "attacking_player": {"role": "Playmaker", "x": 65, "y": 40},
            "defenders_in_path": 3,
            "passing_lane_width_meters": 0.8,
            "predicted_success_rate": "5.2%",
            "actual_outcome": "Successful pass, leading to a goal."
        }
    }
