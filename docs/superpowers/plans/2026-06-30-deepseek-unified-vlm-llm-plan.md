# DeepSeek Unified VLM + LLM Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Gemini VLM with DeepSeek multimodal, switch commentary to `deepseek-v4-flash`, fix `max_tokens` configuration, and remove the deprecated `google-genai` dependency.

**Architecture:** VideoAnalyzer calls DeepSeek vision via the new `call_llm_multimodal()` in `core/llm_client.py`, using the same Anthropic-compatible endpoint as CommentaryGen. Both agents share a unified API key, base URL, and client creation pattern.

**Tech Stack:** Python 3.14, Anthropic SDK >= 0.100.0, DeepSeek Anthropic-compatible endpoint

---

## File Structure Map

| File | Role | Change |
|------|------|--------|
| `core/llm_client.py` | Generic LLM client — `create_client()`, `call_llm()`, new `call_llm_multimodal()` | **Modify** |
| `agents/video_analyzer/agent.py` | Agent ① — VLM keyframe analysis | **Modify** |
| `agents/video_analyzer/config.yaml` | Agent ① config | **Modify** |
| `agents/commentary_gen/config.yaml` | Agent ③ config | **Modify** |
| `src/config.py` | Legacy global config | **Modify** |
| `requirements.txt` | Python dependencies | **Modify** |
| `tests/test_llm_client.py` | New tests for multimodal function | **Create** |

---

### Task 1: Add `call_llm_multimodal()` to `core/llm_client.py`

**Files:**
- Modify: `core/llm_client.py`

- [ ] **Step 1: Add `call_llm_multimodal()` function**

Insert after `call_llm()` (after line 69). The function sends text + base64-encoded images via the Anthropic Messages API, following the standard multimodal content-block format.

```python
def call_llm_multimodal(
    client: Anthropic,
    model: str,
    system_prompt: str,
    user_text: str,
    images: list[dict],
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """Multimodal LLM call — text + images via Anthropic Messages API.

    Used by VideoAnalyzer to send keyframes to DeepSeek vision models.

    Args:
        client: Anthropic client from create_client()
        model: Model name string (e.g. "deepseek-v4-flash")
        system_prompt: System prompt
        user_text: Text portion of the user message
        images: List of {"data": "<base64_str>", "media_type": "image/jpeg"}
        max_tokens: Max tokens to generate
        temperature: Sampling temperature

    Returns:
        Generated text string

    Raises:
        ModelCallError: On API failure
    """
    t0 = time.time()

    # Build content blocks: text first, then images
    content_blocks = [{"type": "text", "text": user_text}]
    for img in images:
        content_blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": img.get("media_type", "image/jpeg"),
                "data": img["data"],
            },
        })

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": content_blocks}],
        )
    except Exception as e:
        raise ModelCallError("llm_client_multimodal", f"API call failed: {e}", original=e)

    elapsed = time.time() - t0
    text_parts = []
    for block in response.content:
        if hasattr(block, "text") and block.text:
            text_parts.append(block.text)
        elif hasattr(block, "content") and block.content:
            text_parts.append(str(block.content))

    result = "\n".join(text_parts)
    if not result.strip():
        raise ModelCallError(
            "llm_client_multimodal", f"Empty response after {elapsed:.1f}s"
        )

    return result
```

- [ ] **Step 2: Verify the file is valid Python**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && python -c "from core.llm_client import create_client, call_llm, call_llm_multimodal; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && git add core/llm_client.py && git commit -m "feat: add call_llm_multimodal() for VLM image+text API calls

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Update `agents/video_analyzer/config.yaml` for DeepSeek

**Files:**
- Modify: `agents/video_analyzer/config.yaml`

- [ ] **Step 1: Replace Gemini config with DeepSeek config**

Replace the entire file content:

```yaml
# Agent 1: VideoAnalyzer — VLM keyframe analysis via DeepSeek
model: "deepseek-v4-flash"
base_url: "https://api.deepseek.com/anthropic"
deepseek_api_key: ""
fps: 1
max_frames: 10
max_tokens: 2048
resolution: [1920, 1080]
timeout: 60
```

Changes explained:
- `model`: `gemini-2.5-flash` → `deepseek-v4-flash`
- `gemini_api_key` → `deepseek_api_key` (resolved from `DEEPSEEK_API_KEY` env var by `load_yaml_and_env`)
- Added `base_url` for DeepSeek endpoint
- Added `max_tokens: 2048` for VLM JSON output budget
- `timeout`: 30 → 60 (VLM responses may take longer with images)

