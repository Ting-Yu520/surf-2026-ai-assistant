# ##VISUAL## ai_scene → MG 动画实验方案

## 问题

当前管线中 LLM 输出 `##VISUAL## highlight pos=(x,y)` 只能画一个红圈，
无法生成丰富的 MG 动画内容。

## 方案

扩展 `##VISUAL##` 指令体系，新增 `ai_scene` 类型：

```text
A: 你看梅西站在这——近门柱位置
##VISUAL## ai_scene "梅西站在近门柱，红色箭头指向球门，
防守球员一字排开，足球在角旗处。概率面板显示 42%"
```

## 架构流程

```text
LLM 输出
  │
  ├── ##VISUAL## highlight pos=(x,y)  → ffmpeg 画红圈 (现有)
  │
  └── ##VISUAL## ai_scene "描述"     → OpenMontage HyperFrames
          │                               │
          │   1. 解析描述 → 场景剧本       │
          │   2. 匹配模板 → 填充参数       │
          │   3. GSAP 渲染 → 输出 MP4      │
          │                               │
          └──▶ 插入视频时间线 (替换原画面)
```

## 技术路线：HyperFrames

选择 HyperFrames (HTML/GSAP) 而非 Remotion (React) 的理由：

| 维度 | HyperFrames | Remotion |
|------|------------|----------|
| MG 动画表现力 | ✅ GSAP 原生动效 | ❌ 需要 React interpolate |
| 快速迭代 | ✅ HTML 直接修改 | ❌ 需编译 |
| 临时场景 | ✅ 零配置启动 | ❌ 需项目结构 |
| SVG 角色动画 | ✅ 原生支持 | △ 需额外库 |

## 示例场景

见 `soccer-tactical-scene.html` — 一段 5 秒的角球战术 MG 动画：

| 时间段 | 内容 | 动画效果 |
|--------|------|----------|
| 0.0-0.5s | 场景渐入 + 标题 | fadeIn + slideDown |
| 0.5-1.0s | 球员弹性出现 + 球场元素 | back.out 弹性 |
| 1.0-1.5s | 高亮圈出现 + 数据面板 | 脉冲动效 |
| 1.5-2.0s | 箭头动画（指向球门） | scaleX |
| 2.0-3.5s | 卡片轮换 + 数据展示 | slideIn |
| 3.5-5.0s | 出画 + TacticAI 结论 | fadeOut |

## 如何在管线中集成

### Step 1: 修改 Prompt（corner_kick.py）

```python
## 视频剪辑指令
新增 ##VISUAL## ai_scene "描述" 类型：
- ai_scene 描述应包含：位置、球员、动作、方向
- 描述越具体，生成的 MG 越准确
- 描述使用引号包裹
```

### Step 2: 解析扩展（parse_script）

```python
# 在 parse_script 中新增 ai_scene 解析
if line.startswith('##VISUAL##'):
    visual = line.replace('##VISUAL##', '').strip()
    if visual.startswith('ai_scene'):
        # 提取引号内的描述
        desc = re.search(r'"(.+?)"', visual)
        current["ai_scene"] = desc.group(1) if desc else ""
    else:
        current["visual"] = visual
```

### Step 3: 生成 MG 动画

```python
def render_ai_scene(description: str, output_path: str):
    """
    1. 解析 ai_scene 描述
    2. 选择对应的 HyperFrames 模板
    3. 填充参数（球员位置、文本、颜色）
    4. 调用 npx hyperframes compose render
    """
    scene_config = parse_scene_description(description)
    html = render_template(scene_config)
    html_path = save_temp_html(html)
    subprocess.run([
        "npx.cmd", "hyperframes", "compose", "render",
        "--input", html_path,
        "--output", output_path,
        "--width", "1280", "--height", "720",
    ])
```

### Step 4: 插入视频时间线

```python
# timeline 中 ai_scene 段替换原视频画面
for seg in timeline:
    if seg.get("ai_scene"):
        # 生成 MG 动画替代原画面
        mg_path = render_ai_scene(seg["ai_scene"], f"_mg_{i}.mp4")
        # 用 MG 动画片段替换原视频的对应时间段
        replace_with_mg(seg, mg_path)
```

## Demo v2 画面策略

| 画面类型 | 占比 | 用途 |
|---------|------|------|
| MG 动画 | ~70% | 战术分析、球员站位、箭头、数据面板 |
| 真实画面（定格） | ~20% | 高光关键帧、实况截图 |
| 真实画面（视频） | ~10% | 让观众知道"这是哪个画面" |

## 实验验证

```bash
# 1. 用 HyperFrames 渲染示例场景
cd D:\ClaudeWorkspace\projects\surf-2026-ai-tactical-assistant\skills\openmontage\remotion-composer

# 方法一：HyperFrames（MG 动画强）
npx hyperframes compose render \
  --input experiments/ai-scene-mg/soccer-tactical-scene.html \
  --output experiments/ai-scene-mg/output/tactical-scene.mp4 \
  --width 1280 --height 720

# 方法二：Remotion（数据驱动）
npx remotion render src/index.tsx Explainer \
  experiments/ai-scene-mg/output/tactical-remotion.mp4 \
  --props experiments/ai-scene-mg/props/tactical-props.json \
  --codec h264

# 2. 评估输出
ffprobe experiments/ai-scene-mg/output/tactical-scene.mp4
```

## 预期效果

一段 5 秒的 MG 动画，展示：
- ✅ 绿色球场 + 禁区 + 球门
- ✅ 红蓝球员点 + 标签
- ✅ 脉冲高亮圈（近门柱 + 球门区）
- ✅ 箭头指示方向
- ✅ 文字卡片（战术术语解释）
- ✅ TacticAI 概率面板
- ✅ 平滑 GSAP 动效
