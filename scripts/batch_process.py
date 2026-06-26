"""
批量处理全部角球数据集

用法: python scripts/batch_process.py
输出: outputs/batch/ 目录下每个条目的解说音频 + 视频(如有视频源)
"""

import sys, json, os, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pipeline import process_corner_kick

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "src" / "data"
VIDEO_DIR = ROOT / "data" / "videos"
OUTPUT_DIR = ROOT / "outputs" / "batch"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 加载数据集
with open(DATA_DIR / "corner_kicks_2026.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

# 加载文章底本
with open(DATA_DIR / "corner_articles.json", "r", encoding="utf-8") as f:
    articles = json.load(f)

# 视频文件映射
video_files = {}
for vf in VIDEO_DIR.glob("*.mp4"):
    # 从文件名提取角球 ID
    name = vf.stem
    for eid in [f"wc2026-corner-{i:03d}" for i in range(1, 17)]:
        if eid in name:
            video_files[eid] = str(vf)
            break

print(f"数据集: {len(dataset['entries'])} 个条目")
print(f"文章底本: {len(articles)} 个")
print(f"视频文件: {len(video_files)} 个")
print(f"输出目录: {OUTPUT_DIR}")
print()

results = []

for i, entry in enumerate(dataset["entries"]):
    eid = entry["id"]
    match = entry["match"]
    minute = entry["minute"]
    scorer = entry["goal_scorer"]

    print(f"[{i+1}/{len(dataset['entries'])}] {eid}: {match} - {scorer} ({minute}')")

    # 获取文章底本
    article_text = articles.get(eid, entry.get("tactical_note", ""))
    if not article_text:
        print(f"  ⚠️ 无文章底本，跳过")
        continue

    # 检查视频
    video_path = video_files.get(eid)
    has_video = video_path is not None
    print(f"  视频: {'✅ ' + os.path.basename(video_path) if has_video else '❌ 无 (仅音频)'}")

    try:
        result = process_corner_kick(
            video_path=video_path if has_video else None,
            article_text=article_text,
        )

        # 保存到 batch 目录
        safe_name = f"{eid}_{match.replace(' ', '_').replace('ü','u')}"

        # 保存解说文本
        narration_path = OUTPUT_DIR / f"{safe_name}_narration.txt"
        with open(narration_path, "w", encoding="utf-8") as f:
            f.write(f"比赛: {match}\n")
            f.write(f"进球者: {scorer}\n")
            f.write(f"时间: {minute}'\n")
            f.write("="*40 + "\n\n")
            f.write(result.get("narration", ""))

        result["entry_id"] = eid
        result["match"] = match
        result["narration_path"] = str(narration_path)
        results.append(result)

        print(f"  ✅ 解说: {len(result.get('narration',''))} 字")
        if result.get("audio_path"):
            print(f"  🎙️ 音频: {os.path.basename(result['audio_path'])}")
        if result.get("output_video"):
            print(f"  📺 视频: {os.path.basename(result['output_video'])}")

    except Exception as e:
        print(f"  ❌ 失败: {e}")

    print()

# 生成汇总
summary = {
    "total": len(dataset["entries"]),
    "processed": len(results),
    "with_video": sum(1 for r in results if r.get("output_video")),
    "results": [
        {
            "entry_id": r["entry_id"],
            "match": r["match"],
            "narration_chars": len(r.get("narration", "")),
            "has_video": bool(r.get("output_video")),
        }
        for r in results
    ],
}

summary_path = OUTPUT_DIR / "summary.json"
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print("=" * 50)
print(f"✅ 处理完成: {len(results)}/{len(dataset['entries'])}")
print(f"   有视频: {summary['with_video']}")
print(f"   仅音频: {len(results) - summary['with_video']}")
print(f"   输出目录: {OUTPUT_DIR}")
print(f"   汇总: {summary_path}")
