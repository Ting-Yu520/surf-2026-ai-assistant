# SURF-2026-0154 双人合作契约

**签署人：** [你的名字]（大三，核心工程师）& [搭档名字]（大一，数据助理）  
**项目：** AI Tactical Assistant — 2026 世界杯角球 AI 科普解说  
**签署日期：** 2026-06-29  
**状态：** ✅ 生效中

---

## 一、核心理念

> 框架已搭好，我们往里填内容。
>
> **你（大三）** 守住框架和核心 IP，保证项目不跑偏。  
> **他（大一）** 负责所有需要人工填的内容，你 Review 兜底。
>
> 他不需要搞懂整个项目才能干活——每件事写成「任务卡」，照着做就行。

---

## 二、角色分工

### 🔥 你（大三）— 核心工程师

| 领域 | 文件/模块 | 权限 |
|------|-----------|------|
| **核心管线** | `src/pipeline.py`, `src/video_overlay.py` | 🚫 只有你能改 |
| **Prompt 工程（核心 IP）** | `src/prompts/corner_kick.py` | 🚫 只有你能改 |
| **API 配置** | `src/config.py`, `.env` | 🚫 只有你能改 |
| **Streamlit 前端升级** | `src/app.py` | ✅ 你主力，他可帮忙加简单卡片 |
| **Review 所有代码** | 他的 Pull Request | ✅ 你负责 |
| **项目方向决策** | 所有 | ✅ 你说了算 |

### 🔧 他（大一）— 数据助理

| 任务 | 涉及文件 | 难度 | 频率 |
|------|---------|------|------|
| ✍️ **写文章底本** | `src/data/corner_articles.json` | ⭐ 纯文案，复制模板改 | 每周 3-5 条 |
| 📥 **下载比赛视频** | `data/videos/` | ⭐ 一行命令 | 有新比赛时 |
| 🏃 **跑批量管线** | `python scripts/batch_process.py` | ⭐ 一行命令 | 每周 1 次 |
| 🎯 **输出质量检查** | `outputs/batch/` | ⭐ 看视频+读文本 | 每次批量后 |
| 📝 **写测试用例** | `tests/` | ⭐⭐ 按模板写 | 每周 2-3 个 |
| 📖 **写文档** | `docs/`, `README.md` | ⭐ 打字就会 | 持续 |

---

## 三、他需要装的环境

> 一次性配好，以后不用再碰。

### 3.1 必须装的

```bash
# 1. Git（代码版本管理）
→ 下载 https://git-scm.com/downloads
→ 安装时一路 Next，别改任何设置

# 2. Python 3.12+
→ 下载 https://www.python.org/downloads/
→ 安装时 ✔ 勾选 "Add Python to PATH"

# 3. ffmpeg（视频处理）
→ 下载 https://ffmpeg.org/download.html
→ 解压后把 ffmpeg.exe 所在文件夹加到系统 PATH

# 4. VS Code（写代码用）
→ 下载 https://code.visualstudio.com/
→ 装好后按 Ctrl+Shift+X，搜索安装：Python (微软官方扩展)
```

### 3.2 第一次运行项目

```bash
# 打开终端（cmd 或 VS Code 终端）
cd 桌面
git clone https://github.com/你的用户名/surf-2026.git
cd surf-2026

# 创建虚拟环境（隔离依赖，防止冲突）
python -m venv venv
venv\Scripts\activate    # Windows 激活

# 安装依赖
pip install -r requirements.txt

# 测试能不能跑
streamlit run src/app.py
# → 浏览器弹出页面 = 成功！
```

---

## 四、Git 云端协作——作弊条

> 他会用的 6 句命令，足够了。

### 4.1 第一次（仅一次）

```bash
git clone https://github.com/你的用户名/surf-2026.git
cd surf-2026
```

### 4.2 每次任务循环

他照着这个顺序打就行：

```bash
# 第1步：拉最新代码（每次干活前必须先做）
git pull

# 第2步：开始干活（写文章 / 下载视频 / 跑脚本...）

# 第3步：看看改了哪些文件
git status

# 第4步：把所有改动打包
git add .

# 第5步：写个说明并提交
git commit -m "add article for corner-017"

# 第6步：推上 GitHub
git push
```

### 4.3 开 Pull Request（每次 push 后）

