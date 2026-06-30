# Agent-Based Modular Architecture Design

**Project:** SURF-2026-0154 AI Tactical Assistant
**Date:** 2026-06-30
**Status:** ✅ Approved
**Decision:** Agent-Based 模块化 (Option B) + YAML 配置 (Option C)

---

## 1. Design Goals

| 目标 | 度量 |
|------|------|
| **高内聚低耦合** | 每个 Agent 只通过 `core/interfaces.py` 互依赖 |
| **零硬编码** | 所有配置在 YAML 文件，API keys 在 `secrets.env` |
| **最小模块化** | 每个功能独立成 Agent 包，含自己的 config + prompt + schema |
| **可商用化** | 每个 Agent 可独立部署、独立测试、独立替换 |
| **对标 OPC 论文** | 三层架构：支撑层 → Agent 执行层 → 应用层 |

---

## 2. Directory Structure

```
surf-2026-ai-tactical-assistant/
├── agents/                          ← 核心：6 Agent，互不依赖
│   ├── base.py                      ← BaseAgent 抽象类 + AgentInput/Output
│   │
│   ├── video_analyzer/              ← Agent 1: VLM 帧分析
│   │   ├── __init__.py
│   │   ├── agent.py                 ← class VideoAnalyzer(BaseAgent)
│   │   ├── config.yaml
│   │   ├── schema.py
│   │   └── prompts/
│   │
│   ├── tactical_extractor/          ← Agent 2: Phase1 战术数据
│   │   ├── __init__.py
│   │   ├── agent.py                 ← class TacticalExtractor(BaseAgent)
│   │   ├── config.yaml
│   │   ├── schema.py
│   │   └── adapters/
│   │       ├── tacticai.py
│   │       ├── socceragent.py
│   │       └── matchtime.py
│   │
│   ├── commentary_gen/              ← Agent 3: LLM 二人转解说
│   │   ├── __init__.py
│   │   ├── agent.py                 ← class CommentaryGenerator(BaseAgent)
│   │   ├── config.yaml
│   │   ├── schema.py
│   │   └── prompts/
│   │       ├── system.txt
│   │       ├── duo_template.j2
│   │       └── constraints.py
│   │
│   ├── voice_gen/                   ← Agent 4: TTS 配音
│   │   ├── __init__.py
│   │   ├── agent.py                 ← class VoiceGenerator(BaseAgent)
│   │   ├── config.yaml
│   │   └── schema.py
│   │
│   ├── video_composer/              ← Agent 5: 视频合成 + MG 动画
│   │   ├── __init__.py
│   │   ├── agent.py                 ← class VideoComposer(BaseAgent)
│   │   ├── config.yaml
│   │   ├── schema.py
│   │   ├── overlays/
│   │   │   ├── highlight.py
│   │   │   ├── caption.py
│   │   │   └── border.py
│   │   └── animations/
│   │       └── mg_renderer.py
│   │
│   └── fusion/                      ← Agent 6: 决策融合 + QC
│       ├── __init__.py
│       ├── agent.py                 ← class FusionAgent(BaseAgent)
│       ├── config.yaml
│       └── schema.py
│
├── core/                            ← 共享基础设施（零业务逻辑）
│   ├── __init__.py
│   ├── interfaces.py                ← BaseAgent, AgentInput, AgentOutput
│   ├── config_loader.py             ← YAML + env 统一加载
│   ├── llm_client.py                ← 通用 LLM 调用（OpenAI 兼容）
│   ├── exceptions.py
│   └── logging.py
│
├── configs/                         ← 全局环境配置
│   ├── dev.yaml
│   ├── prod.yaml
│   └── secrets.env                  ← gitignore
│
├── papers/                          ← 文献管理
├── data/                            ← 数据集
├── outputs/                         ← 生成产物
├── tests/                           ← 每个 Agent 一个 test 文件
├── scripts/                         ← 批量处理 / 工具
├── docs/                            ← 项目文档
├── app.py                           ← Streamlit UI（只调 Fusion Agent）
└── requirements.txt
```

---

## 3. Core Interface Contract

### BaseAgent (abstract)

