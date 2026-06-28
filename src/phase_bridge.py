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


def sample_tacticai_output() -> dict:
    """返回一个模拟的 TacticAI 输出，用于测试 Phase 2 管线。"""
    return {
        "success": True,
        "predictions": [
            {"player_index": i, "probability": p, "is_attacker": a, "position": pos}
            for i, (p, a, pos) in enumerate([
                (0.45, True, (65.0, 40.0)),
                (0.20, True, (60.0, 35.0)),
                (0.08, True, (55.0, 30.0)),
                (0.03, True, (70.0, 45.0)),
                (0.02, True, (58.0, 28.0)),
                (0.01, True, (62.0, 42.0)),
                (0.06, False, (68.0, 38.0)),
                (0.05, False, (55.0, 50.0)),
                (0.04, False, (72.0, 42.0)),
                (0.03, False, (60.0, 55.0)),
                (0.02, False, (65.0, 48.0)),
                (0.01, False, (50.0, 45.0)),
            ])
        ],
        "top_receiver": 0,
        "top_probability": 0.45,
    }


def format_for_prompt(phase2_input: dict, corner_entry: Optional[dict] = None) -> str:
    """
    将 Phase 2 输入格式化为 Prompt 可读的文本。

    作为底层描述文本输入给二人转 Prompt。
    """
    lines = []
    if corner_entry:
        match = corner_entry.get("match", "?")
        minute = corner_entry.get("minute", "?")
        scorer = corner_entry.get("goal_scorer", "?")
        note = corner_entry.get("tactical_note", "")
        lines.append(f"比赛：{match}")
        lines.append(f"时间：{minute}'")
        lines.append(f"进球者：{scorer}")
        if note:
            lines.append(f"战术描述：{note}")

    lines.append(f"\n攻击球员：{phase2_input.get('attacking_players', '?')}人")
    lines.append(f"防守球员：{phase2_input.get('defending_players', '?')}人")
    lines.append(f"最可能接球概率：{phase2_input.get('top_receiver_probability', '?')}%")

    return "\n".join(lines)
