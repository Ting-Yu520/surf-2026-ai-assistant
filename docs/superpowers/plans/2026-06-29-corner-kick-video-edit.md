# 角球解说视频剪辑实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task.

**Goal:** 管线输出视频（非音频），二人转脚本引用 TacticAI 彩蛋，视频按文本剪辑带角色区分

**Architecture:** Prompt 两段式（事实+彩蛋）→ LLM → 逐句 TTS 获取时间轴 → ffmpeg 按时间轴叠边框/角标/高光 → 最终视频

**Tech Stack:** ffmpeg (openmontage video-edit), edge-tts, Python

---

### Task 1: phase_bridge.py — 两段式格式化

**Modify:** `src/phase_bridge.py:82-104`

- [ ] **Step 1: 重写 format_for_prompt() 为两段输出**

```python
def format_for_prompt(phase2_input: dict, corner_entry: Optional[dict] = None) -> dict:
    """
    返回两段式结构：
      fact_section: 比赛事实 + 战术描述
      tactic_section: TacticAI 彩蛋数据（可选）
    """
    fact_lines = []
    if corner_entry:
        match = corner_entry.get("match", "?")
        minute = corner_entry.get("minute", "?")
        scorer = corner_entry.get("goal_scorer", "?")
        note = corner_entry.get("tactical_note", "")
        fact_lines.append(f"比赛：{match}")
        fact_lines.append(f"时间：{minute}'")
        fact_lines.append(f"进球者：{scorer}")
        if note:
            fact_lines.append(f"战术描述：{note}")

    tactic_lines = []
    att = phase2_input.get("attacking_players", "?")
    deff = phase2_input.get("defending_players", "?")
    prob = phase2_input.get("top_receiver_probability", "?")
    tactic_lines.append(f"攻击球员：{att}人")
    tactic_lines.append(f"防守球员：{deff}人")
    tactic_lines.append(f"最可能接球概率：{prob}%")
    pos = phase2_input.get("top_receiver_position", [])
    if pos:
        tactic_lines.append(f"最可能接球位置：({pos[0]:.0f}, {pos[1]:.0f})")
    dpos = phase2_input.get("top_defender_position", [])
    if dpos:
        tactic_lines.append(f"防守方关键位置：({dpos[0]:.0f}, {dpos[1]:.0f})")

    return {
        "fact_section": "\n".join(fact_lines),
        "tactic_section": "\n".join(tactic_lines),
    }
```

- [ ] **Step 2: 更新 app.py 中调用处，解包两段**

```python
formatted = format_for_prompt(phase2_input, entry)
article_text = f"{formatted['fact_section']}\n\n{formatted['tactic_section']}"
```

- [ ] **Step 3: 验证**

```bash
cd /d/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && D:/Tools/Python314/python -c "
from src.phase_bridge import sample_tacticai_output, tacticai_to_phase2, format_for_prompt
from src.data.corner_kicks_2026 import entries
out = tacticai_to_phase2(sample_tacticai_output())
entry = entries[0]
result = format_for_prompt(out, entry)
print('=== FACT ===')
print(result['fact_section'])
print('=== TACTIC ===')
print(result['tactic_section'])
"
```
Expected: 清晰的两段式输出

---

### Task 2: prompts/corner_kick.py — 战术彩蛋指令

**Modify:** `src/prompts/corner_kick.py`

- [ ] **Step 1: DUO_SYSTEM_PROMPT 末尾新增角色指令**

在 `## 角球名词解释` 之后、`## 输出格式` 之前插入：

```
## 战术彩蛋
A 可以偶尔引用战术分析数据来显摆专业度，如：
"TacticAI 算出来这个球员有 45% 的概率接到球"
但整段脚本最多用 2 次，重点是让故事有意思。
```

- [ ] **Step 2: 更新 DUO_USER_TEMPLATE 为两段入参**

