"""
Phase 1 → Phase 2 桥接模块

将 Phase 1 工具（TacticAI Recreation / SoccerAgent）的输出格式，
转换为 Phase 2（二人转 Prompt）的输入格式。

当前支持：
- TacticAI Recreation JSON 格式
- 手动构造角球数据
"""

import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "src" / "data"


def tacticai_to_phase2(tacticai_json: dict) -> dict:
    """
    将 TacticAI Recreation 的 PredictResponse 输出
    转换为 Phase 2 的输入格式。

    TacticAI 输出格式:
    {
        "success": true,
        "predictions": [
            {"player_index": 0, "probability": 0.45, "is_attacker": true, "position": [65.0, 40.0]},
            ...
        ],
        "top_receiver": 0,
        "top_probability": 0.45
    }
    """
    predictions = tacticai_json.get("predictions", [])
    attackers = [p for p in predictions if p.get("is_attacker")]
    defenders = [p for p in predictions if not p.get("is_attacker")]

    top_attacker = max(attackers, key=lambda p: p.get("probability", 0)) if attackers else None
    top_defender = max(defenders, key=lambda p: p.get("probability", 0)) if defenders else None

    return {
        "scenario": "corner_kick",
        "game_time": "?",
        "score": "? - ?",
        "match_info": "TacticAI Analysis",
        "attacking_players": len(attackers),
        "defending_players": len(defenders),
        "top_receiver_probability": round(top_attacker["probability"] * 100, 1) if top_attacker else "?",
        "top_receiver_position": top_attacker["position"] if top_attacker else [],
        "top_defender_position": top_defender["position"] if top_defender else [],
    }


def sample_tacticai_output(corner_entry: Optional[dict] = None) -> dict:
    """
    返回一个依 entry 特征变化的模拟 TacticAI 输出。
    虽然仍是模拟数据，但至少每个角球场景不同。
    """
    import hashlib

    # 用 entry_id 做种子，保证同一场景始终一致
    eid = corner_entry.get("id", "default") if corner_entry else "default"
    seed = int(hashlib.md5(eid.encode()).hexdigest()[:8], 16)

    # 根据 corner_type 调整球员分布
    corner_type = (corner_entry or {}).get("corner_type", "in-swinging")

    # 进攻球员位置偏移
    if "left" in corner_type:
        base_x, base_y = 55, 40  # 左侧角球，进攻偏左
    elif "right" in corner_type:
        base_x, base_y = 65, 40  # 右侧角球，进攻偏右
    else:
        base_x, base_y = 60, 38

    rng = _RNG(seed)
    predictions = []
    # 6 个进攻球员
    for i in range(6):
        prob = max(0.01, round(rng() * 0.45, 2))
        predictions.append({
            "player_index": i,
            "probability": prob,
            "is_attacker": True,
            "position": [
                round(base_x + rng() * 15 - 5, 1),
                round(base_y + rng() * 15 - 5, 1),
            ],
        })
    # 6 个防守球员
    for i in range(6, 12):
        prob = max(0.01, round(rng() * 0.08, 2))
        predictions.append({
            "player_index": i,
            "probability": prob,
            "is_attacker": False,
            "position": [
                round(base_x + rng() * 20 - 5, 1),
                round(base_y + rng() * 20 - 10, 1),
            ],
        })

    # 人概率降序
    predictions.sort(key=lambda p: p["probability"], reverse=True)
    top = predictions[0]

    return {
        "success": True,
        "predictions": predictions,
        "top_receiver": top["player_index"],
        "top_probability": top["probability"],
    }


class _RNG:
    """简易确定性伪随机数生成器"""
    def __init__(self, seed: int):
        self.state = seed
    def __call__(self) -> float:
        self.state = (self.state * 1103515245 + 12345) & 0x7fffffff
        return self.state / 0x7fffffff


BATCH_OUTPUT_PATH = DATA_DIR / "phase1_batch_output.json"

_batch_cache = None


