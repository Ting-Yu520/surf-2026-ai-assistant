"""
角球视频下载器 v2.0 — 强制 ≥720p（ffmpeg 已安装）

策略:
  - yt-dlp 首选 1080p 单文件 (MP4)
  - fallback: 任意视频 + bestaudio 合并 (需要 ffmpeg)
  - fallback: 任意 best 单一格式
  - 下载后 ffprobe 检查实际高度
  - < 720p → ffmpeg 超分升频至 720p (lanczos)
  - 全部临时文件在 D 盘 (VIDEO_DIR/.tmp/)

依赖: yt-dlp, ffmpeg (D:\\Tools\\ffmpeg\\ffmpeg-8.1.2-full_build\\bin)
"""

import sys
import json
import argparse
import subprocess
import shutil
import time
from pathlib import Path
from typing import Optional, Tuple

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "src" / "data"
VIDEO_DIR = ROOT / "data" / "videos"
TMP_DIR = VIDEO_DIR / ".tmp"
COOKIES_FILE = ROOT / "scripts" / "bilibili_cookies.txt"
DATASET_FILE = DATA_DIR / "corner_kicks_2026.json"

VIDEO_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# 清理脚本启动时的临时残留
for old_file in TMP_DIR.glob("*"):
    try:
        if old_file.is_file():
            old_file.unlink()
    except Exception:
        pass

# 找到 ffmpeg（先看 PATH，再看固定路径）
FFMPEG = shutil.which("ffmpeg") or "D:/Tools/ffmpeg/ffmpeg-8.1.2-full_build/bin/ffmpeg.exe"
FFPROBE = shutil.which("ffprobe") or "D:/Tools/ffmpeg/ffmpeg-8.1.2-full_build/bin/ffprobe.exe"

MIN_HEIGHT = 720


def get_bilibili_cookies_args(use_browser: bool = False, browser: str = "edge") -> dict:
    """返回 yt-dlp 用的 cookie 参数。"""
    if COOKIES_FILE.exists():
        return {"cookiefile": str(COOKIES_FILE)}
    if use_browser:
        return {"cookiesfrombrowser": (browser,)}
    return {}


def get_video_height(video_path: Path) -> Optional[int]:
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=height", "-of", "csv=p=0",
             str(video_path)],
            capture_output=True, text=True, timeout=30,
        )
        out = result.stdout.strip().split("\n")[0]
        return int(out) if out.isdigit() else None
    except Exception:
        return None


def probe_max_height(url: str) -> Optional[int]:
    import yt_dlp
    try:
        ydl_opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            best = 0
            for fmt in info.get("formats", []):
                h = fmt.get("height")
                if h and h > best:
                    best = h
            return best if best > 0 else None
    except Exception:
        return None