```python
DUO_USER_TEMPLATE = """请根据下面的足球比赛信息，写一段双口相声科普脚本。

## 比赛事实
{fact_section}

## 战术彩蛋（可选）
下面这些战术分析数据 A 可偶尔引用：
{tactic_section}

## 要求
- 4-6 轮对话
- A 上来先卖弄知识
- B 一脸懵逼，逼 A 解释人话
- 最后 B 表示懂了
- 纯对话，不要叙述"""
```

- [ ] **Step 3: 更新 build_duo_prompt 签名**

```python
def build_duo_prompt(formatted: dict) -> tuple[str, str]:
    return (
        DUO_SYSTEM_PROMPT,
        DUO_USER_TEMPLATE.format(
            fact_section=formatted["fact_section"],
            tactic_section=formatted["tactic_section"],
        ),
    )
```

---

### Task 3: video_overlay.py — ffmpeg 剪辑管线（核心）

**Rewrite:** `src/video_overlay.py`

核心思路：接收脚本（A/B 行列表）+ 时间轴（逐句偏移秒数）+ 视频源，输出 ffmpeg 命令逐段剪辑。

- [ ] **Step 1: 编写 parse_script() — 从 LLM 输出中提取 A/B 行**

```python
import re
from typing import List, Dict

def parse_script(script: str) -> List[Dict[str, str]]:
    """解析 LLM 输出，返回 [{speaker: 'A'|'B', text: '...'}, ...]"""
    lines = []
    for line in script.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^([AB]):\s*(.+)$', line)
        if m:
            lines.append({"speaker": m.group(1), "text": m.group(2).strip()})
    return lines
```

- [ ] **Step 2: 编写时间轴构建器**

```python
def build_timeline(
    segments: List[Dict],
    seg_durations: List[float],
    gap: float = 0.3
) -> List[Dict]:
    """逐句 TTS 结果组装时间轴，返回每句的 start/end 秒数"""
    timeline = []
    cursor = 0.0
    for seg, dur in zip(segments, seg_durations):
        timeline.append({
            "speaker": seg["speaker"],
            "text": seg["text"],
            "start": cursor,
            "end": cursor + dur,
        })
        cursor += dur + gap
    return timeline
```

- [ ] **Step 3: 编写 ffmpeg 命令生成器**

```python
import subprocess

def create_titled_video(
    video_path: str,
    audio_path: str,
    timeline: List[Dict],
    output_path: str,
    match_info: str = "⚽ AI 角球战术解说",
):
    """
    使用 ffmpeg 生成最终视频。

    每一帧都通过 drawtext 检测当前时间属于哪段对话，
    从而绘制对应颜色的边框和角标。
    """
    width = 1280
    height = 720
    
    # 构建 drawtext 滤镜链
    # 因为 ffmpeg 的 drawtext 不支持条件分支，我们用 overlay 的 enable 参数
    # 在时间轴上分别叠加不同颜色的边框 + 角标
    
    filters = []
    
    # 对每个 segment 创建两个叠加层：边框 + 角标
    for i, seg in enumerate(timeline):
        start = seg["start"]
        end = seg["end"]
        color = "red" if seg["speaker"] == "A" else "blue"
        label = "懂哥" if seg["speaker"] == "A" else "小白"
        emoji = "🔴" if seg["speaker"] == "A" else "🔵"
        
        # 边框：drawbox 在四边
        border = (
            f"drawbox=x=0:y=0:w={width}:h=4:color={color}@0.8:t=fill:enable='between(t,{start},{end})',"
            f"drawbox=x=0:y={height-4}:w={width}:h=4:color={color}@0.8:t=fill:enable='between(t,{start},{end})',"
            f"drawbox=x=0:y=0:w=4:h={height}:color={color}@0.8:t=fill:enable='between(t,{start},{end})',"
            f"drawbox=x={width-4}:y=0:w=4:h={height}:color={color}@0.8:t=fill:enable='between(t,{start},{end})'"
        )
        
        # 角标（左上角）
        label_filter = (
            f"drawtext=x=10:y=10:fontfile={FONT}:text='{emoji} {label}':"
            f"fontsize=24:fontcolor={color}:box=1:boxcolor=black@0.5:boxborderw=4:"
            f"enable='between(t,{start},{end})'"
        )
        
        filters.append(border)
        filters.append(label_filter)
    
    # 合并所有滤镜，用逗号连接
    filter_complex = ",".join(filters)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-preset", "medium",
        "-crf", "22",
        output_path,
    ]
    
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path
```

