# DeepSeek 统一 VLM + LLM 重构设计

**日期:** 2026-06-30  
**状态:** 已批准  
**范围:** VLM 关键帧分析 + 解说生成引擎

---

## 背景与动机

4 个阻塞性问题驱动本次重构：

| # | 问题 | 根因 |
|---|------|------|
| 1 | Gemini API 不可达 | 企业网络封锁 `generativelanguage.googleapis.com`，VideoAnalyzer 静默降级为 stub |
| 2 | google-generativeai SDK 废弃 | 代码导入旧 SDK，requirements.txt 写新 SDK 名，包名不匹配 |
| 3 | DeepSeek V4 Pro 思考模式慢 | 每条解说 ~30s，思考链消耗大量 token |
| 4 | max_tokens 硬编码 | config.yaml 写死 2048，legacy src/config.py 也有冗余定义 |

**目标：** 用 DeepSeek 统一所有 API 调用，消除 Gemini 依赖，提升速度，修复 max_tokens 配置管理。

---

## 设计方案

### 1. VideoAnalyzer：Gemini → DeepSeek 多模态

**文件变更：**

| 文件 | 操作 |
|------|------|
| `core/llm_client.py` | 新增 `call_llm_multimodal()` 函数 |
| `agents/video_analyzer/agent.py` | 改用 Anthropic SDK 调用 DeepSeek 视觉 |
| `agents/video_analyzer/config.yaml` | model 改为 deepseek-v4-flash |
| `requirements.txt` | 删除 `google-genai>=0.3.0` |

**`core/llm_client.py` 新增函数：**

```python
def call_llm_multimodal(
    model: str,
    system_prompt: str,
    user_text: str,
    images: list[dict],  # [{"data": "<base64>", "media_type": "image/jpeg"}, ...]
    api_key: str,
    base_url: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    timeout: int = 60,
) -> str:
```

函数内部构造 Anthropic Messages API 格式的 content blocks（text + image），通过 `anthropic.Anthropic` 客户端发送。

**VideoAnalyzer 调用变更：**

```python
# 改前：google.generativeai SDK
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content(content, request_options={"timeout": timeout_ms})

# 改后：通过 core/llm_client.py 统一调用
text = call_llm_multimodal(
    model=self.config.get("model", "deepseek-v4-flash"),
    system_prompt="",
    user_text=prompt,
    images=[{"data": base64_bytes, "media_type": "image/jpeg"} for ...],
    api_key=api_key,
    base_url=base_url,
    max_tokens=self.config.get("max_tokens", 2048),
    timeout=self.config.get("timeout", 30),
)
```

**删除：**
- `import google.generativeai as genai`
- `HAS_GEMINI` 标志
- `_stub_analysis()` 方法
- stub 降级逻辑（API 不可达时直接抛出 `ModelCallError`，由上层 FusionAgent 处理）

> **⚠️ 风险提示：** DeepSeek Anthropic 兼容端点是否支持图片输入需实测。如不支持，备选方案：
> - 备选 A：接入国内视觉模型 API（如通义千问 VL，通过 OpenAI 兼容端点）
> - 备选 B：VLM 降级为可选增强，以 `phase1_batch_output.json` 为主数据源

---

### 2. CommentaryGen：deepseek-v4-pro → deepseek-v4-flash

**文件变更：**

| 文件 | 操作 |
|------|------|
| `agents/commentary_gen/config.yaml` | `model` 改为 `deepseek-v4-flash` |
| `src/config.py` | `DEEPSEEK_MODEL` 默认值不变（legacy 兼容），加注释 |

**速度预估：** 30s → 3-5s（无思考链，直出结果）

---

### 3. max_tokens 按模型配置

**文件变更：**

| 文件 | 操作 |
|------|------|
| `agents/commentary_gen/config.yaml` | 保留 `max_tokens: 2048`，加注释说明模型对应的推荐值 |
| `src/config.py` | 保留 `MAX_TOKENS = 2048`，加 note 指向新 agent 配置 |

**`agents/commentary_gen/config.yaml` 最终内容：**

```yaml
model: "deepseek-v4-flash"
base_url: "https://api.deepseek.com/anthropic"
deepseek_api_key: ""
# max_tokens 按模型推荐：
#   deepseek-v4-flash: 2048（纯输出，无思考预算需求）
#   deepseek-v4-pro:   4096（思考链 + 输出各约 2000）
# 可通过环境变量 MAX_TOKENS 覆盖
max_tokens: 2048
temperature: 0.85
timeout: 120
```

`core/config_loader.py` 的 `load_yaml_and_env()` 已支持大写环境变量覆盖 YAML key，无需改动。

`src/config.py` 中 `MAX_TOKENS` 保留供 legacy `src/pipeline.py` 使用，加注释。

---

### 4. 依赖清理

**`requirements.txt` 变更：**

```diff
- google-genai>=0.3.0
+ # google-genai removed (2026-06-30): VLM now uses DeepSeek via Anthropic SDK
```

---

## 影响评估

| 指标 | 改前 | 改后 |
|------|------|------|
| 外部 API 依赖 | DeepSeek + Gemini | **仅 DeepSeek** |
| SDK 数量 | anthropic + google-generativeai | **仅 anthropic** |
| 解说生成速度 | ~30s | **~3-5s** |
| max_tokens 管理 | 单一硬编码值 | **按模型文档化 + 环境变量覆盖** |
| VLM 故障行为 | 静默 stub（输出空数据） | **明确报错（ModelCallError）** |
| 网络依赖 | 需 Google API（被封锁） | **仅 DeepSeek（国内可达）** |

---

## 文件变更清单

```
修改:
  core/llm_client.py               — 新增 call_llm_multimodal()
  agents/video_analyzer/agent.py   — Gemini SDK → Anthropic SDK + DeepSeek VLM
  agents/video_analyzer/config.yaml — model: deepseek-v4-flash
  agents/commentary_gen/config.yaml — model: deepseek-v4-flash, max_tokens 注释
  src/config.py                    — MAX_TOKENS 加注释
  requirements.txt                 — 删除 google-genai

删除（逻辑层面，文件不动）:
  agents/video_analyzer/agent.py   — HAS_GEMINI / _stub_analysis() / genai import
```

---

## 测试要点

1. **DeepSeek VLM 可达性**：发送单张关键帧，验证返回 JSON 格式战术数据
2. **CommentaryGen 速度**：用 flash 模型生成完整解说，计时对比
3. **max_tokens 环境变量覆盖**：设置 `MAX_TOKENS=4096` 验证并发生效
4. **完整管线**：FusionAgent 端到端运行，确认不再报 Gemini 相关错误
5. **Legacy pipeline**：`scripts/batch_process.py` 确认不受影响
