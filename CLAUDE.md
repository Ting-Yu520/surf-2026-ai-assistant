# CLAUDE.md — SURF-2026-0154 AI Tactical Assistant

Generative HCI for Sports Analytics：用 LLM/VLM 将足球战术数据转化为新手可理解的叙述。

详见 [[surf-2026-project-init]]、[[surf-2026-architecture]]、[[workspace-d-drive-constraint]]。

## 项目身份

| 属性 | 值 |
|------|-----|
| 项目编号 | SURF-2026-0154 |
| 导师 | Dr. Nanlin Jin & Dr. Thomas Selig (XJTLU) |
| 我的定位 | IMIS 学生，核心优势：AI-Assisted Engineering、Prompt-Driven Development、System Analysis |
| 最终目标 | 10 周 SURF → FYP → HCI/Applied AI 高影响力论文 |

## 核心学术概念（战略转向）

- **不做**：预测性模型（球轨迹、球员坐标）——缺乏 DeepMind 的专有 3D 追踪数据
- **做**：生成式 HCI for Sports Analytics——假设追踪数据已提取（JSON），用 GenAI 将高维枯燥战术数据转化为新手友好的叙述

## 三阶段路线图

| 阶段 | 时间 | 目标 | 输入源 |
|------|------|------|--------|
| Phase 1: PoC | 当前 | 快速原型证明 workflow | 模拟 JSON |
| Phase 2: SURF | 暑期 | 健壮工作原型，集成 VLM 处理关键帧/短视频 | 模拟 JSON + VLM |
| Phase 3: FYP | 大四 | 严格用户研究（A/B 测试、NASA-TLX 认知负荷量表） | 真实 API / CV 输出 |

## 技术栈

| 层 | 技术 | 用途 |
|----|------|------|
| 前端 | Streamlit | 交互式 PoC / 原型 UI |
| 后端 | Python 3.14 | 核心逻辑 |
| AI | DeepSeek API (via 代理) | LLM 推理，Prompt 即核心算法 |
| 数据格式 | JSON | 模拟战术数据输入（Phase 2 可替换为真实 API） |
| 版本控制 | Git (D:\Tools\Git) | 代码管理 |

## 环境

- Python 3.14.5 (`D:\Tools\Python314\`)
- pip 26.1+
- 虚拟环境：项目级别 venv（待创建）
- LLM API：DeepSeek API 代理（`ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`）

## 项目结构

```
surf-2026-ai-tactical-assistant/
├── src/
│   ├── app.py                  # Streamlit 主入口
│   ├── llm_client.py           # LLM API 客户端
│   ├── prompts/                # Prompt 模板（核心算法）
│   │   ├── tactical_narrative.py
│   │   └── constraints.py
│   ├── data/                   # 模拟 JSON 战术数据
│   └── utils/
├── tests/                      # 测试
├── memory/                     # 项目记忆文件
├── docs/                       # 论文、参考文献
├── outputs/                    # 生成输出
└── requirements.txt
```

## 设计原则

1. **目标受众永远是新手**——不做复杂数据可视化，除非新手能理解
2. **输入可替换**——今天的模拟 JSON 明天可换成真实 API 数据
3. **Prompt 即算法**——LLM Prompt 是本项目的核心 IP，必须高度结构化、严格约束
4. **模块化架构**——每个组件独立可测

## 运行

```bash
# 首次
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
streamlit run src/app.py
```
