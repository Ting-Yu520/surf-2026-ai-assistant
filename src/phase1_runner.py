"""
Phase 1 统一推理器 — 将 TacticAI、SoccerAgent、MatchTime 的输出转为 Phase 2 格式。

已就绪:  TacticAI (GNN 推理) + SoccerAgent (LLM 上下文)
预留接口: MatchTime (单人 AI 解说, 需 >16GB VRAM)

用法:
  source /mnt/d/ClaudeWorkspace/phase1/venv/bin/activate
  cd /mnt/d/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant

  # 单个角球: TacticAI + SoccerAgent
  python3 src/phase1_runner.py --source both --entry-id wc2026-corner-021

  # 批量: 所有 21 个角球
  python3 src/phase1_runner.py --source both --output src/data/phase1_output.json

架构:
  TacticAI (GNN)    ──→ 接球概率/球员位置 ──┐
  SoccerAgent (LLM) ──→ 比赛上下文/球员背景 ──┤
  MatchTime  (预留) ──→ AI 单人解说 ─────────┤
                                              ├──→ Phase 2 pipeline.py → 🎬
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field, asdict

ROOT = Path(__file__).parent.parent  # surf-2026-ai-tactical-assistant 根目录

# ============================================================
# 标准化 Phase 1 输出 Schema
# ============================================================

@dataclass
class PlayerOutput:
    player_index: int
    position: List[float]  # [x, y] in meters
    is_attacker: bool
    receiver_probability: float
    role: str = "unknown"  # GK/DEF/MID/FWD

@dataclass
class CornerAnalysisOutput:
    """单个角球的完整分析结果 — Phase 1 标准输出格式"""
    corner_id: str
    match: str = ""
    date: str = ""
    minute: str = ""
    score_at_time: str = ""
    corner_type: str = ""
    kick_taker: str = ""
    goal_scorer: str = ""
    goal_type: str = ""
    result: str = ""
    tactical_note: str = ""
    # TacticAI 预测
    tacticai_predictions: List[PlayerOutput] = field(default_factory=list)
    tacticai_top_receiver: int = -1
    tacticai_top_probability: float = 0.0
    # 优化建议
    optimization_possible: bool = False
    optimized_probability: float = 0.0
    # SoccerAgent 元数据（如果有）
    recognized_players: List[Dict] = field(default_factory=list)
    game_context: Dict = field(default_factory=dict)
    commentary_snippet: str = ""


def convert_to_phase2_format(analysis: CornerAnalysisOutput, corner_entry: Optional[dict] = None) -> dict:
    """
    将 Phase 1 标准输出转换为 Phase 2 pipeline.py 所需格式。

    与 phase_bridge.py 的 tacticai_to_phase2() + format_for_prompt() 对齐。
    """
    from phase_bridge import format_for_prompt

    # 构建 TacticAI 格式（兼容现有 phase_bridge）
    tacticai_json = {
        "success": True,
        "predictions": [
            {
                "player_index": p.player_index,
                "probability": p.receiver_probability,
                "is_attacker": p.is_attacker,
                "position": p.position,
            }
            for p in analysis.tacticai_predictions
        ],
        "top_receiver": analysis.tacticai_top_receiver,
        "top_probability": analysis.tacticai_top_probability,
    }

    from phase_bridge import tacticai_to_phase2
    phase2_input = tacticai_to_phase2(tacticai_json)

    # 如果有比赛元数据，填入
    if corner_entry:
        phase2_input["match_info"] = corner_entry.get("match", "")
        phase2_input["game_time"] = corner_entry.get("minute", "?")
        phase2_input["score"] = corner_entry.get("score_at_time", "? - ?")

    return format_for_prompt(phase2_input, corner_entry)


# ============================================================
# TacticAI 推理器
# ============================================================

class TacticAIInference:
    """直接加载训练好的 TacticAI 模型进行推理（不通过 API）"""

    def __init__(self, checkpoint_path: str = None, device: str = None):
        import torch

        # 自动选择 checkpoint
        if checkpoint_path is None:
            candidates = [
                "models/checkpoints/best_model.pth",
                "/mnt/d/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant/phase1/tools/tactic-ai-recreation/models/checkpoints/best_model.pth",
            ]
            for c in candidates:
                if Path(c).exists():
                    checkpoint_path = c
                    break
            else:
                raise FileNotFoundError(f"No checkpoint found. Tried: {candidates}")

        # 设备选择
        if device is None:
            if torch.cuda.is_available():
                device = 'cuda'
            elif torch.backends.mps.is_available():
                device = 'mps'
            else:
                device = 'cpu'

        print(f"[TacticAI] Loading checkpoint: {checkpoint_path}")
        print(f"[TacticAI] Device: {device}")

        # 动态导入（避免与 SURF 项目 data/models 包冲突，用 importlib 直接加载）
        import importlib.util

        project_root = Path(checkpoint_path).resolve().parent.parent.parent
        src_dir = str(project_root / "src")
        print(f"[TacticAI] src dir: {src_dir}")

        # 直接用文件路径加载模块
        def _load_module(module_name, file_path):
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod  # 注册到 sys.modules 以防循环导入
            spec.loader.exec_module(mod)
            return mod

        _load_module("tacticai_models_gnn", os.path.join(src_dir, "models", "gnn.py"))
        get_model = sys.modules["tacticai_models_gnn"].get_model

        _load_module("tacticai_data_processor", os.path.join(src_dir, "data", "processor.py"))
        CornerKickProcessor = sys.modules["tacticai_data_processor"].CornerKickProcessor

        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
        config = checkpoint.get('config', {
            'model_type': 'gat',
            'node_features': 14,
            'hidden_dim': 128,
            'num_layers': 4,
            'dropout': 0.2,
            'distance_threshold': 5.0,
            'use_enhanced_features': True,
            'use_role_features': True,
            'use_positional_context': True,
        })

        # 构建模型
        model = get_model(
            config.get('model_type', 'gat'),
            node_features=config.get('node_features', 14),
            hidden_dim=config.get('hidden_dim', 128),
            num_layers=config.get('num_layers', 4),
            dropout=config.get('dropout', 0.2),
        )
        state_key = 'model_state_dict' if 'model_state_dict' in checkpoint else None
        model.load_state_dict(checkpoint[state_key] if state_key else checkpoint)
        model.to(device)
        model.eval()

        # 构建数据处理器
        processor = CornerKickProcessor(
            distance_threshold=config.get('distance_threshold', 5.0),
            normalize_positions=True,
            use_enhanced_features=config.get('use_enhanced_features', True),
            use_role_features=config.get('use_role_features', True),
            use_positional_context=config.get('use_positional_context', True),
        )

        self.model = model
        self.processor = processor
        self.config = config
        self.device = device
        self._torch = torch
        self._F = torch.nn.functional

        print(f"[TacticAI] Model loaded: {config.get('model_type')}, "
              f"{sum(p.numel() for p in model.parameters()):,} params")

    def predict(self, graph) -> List[PlayerOutput]:
        """对单个图进行预测，返回所有球员的概率"""

        graph = graph.to(self.device)
        with self._torch.no_grad():
            batch = self._torch.zeros(graph.num_nodes, dtype=self._torch.long, device=self.device)
            edge_attr = graph.edge_attr if hasattr(graph, 'edge_attr') else None
            logits = self.model(graph.x, graph.edge_index, batch, edge_attr=edge_attr)
            if isinstance(logits, dict):
                logits = logits['receiver']
            probs = self._F.softmax(logits, dim=0)

        results = []
        for i in range(graph.num_nodes):
            x_pos = graph.x[i, 0].item() * 120  # 反归一化
            y_pos = graph.x[i, 1].item() * 80
            # x[:, 2] 是 team 特征: >0.5 = attacker
            is_attacker = graph.x[i, 2].item() > 0.5

            # 推断角色（x[:, 7:11] 是 one-hot GK/DEF/MID/FWD）
            role = "unknown"
            if hasattr(graph, 'x') and graph.x.shape[1] >= 11:
                role_ids = ["GK", "DEF", "MID", "FWD"]
                role_probs = graph.x[i, 7:11].cpu().numpy()
                if role_probs.max() > 0.1:
                    role = role_ids[int(role_probs.argmax())]

            results.append(PlayerOutput(
                player_index=i,
                position=[round(x_pos, 1), round(y_pos, 1)],
                is_attacker=bool(is_attacker),
                receiver_probability=round(probs[i].item(), 4),
                role=role,
            ))

        # 按概率降序
        results.sort(key=lambda p: p.receiver_probability, reverse=True)
        return results

    def analyze_dataset(self, corner_entries: List[dict]) -> List[CornerAnalysisOutput]:
        """
        对 Phase 2 角球数据集进行 TacticAI 推理。
        每个 corner_entry 由 predict_from_corner_entry 单独处理（因为 Phase 2
        数据集没有 freeze frame 数据，需要从 entry 元数据构建模拟场景）。
        """
        results = []
        for entry in corner_entries:
            analysis = self.predict_from_corner_entry(entry)
            if analysis:
                results.append(analysis)
                print(f"   ✅ {analysis.corner_id}: top_prob={analysis.tacticai_top_probability:.3f} "
                      f"({len(analysis.tacticai_predictions)} players)")
        return results

    def predict_from_corner_entry(self, entry: dict) -> Optional[CornerAnalysisOutput]:
        """从单个 corner_entry（Phase 2 数据集格式）进行预测"""
        import pandas as pd
        import numpy as np

        # 尝试用 entry 中的 tactical_note 和已知位置构建简单场景
        # 如果 entry 有实际位置信息就用它，否则用默认布局
        if "player_positions" in entry:
            # entry 自带位置
            players_data = entry["player_positions"]
        else:
            # 用 entry 特征构建合理的默认角球场景
            corner_type = entry.get("corner_type", "in-swinging")
            if "left" in corner_type:
                corner_x, corner_y = 0.0, 40.0
            elif "right" in corner_type:
                corner_x, corner_y = 120.0, 40.0
            else:
                corner_x, corner_y = 120.0, 0.0

            # 构建默认球员布局（6 攻击 + 11 防守，角球典型分布）
            rng = np.random.RandomState(hash(entry.get("id", "default")) % 2**31)
            players_data = []
            # 进攻球员（集中在禁区）
            for _ in range(6):
                players_data.append({
                    "x": float(60 + rng.randn() * 10),
                    "y": float(40 + rng.randn() * 8),
                    "is_teammate": True,
                    "position_role": rng.choice(["FWD", "MID", "MID"]),
                })
            # 防守球员
            for _ in range(11):
                players_data.append({
                    "x": float(55 + rng.randn() * 12),
                    "y": float(40 + rng.randn() * 10),
                    "is_teammate": False,
                    "position_role": rng.choice(["DEF", "DEF", "MID", "GK"]),
                })

        # 构建 freeze frame
        freeze_frame = []
        for p in players_data:
            pos_id = {"GK": 1, "DEF": 4, "MID": 10, "FWD": 23}.get(
                p.get("position_role", "MID"), 10
            )
            freeze_frame.append({
                "location": [p["x"], p["y"]],
                "teammate": p["is_teammate"],
                "position": {"id": pos_id},
            })

        # 用 processor 构建图
        import pandas as pd
        row = pd.Series({
            "freeze_frame_parsed": freeze_frame,
            "corner_pass_end_location": [corner_x, corner_y],
            "location": [corner_x, corner_y],
        })
        graph = self.processor.corner_to_graph(row)

        # 预测
        predictions = self.predict(graph)

        return CornerAnalysisOutput(
            corner_id=entry.get("id", "unknown"),
            match=entry.get("match", ""),
            date=entry.get("date", ""),
            minute=entry.get("minute", ""),
            score_at_time=entry.get("score_at_time", ""),
            corner_type=entry.get("corner_type", ""),
            kick_taker=entry.get("kick_taker", ""),
            goal_scorer=entry.get("goal_scorer", ""),
            goal_type=entry.get("goal_type", ""),
            result=entry.get("result", ""),
            tactical_note=entry.get("tactical_note", ""),
            tacticai_predictions=predictions,
            tacticai_top_receiver=predictions[0].player_index if predictions else -1,
            tacticai_top_probability=predictions[0].receiver_probability if predictions else 0.0,
        )


# ============================================================
# SoccerAgent 增强接入
# ============================================================

class SoccerAgentBridge:
    """
    SoccerAgent 桥接 — 调用 phase1_socceragent 的增强能力。
    利用 DeepSeek API + game_database.csv 提取丰富的比赛上下文。
    """

    def __init__(self, codebase_path: str = None):
        if codebase_path is None:
            codebase_path = str(
                Path(__file__).parent.parent / "phase1" / "tools" / "soccer-agent"
            )
        self.codebase_path = Path(codebase_path)
        self._enhanced = None

    def _get_enhanced(self):
        if self._enhanced is None:
            try:
                from phase1_socceragent import SoccerAgentEnhanced
                self._enhanced = SoccerAgentEnhanced()
            except Exception as e:
                print(f"[SoccerAgent] Enhanced bridge unavailable: {e}")
                self._enhanced = False
        return self._enhanced if self._enhanced else None

    def extract_match_facts(self, entry: dict) -> Dict:
        """从 corner entry 提取结构化比赛上下文"""
        match = entry.get("match", "")
        enhanced = self._get_enhanced()

        result = {
            "match": match,
            "date": entry.get("date", ""),
            "score": entry.get("score_at_time", ""),
            "minute": entry.get("minute", ""),
            "corner_type": entry.get("corner_type", ""),
            "kick_taker": entry.get("kick_taker", ""),
            "goal_scorer": entry.get("goal_scorer", ""),
            "result": entry.get("result", ""),
            "tournament": "",
            "venue": "",
            "entities": {},
        }

        if enhanced:
            try:
                # 用增强桥接获取更丰富的上下文
                ctx = enhanced.enhance_corner_entry(entry)
                sa_ctx = ctx.get("socceragent_context", {})
                gs = sa_ctx.get("game_search") or {}
                result["tournament"] = gs.get("league", "2026 FIFA World Cup")
                result["entities"] = sa_ctx.get("entities", {})
            except Exception as e:
                print(f"[SoccerAgent] Context enhancement failed: {e}")

        return result


# ============================================================
# 主入口
# ============================================================

def run_phase1_pipeline(
    source: str = "tacticai",
    checkpoint_path: str = None,
    dataset_path: str = None,
    output_path: str = None,
    corner_entry: dict = None,
) -> List[Dict]:
    """
    Phase 1 统一入口。

    Args:
        source: "tacticai" | "socceragent" | "both"
        checkpoint_path: TacticAI checkpoint 路径
        dataset_path: 角球数据 JSON（Phase 2 格式）
        output_path: 输出 JSON 路径
        corner_entry: 单个角球 entry（用于实时推理）

    Returns:
        Phase 2 就绪的格式化数据列表
    """
    results = []

    if source in ("tacticai", "both"):
        print("\n" + "=" * 60)
        print(" [Phase 1] TacticAI 推理")
        print("=" * 60)

        inference = TacticAIInference(checkpoint_path=checkpoint_path)

        if corner_entry:
            # 单个角球实时推理
            analysis = inference.predict_from_corner_entry(corner_entry)
            if analysis:
                formatted = convert_to_phase2_format(analysis, corner_entry)
                results.append({"corner_entry": corner_entry, "analysis": asdict(analysis), "formatted": formatted})
                print(f"   ✅ {analysis.corner_id}: top_prob={analysis.tacticai_top_probability:.3f}")
        elif dataset_path:
            # 批量处理
            with open(dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            entries = data.get("entries", [])

            analyses = inference.analyze_dataset(entries)
            for analysis, entry in zip(analyses, entries):
                formatted = convert_to_phase2_format(analysis, entry)
                results.append({"corner_entry": entry, "analysis": asdict(analysis), "formatted": formatted})

            print(f"\n   ✅ Analyzed {len(analyses)} corners")

    if source in ("socceragent", "both"):
        print("\n" + "=" * 60)
        print(" [Phase 1] SoccerAgent 上下文提取")
        print("=" * 60)

        bridge = SoccerAgentBridge()
        for r in results:
            entry = r["corner_entry"]
            match_facts = bridge.extract_match_facts(entry)

            # 将 SoccerAgent 上下文注入到 formatted 输出
            if match_facts.get("tournament"):
                old_fact = r["formatted"]["fact_section"]
                additions = []
                if match_facts.get("tournament"):
                    additions.append(f"赛事：{match_facts['tournament']}")
                new_fact = "\n".join(additions) + "\n" + old_fact if additions else old_fact
                r["formatted"]["fact_section"] = new_fact

            r["match_context"] = match_facts
            print(f"   📋 {entry.get('id', '?')}: {match_facts['match']} "
                  f"({match_facts.get('tournament', '?')})")

    if source in ("matchtime", "both"):
        # MatchTime 预留接口 — 当 phase1_matchtime.MATCHTIME_AVAILABLE = True 时激活
        from phase1_matchtime import MATCHTIME_AVAILABLE, generate_commentary
        if MATCHTIME_AVAILABLE:
            print("\n" + "=" * 60)
            print(" [Phase 1] MatchTime AI 解说生成")
            print("=" * 60)
            for r in results:
                entry = r["corner_entry"]
                vid = entry.get("local_video_path", "")
                if vid:
                    commentary = generate_commentary(str(ROOT / vid))
                    if commentary:
                        r["matchtime_commentary"] = commentary
                        print(f"   🎙️ {entry.get('id', '?')}: {len(commentary)} chars")
        else:
            print("\n [Phase 1] MatchTime ⏭ (硬件不满足，跳过)")

    # 保存输出
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📁 Phase 1 output saved to: {output_path}")

    return results


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1 统一推理器")
    parser.add_argument("--source", choices=["tacticai", "socceragent", "matchtime", "both"], default="tacticai")
    parser.add_argument("--checkpoint", help="TacticAI checkpoint path")
    parser.add_argument("--dataset", default="src/data/corner_kicks_2026.json", help="角球数据集 JSON")
    parser.add_argument("--output", default="src/data/phase1_output.json")
    parser.add_argument("--entry-id", help="单个角球 ID（跳过批量处理）")
    args = parser.parse_args()

    entry = None
    if args.entry_id:
        with open(args.dataset, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for e in data.get("entries", []):
            if e["id"] == args.entry_id:
                entry = e
                break
        if entry is None:
            print(f"Entry '{args.entry_id}' not found in {args.dataset}")
            sys.exit(1)

    results = run_phase1_pipeline(
        source=args.source,
        checkpoint_path=args.checkpoint,
        dataset_path=None if entry else args.dataset,
        output_path=args.output,
        corner_entry=entry,
    )

    print(f"\n✅ Phase 1 complete: {len(results)} results")
