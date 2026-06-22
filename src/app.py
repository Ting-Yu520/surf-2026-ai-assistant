"""
SURF-2026-0154 AI Tactical Assistant — Demo
============================================
核心演示：将计算机看到的"冰冷战术数据"转化为任何人都能理解的"温暖故事"。

设计原则：极简、两栏对比、一个按钮、清晰目的。
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
st.set_page_config(
    page_title="AI Tactical Translator",
    page_icon="⚽",
    layout="wide",
)

# ── 超轻量 CSS，只做排版不做主题 ────────────────────────
st.markdown("""
<style>
    .stButton > button {
        font-size: 1.05rem; font-weight: 600;
        padding: 0.5rem 2.5rem; border-radius: 8px;
    }
    .stTextArea textarea {
        font-family: 'Consolas','Monaco',monospace;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# ── 辅助函数 ────────────────────────────────────────────
def validate_json(json_str: str) -> tuple[bool, dict | str]:
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            return False, f"JSON 必须是对象，不是 {type(data).__name__}"
        return True, data
    except json.JSONDecodeError as e:
        return False, f"JSON 格式错误（第{e.lineno}行）：{e.msg}"

def call_llm(api_key: str, scenario_data: dict) -> tuple[bool, str]:
    try:
        client = Anthropic(api_key=api_key, base_url=DEEPSEEK_BASE_URL, timeout=float(API_TIMEOUT))
        user_prompt = build_user_prompt(scenario_data)
        response = client.messages.create(
            model=DEEPSEEK_MODEL, max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_parts = [b.text for b in response.content if hasattr(b, 'text')]
        return True, '\n\n'.join(text_parts) if text_parts else '(未生成文本)'
    except Exception as e:
        err = str(e)
        if "401" in err or "auth" in err.lower():
            return False, "🔑 API Key 无效。"
        elif "429" in err:
            return False, "⏳ 请求太频繁，稍等几秒。"
        elif "timeout" in err.lower():
            return False, "⏰ 请求超时，请重试。"
        else:
            return False, f"调用失败：{err[:300]}"


# ── 主界面 ──────────────────────────────────────────────
def main():
    # 标题行
    st.markdown("""
    <div style="text-align:center; padding:0.5rem 0 1rem 0;">
        <h1 style="margin:0; font-size:2rem;">⚽ AI Tactical Translator</h1>
        <p style="color:#666; font-size:0.95rem; margin:0.3rem 0 0 0;">
            Making professional sports data <b>accessible to everyone</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── 两栏：左输入 / 右输出 ──
    left, right = st.columns([1, 1], gap="large")

    # ============ 左栏：输入区 ============
    with left:
        st.markdown("### 📊 原始战术数据")
        st.caption("计算机视觉系统从比赛视频中提取的结构化数据——对普通人来说完全不可读。")

        # 场景选择
        scenarios = load_scenarios()
        scenario_name = st.selectbox(
            "选择场景",
            list(scenarios.keys()),
            label_visibility="collapsed",
        )
        scenario = scenarios[scenario_name]

        # JSON 编辑
        json_str = json.dumps(scenario, indent=2, ensure_ascii=False)
        key = f"json_{scenario_name}"
        if key not in st.session_state:
            st.session_state[key] = json_str

        edited_json = st.text_area(
            "战术数据 (JSON)",
            value=st.session_state[key],
            height=340,
            key=f"editor_{scenario_name}",
            label_visibility="collapsed",
        )
        st.session_state[key] = edited_json

        # 生成按钮
        generate = st.button("🎙️ 生成通俗解说", use_container_width=True)

        # 场景信息
        st.caption(
            f"⏱ {scenario.get('game_time','')}  "
            f"⚽ {scenario.get('score','')}  "
            f"🎯 成功率 {scenario.get('predicted_success_rate','')}"
        )

    # ============ 右栏：输出区 ============
    with right:
        st.markdown("### 🎤 人人都能理解的故事")
        st.caption("AI 将上面的 JSON 数据转化为完全不懂足球的人也能感受的故事。")

        output_placeholder = st.empty()

        if generate:
            # 检查 API Key
            effective_key = DEEPSEEK_API_KEY
            if not effective_key:
                output_placeholder.error("未找到 API Key。请检查 `.env` 文件。")
                st.stop()

            # 验证 JSON
            ok, result = validate_json(edited_json)
            if not ok:
                output_placeholder.error(result)
                st.stop()

            # 调用 LLM
            with st.spinner("AI 正在将数据转化为故事..."):
                t0 = time.time()
                success, llm_output = call_llm(effective_key, result)
                elapsed = time.time() - t0

            if success:
                # 渲染在干净的白色卡片中
                output_placeholder.markdown(f"""
                <div style="background:#fafafa; border:1px solid #e0e0e0;
                     border-radius:10px; padding:1.5rem 1.8rem; line-height:1.9;
                     font-size:0.95rem; color:#222;">
                {llm_output}
                </div>
                """, unsafe_allow_html=True)
                st.caption(f"⚡ 生成耗时 {elapsed:.1f}s · 模型 {DEEPSEEK_MODEL}")
            else:
                output_placeholder.error(llm_output)
        else:
            # 初始占位
            output_placeholder.markdown("""
            <div style="background:#fafafa; border:1px dashed #ddd;
                 border-radius:10px; padding:2.5rem 1.5rem; text-align:center; color:#999;">
                <p style="font-size:2rem; margin:0;">🎙️</p>
                <p style="margin:0.5rem 0 0 0;">选择左侧场景，点击<br><b>"生成通俗解说"</b></p>
                <p style="font-size:0.8rem; margin:0.5rem 0 0 0; color:#bbb;">
                    你会看到：冰冷的 JSON → 温暖的故事
                </p>
            </div>
            """, unsafe_allow_html=True)

    # ── 底部 ──
    st.divider()
    st.markdown("""
    <div style="text-align:center; color:#999; font-size:0.75rem;">
        SURF-2026-0154 · Generative HCI for Sports Analytics<br>
        Ting-Yu (IMIS, XJTLU) · Dr. Nanlin Jin & Dr. Thomas Selig
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
