"""
视频合成 v2 — ffmpeg 剪辑管线

将二人转脚本逐句时间轴映射为视频上的彩色边框、角色角标、标题尾卡。
使用 openmontage video-edit skill（ffmpeg）替代旧版 moviepy。

关键设计：
- 避免 ffmpeg filter 语法中 Windows 盘符冒号被当选项分隔符
  → 字体复制到本地相对路径使用
  → 文本文件写入本地临时目录（无盘符路径）
- 逐句时间轴驱动边框色 + 角标切换
"""

import re
import subprocess
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Optional

# 将字体复制到本地，避免 C: 盘符冒号破坏 ffmpeg filter 语法
_FONT_SRC = "C:/Windows/Fonts/msyh.ttc"
_FONT_DST = Path(__file__).parent / "_font_msyh.ttc"
if not _FONT_DST.exists():
    shutil.copy2(_FONT_SRC, _FONT_DST)
FONT = str(_FONT_DST.resolve())  # 绝对路径，等会儿会被转为相对用

# 临时文件目录（相对于项目 outputs，避免 TEMP 目录的盘符）
_TMP_DIR = Path(__file__).parent.parent / "outputs" / "_ffmpeg_assets"
_TMP_DIR.mkdir(parents=True, exist_ok=True)


def _field_to_pixel(field_x: float, field_y: float,
                    data_x_range=(0, 100), data_y_range=(0, 100)) -> tuple:
    """
    将 TacticAI 球场坐标映射到视频像素坐标 (1280x720)。

    自适应数据范围：根据实际球员坐标的 min/max 线性映射到画面主体区域。
    Fallback: 如果未提供 data range，使用默认 0-100 → 全画面映射。
    """
    # 画面主体区域（留边距给 UI 元素）
    VIEW_LEFT, VIEW_RIGHT = 120, 1160
    VIEW_TOP, VIEW_BOTTOM = 80, 640

    x_min, x_max = data_x_range
    y_min, y_max = data_y_range

    x_range = (x_max - x_min) or 1
    y_range = (y_max - y_min) or 1

    px = int(VIEW_LEFT + (field_x - x_min) / x_range * (VIEW_RIGHT - VIEW_LEFT))
    py = int(VIEW_TOP + (field_y - y_min) / y_range * (VIEW_BOTTOM - VIEW_TOP))

    px = max(0, min(1280, px))
    py = max(0, min(720, py))
    return px, py


def parse_script(script: str) -> List[Dict]:
    """
    解析 LLM 输出，返回 [{speaker, text, visual, visual_type}, ...]
    支持 ##VISUAL## 视觉指令
    """
    segments = []
    current = None
    for line in script.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^([AB]):\s*(.+)$', line)
        if m:
            if current:
                segments.append(current)
            current = {
                "speaker": m.group(1),
                "text": m.group(2).strip(),
                "visual": None,
                "visual_type": None,
            }
        elif line.startswith('##VISUAL##') and current:
            visual = line.replace('##VISUAL##', '').strip()
            current["visual"] = visual
            if visual == 'ai_scene':
                current["visual_type"] = 'ai_scene'
            elif visual == 'clear':
                current["visual_type"] = 'clear'
            elif visual.startswith('highlight'):
                current["visual_type"] = 'highlight'
            else:
                current["visual_type"] = None
    if current:
        segments.append(current)
    return segments


def build_timeline(
    segments: List[Dict],
    seg_durations: List[float],
    gap: float = 0.3,
) -> List[Dict]:
    """逐句时长组装时间轴，返回每句的 start/end 秒数"""
    timeline = []
    cursor = 0.0
    for seg, dur in zip(segments, seg_durations):
        timeline.append({
            "speaker": seg["speaker"],
            "text": seg["text"],
            "visual": seg.get("visual"),
            "visual_type": seg.get("visual_type"),
            "start": cursor,
            "end": cursor + dur,
        })
        cursor += dur + gap
    return timeline


def _write_textfile(text: str) -> str:
    """把文本写入本地临时文件，返回不带盘符的相对路径"""
    name = f"txt_{uuid.uuid4().hex[:8]}.txt"
    path = _TMP_DIR / name
    path.write_text(text, encoding="utf-8")
    return str(path)  # 返回绝对路径，但等会儿用相对引用