- [ ] **Step 2: Commit**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && git add agents/video_analyzer/config.yaml && git commit -m "refactor: switch VideoAnalyzer config from Gemini to DeepSeek VLM

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Rewrite `agents/video_analyzer/agent.py` — Gemini SDK → Anthropic SDK

**Files:**
- Modify: `agents/video_analyzer/agent.py`

This is the core change. Three sub-steps: (a) replace imports and remove Gemini/stub code, (b) rewrite `run()`, (c) rewrite `_analyze_with_vlm()`.

- [ ] **Step 1: Replace imports and module-level code (lines 1–20)**

Replace lines 1–20 (everything before `class VideoAnalyzer`) with:

```python
"""Agent 1: VLM video frame analysis → tactical JSON via DeepSeek multimodal."""
import base64
import json as json_lib
from pathlib import Path

from moviepy import VideoFileClip

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger
from core.exceptions import ModelCallError
from core.llm_client import create_client, call_llm_multimodal

logger = get_logger("video_analyzer")
```

Changes:
- Removed `import google.generativeai as genai` and `HAS_GEMINI` flag
- Added `create_client`, `call_llm_multimodal` from `core.llm_client`

- [ ] **Step 2: Rewrite `run()` method (lines 29–57)**

Replace the existing `run()` method:

```python
    def run(self, agent_input: AgentInput) -> AgentOutput:
        video_path = agent_input.data.get("video_path")
        frames_data = agent_input.data.get("frames", [])

        if not video_path and not frames_data:
            return AgentOutput(
                status="error", data={}, agent_name="video_analyzer",
                error="No video_path or frames provided",
            )

        # Extract keyframes if not provided
        if not frames_data and video_path:
            frames_data = self._extract_keyframes(video_path)

        # Analyze frames with DeepSeek VLM
        if not frames_data:
            return AgentOutput(
                status="error", data={}, agent_name="video_analyzer",
                error="No frames available for analysis",
            )

        try:
            tactical_json = self._analyze_with_vlm(frames_data)
        except Exception as e:
            logger.error(f"VLM analysis failed: {e}")
            return AgentOutput(
                status="error", data={}, agent_name="video_analyzer",
                error=f"VLM analysis failed: {e}",
            )

        return AgentOutput(
            status="ok",
            data={"tactical_json": tactical_json, "frames": frames_data},
            agent_name="video_analyzer",
        )
```

Changes:
- Removed `HAS_GEMINI` conditional and stub fallback
- VLM failure now returns `status="error"` instead of silently degrading — FusionAgent can handle this explicitly
- Removed the bare `except Exception` that swallowed errors

- [ ] **Step 3: Rewrite `_analyze_with_vlm()` method (lines 86–121)**

Replace the existing `_analyze_with_vlm()`:

```python
    def _analyze_with_vlm(self, frames: list[dict]) -> dict:
        """Send keyframes to DeepSeek VLM via Anthropic-compatible API."""
        api_key = self.config.get("deepseek_api_key", "")
        if not api_key:
            raise ModelCallError("video_analyzer", "No DEEPSEEK_API_KEY configured")

        base_url = self.config.get("base_url", "https://api.deepseek.com/anthropic")
        model = self.config.get("model", "deepseek-v4-flash")
        timeout = self.config.get("timeout", 60)
        max_tokens = self.config.get("max_tokens", 2048)
        temperature = self.config.get("temperature", 0.3)

        client = create_client(base_url=base_url, api_key=api_key, timeout=timeout)

        prompt = self._load_prompt("frame_analysis.txt")
        images = []
        max_f = self.config.get("max_frames", 10)
        for frame in frames[:max_f]:
            with open(frame["path"], "rb") as img_file:
                images.append({
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(img_file.read()).decode(),
                })

        text = call_llm_multimodal(
            client=client,
            model=model,
            system_prompt="",
            user_text=prompt,
            images=images,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Extract JSON block if wrapped in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        logger.info(f"VLM response parsed ({len(text)} chars)")
        return json_lib.loads(text.strip())
```

Key changes from old `_analyze_with_vlm()`:
- `genai.configure()` + `genai.GenerativeModel().generate_content()` → `create_client()` + `call_llm_multimodal()`
- Config keys: `gemini_api_key` → `deepseek_api_key`, `timeout` unit is now seconds (not ms → need to convert)
- `content = [prompt] + image_parts` → proper `content_blocks` built inside `call_llm_multimodal()`
- Added `temperature: 0.3` for deterministic JSON output

- [ ] **Step 4: Remove `_stub_analysis()` method (lines 122–133)**

Delete the entire `_stub_analysis()` method — it is no longer needed. VLM failure is now an explicit error, not a silent degradation.