1. 浏览器打开 `https://github.com/你的用户名/surf-2026`
2. 页面顶部会弹出黄色的 `Compare & pull request` 按钮 → 点它
3. 标题写改了啥（比如 `feat: add corner-017 article`）
4. 点 `Create pull request`
5. **等着你来 Review**
6. 你 Approve + Merge 后，他那边 `git pull` 拉回最新代码

### 4.4 不要做的事

```diff
- ❌ 不要在 GitHub 网页上直接改代码
- ❌ 不要改 pipeline.py / prompts/ 下的任何文件
- ❌ 不要改 .env 文件
- ❌ 不要用 git push --force（强推会删代码）
```

---

## 五、任务卡模板

> 你给他派任务时，直接复制下面的模板发给他就行了。

### 📋 任务卡 1：写文章底本

```
任务：给角球 XXX 写文章底本
文件：src/data/corner_articles.json
要求：200-400 字，写这个角球的比赛经过
      - 什么时候、谁对谁
      - 谁罚的角球、怎么罚的
      - 谁进的球、怎么进的
      - 这个球为什么重要

步骤：
1. git pull
2. 打开 src/data/corner_articles.json
3. 在末尾加一条："{eid}": "你的文案"
4. 运行 python -c "import json; json.load(open('src/data/corner_articles.json'))"
   看到没报错 = 格式正确
5. git add . → git commit -m "add article for {eid}" → git push
6. 在 GitHub 开 Pull Request
```

### 📋 任务卡 2：下载视频

```
任务：下载新比赛视频
命令：python scripts/download_videos.py

步骤：
1. git pull
2. python scripts/download_videos.py
3. 看 data/videos/ 目录下有没有新 mp4 文件
4. 有的话 git add . → git commit -m "add new videos" → git push
```

### 📋 任务卡 3：跑批量管线

```
任务：跑全部角球的 AI 解说
命令：python scripts/batch_process.py

步骤：
1. git pull
2. python scripts/batch_process.py
3. 等它跑完（大概 5-10 分钟）
4. 打开 outputs/batch/ 目录，翻一遍生成的结果
5. 告诉我：✅ 哪几条效果好 / ❌ 哪几条有问题
```

### 📋 任务卡 4：质量检查

```
任务：检查 batch 输出的质量
位置：outputs/batch/

检查清单：
[ ] 生成了几条？数量对得上 dataset 里的条目数吗？
[ ] 随机打开 3 条解说文本，读一遍，有没有明显胡说的？
[ ] 有视频的输出，声音和画面同步吗？
[ ] 把有问题的那几条告诉我（编号+问题描述）
```

---

## 六、质量验收标准

> 他交上来的东西，你用这个标准检查。

| 交付物 | 验收标准 |
|--------|---------|
| **文章底本** | ✅ JSON 格式能通过 `json.load()` | ✅ 200-400 字 | ✅ 基于事实不编造 | ✅ 语言通顺 |
| **下载的视频** | ✅ 文件存在 `data/videos/` | ✅ 能正常播放 | ✅ 命名规范 `wc2026-corner-XXX.mp4` |
| **批量跑的结果** | ✅ 所有条目都跑完 | ✅ 输出文件完整 | ✅ 汇报了哪些好哪些差 |
| **测试用例** | ✅ `pytest tests/` 通过 | ✅ 测的是你指定那个函数 |
| **文档** | ✅ Markdown 格式 | ✅ 步骤可操作 | ✅ 没有错别字 |

---

## 七、每周节奏

```
周一
  ├─ 你：告诉他这周要做什么（发任务卡）
  └─ 他：领任务，开始干

周二 ~ 周四
  ├─ 他：干活，push，开 PR
  └─ 你：Review + Merge（每天花 5 分钟看一眼）

周五
  ├─ 他：交本周成果，跑一遍批量管线
  ├─ 你：最终 Review，合并所有 PR
  └─ 你俩（可选）：语音 5 分钟，下周计划
```

---

## 八、意外处理

| 情况 | 怎么办 |
|------|--------|
| **他 git 操作卡住了** | 别自己乱试！截图发给你 |
| **他电脑环境坏了** | 重装看第三章，或找你远程 |
| **他改错了文件** | 你 git revert 回滚，然后告诉他错在哪 |
| **他不确定怎么做** | 先不做，问清楚再动手 |
| **管线跑出来结果很烂** | 不是他的问题，是你 Prompt 或数据集的问题 |

---

## 九、签署

```
你（大三核心工程师）：_______________    日期：________
他（大一数据助理）：_________________    日期：________
```

*本契约一式两份，存于 `docs/collaboration-contract.md`，可随时修订。*
