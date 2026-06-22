"""
SURF-2026-0154 AI Tactical Assistant — 学术提案 Demo
===========================================================

目的：向导师完整展示研究空白、我们的方案、技术原型、和长期规划。

设计理念：
  这个 Demo 不是"工具演示"，而是"学术提案的视觉辅助"。
  导师打开后能按顺序理解：为什么做 → 做什么 → 怎么做 → 做成什么样。

作者：Ting-Yu (IMIS, XJTLU)
导师：Dr. Nanlin Jin & Dr. Thomas Selig
"""

import streamlit as st
import json
import time
from pathlib import Path
from openai import OpenAI

# 项目模块
from config import (
    DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, DEEPSEEK_API_KEY,
    API_TIMEOUT, MAX_TOKENS, TEMPERATURE, load_scenarios,
)
from prompts.templates import SYSTEM_PROMPT, build_user_prompt


# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="SURF-2026-0154 · Generative HCI for Sports Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================
def inject_css():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(160deg, #0a150a 0%, #101f10 50%, #0a150a 100%); }
    .main-header { text-align:center; padding:1rem 0 0 0; font-size:2rem; font-weight:800;
        background: linear-gradient(90deg, #f7c948, #ff6b35, #f7c948); -webkit-background-clip:text;
        -webkit-text-fill-color:transparent; }
    .sub-header { text-align:center; color:#8aaa8a; font-size:1rem; margin-bottom:1rem; }
    .card { background:rgba(255,255,255,0.03); border:1px solid rgba(247,201,72,0.15);
        border-radius:10px; padding:1.2rem 1.5rem; margin:0.8rem 0; }
    .card-accent { border-left:3px solid #f7c948; }
    .highlight-box { background:rgba(247,201,72,0.06); border:1px solid rgba(247,201,72,0.25);
        border-radius:10px; padding:1.2rem 1.5rem; margin:1rem 0; }
    .gap-box { background:rgba(255,107,53,0.06); border:1px solid rgba(255,107,53,0.25);
        border-radius:10px; padding:1.2rem 1.5rem; margin:1rem 0; }
    .output-box { background:linear-gradient(135deg, #1a3a2a, #0d2818);
        border:1px solid #4a8a6a; border-left:4px solid #f7c948; border-radius:10px;
        padding:1.5rem 2rem; margin:1rem 0; color:#e0f0e0; }
    .venue-card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);
        border-radius:8px; padding:1rem; margin:0.5rem 0; }
    .stButton > button { background:linear-gradient(90deg, #ff6b35, #f7a948) !important;
        color:white !important; font-weight:700 !important; padding:0.6rem 2rem !important;
        border-radius:30px !important; border:none !important; width:100% !important; }
    .stButton > button:hover { transform:translateY(-2px);
        box-shadow:0 6px 20px rgba(255,107,53,0.4); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background:transparent; color:#8aaa8a; font-weight:600;
        padding:0.6rem 1.2rem; border-radius:8px 8px 0 0; }
    .stTabs [aria-selected="true"] { background:rgba(247,201,72,0.1) !important;
        color:#f7c948 !important; border-bottom:2px solid #f7c948 !important; }
    .stTextArea textarea { font-family:'Consolas','Monaco',monospace !important;
        font-size:0.85rem !important; background:#0d1a0d !important; color:#c8e0c8 !important;
        border:1px solid #3a5a3a !important; }
    .footnote { color:#5a7a5a; font-size:0.7rem; text-align:center; }
    .stMarkdown, .stText, p, span, label, div { color:#d0e0d0; }
    h2, h3 { color:#f7c948 !important; }
    h1 { color:#f7c948 !important; }
    hr { border-color:rgba(247,201,72,0.15); }
    @media (max-width:768px) { .main-header { font-size:1.4rem; } }
    </style>""", unsafe_allow_html=True)


# ============================================================
# 工具函数（复用）
# ============================================================
def validate_json(json_str: str) -> tuple[bool, dict | str]:
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            return False, f"❌ JSON 必须是对象，而不是 {type(data).__name__}"
        return True, data
    except json.JSONDecodeError as e:
        return False, f"❌ JSON 格式错误（第{e.lineno}行）：{e.msg}"

def call_llm(api_key: str, scenario_data: dict) -> tuple[bool, str]:
    try:
        client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL, timeout=float(API_TIMEOUT))
        user_prompt = build_user_prompt(scenario_data)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL, messages=messages,
            max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
        )
        return True, response.choices[0].message.content
    except Exception as e:
        err = str(e)
        if "401" in err or "auth" in err.lower():
            return False, f"🔑 API Key 无效。请检查侧边栏输入或 .env 文件。\n\n`{err[:200]}`"
        elif "429" in err:
            return False, f"⏳ 请求过于频繁，请稍后重试。\n\n`{err[:200]}`"
        elif "timeout" in err.lower():
            return False, f"⏰ 调用超时（{API_TIMEOUT}s）。\n\n`{err[:200]}`"
        else:
            return False, f"❌ API 调用失败：\n\n```\n{err[:500]}\n```"

def render_pitch_html(scenario: dict) -> str:
    atk = scenario.get("attacking_player", {})
    time_s = scenario.get("game_time", "??:??")
    score_s = scenario.get("score", "? - ?")
    defenders = scenario.get("defenders_in_path", "?")
    success = scenario.get("predicted_success_rate", "?%")
    return f"""
    <div style="background:linear-gradient(180deg,#1e4d1e,#2d6b2d 30%,#2d6b2d 70%,#1e4d1e);
        border:3px solid rgba(255,255,255,0.25); border-radius:12px; padding:20px;
        position:relative; min-height:180px; box-shadow:inset 0 0 60px rgba(0,0,0,0.3);">
        <div style="position:absolute; left:50%; top:8%; width:2px; height:84%;
            background:rgba(255,255,255,0.35);"></div>
        <div style="position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
            width:70px; height:70px; border-radius:50%; border:2px solid rgba(255,255,255,0.25);"></div>
        <div style="position:absolute; top:10px; left:50%; transform:translateX(-50%);
            background:rgba(0,0,0,0.75); color:#f7c948; padding:4px 16px; border-radius:20px;
            font-weight:700; font-size:0.9rem; z-index:10;">⏱ {time_s} &nbsp;|&nbsp; ⚽ {score_s}</div>
        <div style="position:absolute; left:{atk.get('x',50)}%; top:{atk.get('y',50)}%;
            transform:translate(-50%,-50%); z-index:5;">
            <div style="width:30px; height:30px; border-radius:50%;
                background:radial-gradient(circle,#ff6b35,#c0392b);
                box-shadow:0 0 16px rgba(255,107,53,0.6); display:flex; align-items:center;
                justify-content:center; color:white; font-weight:900; font-size:0.7rem;">A</div>
            <div style="color:white; font-size:0.65rem; text-align:center;
                text-shadow:0 0 6px black;">{atk.get('role', '')}</div></div>
        <div style="position:absolute; left:{atk.get('x',50)+18}%;
            top:{atk.get('y',50)-10}%; transform:translate(-50%,-50%); z-index:4;">
            <div style="width:22px; height:22px; border-radius:50%;
                background:radial-gradient(circle,#4a90d9,#1a5a9a);
                box-shadow:0 0 10px rgba(74,144,217,0.5); display:flex; align-items:center;
                justify-content:center; color:white; font-weight:700; font-size:0.6rem;">D</div>
            <div style="color:#b0c0e0; font-size:0.6rem; text-align:center;
                text-shadow:0 0 4px black;">×{defenders} defenders</div></div>
        <div style="position:absolute; bottom:10px; left:50%; transform:translateX(-50%);
            background:rgba(0,0,0,0.75); border-radius:8px; padding:5px 16px;
            font-size:0.75rem; display:flex; gap:16px; z-index:10;">
            <span>🎯 成功率 <b style="color:#ff6b35">{success}</b></span>
            <span>📐 传球通道 <b style="color:#f7c948">0.8m</b></span></div>
        <div style="position:absolute; top:6px; right:10px; background:rgba(247,201,72,0.12);
            color:#f7c948; font-size:0.6rem; padding:2px 8px; border-radius:10px;
            border:1px solid rgba(247,201,72,0.25);">📸 Phase 2: VLM →</div>
    </div>"""


# ============================================================
# TAB 1: Research Context & Gap
# ============================================================
def render_tab_context():
    """展示研究背景：TacticAI 做了什么、留下了什么空白。"""

    st.markdown("## 🔬 研究背景：AI 已经能「看懂」足球了")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        <div class="card card-accent">
        <h3>🏆 TacticAI (DeepMind × 利物浦, Nature Communications 2024)</h3>
        <p>Google DeepMind 与利物浦俱乐部合作，利用<strong>几何深度学习（Geometric Deep Learning）</strong>
        和图神经网络（GNN），在 <b>7,176 次英超角球</b>数据上训练了一个 AI 战术助手。</p>
        <ul>
        <li>✅ <b>预测</b>：角球第一接球人 → 是否形成射门</li>
        <li>✅ <b>生成</b>：建议球员站位调整 → 最大化射门概率</li>
        <li>✅ <b>检索</b>：查找历史上类似战术案例</li>
        <li>🏅 AI 建议在 <b>90%</b> 情况下优于人类教练的原始战术布置</li>
        <li>🏅 专家无法区分 AI 生成的战术与真实角球战术</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card" style="text-align:center;">
        <div style="font-size:3rem;">🧠</div>
        <b>核心方法</b><br>
        <span style="font-size:0.85rem; color:#8aaa8a;">
        群等变卷积网络<br>
        Group Equivariant CNN<br>
        + 图注意力机制<br>
        Graph Attention
        </span>
        <hr style="margin:0.5rem 0;">
        <span style="font-size:0.75rem; color:#8aaa8a;">
        依赖：多机位3D追踪<br>
        专有数据 (利物浦独家)
        </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("## 🕳️ 关键空白：TacticAI 为谁服务？")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="gap-box">
        <h3>❌ TacticAI 没有回答的问题</h3>
        <ul>
        <li><b>输出面向专业教练</b>——需要深厚的战术知识才能理解</li>
        <li><b>没有考虑"普通人"</b>——那些看不懂足球但可能感兴趣的人</li>
        <li><b>没有解释"为什么厉害"</b>——给出了概率，但没讲出故事</li>
        <li><b>没有降低认知门槛</b>——足球数据分析仍然是小圈子的特权</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div class="highlight-box">
        <h3>🎯 我们的机会</h3>
        <p>如果说 <b>TacticAI 是给教练的望远镜</b>，<br>
        那我们要做的，是<b>给普通人的翻译耳机</b>。</p>
        <p style="font-size:0.9rem; color:#8aaa8a;">
        把同样的高维战术数据，<br>
        变成人人都能感受的情感体验。
        </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("## 📚 相关研究佐证：这个方向是学术空白")

    st.markdown("""
    <div class="card">
    <table style="width:100%; border-collapse:collapse; color:#d0e0d0;">
    <tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
        <th style="padding:8px; text-align:left;">研究</th>
        <th style="padding:8px; text-align:left;">发表</th>
        <th style="padding:8px; text-align:left;">做了什么</th>
        <th style="padding:8px; text-align:left;">没做什么</th>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:8px;"><b>TacticAI</b></td>
        <td style="padding:8px; font-size:0.8rem;">Nature Comms '24</td>
        <td style="padding:8px;">角球战术预测+生成</td>
        <td style="padding:8px; color:#ff6b35;">未考虑非专业受众</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:8px;"><b>SportsBuddy</b></td>
        <td style="padding:8px; font-size:0.8rem;">IEEE PacificVis '25</td>
        <td style="padding:8px;">AI 体育视频故事化</td>
        <td style="padding:8px; color:#ff6b35;">面向已有兴趣的球迷</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:8px;"><b>Sportify</b></td>
        <td style="padding:8px; font-size:0.8rem;">IEEE TVCG</td>
        <td style="padding:8px;">LLM+RAG 篮球战术问答</td>
        <td style="padding:8px; color:#ff6b35;">仍然假设用户有基础知识</td>
    </tr>
    <tr>
        <td style="padding:8px;"><b>PXAI-Coach</b></td>
        <td style="padding:8px; font-size:0.8rem;">ABC '25</td>
        <td style="padding:8px;">运动健康 XAI 仪表盘</td>
        <td style="padding:8px; color:#ff6b35;">面向运动员，非"完全小白"</td>
    </tr>
    </table>
    </div>
    """, unsafe_allow_html=True)

    st.info(
        "💡 **结论**：现有 AI 体育系统要么面向专业教练，要么面向已有兴趣的球迷。\n\n"
        "**面向「对足球零认知甚至抗拒的人」的 AI 战术解释系统，是一个无人占领的交叉领域。**"
    )


# ============================================================
# TAB 2: Our Approach
# ============================================================
def render_tab_approach():
    """展示我们的研究方向、核心概念、和技术路线。"""

    st.markdown("## 💡 我们的方向：Generative HCI for Sports Analytics")

    st.markdown("""
    <div class="highlight-box">
    <h3>核心定义</h3>
    <p style="font-size:1.1rem;">
    <b>Generative HCI for Sports Analytics</b> 研究的是：<br><br>
    "如何利用生成式 AI，将高维度的专业体育数据，
    转化为<u>零知识门槛</u>的、<u>有情感吸引力</u>的、<u>可验证准确性</u>的用户体验。"
    </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔄 战略转向（The Pivot）")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="gap-box">
        <h4>❌ 不做：预测模型</h4>
        <ul>
        <li>不做球轨迹预测</li>
        <li>不做球员跑位预测</li>
        <li>不训练 CV 模型从零开始</li>
        </ul>
        <p style="font-size:0.8rem; color:#aaa;">
        <b>原因：</b>缺乏专有 3D 追踪数据；<br>
        10 周内无法达到学术级别；<br>
        算法创新空间有限。
        </p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="highlight-box">
        <h4>✅ 做：AI 驱动的"数据翻译"</h4>
        <ul>
        <li><b>假设数据已有</b>（JSON 格式的追踪数据）</li>
        <li><b>Prompt Engineering 为核心算法</b></li>
        <li><b>VLM 识别战术关键帧</b>的"张力"</li>
        <li><b>LLM 转化为</b>新手友好的叙事</li>
        <li><b>用 HCI 方法</b>验证效果</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🧬 系统工作流")

    st.markdown("""
    <div class="card" style="text-align:center; font-family:monospace; font-size:0.9rem;">
    <table style="width:100%; text-align:center; border-collapse:collapse;">
    <tr>
        <td style="padding:12px; background:rgba(255,107,53,0.08); border-radius:8px;">
            📹<br><b>比赛视频</b><br><span style="font-size:0.7rem;">公开转播画面</span>
        </td>
        <td style="color:#f7c948; font-size:1.5rem;">→</td>
        <td style="padding:12px; background:rgba(74,144,217,0.08); border-radius:8px;">
            🔍<br><b>VLM 识别</b><br><span style="font-size:0.7rem;">关键帧/战术张力</span>
        </td>
        <td style="color:#f7c948; font-size:1.5rem;">→</td>
        <td style="padding:12px; background:rgba(247,201,72,0.08); border-radius:8px;">
            📊<br><b>JSON 数据</b><br><span style="font-size:0.7rem;">结构化战术表示</span>
        </td>
        <td style="color:#f7c948; font-size:1.5rem;">→</td>
        <td style="padding:12px; background:rgba(74,144,217,0.08); border-radius:8px;">
            🧠<br><b>LLM Prompt 引擎</b><br><span style="font-size:0.7rem;">核心算法</span>
        </td>
        <td style="color:#f7c948; font-size:1.5rem;">→</td>
        <td style="padding:12px; background:rgba(255,107,53,0.08); border-radius:8px;">
            💬<br><b>新手友好叙事</b><br><span style="font-size:0.7rem;">文本+画面高亮</span>
        </td>
    </tr>
    </table>
    <p style="margin-top:10px; font-size:0.75rem; color:#8aaa8a;">
    ⬆️ 每一层之间用明确接口连接 → Phase 1 模拟 JSON 可随时替换为真实 VLM 输出
    </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🎓 为什么这个方向能发高水平论文？")

    st.markdown("""
    <div class="card card-accent">
    <p>HCI 领域的顶级会议（如 <b>ACM CHI</b>、<b>CSCW</b>、<b>IUI</b>、<b>DIS</b>）
    <strong>不要求发明新的底层算法</strong>。</p>
    <p>它们看重的是：</p>
    <ol>
    <li><b>AI 系统如何改变人类认知和行为？</b>
        → 我们的系统让"看不懂足球的人"开始理解战术</li>
    <li><b>是否有严谨的用户研究？</b>
        → 我们设计 A/B 测试 + NASA-TLX 认知负荷量表 + 统计检验</li>
    <li><b>是否填补了已知空白？</b>
        → 现有系统全部面向专业用户，无人在做"零基础受众"</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🧩 为什么我有独特优势做这个？")

    st.markdown("""
    <div class="card">
    <table style="width:100%; border-collapse:collapse;">
    <tr>
        <td style="padding:8px; width:50%;"><b>传统 CV 研究者</b></td>
        <td style="padding:8px; width:50%;"><b>我（IMIS 信管）</b></td>
    </tr>
    <tr>
        <td style="padding:8px; color:#aaa; font-size:0.85rem;">擅长训练模型、调参</td>
        <td style="padding:8px; font-size:0.85rem;">擅长 AI-Assisted Engineering</td>
    </tr>
    <tr>
        <td style="padding:8px; color:#aaa; font-size:0.85rem;">关注准确率、loss 曲线</td>
        <td style="padding:8px; font-size:0.85rem;">关注用户体验、Prompt 设计</td>
    </tr>
    <tr>
        <td style="padding:8px; color:#aaa; font-size:0.85rem;">论文发在 CV 会议</td>
        <td style="padding:8px; font-size:0.85rem;">论文发在 HCI 会议（学科交叉优势）</td>
    </tr>
    <tr>
        <td style="padding:8px; color:#ff6b35; font-size:0.85rem;">不会做用户研究</td>
        <td style="padding:8px; font-size:0.85rem;">信管训练包含系统分析、用户需求</td>
    </tr>
    </table>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# TAB 3: Live Prototype
# ============================================================
def render_tab_demo():
    """交互式原型演示：JSON 数据 → LLM Prompt → 新手友好解说。"""

    st.markdown("## 🧪 原型演示：JSON → LLM → 情感叙事")

    # 侧边栏配置（仅在 Demo tab 显示）
    with st.sidebar:
        st.markdown("### ⚙️ Demo 设置")
        api_key_input = st.text_input(
            "DeepSeek API Key", type="password",
            placeholder="留空使用 .env 中的 Key",
            help="你的 DeepSeek API Key。已在 .env 中配置则可留空。"
        )
        effective_key = api_key_input.strip() if api_key_input.strip() else DEEPSEEK_API_KEY
        if not effective_key:
            st.warning("⚠️ 请设置 API Key")

        st.markdown("---")
        st.markdown("### 📋 场景")
        scenarios = load_scenarios()
        scenario_name = st.selectbox("选择战术场景", list(scenarios.keys()))
        scenario = scenarios[scenario_name]

        st.markdown("---")
        st.markdown("### ℹ️ 关于本 Demo")
        st.markdown("""
        <span style="font-size:0.8rem;">
        本 Demo 演示 <b>Phase 1 概念验证</b>：<br>
        - 数据源：<b>模拟 JSON</b>（代表 CV 输出）<br>
        - 核心算法：<b>Prompt Engineering</b><br>
        - Phase 2 可替换为 <b>VLM + 真实 API</b>
        </span>
        """, unsafe_allow_html=True)

    # 主区域
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        st.markdown("### 📸 战术场景可视化")
        st.markdown("*简易球场示意图 · Phase 2 将替换为 VLM 自动标注的关键帧*")
        st.markdown(render_pitch_html(scenario), unsafe_allow_html=True)
        ctx = scenario.get("match_context", "")
        if ctx:
            st.info(f"📖 {ctx}")
        # 显示场景元数据
        st.markdown(f"""
        <div class="card" style="font-size:0.85rem;">
        <b>⏱</b> {scenario.get('game_time','')} &nbsp;
        <b>⚽</b> {scenario.get('score','')} &nbsp;
        <b>🎯</b> 成功率 {scenario.get('predicted_success_rate','')}<br>
        <b>📋</b> {scenario.get('actual_outcome','')}
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown("### 🧬 模拟 CV 数据 (JSON)")
        st.markdown("*这是假设 CV 系统从视频中提取的原始战术数据。可编辑。*")
        json_str = json.dumps(scenario, indent=2, ensure_ascii=False)
        json_key = f"json_{scenario_name}"
        if json_key not in st.session_state:
            st.session_state[json_key] = json_str
        edited_json = st.text_area(
            "战术数据（可编辑）", value=st.session_state[json_key],
            height=330, label_visibility="collapsed",
            key=f"ta_{scenario_name}"
        )
        st.session_state[json_key] = edited_json

    st.markdown("---")

    # 生成按钮
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        generate = st.button("🎙️ 生成 AI 通俗解说", use_container_width=True)

    st.markdown("---")
    st.markdown("### 🎤 AI 解说输出")

    output_placeholder = st.empty()

    if generate:
        if not effective_key:
            output_placeholder.error("请在侧边栏输入 API Key，或创建 `.env` 文件。")
            st.stop()
        is_valid, result = validate_json(edited_json)
        if not is_valid:
            output_placeholder.error(result)
            st.stop()
        with st.spinner("🤔 AI 分析战术数据中..."):
            t0 = time.time()
            ok, llm_out = call_llm(effective_key, result)
            elapsed = time.time() - t0
        if ok:
            output_placeholder.markdown(f"""
            <div class="output-box">{llm_out}</div>
            """, unsafe_allow_html=True)
            st.caption(f"✅ 生成完成 · {elapsed:.1f}s · {DEEPSEEK_MODEL}")
        else:
            output_placeholder.error(llm_out)
    else:
        output_placeholder.markdown("""
        <div class="output-box" style="text-align:center; opacity:0.6;">
        <div style="font-size:2.5rem; margin-bottom:0.3rem;">🎙️</div>
        <p>选择一个场景，点击 <b>"生成 AI 通俗解说"</b><br>
        看看 AI 如何把枯燥的战术数据变成情感丰富的故事</p>
        <p style="font-size:0.75rem; color:#6a9a6a;">💡 你可以先编辑右侧 JSON，改变输入数据，对比不同的输出</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# TAB 4: Research Roadmap
# ============================================================
def render_tab_roadmap():
    """展示从 SURF 到论文发表的完整路线图。"""

    st.markdown("## 🗺️ 研究路线图：从 SURF 到论文发表")

    st.markdown("### ⏳ 三阶段规划")

    # Phase 1
    st.markdown("""
    <div class="highlight-box">
    <h3>Phase 1 · SURF 暑期（2026 年 6-8 月，10 周）<br>
    <span style="font-size:0.85rem; color:#8aaa8a;">系统构建与概念验证</span></h3>
    <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px; width:15%;">Week 1-2</td>
        <td style="padding:6px 8px; width:25%; color:#f7c948;">文献调研 + 需求分析</td>
        <td style="padding:6px 8px;">阅读 TacticAI、SportsBuddy、PXAI-Coach 及相关 HCI 论文 · 定义目标用户画像</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px;">Week 3-4</td>
        <td style="padding:6px 8px; color:#f7c948;">Prompt Engineering 核心</td>
        <td style="padding:6px 8px;">设计多场景 JSON Schema · 迭代 System Prompt（至少 3 轮）· 建立输出质量评估标准</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px;">Week 5-6</td>
        <td style="padding:6px 8px; color:#f7c948;">Streamlit 原型开发</td>
        <td style="padding:6px 8px;">完整 UI · 多场景支持 · 错误处理 · JSON 编辑 · 对比模式（AI vs 传统解说）</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px;">Week 7-8</td>
        <td style="padding:6px 8px; color:#f7c948;">VLM 集成</td>
        <td style="padding:6px 8px;">接入 GPT-4o/Gemini Vision 处理静态关键帧 · 从图像直接提取战术场景描述</td>
    </tr>
    <tr>
        <td style="padding:6px 8px;">Week 9-10</td>
        <td style="padding:6px 8px; color:#f7c948;">预实验 + 完善</td>
        <td style="padding:6px 8px;">5-10 人小型预实验 · 收集反馈 · 完善文档和演示 · 准备 FYP 开题材料</td>
    </tr>
    </table>
    <p style="margin-top:10px;"><b>🎯 交付物：</b>一个可稳定运行的 Working Prototype + 初步用户反馈数据</p>
    </div>
    """, unsafe_allow_html=True)

    # Phase 2
    st.markdown("""
    <div class="card card-accent">
    <h3>Phase 2 · FYP 大四（2026 年 9 月 - 2027 年 5 月）<br>
    <span style="font-size:0.85rem; color:#8aaa8a;">严谨用户研究与论文撰写</span></h3>
    <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px; width:15%;">9-10 月</td>
        <td style="padding:6px 8px; width:25%; color:#f7c948;">实验设计</td>
        <td style="padding:6px 8px;">IRB 伦理审批 · 样本量计算（G*Power）· A/B 测试协议 · 量表选择（NASA-TLX + SUS）</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px;">11-12 月</td>
        <td style="padding:6px 8px; color:#f7c948;">用户研究执行</td>
        <td style="padding:6px 8px;">招募 ≥30 名零足球知识被试 · 对照组（传统解说）vs 实验组（AI 解说）· 数据收集</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:6px 8px;">1-2 月</td>
        <td style="padding:6px 8px; color:#f7c948;">数据分析</td>
        <td style="padding:6px 8px;">T 检验 / ANOVA · 效应量计算 · 定性编码（用户访谈）· 可视化</td>
    </tr>
    <tr>
        <td style="padding:6px 8px;">3-5 月</td>
        <td style="padding:6px 8px; color:#f7c948;">论文撰写</td>
        <td style="padding:6px 8px;">按 CHI/CHI Late-Breaking Work 格式撰写 · 导师审阅 · 投稿</td>
    </tr>
    </table>
    </div>
    """, unsafe_allow_html=True)

    # Phase 3
    st.markdown("""
    <div class="highlight-box">
    <h3>Phase 3 · 发表与推广（2027 年中起）</h3>
    <p>根据审稿意见修改 · 申请研究生时将论文作为核心成果 · 扩展至其他运动（篮球、网球）</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## 🎯 目标发表渠道")

    st.markdown("""
    <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px;">
    <div class="venue-card">
        <h4>🏆 ACM CHI</h4>
        <p>人机交互顶会<br>
        <span style="font-size:0.8rem; color:#8aaa8a;">
        接收率: ~25%<br>
        CCF-A · HCI 领域 #1<br>
        2026: 6,730 投稿 / 1,703 录用<br>
        </span></p>
        <p style="font-size:0.75rem; color:#f7c948;">Full Paper 投稿截止：约每年 9 月</p>
    </div>
    <div class="venue-card">
        <h4>🏆 ACM IUI</h4>
        <p>智能用户界面<br>
        <span style="font-size:0.8rem; color:#8aaa8a;">
        接收率: ~24%<br>
        聚焦 AI + 用户交互<br>
        与我们的"LLM生成叙事"高度匹配
        </span></p>
    </div>
    <div class="venue-card">
        <h4>🏆 ACM DIS</h4>
        <p>交互系统设计<br>
        <span style="font-size:0.8rem; color:#8aaa8a;">
        接收率: ~28%<br>
        重视系统设计+用户评估<br>
        SportsBuddy 相关论文在此发表
        </span></p>
    </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
    <div style="display:grid; grid-template-columns:repeat(2,1fr); gap:12px;">
    <div class="venue-card">
        <h4>📝 IEEE TVCG</h4>
        <p>可视化与图形学顶刊<br>
        <span style="font-size:0.8rem; color:#8aaa8a;">
        SCI一区 · CCF-A<br>
        视觉叙事+体育方向对口<br>
        Sportify 在此发表
        </span></p>
    </div>
    <div class="venue-card">
        <h4>📝 ACM CSCW</h4>
        <p>计算机支持协同工作<br>
        <span style="font-size:0.8rem; color:#8aaa8a;">
        CCF-A<br>
        人机协作+AI辅助决策<br>
        适合"AI辅助理解复杂信息"主题
        </span></p>
    </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.info(
        "📌 **发表策略**：优先投稿 **ACM CHI 2027 Late-Breaking Work**（短文，接收率较高，适合首次投稿）。"
        "正式 Full Paper 投 **ACM CHI 2028** 或 **IUI 2028**。"
        "研究生申请（2027 年底）时可附上 Accepted Paper / Under Review。"
    )


# ============================================================
# 主入口
# ============================================================
def main():
    inject_css()

    # 页头
    st.markdown(
        '<div class="main-header">⚽ Generative HCI for Sports Analytics</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="sub-header">SURF-2026-0154 · AI Tactical Assistant · Ting-Yu (IMIS, XJTLU)</div>',
        unsafe_allow_html=True
    )

    # 4 个导航 Tab
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔬 研究背景与空白",
        "💡 我们的方案",
        "🧪 原型演示",
        "🗺️ 研究路线图"
    ])

    with tab1:
        render_tab_context()
    with tab2:
        render_tab_approach()
    with tab3:
        render_tab_demo()
    with tab4:
        render_tab_roadmap()

    # 页脚
    st.markdown("---")
    st.markdown("""
    <div class="footnote">
        SURF-2026-0154 AI Tactical Assistant · Generative HCI for Sports Analytics<br>
        Ting-Yu (IMIS, XJTLU) · 导师：Dr. Nanlin Jin & Dr. Thomas Selig · Summer 2026
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