```python
# core/interfaces.py
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any

@dataclass
class AgentInput:
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentOutput:
    status: str              # "ok" | "error" | "skipped"
    data: dict[str, Any]
    agent_name: str
    error: str | None = None
    elapsed_ms: float = 0.0

class BaseAgent(ABC):
    """每个 Agent 的唯一入口。子类只实现 load_config() 和 run()。"""

    def __init__(self, config_override: dict | None = None):
        self.config = self.load_config()
        if config_override:
            self.config.update(config_override)

    @abstractmethod
    def load_config(self) -> dict:
        """从 config.yaml + 环境变量加载配置"""
        ...

    @abstractmethod
    def run(self, input: AgentInput) -> AgentOutput:
        """唯一入口：输入 → 处理 → 输出"""
        ...

    @abstractmethod
    def validate(self, output: AgentOutput) -> bool:
        """自检输出是否符合 Schema"""
        ...
```

### Agent Contract

- 每个 Agent **只能依赖** `core/`（interfaces, config_loader, llm_client, exceptions, logging）
- 每个 Agent **禁止** import 其他 Agent
- 每个 Agent 的 `run()` 是唯一公共接口
- 配置加载统一走 `core/config_loader.py` 的 `load_yaml_and_env()`

---

## 4. Data Flow (6-Agent Pipeline)

```
① VideoAnalyzer.run({frames})
   → output.data["tactical_json"]
                    ↘
② TacticalExtractor.run({tactical_json, video_meta})
   → output.data["tactical_scene"]
                    ↘
③ CommentaryGen.run({tactical_scene, article})
   → output.data["script", "segments"]
         ↙                          ↘
④ VoiceGen.run({segments})          ⑤ VideoComposer.run({script, video})
   → output.data["audio"]              → output.data["clips"]
         ↘                          ↙
⑥ Fusion.run({audio, clips, script, tactical_scene})
   → output.data["final_video_path"] ✅
```

VoiceGen 和 VideoComposer **并行执行**（互不依赖），Fusion 等两者都完成后融合。

---

## 5. Configuration Strategy

### Per-Agent config.yaml

```yaml
# agents/video_analyzer/config.yaml
model: gemini-2.0-flash
fps: 1
max_frames: 10
resolution: [1920, 1080]
timeout_sec: 30
```

### Global Environment

```yaml
# configs/prod.yaml
log_level: INFO
output_dir: ./outputs
parallel: true
```

### Secrets (gitignored)

```bash
# configs/secrets.env
DEEPSEEK_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
```

### Loading

```python
from core.config_loader import load_yaml_and_env

config = load_yaml_and_env("agents/video_analyzer/config.yaml")
# → YAML 默认值 + secrets.env 覆盖 + 环境变量最高优先级
```

---

## 6. Migration Plan (from current src/ to agents/)

| Step | From | To | Risk |
|------|------|----|------|
| 1 | Create `core/` package | New | Low — 纯新代码 |
| 2 | Extract `tts_client.py` | `agents/voice_gen/` | Low — 已有独立接口 |
| 3 | Extract `prompts/corner_kick.py` | `agents/commentary_gen/` | Low — 已有独立模块 |
| 4 | Extract `video_overlay.py` + `mg_renderer.py` | `agents/video_composer/` | Medium — 拆分 overlays |
| 5 | Extract `phase1_*.py` + `phase_bridge.py` | `agents/tactical_extractor/` | Medium — 多文件合并 |
| 6 | Create `agents/video_analyzer/` | New | Low — 全新 VLM 功能 |
| 7 | Create `agents/fusion/` | New | Low — 从 pipeline 提取编排逻辑 |
| 8 | Rewrite `app.py` | 只调 Fusion Agent | Low — 接口简化 |
| 9 | Delete old `src/` | — | Low — 最后一步 |

**策略：** 渐进迁移，每步保持 `app.py` 可运行。旧代码和新 Agent 并行存在直到全部迁移完毕。

---

## 7. Self-Review

- ✅ 无 TBD / TODO
- ✅ 架构与 Agent 设计一致（6 Agent + core）
- ✅ 数据流明确（①②③④⑤⑥ 链路）
- ✅ 配置策略无硬编码
- ✅ 迁移路径可渐进执行
- ✅ scope 聚焦 SURF 项目，无过度设计
