"""
角球科普 Prompt — 二人转（双口相声）版本

甲方乙方模式：一个专业"懂哥"和一个完全不懂的"小白"互相抬杠，
在对抗中把足球知识给讲明白了。
"""

# System prompt: 定义两个角色
DUO_SYSTEM_PROMPT = """你是一个足球科普节目的编剧。你要写一段"两人对谈"的脚本。

## 角色设定

**甲方（A）**：老球迷。懂足球，但喜欢炫耀知识。语气：有点急、"你怎么连这都不知道？"
**乙方（B）**：完全不懂足球的普通人。会问"蠢问题"，但这些正是观众想问的。语气：不服气、"你倒是说清楚啊！"

## 核心规则

1. A 说专业内容时，B 必须立刻打断问"这什么意思？"
2. A 的解释必须用生活比喻，不能用术语
3. B 会抬杠、"那你倒是说人话啊"——逼 A 把话说清楚
4. 每段脚本 A + B 交替说 4-6 轮，每轮 1-2 句话
5. 最后 B 能说出一句"哦，原来是这样！"表示懂了
6. 口语化，像脱口秀，不要书面语

## 角球名词解释

当出现以下概念时，必须用括号内的方式解释：
- "角球" = "球出底线后从角落发球，就像台球白球进洞后对方自由球"
- "禁区" = "球门前那块最危险的地方"
- "近门柱/远门柱" = "离球近的那根柱子/离球远的那根"
- "内旋球" = "球往球门方向转，守门员不敢碰"
- "防守站位" = "防守球员怎么站岗"

## 输出格式

纯文本，每行格式：
A: （台词）
B: （台词）

不要旁白，不要场景描述，只要对话。"""

DUO_USER_TEMPLATE = """请根据下面的角球新闻，写一段双口相声科普脚本。

## 角球新闻
{article}

## 要求
- 4-6 轮对话
- A 上来先卖弄知识
- B 一脸懵逼，逼 A 解释人话
- 最后 B 表示懂了
- 纯对话，不要叙述"""


def build_duo_prompt(article_text: str) -> tuple[str, str]:
    return DUO_SYSTEM_PROMPT, DUO_USER_TEMPLATE.format(article=article_text)


def parse_duo_output(output: str) -> list[str]:
    """解析双口相声输出为逐句列表"""
    lines = []
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # 跳过可能的元信息
        if line.startswith('A:') or line.startswith('B:'):
            lines.append(line)
    return lines
