# CLAUDE.md — SURF-2026-0154 AI Tactical Assistant

**Generative HCI for Sports Analytics**：用 LLM 将足球战术数据转化为新手可理解的趣味叙述。

详见 [[surf-2026-project-init]]、[[surf-2026-architecture]]。

---

## 两阶段项目结构

```
surf-2026-ai-tactical-assistant/
│
├── phase1/                    # Phase 1: 视频 → 专业 JSON（工具集成）
│   ├── README.md              # 工具清单 + 接入方法
│   └── tools/                 # git clone 外部工具到这里
│
├── src/                       # Phase 2: JSON → 趣味解说（核心）
│   ├── pipeline.py            # 端到端管线
│   ├── app.py                 # Streamlit Demo
│   ├── config.py              # 全局配置
│   ├── tts_client.py          # Edge TTS 配音
│   ├── video_overlay.py       # 视频合成
│   ├── prompts/
│   │   └── corner_kick.py     # 二人转 Prompt（核心 IP）
│   └── data/
│       ├── corner_kicks_2026.json  # 2026世界杯角球数据集
│       └── corner_articles.json    # 文章底本
│
├── data/videos/               # 原始角球视频
├── outputs/                   # AI 生成产物
│   ├── videos/
│   ├── audio/
│   └── texts/
├── skills/openmontage/        # 视频合成增强（本地 skill，不提交）
├── docs/                      # 项目文档
│
├── CLAUDE.md
└── requirements.txt
```

## Phase 1（视频 → 专业 JSON）— 工具集成

| 用途 | 工具 | 状态 |
|------|------|------|
| 角球战术分析 | TacticAI Recreation | ✅ 代码全 |
| 足球问答/视频理解 | SoccerAgent | ✅ 代码+数据 |
| 自动解说 | MatchTime | ✅ 代码+模型 |

克隆到 `phase1/tools/` 后，输出格式化 JSON → Phase 2 消费。

## Phase 2（专业 JSON → 趣味解说）— 核心研发

**管线流程：**

```
数据集 JSON → 二人转 Prompt → LLM (DeepSeek) → 科普脚本 → TTS → 视频合成
```

**Prompt 风格：** 双口相声（A：懂哥 + B：小白），对抗中解释角球知识。

## 运行

```bash
# Phase 2 Demo
streamlit run src/app.py

# 批量处理
python scripts/batch_process.py
```

## 目标

- Phase 1: 复用开源工具，不投入开发
- Phase 2: 打磨 Prompt → 用户研究 → FYP → CHI/IUI 论文
