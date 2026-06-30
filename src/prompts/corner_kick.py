"""
角球科普 Prompt — 二人转（双口相声）版本
Backward-compatible shim. Prompt templates migrated to agents/commentary_gen/prompts/.

Prefer:  from agents.commentary_gen.agent import CommentaryGenerator
Legacy:  from src.prompts.corner_kick import DUO_SYSTEM_PROMPT, DUO_USER_TEMPLATE
"""
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent.parent.parent / "agents" / "commentary_gen" / "prompts"

# Load from canonical location
DUO_SYSTEM_PROMPT = (_PROMPT_DIR / "system.txt").read_text(encoding="utf-8")

DUO_USER_TEMPLATE = """请根据下面的足球比赛信息，写一段双口相声科普脚本。

## 比赛事实
{fact_section}

## 战术彩蛋（可选）
下面这些战术分析数据 A 可偶尔引用：
{tactic_section}

## 要求
- 3-4 轮对话
- A 上来先卖弄知识
- B 一脸懵逼，逼 A 解释人话
- 最后 B 表示懂了
- 每段 A 台词后紧跟 ##VISUAL## 视觉指令
- 对话里不要出现坐标数字"""


def build_duo_prompt(formatted: dict) -> tuple[str, str]:
    """Legacy interface — builds system + user prompt tuple."""
    return (
        DUO_SYSTEM_PROMPT,
        DUO_USER_TEMPLATE.format(
            fact_section=formatted["fact_section"],
            tactic_section=formatted["tactic_section"],
        ),
    )


def parse_duo_output(output: str) -> list[dict]:
    """Parse duo commentary output into structured segments.
    Migrated logic — kept here for backward compat.
    """
    items = []
    current = None
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('A:') or line.startswith('B:'):
            if current:
                items.append(current)
            speaker = line[0]
            text = line[2:].strip()
            current = {"speaker": speaker, "text": text, "visual": None}
        elif line.startswith('##VISUAL##') and current:
            visual = line.replace('##VISUAL##', '').strip()
            if visual == 'ai_scene':
                current["visual"] = 'ai_scene'
                current["visual_type"] = 'ai_scene'
            elif visual == 'clear':
                current["visual"] = 'clear'
                current["visual_type"] = 'clear'
            else:
                current["visual"] = visual
                current["visual_type"] = 'highlight'
    if current:
        items.append(current)
    return items
