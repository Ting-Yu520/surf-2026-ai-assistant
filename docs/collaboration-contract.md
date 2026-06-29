# SURF-2026-0154 双人合作契约

**签署人：** [你的名字]（大三，核心工程师）& [搭档名字]（大一，前端/脚本/测试）  
**项目：** AI Tactical Assistant — 2026 世界杯角球 AI 科普解说  
**签署日期：** 2026-06-29  
**状态：** ✅ 生效中

---

## 一、核心理念

> 按技术栈分拆，各管一层：
>
> **你（大三）** — 技术管线（后端逻辑 + 核心 IP）  
> **他（大一）** — 前端呈现 + 脚本工具 + 测试保障
>
> 接口就是 `process_corner_kick()` 那几个函数，你固定了接口签名，他随便调。
> 互不踩脚，各改各的文件。

---

## 二、角色分工

### 🔥 你（大三）— 核心管线工程师

| 领域 | 文件/模块 | 权限 |
|------|-----------|------|
| **管线编排** | `src/pipeline.py` | 🚫 只有你能改 |
| **Prompt 工程（核心 IP）** | `src/prompts/corner_kick.py` | 🚫 只有你能改 |
| **视频合成** | `src/video_overlay.py` | 🚫 只有你能改 |
| **TTS 配音** | `src/tts_client.py` | 🚫 只有你能改 |
| **API 配置** | `src/config.py`, `.env` | 🚫 只有你能改 |
| **Review 所有代码** | 他的 Pull Request | ✅ 你负责 |
| **项目方向决策** | 所有 | ✅ 你说了算 |

### 🔧 他（大一）— 前端 & 工程支持

| 领域 | 文件/模块 | 说明 |
|------|-----------|------|
| 🎨 **Streamlit 前端** | `src/app.py` | 加新页面、新卡片、调布局、改样式 |
| 🔧 **脚本工具** | `scripts/` | 写辅助脚本、数据处理工具、自动化小工具 |
| ✅ **测试** | `tests/` | 给每个函数写 pytest 用例 |
| 📖 **文档** | `docs/`, `README.md` | 使用指南、API 说明 |

**他不准碰：** `pipeline.py` / `prompts/` / `video_overlay.py` / `tts_client.py` / `config.py` / `.env`

> **为什么这么分：**
>
> - 他改 `app.py` 加个卡片 → 你管线不用动，他马上看到页面变了，成就感来的快
> - 他写脚本工具 → 独立的小程序，写坏了删了就行，不影响核心
> - 他写测试 → 写得再烂也不会炸生产代码，反而帮你抓 bug

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

# 3. VS Code（写代码用）
→ 下载 https://code.visualstudio.com/
→ 装好后按 Ctrl+Shift+X，搜索安装：Python (微软官方扩展)
→ 再搜安装：GitLens（看 git 记录更直观）
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

```bash
# 第1步：拉最新代码（每次干活前必须先做）
git pull

# 第2步：开始干活（改 app.py / 写测试 / 写脚本...）

# 第3步：看看改了哪些文件
git status

# 第4步：把所有改动打包
git add .

# 第5步：写个说明并提交
git commit -m "feat: app.py 新增角球对比页面"

# 第6步：推上 GitHub
git push
```

### 4.3 开 Pull Request（每次 push 后）

1. 浏览器打开 `https://github.com/你的用户名/surf-2026`
2. 页面顶部会弹出黄色的 `Compare & pull request` 按钮 → 点它
3. 标题写改了啥（比如 `feat: app.py 新增角球对比页面`）
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

### 📋 任务卡 1：前端——加新卡片 / 新页面

```
任务：在 app.py 加一个 [功能名称]
文件：src/app.py

具体要求：
- 在 [位置] 加一个 [组件类型：按钮/选择框/卡片]
- 功能是 [描述功能]
- 参考代码：app.py 里第 XX 行那个 similar 组件，照着写就行

成功标准：
1. git pull
2. 修改 src/app.py
3. 终端运行：streamlit run src/app.py
4. 浏览器打开 http://localhost:8501
5. 能看到新加的组件正常工作
6. git add . → git commit -m "feat: 加XXX" → git push → 开 PR
```

### 📋 任务卡 2：脚本工具

```
任务：写一个 [脚本名称]
文件：scripts/[脚本名].py

用途：[一两句话说明这个脚本干什么的]
输入：[什么格式的数据]
输出：[什么格式的结果]

参考模板：scripts/batch_process.py（照着它的结构写）

成功标准：
1. python scripts/[脚本名].py 能跑通
2. 产出结果符合预期
3. git add . → git commit -m "feat: 添加XXX脚本" → git push → 开 PR
```

### 📋 任务卡 3：写测试

```
任务：给 [函数名] 写测试
文件：tests/test_[模块名].py

函数在：src/[文件名].py 第 XX 行
函数签名：[复制函数签名给它]

要求：
- 正常输入 → 检查输出格式正确
- 边界情况 → 空输入 / 极端值
- 错误情况 → 应该抛出什么异常

参考写法：看 tests/ 目录下已有的测试

成功标准：
1. pytest tests/test_[模块名].py -v
2. 所有测试绿色 PASS
3. git add . → git commit -m "test: 添加XXX测试" → git push → 开 PR
```

### 📋 任务卡 4：修 Bug（前端/样式类）

```
任务：修 [问题描述]
文件：src/app.py 或 相关样式文件

现象：[截图或描述，比如"选择框跑出页面边界了"]

定位：
- 问题大概在 app.py 第 XX 行附近
- 可能是 [原因推测]

思路：[你给的解决方向]

成功标准：
1. 修复后 streamlit run src/app.py 正常显示
2. 之前出问题的地方不再出现
3. git add . → git commit → git push → 开 PR
```

---

## 六、质量验收标准

> 他交上来的东西，你用这个标准检查。

| 交付物 | 验收标准 |
| :------ | :-------- |
| **前端修改** | ✅ `streamlit run src/app.py` 不报错；新功能按预期工作；没破坏现有页面 |
| **脚本工具** | ✅ `python scripts/xxx.py` 能跑通；产出结果格式正确；代码有注释 |
| **测试用例** | ✅ `pytest tests/ -v` 全部绿色；覆盖正常+边界+异常；没有假测试 |
| **文档** | ✅ Markdown 格式；步骤可操作；别人照着能做 |

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
  ├─ 他：交本周成果，所有 PR 都开好
  ├─ 你：最终 Review，合并所有 PR
  └─ 你俩（可选）：语音 5 分钟，下周计划
```

---

## 八、意外处理

| 情况 | 怎么办 |
|------|--------|
| **他 git 操作卡住了** | 别自己乱试！截图发给你 |
| **他电脑环境坏了** | 重装看第三章，或找你远程 |
| **他改错了文件** | 你 `git revert` 回滚，然后告诉他错在哪 |
| **他不确定怎么做** | 先不做，问清楚再动手 |
| **他改 app.py 把页面搞崩了** | 你 `git revert` 那个 PR，让他重写 |
| **管线跑出来结果很烂** | 不是他的问题，是你 Prompt 或数据集的问题 |

---

## 九、签署

```
你（大三核心管线工程师）：_______________    日期：________
他（大一前端/脚本/测试）：_________________    日期：________
```

*本契约一式两份，存于 `docs/collaboration-contract.md`，可随时修订。*
