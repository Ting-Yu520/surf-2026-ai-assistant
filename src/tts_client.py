"""
TTS 客户端 — Edge TTS（免费）

支持逐段配音 + 精确时长记录，解决字幕音画同步问题。
"""

import asyncio
import edge_tts
from config import TTS_VOICE, TTS_SPEED


async def _generate_single(text: str, output_path: str) -> float:
    """生成单段语音，返回实际时长（秒）"""
    communicate = edge_tts.Communicate(text=text, voice=TTS_VOICE, rate=TTS_SPEED)
    await communicate.save(output_path)

    # 使用 moviepy 获取音频时长（避免 mutagen 兼容性问题）
    from moviepy import AudioFileClip
    clip = AudioFileClip(output_path)
    duration = clip.duration
    clip.close()
    return duration


async def _generate_segments(segments: list[dict], output_dir: str) -> list[dict]:
    """
    逐段生成语音。

    Args:
        segments: [{"start_sec": 0, "end_sec": 3, "narration": "..."}, ...]
        output_dir: 输出目录

    Returns:
        segments 添加了 audio_path 和 actual_duration_sec 字段
    """
    import os
    results = []

    for i, seg in enumerate(segments):
        audio_path = os.path.join(output_dir, f"seg_{i:03d}.mp3")
        duration = await _generate_single(seg["narration"], audio_path)
        results.append({
            **seg,
            "audio_path": audio_path,
            "actual_duration_sec": duration,
        })

    return results


def generate_audio(text: str, output_path: str) -> str:
    """
    生成整段中文语音（单段，非时间线版本）。

    Returns:
        str: 音频文件路径
    """
    asyncio.run(_generate_single(text, output_path))
    return output_path


def generate_timeline_audio(segments: list[dict], output_dir: str) -> list[dict]:
    """
    同步接口：逐段生成语音并返回含精确时长的分段数据。

    Returns:
        segments 添加了 audio_path 和 actual_duration_sec
    """
    return asyncio.run(_generate_segments(segments, output_dir))


def concat_audio_segments(segments: list[dict], output_path: str) -> str:
    """
    将逐段音频合并为一个完整音频文件（使用 moviepy 避免 pydub 的 audioop 依赖）。
    """
    from moviepy import AudioFileClip, concatenate_audioclips

    clips = []
    for seg in segments:
        if seg.get("audio_path"):
            clip = AudioFileClip(seg["audio_path"])
            clips.append(clip)

    if not clips:
        # 创建一个静音占位
        from moviepy import AudioClip
        import numpy as np
        duration = sum(s.get("actual_duration_sec", 1) for s in segments)
        def make_frame(t): return np.zeros((1, 2))
        combined = AudioClip(make_frame, duration=duration, fps=44100)
    elif len(clips) == 1:
        clips[0].write_audiofile(output_path)
        clips[0].close()
        return output_path
    else:
        combined = concatenate_audioclips(clips)

    combined.write_audiofile(output_path)
    combined.close()
    for c in clips:
        c.close()
    return output_path
