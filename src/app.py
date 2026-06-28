"""
SURF-2026-0154 端到端 Demo v3
流程：数据集 → Phase 1 (TacticAI 专业 JSON) → Phase 2 (二人转解说) → 视频
"""

import streamlit as st
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pipeline import process_corner_kick
from phase_bridge import sample_tacticai_output, tacticai_to_phase2, format_for_prompt

DATA = ROOT / "src" / "data"
VIDEO_DIR = ROOT / "data" / "videos"
OUTPUTS = ROOT / "outputs"

st.set_page_config(page_title="SURF-2026 · AI 角球翻译官", page_icon="⚽", layout="wide")
st.markdown("""
<style>
.pipeline {display:flex;gap:8px;margin:0.5rem 0;flex-wrap:wrap}
.pipeline .step{flex:1;min-width:80px;text-align:center;padding:8px 6px;border-radius:8px;font-size:0.75rem}
.step-1{background:#e3f2fd;border:1px solid #90caf9}
.step-2{background:#fff3e0;border:1px solid #ffcc80}
.step-3{background:#e8f5e9;border:1px solid #a5d6a7}
.step-4{background:#f3e5f5;border:1px solid #ce93d8}
.duo-a{color:#d32f2f;font-weight:600}
.duo-b{color:#1976d2;font-weight:600}
.story-card{background:#fafafa;border:1px solid #e0e0e0;border-radius:10px;padding:1.2rem 1.5rem;line-height:1.8}
</style>
""", unsafe_allow_html=True)

# ── 饼图式管线 ──
st.markdown('<div class="pipeline">'
    '<div class="step step-1">📹 ①比赛视频<br><small>原始片段</small></div>'
    '<div class="step step-2">📊 ②TacticAI 分析<br><small>专业 JSON</small></div>'
    '<div class="step step-3">🎤 ③二人转生成<br><small>科普文本</small></div>'
    '<div class="step step-4">📺 ④视频合成<br><small>最终输出</small></div>'
    '</div>', unsafe_allow_html=True)

st.markdown("""<div style='text-align:center;padding:0.2rem 0 1rem 0'>
    <h1 style='margin:0;font-size:1.6rem'>⚽ AI 角球翻译官 — 端到端管线演示</h1>
    <p style='color:#666;font-size:0.85rem;margin:0.2rem 0 0 0'>
        数据集 JSON → TacticAI 专业分析 → 二人转通俗解说 → AI 配音视频
    </p>
</div>""", unsafe_allow_html=True)

st.divider()

# ── 加载数据集 ──
with open(DATA / "corner_kicks_2026.json", "r", encoding="utf-8") as f:
    dataset = json.load(f)
with open(DATA / "corner_articles.json", "r", encoding="utf-8") as f:
    articles = json.load(f)

entries = dataset["entries"]

# 选一个角球
selected = st.selectbox(
    "选择角球场景",
    [f"#{e['id'].replace('wc2026-corner-','')} {e['match']} — {e['goal_scorer']} ({e['minute']}')" for e in entries],
    help="从 2026 世界杯角球数据集中选择一个"
)

eid = f"wc2026-corner-{selected.split(' #')[1].split(' ')[0] if '#' in selected else selected.split('—')[0].strip().split('#')[1]}"
entry = next(e for e in entries if e["id"] == eid)

st.divider()

