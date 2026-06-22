"""
Prompt 模板 — SURF-2026 核心 IP

本项目核心算法：将结构化 JSON 战术数据注入精心设计的 Prompt，
让 LLM 生成面向"零足球知识受众"的趣味战术解说。

设计原则（来自 [[surf-2026-project-init]]）：
1. 角色设定：足球战术解说员，面向完全不懂足球的观众
2. 输入约束：只能基于提供的 JSON 数据生成内容，禁止编造
3. 输出格式：结构化 Markdown（🛑 → 🤯 → 💡）
4. 语言风格：用生活化比喻解释战术概念
5. 防幻觉约束：不确定内容标注 [推测]
"""

# ============================================================
# System Prompt — 定义 LLM 的角色和行为边界
# ============================================================

SYSTEM_PROMPT = """You are a passionate and slightly dramatic sports storyteller.

Your job is to translate dry, geometric football tracking data into a thrilling narrative for an audience that knows absolutely nothing about football tactics.

CRITICAL RULES:
1. Do NOT use complex jargon (like 'half-spaces', 'xG', 'inverted fullback', or 'overlapping run').
2. Use everyday analogies — threading a needle, a traffic jam dissolving, a chess sacrifice, a key unlocking a door.
3. Your goal is to make the audience FEEL the tension and understand WHY the specific play was extraordinary based purely on the data constraints provided.
4. ONLY describe what the data supports. If something is unclear, mark it as [推测].
5. Write in Chinese (Simplified). Use vivid, accessible language suitable for a general audience.
6. Keep each section concise — 2-4 sentences max per section."""


# ============================================================
# User Prompt 模板 — 将 JSON 数据注入叙事框架
# ============================================================

USER_PROMPT_TEMPLATE = """请分析以下足球战术数据，并按照指定格式生成面向完全不懂足球的观众的趣味解说。

## 战术数据 (JSON)

```json
{scenario_json}
```

## 输出格式要求

请严格按照以下三段式结构输出（每段 2-4 句话）：

### 🛑 当前局势
- 用比赛时间和比分制造紧张感
- 一句话解释当前场上的困境（比如：进攻方被多少人包围、空间有多小）

### 🤯 神来之笔
- 解释球员做了什么动作
- 用具体数字强调难度（成功率、空间大小）
- 让观众感受到"这几乎不可能完成"

### 💡 为什么这很厉害（给不懂球的朋友）
- 用一个生活化的类比来解释
- 例如："这就像在早高峰地铁站台上，从人缝中精准地把手机滑进充电宝接口"
- 不要出现任何足球专业术语

---

请开始生成。记住：你的观众可能这辈子第一次看足球。"""


# ============================================================
# 辅助函数
# ============================================================

def build_user_prompt(scenario_data: dict) -> str:
    """
    将场景 JSON 数据注入 User Prompt 模板。

    Args:
        scenario_data: 战术场景字典，包含球员位置、比赛时间等

    Returns:
        完整的 User Prompt 字符串，可直接发送给 LLM

    这个函数是本项目的关键接口——输入格式改变时只需修改这里。
    """
    import json
    # 格式化 JSON 为可读的多行字符串（缩进 2 空格）
    scenario_json_str = json.dumps(scenario_data, indent=2, ensure_ascii=False)
    return USER_PROMPT_TEMPLATE.format(scenario_json=scenario_json_str)


def build_messages(scenario_data: dict) -> list[dict]:
    """
    构建完整的 messages 列表，可直接传给 OpenAI API。

    Args:
        scenario_data: 战术场景字典

    Returns:
        messages 列表: [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(scenario_data)}
    ]