def upscale_to_720p(input_path: Path, output_path: Path) -> Tuple[bool, str]:
    try:
        cmd = [
            FFMPEG, "-y", "-i", str(input_path),
            "-vf", "scale=-2:720:flags=lanczos:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0 and output_path.exists():
            return True, "upscaled"
        return False, f"ffmpeg 退出码 {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "ffmpeg 超时（>10分钟）"
    except Exception as e:
        return False, f"ffmpeg 异常: {type(e).__name__}: {e}"


def download_video(url: str, target_path: Path,
                   use_browser_cookies: bool = False,
                   browser: str = "edge") -> Tuple[bool, str]:
    import yt_dlp

    src_max = probe_max_height(url)

    if src_max and src_max >= 1080:
        format_sel = "bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height>=1080]+bestaudio/best[height>=1080]"
    elif src_max and src_max >= 720:
        format_sel = "bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height>=720]+bestaudio/best[height>=720]"
    else:
        format_sel = "bestvideo+bestaudio/best"

    ydl_opts = {
        "format": format_sel,
        "outtmpl": str(TMP_DIR / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "max_filesize": 500 * 1024 * 1024,
        "socket_timeout": 30,
        "retries": 3,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }] if "bestvideo+bestaudio" in format_sel else [],
    }

    # B站附加 cookie
    if "bilibili.com" in url:
        cookie_args = get_bilibili_cookies_args(use_browser=use_browser_cookies, browser=browser)
        if cookie_args:
            ydl_opts.update(cookie_args)
        ydl_opts["format"] = "bestvideo[height>=1080]+bestaudio/best"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        return False, f"yt-dlp 异常: {type(e).__name__}"

    candidates = sorted(TMP_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    downloaded = candidates[0] if candidates else None
    if downloaded is None or not downloaded.exists():
        return False, "下载后未找到文件"

    actual_h = get_video_height(downloaded)
    if actual_h is None:
        downloaded.unlink(missing_ok=True)
        return False, "无法读取分辨率"

    if actual_h >= 720:
        shutil.move(str(downloaded), str(target_path))
        size_mb = target_path.stat().st_size / (1024 * 1024)
        return True, f"原生 {actual_h}p, {size_mb:.1f}MB"
    else:
        print(f"    ⬆️  {actual_h}p → 升频至 720p...")
        upscaled = TMP_DIR / f"upscaled_{downloaded.stem}.mp4"
        ok, msg = upscale_to_720p(downloaded, upscaled)
        downloaded.unlink(missing_ok=True)
        if not ok:
            return False, f"升频失败: {msg}"
        shutil.move(str(upscaled), str(target_path))
        final_h = get_video_height(target_path)
        size_mb = target_path.stat().st_size / (1024 * 1024)
        return True, f"{actual_h}p→{final_h}p 升频, {size_mb:.1f}MB"


def process_entry(entry: dict, force: bool = False,
                  use_browser_cookies: bool = False,
                  browser: str = "edge") -> dict:
    eid = entry["id"]
    target = VIDEO_DIR / f"{eid}.mp4"

    if target.exists() and not force:
        h = get_video_height(target)
        return {"id": eid, "status": "exists", "path": str(target), "height": h}

    urls = entry.get("video_urls", [])
    if not urls:
        return {"id": eid, "status": "no_url", "reason": "video_urls 为空"}

    def priority(url: str) -> int:
        if "cctv" in url or "yangshipin" in url:
            return 0
        if "bilibili" in url:
            return 1
        return 99

    sorted_urls = sorted(urls, key=priority)

    last_err = ""
    for url in sorted_urls:
        print(f"    → 尝试: {url[:75]}...")
        ok, msg = download_video(url, target, use_browser_cookies=use_browser_cookies, browser=browser)
        if ok:
            return {"id": eid, "status": "downloaded", "path": str(target), "msg": msg}
        last_err = msg
        print(f"    ❌ {msg}")

    return {"id": eid, "status": "failed", "reason": last_err}


def update_dataset_with_local_paths(results: list):
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_id = {r["id"]: r for r in results if r["status"] in ("downloaded", "exists")}
    for entry in data["entries"]:
        if entry["id"] in by_id:
            entry["local_video_path"] = str(by_id[entry["id"]]["path"])
            if by_id[entry["id"]].get("height"):
                entry["local_video_height"] = by_id[entry["id"]]["height"]

    with open(DATASET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="下载角球视频，强制 ≥720p")
    parser.add_argument("--force", action="store_true", help="强制重新下载")
    parser.add_argument("--id", help="只处理指定 ID")
    parser.add_argument("--no-update-json", action="store_true", help="不写回 JSON")
    parser.add_argument("--use-browser-cookies", action="store_true",
                        help="从浏览器提取 B站 cookies（需先登录 bilibili.com）")
    parser.add_argument("--browser", default="edge",
                        choices=["chrome", "edge", "firefox", "brave", "opera", "chromium"],
                        help="浏览器名称（默认 edge）")
    args = parser.parse_args()

    if not Path(FFMPEG).exists() and not shutil.which("ffmpeg"):
        print(f"❌ ffmpeg 未找到: {FFMPEG}")
        sys.exit(1)

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data["entries"]
    if args.id:
        entries = [e for e in entries if e["id"] == args.id]
        if not entries:
            print(f"❌ 未找到 ID={args.id}")
            return

    print(f"📦 数据集: {len(data['entries'])} 条目")
    print(f"🎯 处理: {len(entries)} 个")
    print(f"📐 目标: ≥{MIN_HEIGHT}p（不足自动升频）")
    print(f"🔧 强制: {args.force}")
    print("=" * 60)

    results = []
    t0 = time.time()
    for i, entry in enumerate(entries, 1):
        eid = entry["id"]
        match = entry["match"]
        print(f"\n[{i}/{len(entries)}] {eid}: {match}")
        result = process_entry(entry, force=args.force,
                               use_browser_cookies=args.use_browser_cookies,
                               browser=args.browser)
        result["match"] = match

        if result["status"] == "downloaded":
            print(f"  ✅ {result['msg']}")
        elif result["status"] == "exists":
            print(f"  ⏭️  已存在 ({result.get('height')}p)")
        elif result["status"] == "no_url":
            print(f"  ⚠️  无 URL")
        else:
            print(f"  ❌ 失败: {result.get('reason', '')}")

        results.append(result)

    if not args.no_update_json:
        update_dataset_with_local_paths(results)
        print(f"\n📝 已写回 local_video_path 到 JSON")

    elapsed = time.time() - t0
    print("\n" + "=" * 60)
    print("📊 汇总:")
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    for s, n in sorted(counts.items()):
        print(f"  {s}: {n}")
    print(f"⏱️  {elapsed:.1f}s")


if __name__ == "__main__":
    main()
