"""运行 MG 动画集成 demo — 完整管线"""
import sys, json, time, os
from pathlib import Path

ROOT = Path(__file__).parent.parent
os.chdir(str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pipeline import process_corner_kick

# 加载数据
data = json.load(open(ROOT / "src/data/corner_kicks_2026.json", "r", encoding="utf-8"))
entries = data["entries"]
entry = entries[0]  # wc2026-corner-001: Netherlands vs Tunisia

video_path = str(ROOT / f"data/videos/{entry['id']}.mp4")
print(f"Running: {entry['id']} — {entry['match']}")
print(f"Video: {video_path}")
print()

t0 = time.time()
result = process_corner_kick(
    video_path=video_path,
    corner_entry=entry,
    output_prefix=f"mg_demo_{entry['id']}",
)
elapsed = time.time() - t0

print(f"\n=== Done in {elapsed:.0f}s ===")
print(f"Script: {len(result.get('script', ''))} chars")
print(f"Output: {result.get('output_video', 'N/A')}")
print(f"MG clips: {result.get('mg_clips', {})}")