def _filter_path(path: str) -> str:
    """
    将路径转为 ffmpeg filter 可用的格式：
    - 去掉盘符（用相对路径或正斜杠+无盘符）
    - 反斜杠转正斜杠
    """
    p = Path(path)
    try:
        # 尝试转为相对路径（相对于 outputs 目录）
        rel = p.relative_to(_TMP_DIR.parent.parent)
        return rel.as_posix()
    except ValueError:
        # 否则用正斜杠
        return p.as_posix()


def _build_zoompan(total_dur: float, fps: int = 25) -> str:
    """
    构建 Ken Burns 风格 zoompan 滤镜表达式。
    产生平滑推拉 + 动态焦点移动的"摄像机运动"效果。

    轨迹设计：
    - 开始：全画幅，居中（解说导入）
    - 前段：缓慢推近到禁区内偏右区域（战术分析）
    - 中段：推到最紧，焦点略上移（关键瞬间）
    - 后段：缓慢拉回全画幅（结论）
    """
    total_frames = max(1, int(total_dur * fps))
    # z: 1.0 → 1.25 → 1.0 的平滑推拉（使用正弦）
    z = f"1+0.2*sin(2*PI*(on-1)/({total_frames}))"
    # cx: 640 → 750 → 640，焦点向右移向球门区
    cx = f"640+80*sin(PI*(on-1)/({total_frames}))"
    # cy: 360 → 330 → 360，焦点略上移
    cy = f"360-20*sin(PI*(on-1)/({total_frames}))"
    # 转换为 zoompan 的 x,y（左上角坐标）
    x = f"{cx}-640/zoom"
    y = f"{cy}-360/zoom"
    return f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s=1280x720:fps={fps}"


def _trim_clip(video_path: Path, start: float, duration: float, output_path: str):
    """从视频中裁剪一段（自动循环如果 start 超出视频时长），无音频"""
    # 先获取视频时长
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path),
    ], capture_output=True, text=True)
    video_dur = float(probe.stdout.strip())

    # 如果 start 超出视频时长，循环视频
    if start >= video_dur:
        subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(video_path),
            "-ss", str(start % video_dur if video_dur > 0 else 0),
            "-t", str(duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "22",
            "-an",
            str(output_path),
        ], capture_output=True, check=True)
    else:
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(duration),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "22",
            "-an",
            str(output_path),
        ], capture_output=True, check=True)


def _trim_or_loop_clip(clip_path: str, target_dur: float, output_path: str):
    """裁剪 MG clip 到目标时长（不够则循环，太长则裁剪）"""
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", clip_path,
    ], capture_output=True, text=True)
    clip_dur = float(probe.stdout.strip())

    if abs(clip_dur - target_dur) < 0.3:
        subprocess.run(["ffmpeg", "-y", "-i", clip_path,
                        "-c", "copy", str(output_path)], capture_output=True, check=True)
    elif clip_dur < target_dur:
        subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", clip_path,
            "-t", str(target_dur),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "22",
            str(output_path),
        ], capture_output=True, check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-ss", "0", "-i", clip_path,
                        "-t", str(target_dur), "-c", "copy",
                        str(output_path)], capture_output=True, check=True)


def _create_highlight_freeze(video_path: Path, seg: dict, output_path: str):
    """B 段：提取一帧作为定格画面"""
    seg_dur = seg["end"] - seg["start"]
    freeze_time = (seg["start"] + seg["end"]) / 2

    frame_path = str(Path(output_path).with_suffix(".png"))
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(freeze_time),
        "-i", str(video_path),
        "-vframes", "1", "-q:v", "2",
        frame_path,
    ], capture_output=True, check=True)

    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", frame_path,
        "-t", str(seg_dur),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "22",
        str(output_path),
    ], capture_output=True, check=True)


def _create_opening_clip(video_path: str, output_dir: Path) -> Optional[str]:
    """从视频中提取前 4 秒作为片头进球回放"""
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path),
    ], capture_output=True, text=True)
    video_dur = float(probe.stdout.strip())
    opening_len = min(4.0, video_dur * 0.3)
    opening_path = output_dir / "_opening.mp4"

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-t", str(opening_len),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "fast", "-crf", "22",
        "-an",
        str(opening_path),
    ], capture_output=True, check=True)

    return str(opening_path) if opening_path.exists() else None


