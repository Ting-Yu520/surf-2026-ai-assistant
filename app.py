"""
SURF-2026-0154 端到端 Demo v4 — Agent-Based Architecture

6 Agent 协作管线：
① VideoAnalyzer → ② TacticalExtractor → ③ CommentaryGen
                                           ↙              ↘
                         ④ VoiceGen (parallel)  ⑤ VideoComposer (parallel)
                                           ↘              ↙
                                   ⑥ Fusion → 最终视频
"""
import streamlit as st
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.interfaces import AgentInput
from agents.fusion.agent import FusionAgent

DATA = ROOT / "src" / "data"
VIDEO_DIR = ROOT / "data" / "videos"

st.set_page_config(page_title="SURF-2026 · AI 角球翻译官 v4", page_icon="⚽", layout="wide")

# ── 样式 ──
st.markdown("""
<style>
.pipeline {display:flex;gap:8px;margin:0.5rem 0;flex-wrap:wrap}
.pipeline .step{flex:1;min-width:70px;text-align:center;padding:8px 6px;border-radius:8px;font-size:0.7rem}
.step-1{background:#e3f2fd;border:1px solid #90caf9}
.step-2{background:#fff3e0;border:1px solid #ffcc80}
.step-3{background:#e8f5e9;border:1px solid #a5d6a7}
.step-4{background:#f3e5f5;border:1px solid #ce93d8}
.step-5{background:#fce4ec;border:1px solid #f48fb1}
.step-6{background:#e0f2f1;border:1px solid #80cbc4}
.duo-a{color:#d32f2f;font-weight:600}
.duo-b{color:#1976d2;font-weight:600}
.story-card{background:#fafafa;border:1px solid #e0e0e0;border-radius:10px;padding:1.2rem 1.5rem;line-height:1.8}
</style>
""", unsafe_allow_html=True)

# ── 管线图 ──
st.markdown('<div class="pipeline">'
    '<div class="step step-1">🔍 ①VLM<br><small>帧分析</small></div>'
    '<div class="step step-2">📊 ②Tactic<br><small>数据提取</small></div>'
    '<div class="step step-3">🎤 ③LLM<br><small>二人转</small></div>'
    '<div class="step step-4">🔊 ④TTS<br><small>配音</small></div>'
    '<div class="step step-5">🎬 ⑤合成<br><small>视频</small></div>'
    '<div class="step step-6">🧠 ⑥Fusion<br><small>融合输出</small></div>'
    '</div>', unsafe_allow_html=True)

st.markdown("""<div style='text-align:center;padding:0.2rem 0 1rem 0'>
    <h1 style='margin:0;font-size:1.6rem'>⚽ AI 角球翻译官 — 6 Agent 架构 (v4)</h1>
    <p style='color:#666;font-size:0.85rem;margin:0.2rem 0 0 0'>
        VLM 帧分析 → 战术提取 → 二人转生成 → TTS 配音 → 视频合成 → 决策融合
    </p>
</div>""", unsafe_allow_html=True)

st.divider()

# ── 加载数据集 ──
with open(DATA / "corner_kicks_2026.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)

entries = dataset["entries"]

selected = st.selectbox(
    "选择角球场景",
    [f"#{e['id'].replace('wc2026-corner-','')} {e['match']} — {e['goal_scorer']} ({e['minute']}')" for e in entries],
    help="从 2026 世界杯角球数据集中选择一个"
)

eid = f"wc2026-corner-{selected.split('#')[1].split()[0]}"
entry = next(e for e in entries if e["id"] == eid)

st.divider()

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📹 输入数据")
    st.json({
        "entry_id": eid,
        "match": entry["match"],
        "minute": entry["minute"],
        "score": entry.get("score_at_time", ""),
        "corner_type": entry.get("corner_type", ""),
        "goal_scorer": entry["goal_scorer"],
        "tactical_note": entry.get("tactical_note", ""),
    })

    video_path = None
    for f in VIDEO_DIR.glob(f"{eid}*.mp4"):
        video_path = str(f)
        break

    if video_path:
        st.markdown("#### 📹 原始比赛视频")
        st.video(video_path)

with col2:
    st.markdown("### 🎬 AI 管线输出")

    if st.button("🚀 全自动 6 Agent 管线", use_container_width=True, type="primary"):
        with st.status("6 Agent 协作中...", expanded=True) as status:
            st.write("① VideoAnalyzer: VLM 关键帧分析...")
            st.write("② TacticalExtractor: Phase 1 战术数据提取...")

            fusion = FusionAgent()
            result = fusion.run(AgentInput(data={
                "video_path": video_path,
                "corner_entry": entry,
                "output_prefix": f"demo_{eid}",
            }))

            traces = result.data.get("agent_traces", [])
            for t in traces:
                agent_name = t.get("agent", "?")
                t_status = t.get("status", "?")
                emoji = "✅" if t_status == "ok" else "⚠️"
                st.write(f"{emoji} {agent_name}: {t_status}")

            status.update(label="✅ 6 Agent 管线完毕！", state="complete")

        # 视频优先
        output_video = result.data.get("output_video")
        if output_video and Path(output_video).exists():
            st.markdown("#### 📺 最终科普视频")
            st.video(output_video)

        # 脚本
        script = result.data.get("script", "")
        if script:
            st.markdown("#### 📝 二人转脚本")
            lines = script.split("\n")
            html_lines = []
            for l in lines:
                if l.startswith("A:"):
                    html_lines.append(f'<p class="duo-a">🧑 懂哥：{l[2:].strip()}</p>')
                elif l.startswith("B:"):
                    html_lines.append(f'<p class="duo-b">🤔 小白：{l[2:].strip()}</p>')
            st.markdown(f'<div class="story-card">{"".join(html_lines)}</div>', unsafe_allow_html=True)

        # 音频
        audio_path = result.data.get("audio_path")
        if audio_path and Path(audio_path).exists():
            st.markdown("#### 🎧 AI 配音音频")
            st.audio(audio_path)

    else:
        st.info("👈 左侧选择角球场景，点击按钮启动 6 Agent 管线")
        st.markdown("""
        **Agent 管线说明：**
        1. **VideoAnalyzer** — VLM (Gemini) 从视频关键帧提取战术信息
        2. **TacticalExtractor** — 处理 Phase 1 工具输出的真实战术数据
        3. **CommentaryGen** — LLM (DeepSeek) 生成双口相声科普脚本
        4. **VoiceGen** — Edge TTS 逐句配音
        5. **VideoComposer** — ffmpeg 视频合成 + MG 动画
        6. **Fusion** — 决策级融合，输出最终科普视频
        """)

st.divider()
st.caption("SURF-2026-0154 · Generative HCI for Sports Analytics · Agent Architecture v4 · 6 Agents | Multi-Modal | Late Fusion")
