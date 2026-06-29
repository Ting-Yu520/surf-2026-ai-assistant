# MG 动画集成设计文档

**项目**: SURF-2026-0154 AI Tactical Assistant
**日期**: 2026-06-30
**目标**: 将 OpenMontage/HyperFrames MG 动画能力接入角球战术解说管线

---

## 一、架构总览

```
Phase1 TacticAI 数据 ──→  Formatted (fact + tactic)
                               ↓
                          LLM (DeepSeek) 生成脚本
                          A: 懂哥台词
                          ##VISUAL## ai_scene      ← 自动触发 MG 动画
                          B: 小白台词
                          ##VISUAL## highlight pos  ← 真实画面定格高亮
                               ↓
                          Edge TTS 逐句配音 + 时长
                               ↓
                          构建 Timeline
                               ↓
  ┌──────────────────────────────┴──────────────────────────────┐
  │  A 段 (懂哥):                               B 段 (小白):     │
  │  1. 提取真实球员坐标                         1. 提取高亮坐标  │
  │  2. 坐标映射→像素                            2. ffmpeg 定格   │
  │  3. 生成 HyperFrames 变量 JSON               3. 画高亮圈      │
  │  4. npx hyperframes render                  4. 慢动作关键帧  │
  │  5. 输出 MG 动画 clip                                        │
  └──────────────────────────────┬──────────────────────────────┘
                                ↓
                          FFmpeg 合成:
                          片头进球→MG→定格→MG→定格→尾卡
                                ↓
                          最终视频 (.mp4)
```

**核心原则**: Python 做所有数据决策，LLM 只负责标记"这里该播动画"，HTML 只管渲染。

---

## 二、画面配比

| 场景 | 画面类型 | 时长占比 | 内容 |
|------|---------|---------|------|
| 片头 | 进球完整回放 | ~10% | 原速播放完整进球 |
| A 段 (懂哥) | MG 动画 | ~55% | 球场俯视图 + 球员位置 + 数据面板 |
| B 段 (小白) | 真实画面定格 | ~15% | 慢动作关键帧 + 高亮圈标注 |
| 过渡 | MG 动画延续 | ~10% | 动画淡出转场 |
| 尾卡 | 静态总结卡 | ~5% | AI 角球翻译官 |
| 字幕 | 叠加层 | 全程 | TikTok 词级字幕 |

---

## 三、真实数据管线

### 3.1 数据源（双路径自适应，绝不使用模拟数据）

路径 A（优先）: Gemini VLM 视频帧分析
路径 B（fallback）: TacticAI Recreation GNN 模型预测

```python
def get_real_positions(corner_entry, video_path=None):
    if video_path and GEMINI_API_KEY:
        frames = extract_key_frames(video_path, corner_entry["minute"])
        positions = analyze_frames_with_vlm(frames)
        return positions, source="gemini-vlm"
    elif TACTICAI_MODEL_READY:
        predictions = tacticai.predict(corner_entry)
        return predictions, source="tacticai-gnn"
    else:
        raise NoRealDataError("需要视频文件或 TacticAI 模型")
```

### 3.2 球场区域检测（从视频中检测，非硬编码）

```python
def detect_field_rect(video_frame):
    """从真实视频帧检测球场在画面中的像素区域"""
    # 使用 Gemini VLM 检测
    return {"left": px, "right": px, "top": py, "bottom": py}
```

### 3.3 坐标映射（自适应数据范围，无魔法数字）

```python
def build_mapping(positions, field_rect):
    xs = [p["x"] for p in positions]
    ys = [p["y"] for p in positions]
    def to_px(x): return field_rect["left"] + (x-min(xs))/max(xs-min(xs),1) * (field_rect["right"]-field_rect["left"])
    def to_py(y): return field_rect["top"]  + (y-min(ys))/max(ys-min(ys),1) * (field_rect["bottom"]-field_rect["top"])
    return to_px, to_py
```

