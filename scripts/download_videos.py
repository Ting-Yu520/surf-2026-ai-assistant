"""
批量下载 2026 世界杯角球视频

用法:
    python scripts/download_videos.py           # 下载数据集中所有有 URL 的角球
    python scripts/download_videos.py --id wc2026-corner-001  # 下载指定角球
    python scripts/download_videos.py --add-url "https://..."  # 下载后添加到数据集

依赖: pip install yt-dlp
"""

import argparse
import subprocess
import sys
from pathlib import Path
import json

# 项目根目录
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "src" / "data"
VIDEO_DIR = ROOT / "data" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 已知的角球视频 URL（持续更新）
# ============================================================
VIDEO_SOURCES = {
    "wc2026-corner-001": {  # Van Hecke vs Tunisia
        "title": "Netherlands Van Hecke corner header vs Tunisia",
        "urls": [
            # CCTV 体育（中国可直连）
            # "https://sports.cctv.com/2026/06/26/...",
            # YouTube（需 VPN）
            # "https://www.youtube.com/watch?v=...",
        ],
    },
    "wc2026-corner-003": {  # Trusty vs Turkiye
        "title": "USA Trusty corner goal vs Turkiye",
        "urls": [],
    },
    "wc2026-corner-007": {  # Rahimi vs Haiti (CCTV)
        "title": "Morocco Rahimi corner goal vs Haiti",
        "urls": [
            "https://sports.cctv.com/2026/06/25/VIDExjrnA3H8FnJOd6UCsD24260625.shtml",
        ],
    },
    "wc2026-corner-008": {  # Ronaldo tap-in
        "title": "Portugal Ronaldo corner tap-in vs Uzbekistan",
        "urls": [],
    },
    # Bilibili 2026 世界杯集锦（含多场角球）
    "bilibili_highlights": {
        "title": "2026 World Cup Highlights June 24 Bilibili",
        "urls": [
            "https://www.bilibili.com/video/BV1Nvjd6yEAB/",
        ],
    },
}


def download_video(url: str, output_name: str) -> bool:
    """使用 yt-dlp 下载单个视频"""
    output_path = VIDEO_DIR / f"{output_name}.%(ext)s"
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--merge-output-format", "mp4",
        "-o", str(output_path),
        url,
    ]
    print(f"  下载: {url}")
    try:
        subprocess.run(cmd, check=True, cwd=str(ROOT))
        return True
    except subprocess.CalledProcessError as e:
        print(f"  失败: {e}")
        return False


def download_from_cctv(page_url: str, output_name: str) -> bool:
    """
    CCTV 页面下载（特殊处理）
    CCTV 的视频通常嵌入在页面中，需要解析出真实的 mp4/m3u8 地址。
    """
    import requests
    import re

    print(f"  解析 CCTV 页面: {page_url}")
    try:
        resp = requests.get(page_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, timeout=30)
        html = resp.text

        # 尝试找 mp4 链接
        mp4_urls = re.findall(r'https?://[^\s"\']+\.mp4[^\s"\']*', html)
        m3u8_urls = re.findall(r'https?://[^\s"\']+\.m3u8[^\s"\']*', html)

        all_urls = mp4_urls + m3u8_urls
        if all_urls:
            print(f"  找到 {len(all_urls)} 个视频链接")
            for i, u in enumerate(all_urls[:3]):  # 最多尝试 3 个
                print(f"  尝试 [{i}]: {u[:100]}...")
                if download_video(u, output_name):
                    return True

        # 如果直接找不到，尝试用 yt-dlp 直接处理页面
        print("  未找到直链，尝试 yt-dlp 解析页面...")
        return download_video(page_url, output_name)

    except Exception as e:
        print(f"  CCTV 解析失败: {e}")
        # fallback: 让 yt-dlp 自己处理
        return download_video(page_url, output_name)


def main():
    parser = argparse.ArgumentParser(description="下载 2026 世界杯角球视频")
    parser.add_argument("--id", help="下载指定角球 ID")
    parser.add_argument("--all", action="store_true", help="下载所有有 URL 的角球")
    parser.add_argument("--add-url", help="手动添加一个视频 URL 并下载")
    parser.add_argument("--list", action="store_true", help="列出所有角球及其 URL 状态")
    args = parser.parse_args()

    if args.list:
        print("\n📋 2026 世界杯角球视频状态:\n")
        for cid, info in VIDEO_SOURCES.items():
            has_url = len(info["urls"]) > 0
            status = "🟢 有 URL" if has_url else "🔴 待添加 URL"
            print(f"  [{status}] {cid}: {info['title']}")
            for u in info["urls"]:
                print(f"         {u[:80]}...")
        print(f"\n提示: 用 --id <id> 下载指定视频")
        print(f"      用 --add-url <url> 手动添加并下载")
        return

    if args.add_url:
        name = input("视频名称: ").strip()
        download_video(args.add_url, name.replace(" ", "_"))
        print(f"\n✅ 下载完成 → {VIDEO_DIR}")
        return

    if args.id:
        if args.id not in VIDEO_SOURCES:
            print(f"❌ 未知 ID: {args.id}")
            print(f"可用 ID: {list(VIDEO_SOURCES.keys())}")
            return
        info = VIDEO_SOURCES[args.id]
        print(f"\n📥 下载: {info['title']}")
        for url in info["urls"]:
            if "cctv.com" in url:
                download_from_cctv(url, args.id)
            else:
                download_video(url, args.id)
        return

    if args.all:
        for cid, info in VIDEO_SOURCES.items():
            if not info["urls"]:
                continue
            print(f"\n📥 [{cid}] {info['title']}")
            for url in info["urls"]:
                if "cctv.com" in url:
                    download_from_cctv(url, cid)
                else:
                    download_video(url, cid)
        print(f"\n✅ 全部完成 → {VIDEO_DIR}")
        return

    # 默认：显示帮助
    parser.print_help()
    print("\n💡 快速开始:")
    print("  python scripts/download_videos.py --list     # 查看所有角球状态")
    print("  python scripts/download_videos.py --id wc2026-corner-007  # 下载摩洛哥角球(CCTV)")
    print("  python scripts/download_videos.py --all      # 下载所有有URL的角球")


if __name__ == "__main__":
    main()
