"""
视频合成 — 极简版本

原视频 + AI 解说音频，无字幕，仅加开场标题高光。
"""

from moviepy import (
    VideoFileClip, AudioFileClip, TextClip,
    CompositeVideoClip, concatenate_videoclips
)


def create_simple_video(video_path: str, audio_path: str, output_path: str) -> str:
    """
    原视频 + AI 解说音频。无字幕。开头 3 秒显示标题。

    Args:
        video_path: 原始角球视频
        audio_path: AI 解说音频
        output_path: 输出路径
    """
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

    # 对齐时长
    if audio.duration > video.duration:
        loops = int(audio.duration / video.duration) + 1
        clips = [video] * loops
        video = concatenate_videoclips(clips)
    video = video.subclipped(0, audio.duration)
    video = video.with_audio(audio)

    # 前 3 秒显示高光标题
    title = TextClip(
        text="⚽ AI 角球战术解说",
        font_size=32,
        color='white',
        stroke_color='black',
        stroke_width=3,
        font='C:/Windows/Fonts/msyh.ttc',
        size=(video.w - 40, None),
        method='caption',
    ).with_duration(min(3.0, audio.duration)).with_position(('center', 30))

    # 画面边缘脉冲高光（简单的彩色边框）
    final = CompositeVideoClip([video, title])

    final.write_videofile(
        output_path, codec='libx264', audio_codec='aac',
        fps=24, preset='medium', threads=2,
    )

    video.close()
    audio.close()
    final.close()
    return output_path