def _add_segment_overlays(input_clip: str, seg: dict, output_path: str, font_rel: str,
                          top_attacker_pos=None, data_x_range=(0, 100), data_y_range=(0, 100)):
    """给单个段 clip 叠加：角标、边框、高亮圈、字幕"""
    color = "red" if seg["speaker"] == "A" else "blue"
    label = "懂哥" if seg["speaker"] == "A" else "小白"
    marker = "●" if seg["speaker"] == "A" else "○"
    text = (seg.get("text", "") or "").strip()[:50]  # 截断长文本，处理 None/空

    label_file = _filter_path(_write_textfile(f"{marker} {label}"))
    # 空文本会导致 ffmpeg drawtext 失败 → 整个 overlay 回退到 raw clip
    # 用空格占位避免空文件
    subtitle_text = text if text else " "
    subtitle_file = _filter_path(_write_textfile(subtitle_text))

    filters = []

    # 四边彩色边框（6px 更醒目）
    bw = 6
    filters.append(f"drawbox=x=0:y=0:w=1280:h={bw}:color={color}@0.85:t=fill")
    filters.append(f"drawbox=x=0:y={720-bw}:w=1280:h={bw}:color={color}@0.85:t=fill")
    filters.append(f"drawbox=x=0:y=0:w={bw}:h=720:color={color}@0.85:t=fill")
    filters.append(f"drawbox=x={1280-bw}:y=0:w={bw}:h=720:color={color}@0.85:t=fill")

    # 角标（左上角）
    filters.append(
        f"drawtext=x=10:y=10:fontfile={font_rel}:"
        f"textfile={label_file}:"
        f"fontsize=24:fontcolor={color}:box=1:boxcolor=black@0.5:boxborderw=4"
    )

    # 高亮圈：优先用 LLM 的 visual 指令，否则 A 段自动高亮 top attacker
    highlight_pos = None
    visual = seg.get("visual", "") or ""
    if "highlight" in visual:
        m = re.search(r'pos=\(?([\d.]+)\s*,?\s*([\d.]+)', visual)
        if m:
            highlight_pos = (float(m.group(1)), float(m.group(2)))
    # 回退：A 段自动高亮 TacticAI 最强接球点
    if highlight_pos is None and seg["speaker"] == "A" and top_attacker_pos:
        highlight_pos = tuple(top_attacker_pos)

    if highlight_pos:
        px, py = _field_to_pixel(highlight_pos[0], highlight_pos[1],
                                 data_x_range, data_y_range)
        filters.append(
            f"drawtext=x={px-18}:y={py-18}:fontfile={font_rel}:"
            f"text='●':fontsize=36:fontcolor=red@0.55"
        )

    # 底部字幕（仅在有文本时添加）
    if text:
        filters.append(
            f"drawtext=x=(w-text_w)/2:y=h-60:fontfile={font_rel}:"
            f"textfile={subtitle_file}:"
            f"fontsize=22:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=6"
        )

    filter_str = ",".join(filters)
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_clip,
            "-vf", filter_str,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "22",
            "-an",
            output_path,
        ], capture_output=True, check=True, timeout=30)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"[video_overlay] Overlay failed for seg, using raw clip: {e}")
        # Fallback: copy raw clip without overlays
        try:
            subprocess.run(["ffmpeg", "-y", "-i", input_clip, "-c", "copy", output_path],
                           capture_output=True, check=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # If even copy fails (corrupt input), generate a blank placeholder
            print(f"[video_overlay] Copy fallback also failed, generating blank placeholder")
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=0x0a1628:s=1280x720:d=2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "fast", "-crf", "22",
                output_path,
            ], capture_output=True, check=True)