def load_batch_output() -> dict:
    """加载 Phase 1 批量推理输出，建立 corner_id → entry 索引（缓存结果，仅首次读取文件）"""
    global _batch_cache
    if _batch_cache is not None:
        return _batch_cache
    if not BATCH_OUTPUT_PATH.exists():
        _batch_cache = {}
        return {}
    try:
        with open(BATCH_OUTPUT_PATH, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except json.JSONDecodeError:
        _batch_cache = {}
        return {}
    _batch_cache = {
        e.get("corner_entry", {}).get("id"): e
        for e in entries
        if e.get("corner_entry", {}).get("id")
    }
    return _batch_cache


def get_real_predictions(corner_id: str) -> dict | None:
    """从 Phase 1 批量输出获取真实 TacticAI 预测。

    Returns:
        None 如果该 corner_id 没有真实数据（调用方应降级）
    """
    batch = load_batch_output()
    entry = batch.get(corner_id)
    if not entry:
        return None

    analysis = entry.get("analysis")
    if not analysis:
        return None
    preds = analysis.get("tacticai_predictions", [])
    if not preds:
        return None

    return {
        "predictions": [
            {
                "player_index": p["player_index"],
                "probability": p.get("receiver_probability", p.get("probability", 0)),
                "is_attacker": p.get("is_attacker", True),
                "position": p["position"],
                "role": p.get("role", ""),
            }
            for p in preds
        ],
        "top_receiver": analysis.get("tacticai_top_receiver", preds[0]["player_index"]),
        "top_probability": analysis.get("tacticai_top_probability", preds[0].get("receiver_probability", 0)),
        "success": True,
    }


def get_real_or_sample(corner_entry: dict | None = None) -> dict:
    """优先返回真实 TacticAI 数据，无真实数据时降级为模拟数据。

    设计原则：数据必须真实不能编造。sample_tacticai_output 仅作
    demo 无 Phase 1 输出时的临时回退。
    """
    if corner_entry and (cid := corner_entry.get("id")):
        real = get_real_predictions(cid)
        if real:
            return real
    return sample_tacticai_output(corner_entry)


def build_field_mapping(predictions: list[dict], canvas_width: int = 1280, canvas_height: int = 720):
    """根据真实球员坐标范围，自适应计算球场→画面映射函数。

    无硬编码。画面布局常量仅定义绘制区域的边界（UI 设计参数），
    坐标映射完全由数据范围驱动。
    """
    if not predictions:
        return None
    xs = [p["position"][0] for p in predictions]
    ys = [p["position"][1] for p in predictions]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    # 画面上的球场绘制区域 — 这是 UI 布局常量，不是数据常量
    FIELD_LEFT, FIELD_RIGHT = 600, int(canvas_width * 0.92)
    FIELD_TOP, FIELD_BOTTOM = 140, int(canvas_height * 0.86)

    x_range = (x_max - x_min) or 1
    y_range = (y_max - y_min) or 1

    def to_px(x: float) -> int:
        return int(FIELD_LEFT + (x - x_min) / x_range * (FIELD_RIGHT - FIELD_LEFT))

    def to_py(y: float) -> int:
        return int(FIELD_TOP + (y - y_min) / y_range * (FIELD_BOTTOM - FIELD_TOP))

    return {
        "field_rect": {"left": FIELD_LEFT, "right": FIELD_RIGHT, "top": FIELD_TOP, "bottom": FIELD_BOTTOM},
        "to_px": to_px,
        "to_py": to_py,
    }


def format_for_prompt(phase2_input: dict, corner_entry: Optional[dict] = None) -> dict:
    """
    返回两段式结构：
      fact_section: 比赛事实 + 战术描述
      tactic_section: TacticAI 彩蛋数据（可选引用）
    """
    fact_lines = []
    if corner_entry:
        match = corner_entry.get("match", "?")
        minute = corner_entry.get("minute", "?")
        scorer = corner_entry.get("goal_scorer", "?")
        note = corner_entry.get("tactical_note", "")
        fact_lines.append(f"比赛：{match}")
        fact_lines.append(f"时间：{minute}'")
        fact_lines.append(f"进球者：{scorer}")
        if note:
            fact_lines.append(f"战术描述：{note}")

    tactic_lines = []
    att = phase2_input.get("attacking_players", "?")
    deff = phase2_input.get("defending_players", "?")
    prob = phase2_input.get("top_receiver_probability", "?")
    tactic_lines.append(f"攻击球员：{att}人")
    tactic_lines.append(f"防守球员：{deff}人")
    tactic_lines.append(f"最可能接球概率：{prob}%")
    pos = phase2_input.get("top_receiver_position", [])
    if pos:
        tactic_lines.append(f"最可能接球位置：({pos[0]:.0f}, {pos[1]:.0f})")
    dpos = phase2_input.get("top_defender_position", [])
    if dpos:
        tactic_lines.append(f"防守方关键位置：({dpos[0]:.0f}, {dpos[1]:.0f})")

    return {
        "fact_section": "\n".join(fact_lines),
        "tactic_section": "\n".join(tactic_lines),
    }
