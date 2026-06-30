"""
Phase 1 全工具集成 → Phase 2 Demo

调用链:
  TacticAI GNN 推理 ──┐
  SoccerAgent 上下文 ──┤
                       ├──→ Phase 2 pipeline → 科普视频
  MatchTime (TBD) ────┘

用法:
  source /mnt/d/ClaudeWorkspace/phase1/venv/bin/activate
  cd /mnt/d/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant
  python3 scripts/phase1_full_demo.py --entry wc2026-corner-021
"""

import sys, json, os, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from pipeline import process_corner_kick
from phase1_runner import TacticAIInference, SoccerAgentBridge
from phase1_runner import convert_to_phase2_format, CornerAnalysisOutput
from dataclasses import asdict


def run_full_demo(entry_id: str = "wc2026-corner-021"):
    t0_total = time.time()

    # ================================================
    # 加载数据
    # ================================================
    dataset_path = ROOT / "src" / "data" / "corner_kicks_2026.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    corner_entry = None
    for e in dataset["entries"]:
        if e["id"] == entry_id:
            corner_entry = e
            break
    if corner_entry is None:
        raise ValueError(f"Entry {entry_id} not found")

    # 视频
    video_path = None
    vid = ROOT / "data" / "videos" / f"{entry_id}.mp4"
    if vid.exists():
        video_path = str(vid)

    print("=" * 60)
    print(f" Phase 1 全工具 → Phase 2 集成测试")
    print(f" Entry: {entry_id}")
    print(f" 比赛: {corner_entry['match']}")
    print("=" * 60)

    # ================================================
    # Phase 1 — TacticAI
    # ================================================
    print("\n--- [1/3] TacticAI 推理 ---")
    checkpoint = "/mnt/d/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant/phase1/tools/tactic-ai-recreation/models/checkpoints/best_model.pth"
    tacticai = TacticAIInference(checkpoint_path=checkpoint)
    analysis = tacticai.predict_from_corner_entry(corner_entry)

    print(f"  最可能接球: Player {analysis.tacticai_top_receiver} "
          f"({analysis.tacticai_top_probability*100:.1f}%)")
    attackers = [p for p in analysis.tacticai_predictions if p.is_attacker][:3]
    for p in attackers:
        print(f"    • {p.role} at ({p.position[0]:.0f},{p.position[1]:.0f}): {p.receiver_probability*100:.1f}%")

    # ================================================
    # Phase 1 — SoccerAgent
    # ================================================
    print("\n--- [2/3] SoccerAgent 上下文 ---")
    sa = SoccerAgentBridge()
    match_ctx = sa.extract_match_facts(corner_entry)
    tournament = match_ctx.get("tournament", "2026 FIFA World Cup")
    print(f"  赛事: {tournament}")
    if match_ctx.get("entities"):
        print(f"  实体: {list(match_ctx['entities'].keys())}")

    # 合并到 formatted
    formatted = convert_to_phase2_format(analysis, corner_entry)
    if match_ctx.get("tournament"):
        formatted["fact_section"] = f"赛事：{match_ctx['tournament']}\n{formatted['fact_section']}"

    print(f"\n  Fact section preview:")
    for line in formatted["fact_section"].split("\n")[:5]:
        print(f"    {line}")
    print(f"\n  Tactic section:")
    for line in formatted["tactic_section"].split("\n"):
        print(f"    {line}")

    # ================================================
    # Phase 2 — Pipeline
    # ================================================
    print(f"\n--- [3/3] Phase 2 生成 ---")
    t0 = time.time()

    result = process_corner_kick(
        video_path=video_path,
        formatted=formatted,
        output_prefix=entry_id.replace("-", "_"),
        corner_entry=corner_entry,
        tacticai_predictions=analysis.tacticai_predictions,
    )

    elapsed = time.time() - t0
    total_elapsed = time.time() - t0_total
    print(f"\n✅ 完成！Phase 2: {elapsed:.1f}s, 总计: {total_elapsed:.1f}s")
    print(f"  脚本: {len(result.get('script',''))} 字")
    if result.get("audio_path"):
        print(f"  音频: {os.path.basename(result['audio_path'])}")
    if result.get("output_video"):
        out = result["output_video"]
        size_mb = Path(out).stat().st_size / 1e6
        print(f"  视频: {os.path.basename(out)} ({size_mb:.1f} MB)")

    # 保存输出
    out_dir = ROOT / "outputs"
    script_path = out_dir / f"{entry_id}_enhanced_script.txt"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(f"# {corner_entry['match']} — {corner_entry['goal_scorer']}\n")
        f.write(f"# Phase 1: TacticAI + SoccerAgent → Phase 2\n")
        f.write(f"# 赛事: {tournament}\n\n")
        f.write(result.get("script", ""))

    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", default="wc2026-corner-021")
    args = parser.parse_args()
    run_full_demo(args.entry)