def create_titled_video(
    video_path: str,
    audio_path: str,
    timeline: List[Dict],
    output_path: str,
    match_info: str = "⚽ AI 角球战术解说",
    total_dur: Optional[float] = None,
    tacticai_predictions: Optional[List] = None,
    mg_clips: Optional[Dict[int, str]] = None,  # NEW: {segment_index: mg_clip_path}
) -> str:
    """
    使用 ffmpeg 生成最终视频。

    两步法：
    1. 叠加 drawtext/drawbox 滤镜到视频画面（去原音频）
    2. 替换为 TTS 配音音频
    """
    video_path = Path(video_path)
    output_path = Path(output_path)
    temp_video = _TMP_DIR / f"_temp_filtered_{video_path.stem}.mp4"

    if not video_path.exists():
        raise FileNotFoundError(f"视频源不存在: {video_path}")

    # 获取视频时长
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        check=True, capture_output=True, text=True,
    )
    video_dur = float(probe.stdout.strip())

    if total_dur is None and timeline:
        total_dur = timeline[-1]["end"]
    elif total_dur is None:
        total_dur = video_dur

    # 解析 TacticAI 预测数据，用于 auto-highlight + 自适应坐标映射
    top_attacker_pos = None
    data_x_range = (0, 100)
    data_y_range = (0, 100)
    if tacticai_predictions:
        attackers = [p for p in tacticai_predictions if p.get("is_attacker")]
        if attackers:
            top = max(attackers, key=lambda p: p.get("probability", 0))
            top_attacker_pos = top.get("position")
        # 计算实际数据范围，用于自适应像素映射
        xs = [p["position"][0] for p in tacticai_predictions]
        ys = [p["position"][1] for p in tacticai_predictions]
        if xs:
            data_x_range = (min(xs), max(xs))
        if ys:
            data_y_range = (min(ys), max(ys))

    # 字体路径（无盘符相对路径）
    font_rel = _filter_path(str(_FONT_DST))

    # 写文本文件
    title_file = _filter_path(_write_textfile(match_info))
    end_file = _filter_path(_write_textfile("AI ⚽ 角球翻译官"))

    if mg_clips and any(mg_clips.values()):
        # ====== NEW: Clip-based composition (MG + freeze-frame + real) ======
        print(f"[video_overlay] Clip-based path: {len([v for v in mg_clips.values() if v])} MG clips available")
        _TMP_DIR.mkdir(parents=True, exist_ok=True)
        seg_clips = []

        for i, seg in enumerate(timeline):
            seg_dur = seg["end"] - seg["start"]
            seg_raw = str(_TMP_DIR / f"_raw_{i:03d}_{uuid.uuid4().hex[:6]}.mp4")
            seg_out = str(_TMP_DIR / f"_seg_{i:03d}_{uuid.uuid4().hex[:6]}.mp4")

            # Step 1: create base clip
            if seg.get("visual_type") == "ai_scene" and mg_clips and mg_clips.get(i):
                print(f"[video_overlay] Seg {i}: MG clip ({seg_dur:.1f}s)")
                _trim_or_loop_clip(mg_clips[i], seg_dur, seg_raw)
            elif seg.get("visual_type") == "highlight" and seg.get("visual"):
                print(f"[video_overlay] Seg {i}: freeze-frame ({seg_dur:.1f}s)")
                _create_highlight_freeze(video_path, seg, seg_raw)
            else:
                print(f"[video_overlay] Seg {i}: raw clip ({seg_dur:.1f}s, type={seg.get('visual_type')})")
                _trim_clip(video_path, seg["start"], seg_dur, seg_raw)

            # Step 2: add overlays (speaker label, border, highlight, subtitle)
            _add_segment_overlays(seg_raw, seg, seg_out, font_rel,
                                  top_attacker_pos, data_x_range, data_y_range)

            seg_clips.append(seg_out)

        # ====== Build opening clip ======
        opening = _create_opening_clip(str(video_path), _TMP_DIR)

        # ====== Concatenate all clips ======
        concat_list = _TMP_DIR / "_concat_list.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            if opening:
                f.write(f"file '{Path(opening).as_posix()}'\n")
            for clip in seg_clips:
                f.write(f"file '{Path(clip).as_posix()}'\n")

        # Replace the direct filter approach with clip-based composition
        temp_concat = _TMP_DIR / f"_concat_{uuid.uuid4().hex[:8]}.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "medium", "-crf", "22",
            str(temp_concat),
        ], capture_output=True, check=True)

        # Add audio to concatenated video
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(temp_concat),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ], capture_output=True, check=True)

        # Cleanup
        temp_concat.unlink(missing_ok=True)
        for clip in seg_clips:
            Path(clip).unlink(missing_ok=True)
        if opening:
            Path(opening).unlink(missing_ok=True)

        return str(output_path)

    # ====== EXISTING: Filter-based composition (unchanged) ======
    filters = []

    # 标题卡：前 2.5 秒
    filters.append(
        f"drawtext=x=(w-text_w)/2:y=50:fontfile={font_rel}:"
        f"textfile={title_file}:"
        f"fontsize=36:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=8:"
        f"enable='between(t,0,2.5)'"
    )

    # 尾卡：最后 2 秒
    end_start = max(0, total_dur - 2)
    filters.append(
        f"drawtext=x=(w-text_w)/2:y=(h-text_h)/2:fontfile={font_rel}:"
        f"textfile={end_file}:"
        f"fontsize=48:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=12:"
        f"enable='between(t,{end_start},{total_dur})'"
    )

    # 逐句边框色 + 角标 + 内容字幕
    for seg in timeline:
        s = seg["start"]
        e = seg["end"]
        color = "red" if seg["speaker"] == "A" else "blue"
        label = "懂哥" if seg["speaker"] == "A" else "小白"
        marker = "●" if seg["speaker"] == "A" else "○"

        label_file = _filter_path(_write_textfile(f"{marker} {label}"))
        # 每句对话内容作为字幕（底部居中，可读性优先）
        subtitle_file = _filter_path(_write_textfile(seg["text"]))

        # 四边彩色边框（4px）
        for edge in ['top', 'bottom', 'left', 'right']:
            if edge == 'top':
                box = f"drawbox=x=0:y=0:w=1280:h=4:color={color}@0.8:t=fill"
            elif edge == 'bottom':
                box = f"drawbox=x=0:y=716:w=1280:h=4:color={color}@0.8:t=fill"
            elif edge == 'left':
                box = f"drawbox=x=0:y=0:w=4:h=720:color={color}@0.8:t=fill"
            elif edge == 'right':
                box = f"drawbox=x=1276:y=0:w=4:h=720:color={color}@0.8:t=fill"
            filters.append(f"{box}:enable='between(t,{s},{e})'")

        # 角标（左上角）
        filters.append(
            f"drawtext=x=10:y=10:fontfile={font_rel}:"
            f"textfile={label_file}:"
            f"fontsize=24:fontcolor={color}:box=1:boxcolor=black@0.5:boxborderw=4:"
            f"enable='between(t,{s},{e})'"
        )

        # 高亮圈：优先用 LLM 的 visual 指令，没有则 A 段自动高亮 top attacker
        highlight_pos = None
        visual = seg.get("visual", "")
        if visual and visual.startswith("highlight"):
            m_pos = re.search(r'pos=\(?([\d.]+)\s*,?\s*([\d.]+)', visual)
            if m_pos:
                highlight_pos = (float(m_pos.group(1)), float(m_pos.group(2)))
        # 回退：懂哥解释时自动高亮 TacticAI 最强接球点
        if highlight_pos is None and seg["speaker"] == "A" and top_attacker_pos:
            highlight_pos = tuple(top_attacker_pos)

        if highlight_pos:
            px, py = _field_to_pixel(highlight_pos[0], highlight_pos[1],
                                     data_x_range, data_y_range)
            filters.append(
                f"drawtext=x={px-18}:y={py-18}:fontfile={font_rel}:"
                f"text='●':fontsize=36:fontcolor=red@0.45:"
                f"enable='between(t,{s},{e})'"
            )

    # 组装滤镜链：zoompan（摄像机运动）→ overlays（边框/字幕）
    zoompan_filter = _build_zoompan(total_dur) if total_dur > 3 else ""
    if zoompan_filter:
        filter_str = zoompan_filter + "," + ",".join(filters)
    else:
        filter_str = ",".join(filters)

    # Step 1: 叠加滤镜（循环视频以匹配音频时长，去原音频）
    cmd_filter = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",  # 循环视频直到够长
        "-i", str(video_path),
        "-vf", filter_str,
        "-an",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "22",
        "-t", str(total_dur),
        str(temp_video),
    ]

    result = subprocess.run(cmd_filter, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 滤镜失败:\n{result.stderr}")

    # Step 2: 替换音频
    cmd_audio = [
        "ffmpeg", "-y",
        "-i", str(temp_video),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd_audio, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 音频合成失败:\n{result.stderr}")

    temp_video.unlink(missing_ok=True)
    return str(output_path)