- [ ] **Step 5: Verify the file is valid Python and imports work**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && python -c "from agents.video_analyzer.agent import VideoAnalyzer; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && git add agents/video_analyzer/agent.py && git commit -m "refactor: migrate VideoAnalyzer from Gemini SDK to DeepSeek VLM via Anthropic SDK

- Replace google.generativeai with core.llm_client.call_llm_multimodal()
- Remove HAS_GEMINI stub/degradation logic — VLM failure is now explicit error
- Remove _stub_analysis() dead code
- Add temperature: 0.3 for deterministic JSON output from VLM

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Switch CommentaryGen model and document max_tokens

**Files:**
- Modify: `agents/commentary_gen/config.yaml`

- [ ] **Step 1: Update model and add max_tokens documentation**

Replace the file content:

```yaml
# Agent 3: CommentaryGen — LLM duo-commentary configuration
model: "deepseek-v4-flash"
base_url: "https://api.deepseek.com/anthropic"
deepseek_api_key: ""
# max_tokens recommendations by model:
#   deepseek-v4-flash: 2048 (no thinking chain — pure output budget)
#   deepseek-v4-pro:   4096 (thinking chain ~2000 + output ~2000)
# Override via environment variable: MAX_TOKENS=4096
max_tokens: 2048
temperature: 0.85
timeout: 120
```

- [ ] **Step 2: Commit**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && git add agents/commentary_gen/config.yaml && git commit -m "refactor: switch CommentaryGen to deepseek-v4-flash, document max_tokens per model

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Update `src/config.py` — add deprecation notes

**Files:**
- Modify: `src/config.py`

- [ ] **Step 1: Add deprecation notes to legacy config, update default model**

Replace lines 21–29 (the LLM config block):

```python
# ============================================================
# LLM 配置 — DeepSeek (Anthropic 兼容端点)
# ⚠️ LEGACY: 新 agent 架构优先使用 agents/*/config.yaml
# 此文件仅供 src/pipeline.py 等旧代码路径使用
# ============================================================
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_TIMEOUT = 60
# max_tokens per model:
#   deepseek-v4-flash: 2048 (no thinking chain)
#   deepseek-v4-pro:   4096 (thinking + output)
# Override via DEEPSEEK_MAX_TOKENS env var
MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "2048"))
TEMPERATURE = 0.7

# ============================================================
# VLM 配置 — 已迁移至 DeepSeek (2026-06-30)
# ⚠️ LEGACY: 这些变量保留用于 src/pipeline.py 向后兼容
# 新代码使用 agents/video_analyzer/config.yaml + core/llm_client.py
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "deepseek-v4-flash")
GEMINI_TIMEOUT = 60
```

Changes:
- `DEEPSEEK_MODEL` default: `deepseek-v4-pro` → `deepseek-v4-flash`
- `MAX_TOKENS` now reads from `DEEPSEEK_MAX_TOKENS` env var instead of hardcoded
- Added deprecation banner pointing to new agent configs
- GEMINI keys now fall back to DEEPSEEK_API_KEY for legacy pipeline compatibility
- GEMINI_MODEL default changed to deepseek-v4-flash

- [ ] **Step 2: Commit**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && git add src/config.py && git commit -m "refactor: update legacy config with deprecation notes, switch default to flash model

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Remove `google-genai` from `requirements.txt`

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Remove google-genai dependency**

Replace lines 9–10:

```
# VLM API (Gemini 视频分析)
google-genai>=0.3.0
```

With:

```
# VLM — migrated to DeepSeek via Anthropic SDK (2026-06-30)
# google-genai removed — no longer needed
```

- [ ] **Step 2: Commit**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && git add requirements.txt && git commit -m "chore: remove google-genai dependency — VLM now uses DeepSeek

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Write unit test for `call_llm_multimodal()`

