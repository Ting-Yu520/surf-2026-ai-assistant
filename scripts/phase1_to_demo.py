"""
Phase 1 → Phase 2 集成测试 — 单条目端到端验证

用法 （Windows 或 WSL）:
  cd projects/surf-2026-ai-tactical-assistant
  python3 scripts/phase1_to_demo.py --entry wc2026-corner-021

流程:
  Phase 1 TacticAI 数据 ──→ pipeline.py ──→ LLM 解说 → TTS → 视频合成
"""

import sys, json, os, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from pipeline import process_corner_kick


def run_single(
    entry_id: str = "wc2026-corner-021",
    dataset_path: str = None,
    phase1_output_path: str = None,
    video_dir: str = None,
) -> dict:
    """
    读取 Phase 1 输出，找到对应角球，送入 Phase 2 管线。
    """
    # 路径
    dataset_path = dataset_path or str(ROOT / "src" / "data" / "corner_kicks_2026.json")
    phase1_output_path = phase1_output_path or str(ROOT / "src" / "data" / "phase1_batch_output.json")
    video_dir = video_dir or str(ROOT / "data" / "videos")

    # 加载数据
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    with open(phase1_output_path, "r", encoding="utf-8") as f:
        phase1_data = json.load(f)

    # 找到对应条目
    corner_entry = None
    for e in dataset["entries"]:
        if e["id"] == entry_id:
            corner_entry = e
            break
    if corner_entry is None:
        raise ValueError(f"Entry {entry_id} not found in dataset")

    phase1_entry = None
    for p in phase1_data:
        if p.get("corner_entry", {}).get("id") == entry_id:
            phase1_entry = p
            break
    if phase1_entry is None:
        raise ValueError(f"Entry {entry_id} not found in Phase 1 output")

    # 获取 Phase 1 格式化数据
    formatted = phase1_entry.get("formatted", {})
    analysis = phase1_entry.get("analysis", {})

    # 获取视频
    video_path = None
    vid = Path(video_dir) / f"{entry_id}.mp4"
    if vid.exists():
        video_path = str(vid)

    print("=" * 60)
    print(f" Phase 1 → Phase 2 集成测试: {entry_id}")
    print("=" * 60)
    print(f"  比赛: {corner_entry['match']}")
    print(f"  进球者: {corner_entry['goal_scorer']}")
    print(f"  视频: {'✅ ' + str(vid.name) if video_path else '❌ 无视频'}")
    print()

    # Phase 1 战术彩蛋
    print(" [Phase 1 — TacticAI 数据]")
    print(f"  最可能接球方: {'进攻' if analysis.get('tacticai_top_receiver', -1) >= 0 else '防守'}")
    print(f"  最高接球概率: {analysis.get('tacticai_top_probability', 0)*100:.1f}%")
    predictions = analysis.get("tacticai_predictions", [])
    attackers_top = [p for p in predictions if p.get("is_attacker")][:3]
    for p in attackers_top:
        pos = p.get("position", [0, 0])
        print(f"    • Player {p['player_index']} ({p['role']}): {p['receiver_probability']*100:.1f}% "
              f"位置 ({pos[0]:.0f}, {pos[1]:.0f})")
    print()

    # Phase 2 格式化输入
    print(" [Phase 2 — Pipeline 输入]")
    print(f"  事实: {formatted['fact_section'][:100]}...")
    print(f"  战术: {formatted['tactic_section']}")
    print()

    # 运行 Phase 2 管线
    print(" [Phase 2 — 开始生成...]")
    t0 = time.time()

    try:
        result = process_corner_kick(
            video_path=video_path,
            formatted=formatted,
            output_prefix=entry_id.replace("-", "_"),
            corner_entry=corner_entry,
            tacticai_predictions=predictions,
        )

        elapsed = time.time() - t0
        print(f"\n ✅ 完成！耗时 {elapsed:.1f}s")
        print(f"  脚本长度: {len(result.get('script', ''))} 字")
        if result.get("audio_path"):
            print(f"  音频: {result['audio_path']}")
        if result.get("output_video"):
            print(f"  输出视频: {result['output_video']}")

        # 保存解说文本
        txt_path = ROOT / "outputs" / f"{entry_id}_script.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"# {corner_entry['match']} — {corner_entry['goal_scorer']}\n\n")
            f.write(result.get("script", ""))
        print(f"  脚本保存: {txt_path}")

        return result

    except Exception as e:
        print(f"\n ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry", default="wc2026-corner-021", help="角球 ID")
    parser.add_argument("--dataset", help="数据集路径")
    parser.add_argument("--phase1-output", help="Phase 1 输出路径")
    args = parser.parse_args()

    run_single(
        entry_id=args.entry,
        dataset_path=args.dataset,
        phase1_output_path=args.phase1_output,
    )
