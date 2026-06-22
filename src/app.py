"""
SURF-2026-0154 AI Tactical Assistant — Demo
============================================
演示流程：真实比赛瞬间 → AI 提取战术 JSON → LLM 生成通俗故事

设计原则：极简、两栏对比、真实数据。
"""

import streamlit as st
import json
import time
from anthropic import Anthropic

from config import (
    DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_API_KEY,
    API_TIMEOUT, MAX_TOKENS, TEMPERATURE, load_scenarios,
)
from prompts.templates import SYSTEM_PROMPT, build_user_prompt

# ── 页面 ───────────────────────────────────────────────
st.set_page_config(page_title="AI Tactical Translator", page_icon="⚽", layout="wide")

st.markdown("""
<style>
    .stButton > button { font-size: 1.05rem; font-weight: 600; padding: 0.5rem 2.5rem; border-radius: 8px; }
    .stTextArea textarea { font-family: 'Consolas','Monaco',monospace; font-size: 0.85rem; }
    .pipeline-box { background:#f8f9fa; border:1px solid #e0e0e0; border-radius:10px; padding:0.8rem 1.2rem; text-align:center; }
    .story-card { background:#fafafa; border:1px solid #e0e0e0; border-radius:10px; padding:1.5rem 1.8rem; line-height:1.9; font-size:0.95rem; color:#222; }
    .video-ref { background:#fffbf0; border:1px solid #f0d060; border-radius:6px; padding:0.5rem 1rem; font-size:0.85rem; margin:0.5rem 0; }
</style>
""", unsafe_allow_html=True)


# ── 辅助函数 ────────────────────────────────────────────
def validate_json(s: str) -> tuple[bool, dict | str]:
    try:
        data = json.loads(s)
        if not isinstance(data, dict):
            return False, f"JSON 必须是对象，不是 {type(data).__name__}"
        return True, data
    except json.JSONDecodeError as e:
        return False, f"JSON 格式错误（第{e.lineno}行）：{e.msg}"

def call_llm(api_key: str, data: dict) -> tuple[bool, str]:
    try:
        client = Anthropic(api_key=api_key, base_url=DEEPSEEK_BASE_URL, timeout=float(API_TIMEOUT))
        response = client.messages.create(
            model=DEEPSEEK_MODEL, max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_prompt(data)}],
        )
        parts = [b.text for b in response.content if hasattr(b, 'text')]
        return True, '\n\n'.join(parts) if parts else '(未生成文本)'
    except Exception as e:
        err = str(e)
        if "401" in err or "auth" in err.lower(): return False, "🔑 API Key 无效。"
        elif "429" in err: return False, "⏳ 请求太频繁，稍等几秒。"
        elif "timeout" in err.lower(): return False, "⏰ 请求超时，请重试。"
        return False, f"调用失败：{err[:300]}"


