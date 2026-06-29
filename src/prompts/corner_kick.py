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

## 战术彩蛋
A 可以偶尔引用战术分析数据来显摆专业度，如：
"TacticAI 算出来这个球员有 45% 的概率接到球"
但整段脚本最多用 2 次，重点是让故事有意思。

**重要：对话里不要念坐标数字(65,40)这种东西，观众听不懂。
用描述代替："你看他站的那个空档位置"**

## 视频剪辑指令

为了让视频画面跟上解说，每段台词后必须紧跟一行视觉指令：

A: （台词）
##VISUAL## ai_scene
B: （台词）
##VISUAL## highlight pos=(x,y)

指令类型：
- ai_scene — 触发全屏 MG 战术动画（仅 A 使用，Python 自动提取数据生成）
- highlight pos=(x,y) — 真实画面定格 + 指定位置显示红色高亮圈（B 使用）
- clear — 清除之前的高亮

坐标范围 (0-100, 0-100)，根据下面"战术彩蛋"里的位置数据填写。
如果当前台词没有对应坐标，就写 ##VISUAL## clear。

输出格式：
A: （台词）
##VISUAL## ai_scene
B: （台词）
##VISUAL## highlight pos=(x,y) 或 ##VISUAL## clear

不要旁白，不要场景描述，只要对话和视觉指令。"""

DUO_USER_TEMPLATE = """请根据下面的足球比赛信息，写一段双口相声科普脚本。

## 比赛事实
{fact_section}

## 战术彩蛋（可选）
下面这些战术分析数据 A 可偶尔引用：
{tactic_section}

## 要求
- A+B 总共 3-4 轮对话
- 脚本总字数不超过 200 字，每句控制在 15 字以内
- A 上来先卖弄知识
- B 一脸懵逼，逼 A 解释人话
- 最后 B 表示懂了
- 每段 A 台词后紧跟 ##VISUAL## 视觉指令
- 对话里不要出现坐标数字"""


def build_duo_prompt(formatted: dict) -> tuple[str, str]:
    return (
        DUO_SYSTEM_PROMPT,
        DUO_USER_TEMPLATE.format(
            fact_section=formatted["fact_section"],
            tactic_section=formatted["tactic_section"],
        ),
    )


def parse_duo_output(output: str) -> list[dict]:
    """解析双口相声输出为带视觉指令的结构化列表"""
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
