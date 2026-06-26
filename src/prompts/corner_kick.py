"""
角球专用 Prompt — 时间线感知版本

LLM 按视频时间轴分段生成叙事，每段对应一个视觉事件。
"""

TIMELINE_SYSTEM_PROMPT = """你是一个擅长讲故事的足球解说员。你的观众这辈子可能第一次看足球。

核心规则：
1. 像朋友聊天，用"你想象一下""你看"这类语气。
2. 绝对禁止足球术语。每个专业概念立刻用生活比喻解释。
3. 只能基于提供的数据，不确定处说"可能是"。
4. 用自然的中文段落，不要 markdown，不要 emoji。

输出格式：
你会被给定一个事件时间线。对每个事件写 1-2 句话的解说词。
每段解说词必须精确描述该时间段内画面上正在发生的事情。
"""

TIMELINE_USER_TEMPLATE = """下面是一个足球角球的完整数据和事件时间线。请为每个时间线事件写 1-2 句解说词。

## 比赛信息
{context}

## 事件时间线
{timeline}

## 要求
对时间线中的每个事件，生成一段解说词，以 JSON 数组返回：

```json
[
  {{
    "start_sec": <事件开始秒>,
    "end_sec": <事件结束秒>,
    "narration": "<1-2句中文解说词，描述这一秒画面上正在发生的事>"
  }},
  ...
]
```

每段解说词必须：
- 精确描述该时间段画面上正在发生的事
- 用生活比喻来解释复杂动作
- 保持和前后段的连贯性
- 输出 ONLY JSON 数组，不要其他文字
"""


def build_timeline_prompt(vlm_data: dict) -> tuple[str, str]:
    """从 VLM 输出的含时间线 JSON 构建 LLM prompt。"""
    import json

    context = json.dumps(vlm_data.get("match_context", {}), indent=2, ensure_ascii=False)
    context += "\n" + json.dumps(vlm_data.get("corner_setup", {}), indent=2, ensure_ascii=False)

    timeline = vlm_data.get("timeline", [])
    timeline_str = json.dumps(timeline, indent=2, ensure_ascii=False)

    user_prompt = TIMELINE_USER_TEMPLATE.format(context=context, timeline=timeline_str)
    return TIMELINE_SYSTEM_PROMPT, user_prompt


def parse_timeline_narrative(llm_output: str) -> list[dict]:
    """解析 LLM 返回的分段叙事 JSON。"""
    import json
    raw = llm_output.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw)
