"""MoviePy-based video composer — zero ffmpeg subprocess calls.

Replaces src/video_overlay.py's ffmpeg pipeline with pure Python moviepy compositing.
Uses imageio-ffmpeg under the hood (Python package, not external exe).
"""
from pathlib import Path
from typing import Optional, List, Dict

from moviepy import (
    VideoFileClip, AudioFileClip, TextClip, ColorClip,
    CompositeVideoClip, concatenate_videoclips,
)


def create_titled_video_moviepy(
    video_path: str,
    audio_path: str,
    timeline: List[Dict],
    output_path: str,
    match_info: str = "⚽ AI 角球战术解说",
    total_dur: Optional[float] = None,
    tacticai_predictions: Optional[List] = None,
    mg_clips: Optional[Dict[int, str]] = None,
) -> str:
    """Generate final video using moviepy compositing.

    Each timeline segment gets:
    - Colored border (A=red, B=blue)
    - Speaker label (懂哥/小白)
    - Subtitle text
    - Optional highlight circle (from TacticAI data)
    - Optional MG animation clip (for ai_scene segments)

    Args:
        video_path: Source match video
        audio_path: TTS narration audio
        timeline: List of {start, end, speaker, text, visual, visual_type} dicts
        output_path: Output MP4 path
        match_info: Match title text
        total_dur: Override total duration (auto from timeline)
        tacticai_predictions: TacticAI player predictions for highlights
        mg_clips: {segment_index: clip_path} for MG animation segments

    Returns:
        Output path string
    """
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

    if total_dur is None:
        total_dur = timeline[-1]["end"] if timeline else video.duration

    # Parse TacticAI predictions for highlight positioning
    top_attacker_pos = None
    data_x_range, data_y_range = (0, 100), (0, 100)
    if tacticai_predictions:
        attackers = [p for p in tacticai_predictions if p.get("is_attacker")]
        if attackers:
            top = max(attackers, key=lambda p: p.get("probability", 0))
            top_attacker_pos = top.get("position")
        xs = [p["position"][0] for p in tacticai_predictions]
        ys = [p["position"][1] for p in tacticai_predictions]
        if xs:
            data_x_range = (min(xs), max(xs))
        if ys:
            data_y_range = (min(ys), max(ys))

    W, H = 1280, 720  # Output resolution

    # Build segment clips
    seg_clips = []
    for i, seg in enumerate(timeline):
        seg_start = seg["start"]
        seg_dur = seg["end"] - seg["start"]
        speaker = seg["speaker"]
        color_rgb = (255, 0, 0) if speaker == "A" else (0, 0, 255)
        color_name = "red" if speaker == "A" else "blue"
        label = "懂哥" if speaker == "A" else "小白"
        text = (seg.get("text") or "").strip()[:80]
        visual_type = seg.get("visual_type")

        # Base video: MG clip, or source video segment (looped if needed)
        if visual_type == "ai_scene" and mg_clips and mg_clips.get(i):
            try:
                base = VideoFileClip(mg_clips[i])
                if base.duration < seg_dur:
                    base = base.looped(duration=seg_dur)
                else:
                    base = base.subclipped(0, seg_dur)
            except Exception:
                base = _get_video_segment(video, seg_start, seg_dur)
        else:
            base = _get_video_segment(video, seg_start, seg_dur)

        base = base.resized(new_size=(W, H))

        # Build overlays
        overlays = []

        # Colored border (4 edges)
        bw = 6
        for edge, (x, y, w, h) in [
            ("x=0:y=0:w=W:h=bw", (0, 0, W, bw)),
            ("x=0:y=H-bw:w=W:h=bw", (0, H - bw, W, bw)),
            ("x=0:y=0:w=bw:h=H", (0, 0, bw, H)),
            ("x=W-bw:y=0:w=bw:h=H", (W - bw, 0, bw, H)),
        ]:
            border = ColorClip(size=(w, h), color=color_rgb)
            border = border.with_position((x, y)).with_duration(seg_dur)
            border = border.with_opacity(0.85)
            overlays.append(border)

        # Speaker label (top-left)
        marker = "●" if speaker == "A" else "○"
        lbl = TextClip(
            text=f"{marker} {label}", font="C:/Windows/Fonts/msyh.ttc",
            font_size=24, color=color_name,
        ).with_position((10, 10)).with_duration(seg_dur)
        overlays.append(lbl)

        # Subtitle (bottom-center)
        if text:
            sub = TextClip(
                text=text, font="C:/Windows/Fonts/msyh.ttc",
                font_size=22, color="white",
            ).with_position(("center", H - 60)).with_duration(seg_dur)
            overlays.append(sub)

        # Highlight circle
        highlight_pos = _get_highlight_pos(seg, top_attacker_pos, speaker)
        if highlight_pos:
            px, py = _field_to_pixel(
                highlight_pos[0], highlight_pos[1], data_x_range, data_y_range
            )
            dot = TextClip(
                text="●", font="C:/Windows/Fonts/msyh.ttc",
                font_size=36, color="red",
            ).with_position((px - 18, py - 18)).with_duration(seg_dur)
            dot = dot.with_opacity(0.55)
            overlays.append(dot)

        # Composite base + overlays
        if overlays:
            seg_clip = CompositeVideoClip([base, *overlays])
        else:
            seg_clip = base

        seg_clips.append(seg_clip)

    # Concatenate all segments
    if seg_clips:
        final_video = concatenate_videoclips(seg_clips)
    else:
        final_video = video.subclipped(0, total_dur)

    # Add audio
    final_video = final_video.with_audio(audio)

    # Write output
    final_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=25,
        preset="medium",
        logger=None,
    )

    # Cleanup
    video.close()
    audio.close()
    for c in seg_clips:
        try:
            c.close()
        except Exception:
            pass
    final_video.close()

    return output_path


def _get_video_segment(video: VideoFileClip, start: float, duration: float):
    """Get a video segment, looping if start exceeds video duration."""
    if start >= video.duration:
        looped = video.looped(duration=duration)
        return looped
    end = min(start + duration, video.duration)
    if end - start < duration * 0.5:
        # Too short, loop instead
        return video.looped(duration=duration)
    return video.subclipped(start, end)


def _get_highlight_pos(seg: dict, top_attacker_pos, speaker: str):
    """Determine highlight circle position from LLM visual instruction or TacticAI data."""
    import re
    visual = seg.get("visual", "") or ""
    if "highlight" in visual:
        m = re.search(r"pos=\(?([\d.]+)\s*,?\s*([\d.]+)", visual)
        if m:
            return (float(m.group(1)), float(m.group(2)))
    # Fallback: A segments auto-highlight top attacker
    if speaker == "A" and top_attacker_pos:
        return tuple(top_attacker_pos)
    return None


def _field_to_pixel(field_x: float, field_y: float,
                    data_x_range=(0, 100), data_y_range=(0, 100)) -> tuple:
    """Map TacticAI field coordinates to video pixel coordinates (1280x720)."""
    VIEW_LEFT, VIEW_RIGHT = 120, 1160
    VIEW_TOP, VIEW_BOTTOM = 80, 640
    x_min, x_max = data_x_range
    y_min, y_max = data_y_range
    x_range = (x_max - x_min) or 1
    y_range = (y_max - y_min) or 1
    px = int(VIEW_LEFT + (field_x - x_min) / x_range * (VIEW_RIGHT - VIEW_LEFT))
    py = int(VIEW_TOP + (field_y - y_min) / y_range * (VIEW_BOTTOM - VIEW_TOP))
    return max(0, min(1280, px)), max(0, min(720, py))
