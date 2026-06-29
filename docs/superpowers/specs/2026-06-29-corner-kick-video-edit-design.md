# 角球解说视频剪辑设计方案

**SURF-2026-0154 · AI Tactical Assistant**
**2026-06-29**

---

## 1. 目标

将 Phase 2 生成的二人转解说文本与角球视频智能剪辑结合，输出最终科普视频：
- 解说内容引用 Phase 1 TacticAI 数据（作为点缀）
- 视频按解说文本节奏剪辑，添加高光彩蛋和角色区分
- 最终产出是 MP4 视频，非音频

## 2. 改动范围

| 文件 | 改动 |
|------|------|
| `src/prompts/corner_kick.py` | Prompt 增加战术数据彩蛋指令 |
| `src/phase_bridge.py` | 输出格式改为两段式（事实 + 战术彩蛋） |
| `src/video_overlay.py` | **重写**：moviepy → ffmpeg 管线，支持字幕高光 |
| `src/app.py` | 传入 video_path，视频优先展示 |
| `src/pipeline.py` | Step 5 改用新的 video_overlay |

## 3. Prompt 设计（corner_kick.py）

### 新增角色指令

```
## 战术彩蛋
A 可以偶尔引用战术分析数据来显摆专业度，如：
"TacticAI 算出来这个球员有 45% 的概率接到球"
但整段脚本最多用 2 次，重点是让故事有意思。
```

### 入参格式

`DUO_USER_TEMPLATE` 改为接收两段式文本：

```
## 比赛事实
{fact_section}

## 战术彩蛋（可选引用）
{tactic_section}
```

## 4. 数据桥接（phase_bridge.py）

`format_for_prompt()` 输出改为两段：

```
比赛：Netherlands vs Tunisia
时间：61'
进球者：Jan Paul van Hecke
战术描述：Near-post header from right-side corner

--- 战术彩蛋 ---
TacticAI 分析：
- 最可能接球球员 #0，概率 45%，位置 (65, 40)
- 防守方关键球员 #6，概率 6%，位置 (68, 38)
```

## 5. 视频剪辑管线（video_overlay.py）

### 技术选型

从 **moviepy** 迁移到 **ffmpeg**（基于 openmontage video-edit skill）。

### 视频结构

```
帧时间轴：
[0s-3s]    标题卡（比赛信息+场景名）
[3s-15s]   角球视频 + 分层解说
              ├ 边框色条（A=红，B=蓝）
              ├ 左上角色标（🔴懂哥 / 🔵小白）
              └ 高光彩蛋（基于时间戳的球员位置标注）
[15s-17s]  尾卡（SURF-2026 credit）
```

### 角色区分：边框色 + 角标

| 角色 | 边框色 | 角标 | 说明 |
|------|--------|------|------|
| A（懂哥） | `#FF4444` 红色 | 🔴 懂哥 | 红色调，代表"老球迷" |
| B（小白） | `#4488FF` 蓝色 | 🔵 小白 | 蓝色调，代表"好奇" |

边框实现：ffmpeg `drawbox` filter，视频四边各 4px 宽。

### 高光彩蛋

基于脚本解析结果（从文本中提取位置/球员信息），在高光时刻叠加：
- **半透明红色圆形高亮** `drawtext` + `overlay` 在对应球员位置
- 显示 2-3 秒后淡出

### 字幕不遮挡画面

不叠加底部字幕条。替代方案：
- **彩色边框** 区分谁在说话
- **左上角色标** 标示当前讲话人
- 关键术语如需展示，用 **小号浮动标签** 短暂显示在画面空白区

### 逐句时间轴（关键设计）

视频剪辑需要精确的 A/B 话时间戳。改为**逐句 TTS 管线**：

```text
脚本 (A/B对话)
  → 每句独立 TTS 生成（含句间静默 0.3s）
  → 累计每句偏移时间（start_at / duration）
  → 组装时间轴: [{speaker, text, start, end}, ...]
  → ffmpeg 按时间轴切换边框色 + 角标
```

pipeline 中 Step 4 拆解：
- 4a: 逐句 TTS（多线程并发）
- 4b: 合并为完整音频
- 4c: 输出时间轴 JSON，供 Step 5 消费

## 6. App UI 调整

- 按钮点下后，管线执行完自动播放视频
- 展示区从上到下：视频 > 脚本 > 音频（可下载）
- 左侧 Phase 1 TacticAI 数据保持不变

## 7. 不变部分

| 组件 | 原因 |
|------|------|
| `tts_client.py` | 工作正常，无需改动 |
| `config.py` | 配置不变 |
| 数据集 JSON | 格式不变 |
| `pipeline.py` Phase 2 生成逻辑 | 数据流不变 |
| 视频原始文件 | 作为剪辑素材 |

## 8. 实现顺序

1. `phase_bridge.py` — 两段式格式化
2. `prompts/corner_kick.py` — Prompt 彩蛋指令
3. `video_overlay.py` — ffmpeg 视频剪辑管线
4. `pipeline.py` — 打通视频合成
5. `app.py` — 传入 video_path，视频优先展示
6. 运行验证