# ── 主界面 ──────────────────────────────────────────────
def main():
    # 标题
    st.markdown("""
    <div style="text-align:center; padding:0.5rem 0 0.5rem 0;">
        <h1 style="margin:0; font-size:1.8rem;">⚽ AI Tactical Translator</h1>
        <p style="color:#666; margin:0.2rem 0 0 0;">真实比赛瞬间 → 结构化战术数据 → <b>人人都能理解的故事</b></p>
    </div>
    """, unsafe_allow_html=True)

    # ── 三步流水线 ──
    c1, c2, c3, c4, c5 = st.columns([1, 0.1, 1, 0.1, 1])
    with c1:
        st.markdown('<div class="pipeline-box">📹 <b>Step 1</b><br><small>真实比赛片段<br>(公开视频)</small></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div style="text-align:center; font-size:1.5rem; color:#aaa; padding-top:0.5rem;">→</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="pipeline-box">📊 <b>Step 2</b><br><small>VLM 提取<br>战术 JSON</small></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div style="text-align:center; font-size:1.5rem; color:#aaa; padding-top:0.5rem;">→</div>', unsafe_allow_html=True)
    with c5:
        st.markdown('<div class="pipeline-box" style="border:2px solid #4a90d9;">📖 <b>Step 3</b><br><small>LLM 生成<br>通俗故事</small></div>', unsafe_allow_html=True)

    st.divider()

    # ── 场景选择 ──
    scenarios = load_scenarios()
    scenario_names = list(scenarios.keys())

    # 用 selectbox 做场景切换
    selected = st.selectbox(
        "选择演示场景",
        scenario_names,
        format_func=lambda x: x.split(' — ')[0] if ' — ' in x else x,
    )
    scenario = scenarios[selected]

    # ── 视频参考 ──
    video_ref = scenario.get("video_reference", "")
    match_info = f"{scenario.get('competition','')} · {scenario.get('date','')}"
    with st.expander(f"📹 视频参考：{match_info}", expanded=True):
        st.markdown(f"""
        **比赛：** {scenario.get('match', '')} — {scenario.get('competition', '')} ({scenario.get('date', '')})

        **🎬 视频连接：** {video_ref}

        **比赛背景：** {scenario.get('match_context', '')}
        """)
        # 关键战术洞察
        insight = scenario.get("key_tactical_insight", scenario.get("why_extraordinary", ""))
        if insight:
            st.info(f"💡 **核心战术亮点：** {insight}")

    # ── 两栏：左 JSON / 右 Story ──
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("### 📊 战术数据 (JSON)")
        st.caption("Step 2 产物 — VLM 从视频中提取的结构化数据。Phase 1 用模拟数据，Phase 2 替换为真实 VLM 输出。")

        json_str = json.dumps(scenario, indent=2, ensure_ascii=False)
        key = f"json_{selected}"
        if key not in st.session_state:
            st.session_state[key] = json_str

        edited = st.text_area(
            "战术数据", value=st.session_state[key], height=360,
            key=f"ta_{selected}", label_visibility="collapsed",
        )
        st.session_state[key] = edited

        # 关键数字高亮
        st.caption(
            f"⏱ {scenario.get('game_time','')}  "
            f"⚽ {scenario.get('score','')}  "
            f"🎯 预测成功率 {scenario.get('predicted_success_rate','')}"
        )

    with right:
        st.markdown("### 📖 通俗故事")
        st.caption("Step 3 产物 — LLM 将 JSON 转化为零足球知识门槛的情感叙事。")

        placeholder = st.empty()

        generate = st.button("🎙️ 生成 AI 解说", use_container_width=True)

        if generate:
            ok, result = validate_json(edited)
            if not ok:
                placeholder.error(result)
                st.stop()

            with st.spinner("AI 正在将战术数据转化为故事..."):
                t0 = time.time()
                success, output = call_llm(DEEPSEEK_API_KEY, result)
                elapsed = time.time() - t0

            if success:
                placeholder.markdown(f'<div class="story-card">{output}</div>', unsafe_allow_html=True)
                st.caption(f"⚡ {elapsed:.1f}s · {DEEPSEEK_MODEL}")
            else:
                placeholder.error(output)
        else:
            placeholder.markdown("""
            <div style="background:#fafafa; border:1px dashed #ddd; border-radius:10px;
                 padding:2rem 1.5rem; text-align:center; color:#999;">
                <p style="font-size:2rem; margin:0;">🎙️</p>
                <p style="margin:0.3rem 0 0 0;">点击左侧按钮<br><b>"生成 AI 解说"</b></p>
                <p style="font-size:0.8rem; margin:0.3rem 0 0 0; color:#ccc;">
                    左侧 JSON → 右侧故事
                </p>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.markdown("""
    <div style="text-align:center; color:#999; font-size:0.75rem;">
        SURF-2026-0154 · Generative HCI for Sports Analytics<br>
        Ting-Yu (IMIS, XJTLU) · Dr. Nanlin Jin & Dr. Thomas Selig
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
