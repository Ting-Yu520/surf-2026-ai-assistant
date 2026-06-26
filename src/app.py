"""
SURF-2026-0154 AI Tactical Translator — Streamlit App

端到端流程：
  上传角球视频 → VLM (Gemini) 提取 JSON → LLM (DeepSeek) 生成叙事
  → TTS (Edge) 配音 → 合成科普短视频
"""

import streamlit as st
import json
import time
import tempfile
from pathlib import Path

from pipeline import process_corner_kick
from config import OUTPUT_DIR

st.set_page_config(page_title="AI Tactical Translator · CORNER KICK", page_icon="⚽", layout="wide")

st.markdown("""
<style>
    .stButton > button { font-size: 1rem; font-weight: 600; padding: 0.5rem 2rem; border-radius: 8px; }
    .pipeline-box { background:#f8f9fa; border:1px solid #e0e0e0; border-radius:8px; padding:0.6rem 1rem; text-align:center; font-size:0.85rem; }
    .pipeline-active { border:2px solid #4a90d9; background:#f0f5ff; }
    .step-done { color: #2d8a2d; font-weight:600; }
    .story-card { background:#fafafa; border:1px solid #e0e0e0; border-radius:10px; padding:1.5rem; line-height:1.9; font-size:0.95rem; }
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown("""
    <div style="text-align:center; padding:0.5rem 0 0.5rem 0;">
        <h1 style="margin:0; font-size:1.8rem;">⚽ AI 角球战术翻译官</h1>
        <p style="color:#666; margin:0.2rem 0 0 0;">
            上传 2026 世界杯角球视频 → AI 生成人人都能懂的科普短视频
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 管线可视化 ──
    c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([1, 0.05, 1, 0.05, 1, 0.05, 1, 0.05, 1])
    with c1:
        st.markdown('<div class="pipeline-box">📹<br><b>上传视频</b></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div style="text-align:center;color:#aaa;">→</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="pipeline-box">🔍<br><b>Gemini<br>分析</b></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div style="text-align:center;color:#aaa;">→</div>', unsafe_allow_html=True)
    with c5:
        st.markdown('<div class="pipeline-box">🧠<br><b>DeepSeek<br>叙事</b></div>', unsafe_allow_html=True)
    with c6:
        st.markdown('<div style="text-align:center;color:#aaa;">→</div>', unsafe_allow_html=True)
    with c7:
        st.markdown('<div class="pipeline-box">🎙️<br><b>AI 配音</b></div>', unsafe_allow_html=True)
    with c8:
        st.markdown('<div style="text-align:center;color:#aaa;">→</div>', unsafe_allow_html=True)
    with c9:
        st.markdown('<div class="pipeline-box pipeline-active">📺<br><b>科普视频</b></div>', unsafe_allow_html=True)

    st.divider()

    # ── 输入区 ──
    tab1, tab2 = st.tabs(["📹 上传视频", "📝 手工 JSON (调试用)"])

    uploaded_video = None
    manual_json = None

    with tab1:
        st.markdown("### 上传角球视频片段")
        st.caption("支持 mp4 / mov / avi。选择 2026 世界杯中的角球瞬间（15-30 秒最佳）。")
        uploaded_file = st.file_uploader(
            "选择视频文件", type=["mp4", "mov", "avi"],
            label_visibility="collapsed",
        )
        if uploaded_file:
            # 保存到临时文件
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp.write(uploaded_file.read())
            uploaded_video = tmp.name
            st.video(uploaded_file)
            st.success(f"✅ 视频已上传 ({uploaded_file.size / 1024:.1f} KB)")

    with tab2:
        st.markdown("### 手工输入角球 JSON")
        st.caption("跳过 VLM 步骤，直接使用手工 JSON 测试 Prompt 和配音效果。")
        manual_json_str = st.text_area(
            "角球战术 JSON", height=250, label_visibility="collapsed",
            placeholder='{"scenario": "corner_kick", ...}',
        )
        if manual_json_str.strip():
            try:
                manual_json = json.loads(manual_json_str)
                st.success("✅ JSON 格式有效")
            except json.JSONDecodeError as e:
                st.error(f"JSON 无效: {e}")

    st.divider()

    # ── 执行按钮 ──
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        can_run = bool(uploaded_video or manual_json)
        run = st.button(
            "🎙️ 生成 AI 科普短视频",
            use_container_width=True,
            disabled=not can_run,
        )

    # ── 输出区 ──
    st.divider()

    if run:
        progress = st.status("处理中...", expanded=True)

        # Step 1
        progress.write("🔍 Step 1/4: Gemini VLM 分析角球场景...")
        t0 = time.time()

        result = process_corner_kick(
            video_path=uploaded_video,
            scenario_json=manual_json,
        )
        progress.write(f"✅ Step 1/4 完成 ({time.time()-t0:.1f}s)")

        # 显示 JSON
        with st.expander("📊 提取的战术 JSON"):
            st.json(result["json_data"])

        # 显示叙事
        st.markdown("### 📖 AI 生成的通俗故事")
        st.markdown(f'<div class="story-card">{result["narration_text"]}</div>', unsafe_allow_html=True)

        # 播放音频
        if result.get("audio_path"):
            st.markdown("### 🎙️ AI 配音")
            st.audio(result["audio_path"])

        # 播放视频
        if result.get("output_video") and Path(result["output_video"]).exists():
            st.markdown("### 📺 最终科普短视频")
            st.video(result["output_video"])
            st.success(f"🎉 全部完成！总耗时 {result['elapsed']:.1f}s")

    else:
        st.markdown("""
        <div style="background:#fafafa; border:1px dashed #ddd; border-radius:10px;
             padding:2rem; text-align:center; color:#999;">
            <p style="font-size:2rem;">⚽</p>
            <p>上传一段 2026 世界杯角球视频<br>点击按钮，看 AI 如何让它变得人人能懂</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()
    st.markdown("""
    <div style="text-align:center; color:#999; font-size:0.75rem;">
        SURF-2026-0154 · Generative HCI for Sports Analytics · Corner Kick Demo<br>
        Ting-Yu (IMIS, XJTLU) · Dr. Nanlin Jin & Dr. Thomas Selig
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