- [ ] **Step 4: 添加标题卡和尾卡**

使用 ffmpeg 的 `drawtext` 在开头几秒叠加标题。

```python
# 标题：前 3 秒，上中位置
title_filter = (
    f"drawtext=x=(w-text_w)/2:y=50:fontfile={FONT}:text='{title}':"
    f"fontsize=36:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=8:"
    f"enable='between(t,0,2.5)'"
)
# 尾卡：最后 2 秒
end_filter = (
    f"drawtext=x=(w-text_w)/2:y=(h-text_h)/2:fontfile={FONT}:text='AI 角球翻译官':"
    f"fontsize=48:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=12:"
    f"enable='between(t,{total_dur-2},{total_dur})'"
)
```

- [ ] **Step 5: 验证 ffmpeg 可用**

```bash
which ffmpeg || echo "需要安装 ffmpeg"
```

---

### Task 4: pipeline.py — 逐句 TTS + 新 video_overlay

**Modify:** `src/pipeline.py`

- [ ] **Step 1: 重写 Step 3-5 为逐句时间轴模式**

```python
# ====== Step 3: 逐句 TTS + 时间轴 ======
segments = parse_script(script)  # [{speaker, text}, ...]

# 每句生成 TTS
tts_segments = generate_timeline_audio(
    [{"narration": f"{s['speaker']}: {s['text']}"} for s in segments],
    str(OUTPUT_DIR / f"{prefix}audio_segs"),
)

# 合并音频
concat_audio_segments(tts_segments, str(OUTPUT_DIR / f"{prefix}narration.mp3"))

# 组装时间轴
timeline = build_timeline(segments, [s["actual_duration_sec"] for s in tts_segments])
```

- [ ] **Step 2: 更新 Step 5 调用新 video_overlay**

```python
# ====== Step 5: 视频合成 ======
if video_path:
    from video_overlay import create_titled_video
    output_video = str(OUTPUT_DIR / f"{prefix}corner_story.mp4")
    create_titled_video(
        video_path=video_path,
        audio_path=str(OUTPUT_DIR / f"{prefix}narration.mp3"),
        timeline=timeline,
        output_path=output_video,
        match_info=f"{entry.get('match','')} — {entry.get('goal_scorer','')} ({entry.get('minute','')}')",
    )
    result['output_video'] = output_video
```

- [ ] **Step 3: 传 entry 进 process_corner_kick**

```python
def process_corner_kick(
    video_path: str = None,
    article_text: str = None,
    output_prefix: str = "",
    corner_entry: Optional[dict] = None,  # NEW
) -> dict:
```

---

### Task 5: app.py — 打通视频管线

**Modify:** `src/app.py:113-171`

- [ ] **Step 1: 传入 video_path 和 corner_entry**

```python
result = process_corner_kick(
    article_text=article_text,
    output_prefix=f"demo_{eid}",
    video_path=video_path,  # 从上面找到的视频路径
    corner_entry=entry,
)
```

- [ ] **Step 2: 视频优先展示**

```python
# 生成成功后
output_video = result.get("output_video")
if output_video:
    st.markdown("#### 📺 最终科普视频")
    st.video(output_video)
    
st.markdown("#### 📝 二人转脚本")
# ... 脚本展示 ...

audio_path = result.get("audio_path")
if audio_path:
    st.markdown("#### 🎧 AI 配音音频（下载用）")
    st.audio(audio_path)
```

---

### Task 6: 运行验证

- [ ] **Step 1: 启动 Streamlit 并观察管线**

```bash
cd /d/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant
D:/Tools/Python314/python -m streamlit run src/app.py
```

- [ ] **Step 2: 选择角球场景，点击生成**

Expected: 管线执行 → 视频生成 → 视频自动播放，带彩色边框和角标
