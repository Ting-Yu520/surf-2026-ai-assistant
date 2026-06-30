"""Agent 2: Tactical data extraction from Phase 1 tool outputs.

Migrated from src/phase_bridge.py. Normalizes TacticAI/SoccerAgent outputs
into the standard TacticalScene format consumed by CommentaryGen.
"""
import hashlib
import json
from pathlib import Path
from typing import Optional

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger

logger = get_logger("tactical_extractor")


class TacticalExtractor(BaseAgent):
    """Extract and normalize tactical data from Phase 1 tool outputs.

    Priority chain:
    1. Real TacticAI predictions (from phase1_batch_output.json)
    2. Sample data (deterministic per corner_entry, for demo fallback)
    """

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/tactical_extractor/config.yaml")

    def run(self, agent_input: AgentInput) -> AgentOutput:
        corner_entry = agent_input.data.get("corner_entry")
        tacticai_json = agent_input.data.get("tacticai_json")

        # Get real data or fall back to sample
        if not tacticai_json and corner_entry:
            tacticai_json = self._get_real_or_sample(corner_entry)

        if not tacticai_json or not tacticai_json.get("predictions"):
            return AgentOutput(
                status="error", data={}, agent_name="tactical_extractor",
                error="No tactical data available",
            )

        predictions = tacticai_json.get("predictions", [])
        phase2 = self._tacticai_to_phase2(tacticai_json)
        formatted = self._format_for_prompt(phase2, corner_entry)
        mapping = self._build_field_mapping(predictions)

        return AgentOutput(
            status="ok",
            data={
                "phase2_input": phase2,
                "formatted": formatted,
                "mapping": mapping,
                "predictions": predictions,
            },
            agent_name="tactical_extractor",
        )

    def validate(self, output: AgentOutput) -> bool:
        return (
            "formatted" in output.data
            and "predictions" in output.data
            and len(output.data["predictions"]) > 0
        )

    # ── Data loading ──

    def _get_real_or_sample(self, corner_entry: dict) -> dict:
        """Try real data first, fall back to deterministic sample."""
        cid = corner_entry.get("id", "")
        if cid:
            real = self._load_real(cid)
            if real:
                logger.info(f"Using real TacticAI data for {cid}")
                return real
        logger.info(f"No real data for {cid}, using sample")
        return self._sample_tacticai_output(corner_entry)

    def _load_real(self, corner_id: str) -> dict | None:
        """Load real TacticAI predictions from Phase 1 batch output."""
        batch_path = self.config.get(
            "batch_output_path", "src/data/phase1_batch_output.json"
        )
        path = Path(batch_path)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except json.JSONDecodeError:
            return None

        for e in entries:
            ce = e.get("corner_entry", {})
            if ce.get("id") == corner_id:
                analysis = e.get("analysis")
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
                    "top_receiver": analysis.get(
                        "tacticai_top_receiver", preds[0]["player_index"]
                    ),
                    "top_probability": analysis.get(
                        "tacticai_top_probability",
                        preds[0].get("receiver_probability", 0),
                    ),
                    "success": True,
                }
        return None

    def _sample_tacticai_output(self, corner_entry: dict) -> dict:
        """Generate deterministic sample TacticAI output from corner entry."""
        eid = corner_entry.get("id", "default")
        seed = int(hashlib.md5(eid.encode()).hexdigest()[:8], 16)
        corner_type = corner_entry.get("corner_type", "in-swinging")

        if "left" in corner_type:
            base_x, base_y = 55, 40
        elif "right" in corner_type:
            base_x, base_y = 65, 40
        else:
            base_x, base_y = 60, 38

        state = seed

        def rng():
            nonlocal state
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            return state / 0x7FFFFFFF

        preds = []
        for i in range(6):
            preds.append({
                "player_index": i,
                "probability": max(0.01, round(rng() * 0.45, 2)),
                "is_attacker": True,
                "position": [
                    round(base_x + rng() * 15 - 5, 1),
                    round(base_y + rng() * 15 - 5, 1),
                ],
            })
        for i in range(6, 12):
            preds.append({
                "player_index": i,
                "probability": max(0.01, round(rng() * 0.08, 2)),
                "is_attacker": False,
                "position": [
                    round(base_x + rng() * 20 - 5, 1),
                    round(base_y + rng() * 20 - 10, 1),
                ],
            })

        preds.sort(key=lambda p: p["probability"], reverse=True)
        return {
            "success": True,
            "predictions": preds,
            "top_receiver": preds[0]["player_index"],
            "top_probability": preds[0]["probability"],
        }

    # ── Data transformation ──

    def _tacticai_to_phase2(self, raw: dict) -> dict:
        preds = raw.get("predictions", [])
        attackers = [p for p in preds if p.get("is_attacker")]
        defenders = [p for p in preds if not p.get("is_attacker")]
        top_a = max(attackers, key=lambda p: p.get("probability", 0)) if attackers else None
        top_d = max(defenders, key=lambda p: p.get("probability", 0)) if defenders else None
        return {
            "scenario": "corner_kick",
            "game_time": "?",
            "score": "? - ?",
            "match_info": "TacticAI Analysis",
            "attacking_players": len(attackers),
            "defending_players": len(defenders),
            "top_receiver_probability": round(top_a["probability"] * 100, 1) if top_a else None,
            "top_receiver_position": top_a["position"] if top_a else [],
            "top_defender_position": top_d["position"] if top_d else [],
        }

    def _format_for_prompt(
        self, phase2: dict, corner_entry: Optional[dict]
    ) -> dict:
        fact_lines, tactic_lines = [], []
        if corner_entry:
            fact_lines.extend([
                f"比赛：{corner_entry.get('match', '?')}",
                f"时间：{corner_entry.get('minute', '?')}'",
                f"进球者：{corner_entry.get('goal_scorer', '?')}",
            ])
            if note := corner_entry.get("tactical_note"):
                fact_lines.append(f"战术描述：{note}")

        tactic_lines.extend([
            f"攻击球员：{phase2.get('attacking_players', '?')}人",
            f"防守球员：{phase2.get('defending_players', '?')}人",
            f"最可能接球概率：{phase2.get('top_receiver_probability', '?')}%",
        ])
        pos = phase2.get("top_receiver_position", [])
        if pos:
            tactic_lines.append(f"最可能接球位置：({pos[0]:.0f}, {pos[1]:.0f})")
        dpos = phase2.get("top_defender_position", [])
        if dpos:
            tactic_lines.append(f"防守方关键位置：({dpos[0]:.0f}, {dpos[1]:.0f})")

        return {"fact_section": "\n".join(fact_lines), "tactic_section": "\n".join(tactic_lines)}

    def _build_field_mapping(self, predictions: list[dict]) -> dict | None:
        """Adaptive coordinate mapping: data → pixel. No hardcoded ranges."""
        if not predictions:
            return None
        xs = [p["position"][0] for p in predictions]
        ys = [p["position"][1] for p in predictions]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        cw = self.config.get("canvas_width", 1280)
        ch = self.config.get("canvas_height", 720)
        FIELD_LEFT, FIELD_RIGHT = 80, int(cw * 0.94)
        FIELD_TOP, FIELD_BOTTOM = 100, int(ch * 0.88)

        x_range = (x_max - x_min) or 1
        y_range = (y_max - y_min) or 1

        return {
            "field_rect": {
                "left": FIELD_LEFT, "right": FIELD_RIGHT,
                "top": FIELD_TOP, "bottom": FIELD_BOTTOM,
            },
            "to_px": lambda x: int(FIELD_LEFT + (x - x_min) / x_range * (FIELD_RIGHT - FIELD_LEFT)),
            "to_py": lambda y: int(FIELD_TOP + (y - y_min) / y_range * (FIELD_BOTTOM - FIELD_TOP)),
        }
