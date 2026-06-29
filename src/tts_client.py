"""
TTS 客户端 — Edge TTS（免费）

支持逐段配音 + 精确时长记录（用 ffprobe 而非 moviepy，避免 mp3 兼容问题）。
"""

import asyncio
import edge_tts
import subprocess
import json
from config import TTS_VOICE, TTS_SPEED


def _ffprobe_duration(path: str) -> float:
    """用 ffprobe 获取音频时长（秒），避免 moviepy/ffmpeg 读 mp3 的兼容性问题"""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", path],
        capture_output=True, text=True, timeout=15,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


async def _generate_single(text: str, output_path: str) -> float:
    """生成单段语音，返回实际时长（秒）"""
    communicate = edge_tts.Communicate(text=text, voice=TTS_VOICE, rate=TTS_SPEED)
    await communicate.save(output_path)

    # 用 ffprobe 而非 moviepy 读时长
    try:
        return _ffprobe_duration(output_path)
    except Exception:
        return 2.0  # 回退：假设 2 秒


async def _generate_segments(segments: list[dict], output_dir: str) -> list[dict]:
    """逐段生成语音。"""
    import os
    results = []

    for i, seg in enumerate(segments):
        audio_path = os.path.join(output_dir, f"seg_{i:03d}.mp3")
        try:
            duration = await _generate_single(seg["narration"], audio_path)
        except Exception as e:
            # 如果 TTS 失败，创建一个静音占位
            duration = 2.0
            _create_silent_mp3(audio_path, duration)
        results.append({
            **seg,
            "audio_path": audio_path,
            "actual_duration_sec": duration,
        })

    return results


def _create_silent_mp3(path: str, duration: float = 2.0):
    """用 ffmpeg 生成静音 mp3 作为 TTS 失败的兜底"""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r=44100:cl=mono", "-t", str(duration),
         "-c:a", "libmp3lame", path],
        capture_output=True, timeout=15,
    )


def generate_audio(text: str, output_path: str) -> str:
    """单段语音生成（同步接口）"""
    asyncio.run(_generate_single(text, output_path))
    return output_path


def generate_timeline_audio(segments: list[dict], output_dir: str) -> list[dict]:
    """逐段语音生成（同步接口）"""
    return asyncio.run(_generate_segments(segments, output_dir))


def concat_audio_segments(segments: list[dict], output_path: str) -> str:
    """用 ffmpeg concat 合并音频段，避免 moviepy 依赖"""
    import os

    # 写文件列表
    list_path = os.path.join(os.path.dirname(output_path), "_concat_list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for seg in segments:
            if seg.get("audio_path") and os.path.exists(seg["audio_path"]):
                f.write(f"file '{os.path.abspath(seg['audio_path'])}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", list_path, "-c", "copy", output_path],
        capture_output=True, timeout=60,
    )

    os.unlink(list_path)
    return output_path