---

## 四、LLM Prompt 扩展

在现有 `corner_kick.py` prompt 的"视频剪辑指令"部分新增：

```
##VISUAL## ai_scene   — 触发全屏 MG 动画（用于 A 的战术解释时段）
##VISUAL## highlight pos=(x,y)  — 真实画面定格 + 高亮圈（用于 B 的提问时段）

规则：
- A 的每段台词后跟 ##VISUAL## ai_scene
- B 的每段台词后跟 ##VISUAL## highlight pos=(x,y) 或 ##VISUAL## clear
- ai_scene 不需要参数，Python 自动从数据提取坐标和内容
```

---

## 五、文件改动清单

### 修改的文件

| 文件 | 改动 |
|------|------|
| `src/prompts/corner_kick.py` | Prompt 新增 ai_scene 视觉指令类型 |
| `src/pipeline.py` | Step 1 加入视频分析，新增 Step 4c MG 渲染 |
| `src/video_overlay.py` | 新增 MG clip 注入 + B 段定格慢动作 + 片头进球回放 |
| `src/phase_bridge.py` | 替换 sample_tacticai_output() 为真实数据路径 |

### 新增的文件

| 文件 | 职责 |
|------|------|
| `src/mg_renderer.py` | HyperFrames 接口：变量填 JSON → 调 npx 渲染 → 返回 clip |
| `src/vision_analyzer.py` | Gemini VLM 接口：视频帧 → 检测球场区域 + 球员位置 |
| `experiments/ai-scene-mg/templates/tactical-scene.html` | 通用 MG 模板（变量驱动） |

---

## 六、HyperFrames 模板变量系统

### 6.1 变量 JSON Schema

```json
{
  "players": [
    {"id": "att-1", "x": 720, "y": 280, "role": "attacker",
     "number": "10", "label": "梅西", "is_top": true, "probability": 0.42}
  ],
  "ball":         {"x": 1100, "y": 360},
  "highlight":    {"x": 720, "y": 280, "label": "近门柱"},
  "arrow":        {"from_x": 1100, "from_y": 360, "to_x": 720, "to_y": 280, "label": "内旋球路线"},
  "cards":        [
    {"type": "term", "title": "近门柱", "sub": "离球最近的球门柱"},
    {"type": "data", "title": "接球概率", "value": "42%"}
  ],
  "title":        "⚽ 角球战术分析",
  "duration":     6.5
}
```

### 6.2 渲染命令

```bash
npx hyperframes render \
  --composition tactical-scene.html \
  --variables '{"players":[...],...}' \
  --width 1280 --height 720 \
  -o mg_clip_001.mp4 .
```

### 6.3 模板中消费变量

```javascript
const vars = window.__hyperframes.getVariables();
// 动态放置球员、高亮圈、箭头、文字卡片
// 使用 GSAP timeline 控制动画时序
```

---

## 七、错误处理

| 场景 | 处理 |
|------|------|
| Gemini VLM 不可用 | fallback TacticAI 模型预测 |
| TacticAI 模型未训练 | 使用 corner_kicks_2026.json 文本描述，无坐标时以文本解说为主 |
| HyperFrames 渲染超时 (>120s) | 跳过该段 MG，用真实画面 + ffmpeg 数据卡片叠层替代 |
| 某段渲染失败 | 不影响其他段，失败段用静态数据卡替代 |

---

## 八、性能预估

| 阶段 | 耗时 |
|------|------|
| 视频分析（Gemini VLM, 3 帧） | ~5-8 秒 |
| LLM 脚本生成 | ~5-10 秒 |
| TTS 逐句配音 | ~10-20 秒 |
| HyperFrames 渲染（每 MG 段） | ~45-60 秒/段 |
| 典型角球 3 段 A = 3 段 MG | ~3 分钟渲染 |
| FFmpeg 最终合成 | ~10 秒 |
| **总计** | **~4-5 分钟/视频** |
