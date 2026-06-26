"""
视频叠加模块 — 时间线精确对齐版本

字幕按每段 TTS 的实际时长精确显示，与画面对应。
"""

from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from config import OUTPUT_DIR


def create_synced_video(
    video_path: str,
    audio_path: str,
    segments: list[dict],
    output_name: str = "corner_story.mp4",
) -> str:
    """
    将原视频 + 完整音频 + 时间线对齐的字幕合成为短视频。

    Args:
        video_path: 原始角球视频
        audio_path: 合并后的完整解说音频
        segments: 分段数据，每段含 start_sec, end_sec, narration, actual_duration_sec
        output_name: 输出文件名

    Returns:
        输出视频路径
    """
    output_path = str(OUTPUT_DIR / output_name)

    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

    # 取视频和音频中较短的
    final_duration = min(video.duration, audio.duration)
    video = video.subclipped(0, final_duration)

    # 替换音频
    video = video.with_audio(audio.subclipped(0, final_duration))

    # 逐段生成字幕，累加时间偏移
    subtitle_clips = []
    time_offset = 0.0  # 当前字幕在视频中的起始秒数

    for seg in segments:
        seg_duration = seg.get("actual_duration_sec", seg["end_sec"] - seg["start_sec"])

        # 跳过超短或无内容的片段
        if seg_duration < 0.3:
            time_offset += seg_duration
            continue

        txt = seg["narration"]
        if not txt.strip():
            time_offset += seg_duration
            continue

        txt_clip = TextClip(
            text=txt,
            font_size=26,
            color='white',
            stroke_color='black',
            stroke_width=2,
            font='C:/Windows/Fonts/msyh.ttc',
            size=(video.w - 80, None),
            method='caption',
        )
        txt_clip = txt_clip.with_start(time_offset)
        txt_clip = txt_clip.with_duration(seg_duration)
        txt_clip = txt_clip.with_position(('center', video.h - 110))
        subtitle_clips.append(txt_clip)

        time_offset += seg_duration

    final = CompositeVideoClip([video] + subtitle_clips)
    final.write_videofile(output_path, codec='libx264', audio_codec='aac', fps=24, preset='medium', threads=2)

    video.close()
    audio.close()
    final.close()

    return output_path
