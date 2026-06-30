# 📋 任务卡 001：环境搭建 + 项目熟悉

**发给：** 大一搭档
**日期：** 2026-06-30
**截止：** 2026-07-02（周三）
**难度：** ⭐ 入门

---

## 任务目标

把你的电脑配置好，能把项目跑起来，然后浏览一遍现有功能。

---

## Step 1：安装必要工具

### 1.1 Git
- 下载：https://git-scm.com/downloads
- 安装时一路 Next，**不要改任何默认设置**

### 1.2 Python 3.12+
- 下载：https://www.python.org/downloads/
- 安装时 **☑ 勾选 "Add Python to PATH"**（这步很重要！）

### 1.3 VS Code
- 下载：https://code.visualstudio.com/
- 装好后按 `Ctrl+Shift+X`，搜索安装：
  - **Python**（微软官方扩展）
  - **GitLens**（看 git 记录更直观）

---

## Step 2：克隆项目 + 装依赖

打开终端（cmd 或 VS Code 内置终端），逐条执行：

```bash
# 1. 克隆项目到桌面
cd %USERPROFILE%\Desktop
git clone https://github.com/Ting-Yu520/surf-2026-ai-tactical-assistant.git
cd surf-2026-ai-tactical-assistant

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 验证能跑
streamlit run src/app.py
```

最后一步如果浏览器自动弹出页面 → ✅ 成功！

**如果任何一步报错，截图发给我，别自己折腾。**

---

## Step 3：熟悉项目（1 小时）

### 3.1 打开 Streamlit Demo，把玩一遍
- 选不同的角球场景
- 点"生成二人转科普解说"看效果
- 看看左侧 Phase 1 的战术数据
- 看看右侧 Phase 2 的 AI 解说

### 3.2 浏览关键文件（用 VS Code 打开，看看就行，不用改）

| 文件 | 干什么的 | 你要改吗 |
|------|---------|---------|
| `src/app.py` | Streamlit 页面 | ✅ 以后你要改 |
| `src/pipeline.py` | 核心管线 | 🚫 别碰 |
| `src/prompts/corner_kick.py` | AI 解说 Prompt | 🚫 别碰 |
| `src/video_overlay.py` | 视频合成 | 🚫 别碰 |
| `src/tts_client.py` | TTS 配音 | 🚫 别碰 |
| `src/config.py` | 配置文件 | 🚫 别碰 |
| `src/data/corner_kicks_2026.json` | 角球数据集 | 🚫 别碰 |
| `scripts/batch_process.py` | 批量处理脚本 | ✅ 以后参考 |
| `tests/` | 测试目录 | ✅ 你要写 |
| `docs/` | 文档目录 | ✅ 你要维护 |

### 3.3 看一遍合作契约
- 打开 `docs/collaboration-contract.md`
- 了解我们怎么分工的
- 了解 Git 流程（6 句命令就够了）

---

## Step 4：小试牛刀（做一个微小改动）

**目的：** 让你体验一次完整的 `改代码 → 验证 → git commit → push` 流程。

**具体操作：**

1. 打开 `src/app.py`
2. 找到页面最底部的这行：
   ```python
   st.caption("SURF-2026-0154 · Generative HCI for Sports Analytics · End-to-End Demo v3")
   ```
3. 把 `v3` 改成 `v3 — 双人团队版`
4. 保存文件
5. 终端运行 `streamlit run src/app.py`，确认页面底部文字变了
6. 执行 Git 提交流程：
   ```bash
   git pull
   git add .
   git commit -m "chore: 添加双人团队署名"
   git push
   ```

**成功后告诉我，我教你怎么开 Pull Request。**

---

## 验收标准

- [x] Python + Git + VS Code 安装完成
- [x] `streamlit run src/app.py` 能正常打开
- [x] 能说出项目 4 个核心文件是干什么的
- [x] 成功完成 Step 4 的微小改动并 push
- [x] 告诉我"好了"，我验收

---

## 有问题？

- **环境报错** → 截图发我，别自己搜 StackOverflow
- **不知道某个文件是干什么的** → 直接问
- **Git 操作卡住了** → 截图发我，别用 `git push --force`

---

*任务卡 001 · 由 Ting-Yu 发出*
