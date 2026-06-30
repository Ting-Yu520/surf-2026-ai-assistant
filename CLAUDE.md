# CLAUDE.md — SURF-2026-0154 AI Tactical Assistant

**Generative HCI for Sports Analytics**：用 LLM 将足球战术数据转化为新手可理解的趣味叙述。

详见 [[surf-2026-project-init]]、[[surf-2026-architecture]]、[[surf-2026-opc-paper]]。

---

## 当前 Sprint（7/20 汇报）

**目标：** Demo v3 → 产品级原型
**核心：** 多模态升级（对标 OPC 论文三层架构）
**Sprint 计划详见：** [[surf-2026-sprint-jul20]]

关键升级：

- VLM (Gemini) 从视频自动提取战术信息（输入多模态）
- MG 动画 + 视频高亮 + TTS（输出多模态）
- 真实 Phase 1 数据替换模拟数据
- UI 产品化 + 视频上传 + 批量处理

## 多模态架构（对标 OPC 论文）

```
Model & Algorithm Support Layer
  ├── VLM (Gemini/GPT-4o)     ← 视频帧 → 战术 JSON
  ├── LLM (DeepSeek V4)       ← Prompt 引擎 → 科普脚本
  ├── TTS (Edge TTS)          ← 脚本 → 语音
  └── CV (ffmpeg/MG)          ← 动画 + 视频合成

Multi-Agent Execution Layer
  ├── Video Analysis Agent    ← VLM 关键帧分析
  ├── Tactical Extract Agent  ← Phase 1 工具输出
  ├── Commentary Agent        ← 二人转 Prompt
  ├── Voice Agent             ← TTS 配音
  └── Fusion Agent            ← 视频合成 + QC

Application Layer
  └── Streamlit UI            ← 上传/查看/下载
```

## 双人团队

| 角色 | 负责 |
|------|------|
| 你（大三） | `pipeline.py` / `prompts/` / `video_overlay.py` / `tts_client.py` / `config.py` |
| 搭档（大一） | `app.py` / `scripts/` / `tests/` / `docs/` |

接口：`process_corner_kick()` —— 搭档通过它调管线，不修改内部。
完整协议：[[surf-2026-collaboration]]

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
