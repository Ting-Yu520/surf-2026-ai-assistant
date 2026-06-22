---
name: surf-2026-architecture
description: SURF-2026 AI Tactical Assistant 架构决策——数据流、Prompt 设计原则、模块化输入可替换架构
metadata:
  type: project
  originSessionId: surf-2026-init
---

# Architecture: SURF-2026 AI Tactical Assistant

## Data Flow (核心工作流)

```
[Simulated JSON Data]           ← Phase 1: 手工构造的战术场景 JSON
        │
        ▼
[Prompt Composer]               ← 将 JSON 数据注入结构化 Prompt 模板
        │
        ▼
[LLM API (DeepSeek)]            ← 推理，生成叙述
        │
        ▼
[Accessible Narrative Output]   ← 面向新手的战术解读文本
        │
        ▼
[Streamlit UI]                  ← 交互式展示
```

**关键设计**：每一层之间用明确的接口（函数签名 + 数据类）连接，使得：
- `Simulated JSON` → 替换为 → `Real API Data`（Phase 2）
- `LLM API (DeepSeek)` → 替换为 → 任何 OpenAI 兼容端点
- `Streamlit UI` → 替换为 → 任何前端框架

## Prompt 设计原则（核心 IP）

Prompt 是本项目的核心算法。每条 Prompt 必须遵循：

1. **角色设定**：明确 LLM 扮演"足球战术解说员，面向完全不懂足球的观众"
2. **输入约束**：严格限定 LLM 只能基于提供的 JSON 数据生成内容，禁止编造
3. **输出格式**：结构化输出（Markdown），含标题、要点、比喻
4. **语言风格**：用生活化比喻解释战术概念（如"这就像下棋时..."）
5. **防幻觉约束**：要求 LLM 标注不确定的内容为 `[推测]`

## 模块化设计

```
src/
├── app.py              # Streamlit UI 入口
├── llm_client.py       # LLM API 封装（支持 OpenAI 兼容接口）
├── prompts/
│   ├── __init__.py
│   ├── templates.py    # Prompt 模板定义（核心 IP）
│   └── constraints.py  # 防幻觉 / 输出验证规则
├── data/
│   ├── __init__.py
│   ├── schema.py       # 战术数据 JSON Schema 定义
│   └── samples/        # 模拟场景数据
├── utils/
│   ├── __init__.py
│   ├── validators.py   # 输出验证
│   └── formatters.py   # 格式化工具
└── config.py           # 全局配置
```

## 输入 Schema 设计（战术数据 JSON）

```python
# 核心数据结构
TacticalScene = {
    "scene_id": str,
    "timestamp": str,          # 比赛时间
    "players": [
        {
            "id": str,
            "team": "attack" | "defense",
            "position": (float, float),  # 标准化坐标 [0,1]
            "role": str,                 # "forward", "midfielder", etc.
            "action": str,               # "passing", "shooting", "tackling"
        }
    ],
    "ball": {
        "position": (float, float),
        "trajectory": str,     # "ground_pass", "cross", "shot"
        "target_player": str   # 接球球员 ID
    },
    "tactical_context": {
        "formation": str,      # "4-3-3", "4-4-2"
        "phase": str,          # "counter_attack", "possession", "set_piece"
        "score_line": str,     # "1-0"
        "minute": int
    }
}
```

## 接口约定

所有 I/O 组件必须实现明确的接口，确保可替换性：

```python
# Prompt Composer 接口
def compose_prompt(scene: TacticalScene, audience_level: str = "novice") -> str:
    """将战术场景 JSON 转化为结构化 LLM Prompt"""
    ...

# LLM Client 接口
def generate_narrative(prompt: str, model: str = "deepseek-v4-pro") -> str:
    """调用 LLM 生成战术叙述"""
    ...

# Output Validator 接口
def validate_narrative(narrative: str, source_scene: TacticalScene) -> ValidationResult:
    """验证 LLM 输出：检查幻觉、格式、完整性"""
    ...
```