# ── 两列：Phase 1 左 | Phase 2 右 ──
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📊 Phase 1：专业战术数据")
    st.caption("TacticAI 从比赛视频中提取的角球分析数据（模拟或真实 API 输出）")

    # 显示原始战术数据
    st.json({
        "entry_id": eid,
        "match": entry["match"],
        "minute": entry["minute"],
        "score": entry.get("score_at_time", ""),
        "corner_type": entry.get("corner_type", ""),
        "goal_scorer": entry["goal_scorer"],
        "goal_type": entry.get("goal_type", ""),
        "tactical_note": entry.get("tactical_note", ""),
    })

    # TacticAI 分析模拟
    st.markdown("#### 🔮 TacticAI 角球分析")
    st.caption("接收者预测 + 攻防球员概率分布")

    # 生成模拟 TacticAI 输出
    tacticai_out = sample_tacticai_output()
    phase2_input = tacticai_to_phase2(tacticai_out)

    # 展示 Top-3 预测
    preds = tacticai_out["predictions"]
    top3_attackers = [p for p in preds if p["is_attacker"]][:3]
    top3_defenders = [p for p in preds if not p["is_attacker"]][:3]

    st.markdown("**🏃 可能接球者 (Top 3)**")
    for p in top3_attackers:
        st.markdown(f"  球员 {p['player_index']} — 概率 **{p['probability']*100:.0f}%** — 位置 ({p['position'][0]:.0f}, {p['position'][1]:.0f})")

    st.markdown("**🛡️ 防守方关键球员 (Top 3)**")
    for p in top3_defenders:
        st.markdown(f"  球员 {p['player_index']} — 概率 **{p['probability']*100:.0f}%** — 位置 ({p['position'][0]:.0f}, {p['position'][1]:.0f})")

    # 视频源
    video_path = None
    for f in VIDEO_DIR.glob(f"{eid}*.mp4"):
        video_path = str(f)
        break

    if not video_path:
        # 查找任何包含此 eid 的视频
        for f in VIDEO_DIR.glob("*.mp4"):
            if eid.replace("wc2026-corner-", "") in f.stem:
                video_path = str(f)
                break

    if video_path:
        st.markdown("#### 📹 原始比赛视频")
        st.video(video_path)

with col2:
    st.markdown("### 🎤 Phase 2：AI 科普生成")
    st.caption("专业数据 → 二人转相声 → AI 配音")

    if st.button("🎙️ 生成二人转科普解说", use_container_width=True, type="primary"):
        # 构造文章底本
        article_text = format_for_prompt(phase2_input, entry)

        with st.status("管线运行中...", expanded=True) as status:
            st.write("① TacticAI 分析完成 → 数据已加载")
            st.write("② 二人转 Prompt 生成中...")

            result = process_corner_kick(article_text=article_text, output_prefix=f"demo_{eid}")

            st.write(f"③ 解说完成 ({len(result.get('script',''))} 字)")
            st.write(f"④ TTS 配音完成 → 音频已就绪")

            status.update(label="✅ 管线运行完毕！", state="complete")

        # 显示二人转脚本
        st.markdown("#### 📝 二人转脚本")
        script = result.get("script", "")
        if script:
            lines = script.split("\n")
            html_lines = []
            for l in lines:
                if l.startswith("A:"):
                    html_lines.append(f'<p class="duo-a">🧑 懂哥：{l[2:].strip()}</p>')
                elif l.startswith("B:"):
                    html_lines.append(f'<p class="duo-b">🤔 小白：{l[2:].strip()}</p>')
            st.markdown(f'<div class="story-card">{"".join(html_lines)}</div>', unsafe_allow_html=True)

        # 音频
        audio_path = result.get("audio_path")
        if audio_path:
            st.markdown("#### 🎧 AI 配音音频")
            st.audio(audio_path)

        # 视频
        output_video = result.get("output_video")
        if output_video:
            st.markdown("#### 📺 最终科普视频")
            st.video(output_video)

    else:
        st.info("👈 左侧选择角球场景，点击按钮生成")
        st.markdown("""
        **管线流程说明：**
        1. **数据集** → 从 2026 世界杯角球数据集选择一场
        2. **TacticAI 分析** → 模拟专业角球战术分析（球员位置、接球概率）
        3. **二人转 Prompt** → A（懂哥）+ B（小白）对抗式科普
        4. **TTS 配音 + 视频** → AI 语音 + 画面合成
        """)

st.divider()
st.caption("SURF-2026-0154 · Generative HCI for Sports Analytics · End-to-End Demo v3")
