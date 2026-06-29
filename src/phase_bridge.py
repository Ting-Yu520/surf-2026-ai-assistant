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