**Files:**
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for core.llm_client — multimodal content block construction."""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.llm_client import call_llm_multimodal
from core.exceptions import ModelCallError


class TestCallLlmMultimodal:
    """Test call_llm_multimodal content block construction and error handling."""

    def test_single_image_content_block_structure(self):
        """Content blocks contain text block + image block with correct structure."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="{}", content=None)]
        mock_client.messages.create.return_value = mock_response

        call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="You are a VLM.",
            user_text="Analyze this frame.",
            images=[{"data": "aW1hZ2VieXRlcw==", "media_type": "image/jpeg"}],
            max_tokens=512,
            temperature=0.3,
        )

        # Verify the messages.create call arguments
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "deepseek-v4-flash"
        assert call_kwargs["max_tokens"] == 512
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["system"] == "You are a VLM."

        content = call_kwargs["messages"][0]["content"]
        assert len(content) == 2  # text + 1 image
        assert content[0] == {"type": "text", "text": "Analyze this frame."}
        assert content[1]["type"] == "image"
        assert content[1]["source"]["type"] == "base64"
        assert content[1]["source"]["media_type"] == "image/jpeg"
        assert content[1]["source"]["data"] == "aW1hZ2VieXRlcw=="

    def test_multiple_images(self):
        """Multiple images produce multiple image content blocks."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="{}", content=None)]
        mock_client.messages.create.return_value = mock_response

        call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="",
            user_text="Compare these frames.",
            images=[
                {"data": "aW1nMQ==", "media_type": "image/jpeg"},
                {"data": "aW1nMg==", "media_type": "image/png"},
                {"data": "aW1nMw==", "media_type": "image/jpeg"},
            ],
        )

        content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert len(content) == 4  # text + 3 images
        assert content[1]["source"]["media_type"] == "image/jpeg"
        assert content[1]["source"]["data"] == "aW1nMQ=="
        assert content[2]["source"]["media_type"] == "image/png"
        assert content[3]["source"]["data"] == "aW1nMw=="

    def test_empty_images_list(self):
        """Empty images list produces text-only content."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="response", content=None)]
        mock_client.messages.create.return_value = mock_response

        result = call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="",
            user_text="Hello",
            images=[],
        )

        content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert len(content) == 1
        assert content[0] == {"type": "text", "text": "Hello"}
        assert result == "response"

    def test_default_media_type_is_jpeg(self):
        """Image dict without media_type defaults to image/jpeg."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="ok", content=None)]
        mock_client.messages.create.return_value = mock_response

        call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="",
            user_text="x",
            images=[{"data": "Zm9v"}],  # no media_type key
        )

        content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert content[1]["source"]["media_type"] == "image/jpeg"

    def test_api_failure_raises_model_call_error(self):
        """API exception is wrapped in ModelCallError."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Connection timeout")

        with pytest.raises(ModelCallError, match="API call failed"):
            call_llm_multimodal(
                client=mock_client,
                model="deepseek-v4-flash",
                system_prompt="",
                user_text="test",
                images=[{"data": "Zm9v"}],
            )

    def test_empty_response_raises_model_call_error(self):
        """Empty/missing text in response raises ModelCallError."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="", content="")]  # both empty
        mock_client.messages.create.return_value = mock_response

        with pytest.raises(ModelCallError, match="Empty response"):
            call_llm_multimodal(
                client=mock_client,
                model="deepseek-v4-flash",
                system_prompt="",
                user_text="test",
                images=[],
            )

    def test_content_block_with_content_attr(self):
        """Blocks with .content attr (not .text) are also extracted."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        # block.text is empty, block.content has the payload
        block = MagicMock()
        block.text = ""
        block.content = "payload from .content attr"
        mock_response.content = [block]
        mock_client.messages.create.return_value = mock_response

        result = call_llm_multimodal(
            client=mock_client,
            model="deepseek-v4-flash",
            system_prompt="",
            user_text="test",
            images=[],
        )

        assert "payload from .content attr" in result
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && python -m pytest tests/test_llm_client.py -v
```

Expected: 7 tests PASS

- [ ] **Step 3: Commit**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && git add tests/test_llm_client.py && git commit -m "test: add unit tests for call_llm_multimodal() content block construction

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: Integration verification

**Files:**
- No new files — verify existing tests still pass

- [ ] **Step 1: Run existing test suite**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && python -m pytest tests/ -v --ignore=tests/test_mg_pipeline.py -k "not slow"
```

Expected: All non-slow tests pass. `test_llm_client.py` 7 tests + existing tests.

- [ ] **Step 2: Smoke-test VideoAnalyzer import chain**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && python -c "
from core.llm_client import create_client, call_llm, call_llm_multimodal
from agents.video_analyzer.agent import VideoAnalyzer
from agents.commentary_gen.agent import CommentaryGenerator
print('All imports OK')
print('VideoAnalyzer methods:', [m for m in dir(VideoAnalyzer) if not m.startswith('_')])
# Verify _stub_analysis is gone
assert '_stub_analysis' not in dir(VideoAnalyzer), '_stub_analysis should be removed!'
print('_stub_analysis confirmed removed')
print('Import chain verified')
"
```

Expected: `All imports OK`, `_stub_analysis confirmed removed`, `Import chain verified`

- [ ] **Step 3: Commit any final adjustments**

```bash
cd d:/ClaudeWorkspace/projects/surf-2026-ai-tactical-assistant && git status
```
