"""
视频叠加模块 — moviepy

功能：在原角球视频上叠加 AI 解说音频 + 简单字幕/高亮标记

使用方法：
    from video_overlay import create_narrated_video
    create_narrated_video("input.mp4", "narration.mp3", overlay_data, "output.mp4")
"""

from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from config import OUTPUT_DIR


def create_narrated_video(
    video_path: str,
    audio_path: str,
    narration_text: str,
    output_name: str = "corner_story.mp4",
) -> str:
    """
    将原视频 + AI 解说音频 + 字幕合成为短视频。

    Args:
        video_path: 原始角球视频路径
        audio_path: AI 生成的解说音频 (mp3) 路径
        narration_text: 解说文本（用作字幕）
        output_name: 输出文件名

    Returns:
        str: 输出视频路径
    """
    output_path = str(OUTPUT_DIR / output_name)

    # 加载视频
    video = VideoFileClip(video_path)

    # 加载 AI 解说音频
    audio = AudioFileClip(audio_path)

    # 如果音频比视频长，循环或截断视频；如果短，截断音频
    final_duration = min(video.duration, audio.duration)
    video = video.subclipped(0, final_duration)
    audio = audio.subclipped(0, final_duration)

    # 替换原音频为 AI 解说
    video = video.with_audio(audio)

    # 添加底部字幕
    # 将长文本分段，每段显示一段时间
    chars_per_second = len(narration_text) / max(final_duration, 1)
    subtitle_clips = []

    # 简化处理：分成几个大段，每段一屏
    sentences = narration_text.replace('\n', ' ').split('。')
    sentences = [s.strip() + '。' for s in sentences if s.strip()]
    if not sentences:
        sentences = [narration_text]

    segment_duration = final_duration / len(sentences)

    for i, sentence in enumerate(sentences):
        txt_clip = TextClip(
            text=sentence,
            font_size=28,
            color='white',
            stroke_color='black',
            stroke_width=2,
            font='Arial',
            size=(video.w - 80, None),
            method='caption',
        )
        txt_clip = txt_clip.with_start(i * segment_duration)
        txt_clip = txt_clip.with_duration(segment_duration)
        txt_clip = txt_clip.with_position(('center', video.h - 120))
        subtitle_clips.append(txt_clip)

    # 合成
    final = CompositeVideoClip([video] + subtitle_clips)

    # 导出
    final.write_videofile(
        output_path,
        codec='libx264',
        audio_codec='aac',
        fps=24,
        preset='medium',
        threads=2,
    )

    # 清理
    video.close()
    audio.close()
    final.close()

    return output_path
