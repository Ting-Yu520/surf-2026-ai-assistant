# Agent-Based Architecture Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor current monolithic `src/` into 6 independent Agent packages + `core/` shared layer, following the approved Agent Architecture Design (2026-06-30-agent-architecture-design.md).

**Architecture:** Each Agent is a self-contained package (agent.py + config.yaml + schema.py + prompts/) that only depends on `core/`. Agents communicate via `AgentInput → AgentOutput` dataclasses. Fusion Agent orchestrates the full pipeline.

**Tech Stack:** Python 3.12+, DeepSeek V4 (LLM), Edge TTS, ffmpeg, Gemini (VLM), Streamlit

**Priority:** Before 7/20 demo → VLM Agent + Fusion Agent + app.py rewrite. Full migration can continue after.

---

## Phase 0: Foundation — `core/` Package

### Task 0.1: Create `core/interfaces.py`

**Files:**
- Create: `agents/__init__.py`
- Create: `agents/base.py`
- Create: `core/__init__.py`
- Create: `core/interfaces.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p agents
mkdir -p core
```

- [ ] **Step 2: Write `core/interfaces.py`**

```python
"""Core interfaces — the only dependency shared by all Agents."""
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any


@dataclass
class AgentInput:
    """Standardized input container for all Agents."""
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentOutput:
    """Standardized output container for all Agents."""
    status: str              # "ok" | "error" | "skipped"
    data: dict[str, Any]
    agent_name: str
    error: str | None = None
    elapsed_ms: float = 0.0


class BaseAgent(ABC):
    """Every Agent must subclass this. Only override load_config() and run()."""

    def __init__(self, config_override: dict | None = None):
        self.config = self.load_config()
        if config_override:
            self.config.update(config_override)

    @abstractmethod
    def load_config(self) -> dict:
        """Load config from config.yaml + environment variables. No hardcoding."""
        ...

    @abstractmethod
    def run(self, input: AgentInput) -> AgentOutput:
        """Single entry point: input → process → output."""
        ...

    @abstractmethod
    def validate(self, output: AgentOutput) -> bool:
        """Validate output against this Agent's schema."""
        ...
```

- [ ] **Step 3: Write `agents/base.py` (re-export)**

```python
"""Re-export BaseAgent from core for convenience."""
from core.interfaces import BaseAgent, AgentInput, AgentOutput

__all__ = ["BaseAgent", "AgentInput", "AgentOutput"]
```

- [ ] **Step 4: Write `agents/__init__.py` and `core/__init__.py`**

```python
# agents/__init__.py
"""SURF-2026 AI Agents — 6 specialized agents for football tactical commentary."""
```

```python
# core/__init__.py
"""Shared infrastructure — zero business logic."""
```

- [ ] **Step 5: Verify imports work**

Run: `python -c "from agents.base import BaseAgent, AgentInput, AgentOutput; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add agents/ core/
git commit -m "feat(core): add BaseAgent interface + AgentInput/Output dataclasses"
```

---

### Task 0.2: Create `core/config_loader.py`

**Files:**
- Create: `core/config_loader.py`

- [ ] **Step 1: Write `core/config_loader.py`**

```python
"""YAML + env var unified config loader. Zero hardcoding."""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load secrets.env once at module level
_ENV_PATH = Path(__file__).parent.parent / "configs" / "secrets.env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


def load_yaml_and_env(yaml_path: str, project_root: Path | None = None) -> dict:
    """Load config from YAML file, merge with environment variables.

    Priority (highest last):
    1. YAML defaults
    2. secrets.env values
    3. OS environment variables

    Args:
        yaml_path: Relative path from project root to config.yaml
        project_root: Auto-detected if None

    Returns:
        Merged config dict
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent

    full_path = project_root / yaml_path
    config = {}

    # Layer 1: YAML defaults
    if full_path.exists():
        with open(full_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Layer 2+3: env vars override (secrets.env already loaded by dotenv)
    for key in config:
        env_val = os.getenv(key.upper())
        if env_val is not None:
            config[key] = env_val

    return config
```

- [ ] **Step 2: Install PyYAML if missing**

Run: `pip install pyyaml -q`
Expected: PyYAML installed

- [ ] **Step 3: Test config loader**

Run: `python -c "from core.config_loader import load_yaml_and_env; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add core/config_loader.py requirements.txt
git commit -m "feat(core): add YAML+env unified config loader"
```

---

### Task 0.3: Create `core/exceptions.py` + `core/logging.py`

**Files:**
- Create: `core/exceptions.py`
- Create: `core/logging.py`

- [ ] **Step 1: Write `core/exceptions.py`**

```python
"""Unified exception types for all Agents."""


class AgentError(Exception):
    """Base exception for all Agent failures."""
    def __init__(self, agent_name: str, message: str, original: Exception | None = None):
        self.agent_name = agent_name
        self.message = message
        self.original = original
        super().__init__(f"[{agent_name}] {message}")


class ConfigError(AgentError):
    """Configuration loading or validation failure."""


class ModelCallError(AgentError):
    """LLM/VLM API call failure."""


class ValidationError(AgentError):
    """Output validation failure."""
```

- [ ] **Step 2: Write `core/logging.py`**

```python
"""Unified logging for all Agents."""
import logging
import sys


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Create a standardized logger with agent name prefix.

    Args:
        name: Agent name (e.g., "video_analyzer")
        level: Log level string

    Returns:
        Configured logger
    """
    logger = logging.getLogger(f"surf.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)-7s] %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
```

- [ ] **Step 3: Commit**

```bash
git add core/exceptions.py core/logging.py
git commit -m "feat(core): add unified exceptions + logging"
```

---

### Task 0.4: Create `core/llm_client.py`

**Files:**
- Create: `core/llm_client.py`

- [ ] **Step 1: Write `core/llm_client.py`**

```python
"""Generic LLM client — OpenAI-compatible API. Zero business logic."""
import time
from anthropic import Anthropic
from core.exceptions import ModelCallError


def create_client(base_url: str, api_key: str, timeout: int = 60) -> Anthropic:
    """Create an Anthropic-compatible client. Works with DeepSeek, OpenAI, etc.

    Args:
        base_url: API base URL
        api_key: API key (never hardcoded)
        timeout: Request timeout in seconds

    Returns:
        Configured Anthropic client
    """
    return Anthropic(api_key=api_key, base_url=base_url, timeout=float(timeout))


def call_llm(
    client: Anthropic,
    model: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2048,
    temperature: float = 0.85,
) -> str:
    """Generic LLM call with error handling and timing.

    Args:
        client: Anthropic client from create_client()
        model: Model name string
        system_prompt: System prompt
        user_message: User message
        max_tokens: Max tokens to generate
        temperature: Sampling temperature

    Returns:
        Generated text string

    Raises:
        ModelCallError: On API failure
    """
    t0 = time.time()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as e:
        raise ModelCallError("llm_client", f"API call failed: {e}", original=e)

    elapsed = time.time() - t0
    text_parts = []
    for block in response.content:
        if hasattr(block, "text") and block.text:
            text_parts.append(block.text)
        elif hasattr(block, "content") and block.content:
            text_parts.append(str(block.content))

    result = "\n".join(text_parts)
    if not result.strip():
        raise ModelCallError("llm_client", f"Empty response after {elapsed:.1f}s")

    return result
```

- [ ] **Step 2: Commit**

```bash
git add core/llm_client.py
git commit -m "feat(core): add generic LLM client (OpenAI-compatible)"
```

---

## Phase 1: Extract Existing Agents (backward compatible)

### Task 1.1: Extract `agents/voice_gen/` from `src/tts_client.py`

**Files:**
- Create: `agents/voice_gen/__init__.py`
- Create: `agents/voice_gen/config.yaml`
- Create: `agents/voice_gen/schema.py`
- Create: `agents/voice_gen/agent.py`
- Modify: `src/tts_client.py` → re-export from new agent for backward compat

- [ ] **Step 1: Create config.yaml**

```yaml
# agents/voice_gen/config.yaml
voice: "zh-CN-XiaoxiaoNeural"
rate: "+10%"
```

- [ ] **Step 2: Write schema.py**

```python
"""VoiceGen Agent data types."""
from dataclasses import dataclass


@dataclass
class VoiceSegment:
    text: str
    audio_path: str = ""
    actual_duration_sec: float = 0.0
```

- [ ] **Step 3: Write agent.py (migrate tts_client.py logic)**

```python
"""Agent 4: TTS voice generation via Edge TTS."""
import asyncio
import json
import os
import subprocess
from pathlib import Path

import edge_tts

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger

logger = get_logger("voice_gen")


class VoiceGenerator(BaseAgent):
    """Generate TTS audio from script segments."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/voice_gen/config.yaml")

    def run(self, input: AgentInput) -> AgentOutput:
        segments = input.data.get("segments", [])
        output_dir = input.data.get("output_dir", "outputs/audio_segs")

        os.makedirs(output_dir, exist_ok=True)
        results = asyncio.run(self._generate_segments(segments, output_dir))

        # Concat audio
        audio_path = input.data.get("audio_path", "outputs/narration.mp3")
        self._concat_audio(results, audio_path)

        return AgentOutput(
            status="ok",
            data={"segments": results, "audio_path": audio_path},
            agent_name="voice_gen",
        )

    def validate(self, output: AgentOutput) -> bool:
        segs = output.data.get("segments", [])
        return all(s.get("audio_path") and os.path.exists(s["audio_path"]) for s in segs)

    async def _generate_segments(self, segments: list[dict], output_dir: str) -> list[dict]:
        voice = self.config.get("voice", "zh-CN-XiaoxiaoNeural")
        rate = self.config.get("rate", "+10%")
        results = []
        for i, seg in enumerate(segments):
            audio_path = os.path.join(output_dir, f"seg_{i:03d}.mp3")
            try:
                communicate = edge_tts.Communicate(text=seg["narration"], voice=voice, rate=rate)
                await communicate.save(audio_path)
                duration = self._ffprobe_duration(audio_path)
            except Exception as e:
                logger.warning(f"TTS failed for seg {i}, using silence: {e}")
                duration = 2.0
                self._create_silent_mp3(audio_path, duration)
            results.append({**seg, "audio_path": audio_path, "actual_duration_sec": duration})
        return results

    @staticmethod
    def _ffprobe_duration(path: str) -> float:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
            capture_output=True, text=True, timeout=15,
        )
        return float(json.loads(result.stdout)["format"]["duration"])

    @staticmethod
    def _create_silent_mp3(path: str, duration: float = 2.0):
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
             "-t", str(duration), "-c:a", "libmp3lame", path],
            capture_output=True, timeout=15,
        )

    @staticmethod
    def _concat_audio(segments: list[dict], output_path: str):
        list_path = os.path.join(os.path.dirname(output_path), "_concat_list.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for seg in segments:
                if seg.get("audio_path") and os.path.exists(seg["audio_path"]):
                    f.write(f"file '{os.path.abspath(seg['audio_path'])}'\n")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_path],
            capture_output=True, timeout=60,
        )
        os.unlink(list_path)
```

- [ ] **Step 4: Add backward compat shim in src/tts_client.py**

```python
"""Backward-compatible re-export. Prefer agents.voice_gen directly."""
from agents.voice_gen.agent import VoiceGenerator

# Legacy interface
from agents.voice_gen.agent import VoiceGenerator as _VG
_vg = _VG()

def generate_audio(text, output_path):
    from core.interfaces import AgentInput
    result = _vg.run(AgentInput(data={"segments": [{"narration": text}], "audio_path": output_path, "output_dir": str(Path(output_path).parent)}))
    return output_path

def generate_timeline_audio(segments, output_dir):
    from core.interfaces import AgentInput
    result = _vg.run(AgentInput(data={"segments": segments, "output_dir": output_dir}))
    return result.data["segments"]

def concat_audio_segments(segments, output_path):
    _vg._concat_audio(segments, output_path)
    return output_path
```

- [ ] **Step 5: Test backward compat**

Run: `python -c "from src.tts_client import generate_audio; print('Backward compat OK')"`
Expected: No import errors

- [ ] **Step 6: Commit**

```bash
git add agents/voice_gen/ src/tts_client.py
git commit -m "feat(agents): extract voice_gen Agent from tts_client.py"
```

---

### Task 1.2: Extract `agents/commentary_gen/` from `src/prompts/corner_kick.py`

**Files:**
- Create: `agents/commentary_gen/__init__.py`
- Create: `agents/commentary_gen/config.yaml`
- Create: `agents/commentary_gen/schema.py`
- Create: `agents/commentary_gen/agent.py`
- Create: `agents/commentary_gen/prompts/system.txt`
- Create: `agents/commentary_gen/prompts/duo_template.j2`
- Create: `agents/commentary_gen/prompts/constraints.py`

- [ ] **Step 1: Create config.yaml**

```yaml
# agents/commentary_gen/config.yaml
model: "deepseek-v4-pro"
base_url: "https://api.deepseek.com/anthropic"
max_tokens: 2048
temperature: 0.85
timeout: 60
```

- [ ] **Step 2: Copy prompts from src/prompts/corner_kick.py**

```bash
cp src/prompts/corner_kick.py agents/commentary_gen/prompts/_original.py
```

- [ ] **Step 3: Write agent.py**

```python
"""Agent 3: LLM duo-commentary generation."""
from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.llm_client import create_client, call_llm
from core.logging import get_logger

logger = get_logger("commentary_gen")


class CommentaryGenerator(BaseAgent):
    """Generate duo-commentary (A: expert + B: novice) from tactical data."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/commentary_gen/config.yaml")

    def run(self, input: AgentInput) -> AgentOutput:
        fact_section = input.data.get("fact_section", "")
        tactic_section = input.data.get("tactic_section", "")

        system_prompt = self._load_prompt("system.txt")
        user_message = self._build_user_message(fact_section, tactic_section)

        client = create_client(
            base_url=self.config["base_url"],
            api_key=self.config.get("api_key", ""),
            timeout=self.config.get("timeout", 60),
        )

        script = call_llm(
            client=client,
            model=self.config["model"],
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=self.config.get("max_tokens", 2048),
            temperature=self.config.get("temperature", 0.85),
        )

        return AgentOutput(
            status="ok",
            data={"script": script},
            agent_name="commentary_gen",
        )

    def validate(self, output: AgentOutput) -> bool:
        script = output.data.get("script", "")
        return len(script) > 50 and ("A:" in script or "B:" in script)

    def _load_prompt(self, filename: str) -> str:
        from pathlib import Path
        path = Path(__file__).parent / "prompts" / filename
        return path.read_text(encoding="utf-8")

    def _build_user_message(self, fact: str, tactic: str) -> str:
        return f"""请根据下面的足球比赛信息，写一段双口相声科普脚本。

## 比赛事实
{fact}

## 战术彩蛋（可选）
下面这些战术分析数据 A 可偶尔引用：
{tactic}

## 要求
- 3-4 轮对话
- A 上来先卖弄知识
- B 一脸懵逼，逼 A 解释人话
- 最后 B 表示懂了
- 每段 A 台词后紧跟 ##VISUAL## 视觉指令
- 对话里不要出现坐标数字"""
```

- [ ] **Step 4: Copy system prompt to prompts/system.txt**

Copy the content of `DUO_SYSTEM_PROMPT` from `src/prompts/corner_kick.py` to `agents/commentary_gen/prompts/system.txt`.

- [ ] **Step 5: Commit**

```bash
git add agents/commentary_gen/
git commit -m "feat(agents): extract commentary_gen Agent from prompts/corner_kick.py"
```

---

### Task 1.3: Extract `agents/tactical_extractor/` from `src/phase_bridge.py`

**Files:**
- Create: `agents/tactical_extractor/__init__.py`
- Create: `agents/tactical_extractor/config.yaml`
- Create: `agents/tactical_extractor/schema.py`
- Create: `agents/tactical_extractor/agent.py`
- Create: `agents/tactical_extractor/adapters/tacticai.py`
- Create: `agents/tactical_extractor/adapters/socceragent.py`

- [ ] **Step 1: Create config.yaml**

```yaml
# agents/tactical_extractor/config.yaml
batch_output_path: "src/data/phase1_batch_output.json"
canvas_width: 1280
canvas_height: 720
```

- [ ] **Step 2: Write agent.py** (migrate `get_real_or_sample`, `build_field_mapping`, `format_for_prompt` logic)

```python
"""Agent 2: Tactical data extraction from Phase 1 tools."""
import json
from pathlib import Path
from typing import Optional

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger

logger = get_logger("tactical_extractor")


class TacticalExtractor(BaseAgent):
    """Extract and normalize tactical data from Phase 1 tool outputs."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/tactical_extractor/config.yaml")

    def run(self, input: AgentInput) -> AgentOutput:
        corner_entry = input.data.get("corner_entry")
        tacticai_json = input.data.get("tacticai_json")

        if not tacticai_json and corner_entry:
            tacticai_json = self._get_real_or_sample(corner_entry)

        if not tacticai_json:
            return AgentOutput(status="error", data={}, agent_name="tactical_extractor",
                             error="No tactical data available")

        phase2 = self._tacticai_to_phase2(tacticai_json)
        formatted = self._format_for_prompt(phase2, corner_entry)
        mapping = self._build_field_mapping(tacticai_json.get("predictions", []))

        return AgentOutput(
            status="ok",
            data={"phase2_input": phase2, "formatted": formatted, "mapping": mapping,
                  "predictions": tacticai_json.get("predictions", [])},
            agent_name="tactical_extractor",
        )

    def validate(self, output: AgentOutput) -> bool:
        return "formatted" in output.data and "predictions" in output.data

    # ── Internal methods (migrated from phase_bridge.py) ──

    def _tacticai_to_phase2(self, raw: dict) -> dict:
        preds = raw.get("predictions", [])
        attackers = [p for p in preds if p.get("is_attacker")]
        defenders = [p for p in preds if not p.get("is_attacker")]
        top_a = max(attackers, key=lambda p: p.get("probability", 0)) if attackers else None
        top_d = max(defenders, key=lambda p: p.get("probability", 0)) if defenders else None
        return {
            "attacking_players": len(attackers),
            "defending_players": len(defenders),
            "top_receiver_probability": round(top_a["probability"] * 100, 1) if top_a else None,
            "top_receiver_position": top_a["position"] if top_a else [],
            "top_defender_position": top_d["position"] if top_d else [],
        }

    def _format_for_prompt(self, phase2: dict, corner_entry: Optional[dict]) -> dict:
        fact_lines, tactic_lines = [], []
        if corner_entry:
            fact_lines.extend([
                f"比赛：{corner_entry.get('match', '?')}",
                f"时间：{corner_entry.get('minute', '?')}'",
                f"进球者：{corner_entry.get('goal_scorer', '?')}",
            ])
            if note := corner_entry.get("tactical_note"):
                fact_lines.append(f"战术描述：{note}")
        tactic_lines.extend([
            f"攻击球员：{phase2.get('attacking_players', '?')}人",
            f"防守球员：{phase2.get('defending_players', '?')}人",
            f"最可能接球概率：{phase2.get('top_receiver_probability', '?')}%",
        ])
        return {"fact_section": "\n".join(fact_lines), "tactic_section": "\n".join(tactic_lines)}

    def _build_field_mapping(self, predictions: list[dict]) -> dict | None:
        if not predictions:
            return None
        xs = [p["position"][0] for p in predictions]
        ys = [p["position"][1] for p in predictions]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        FIELD_LEFT, FIELD_RIGHT = 80, 1203
        FIELD_TOP, FIELD_BOTTOM = 100, 634
        x_range = (x_max - x_min) or 1
        y_range = (y_max - y_min) or 1
        return {
            "field_rect": {"left": FIELD_LEFT, "right": FIELD_RIGHT, "top": FIELD_TOP, "bottom": FIELD_BOTTOM},
            "to_px": lambda x: int(FIELD_LEFT + (x - x_min) / x_range * (FIELD_RIGHT - FIELD_LEFT)),
            "to_py": lambda y: int(FIELD_TOP + (y - y_min) / y_range * (FIELD_BOTTOM - FIELD_TOP)),
        }

    def _get_real_or_sample(self, corner_entry: dict) -> dict:
        cid = corner_entry.get("id", "")
        batch = self._load_batch()
        if cid in batch:
            return batch[cid]
        return self._sample_tacticai_output(corner_entry)

    def _load_batch(self) -> dict:
        path = Path(self.config.get("batch_output_path", "src/data/phase1_batch_output.json"))
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        return {e.get("corner_entry", {}).get("id"): e for e in entries if e.get("corner_entry", {}).get("id")}

    def _sample_tacticai_output(self, corner_entry: dict) -> dict:
        import hashlib
        eid = corner_entry.get("id", "default")
        seed = int(hashlib.md5(eid.encode()).hexdigest()[:8], 16)
        corner_type = corner_entry.get("corner_type", "in-swinging")
        base_x, base_y = (55, 40) if "left" in corner_type else (65, 40) if "right" in corner_type else (60, 38)
        state = seed
        def rng():
            nonlocal state
            state = (state * 1103515245 + 12345) & 0x7fffffff
            return state / 0x7fffffff
        preds = []
        for i in range(6):
            preds.append({"player_index": i, "probability": max(0.01, round(rng() * 0.45, 2)),
                          "is_attacker": True, "position": [round(base_x + rng() * 15 - 5, 1), round(base_y + rng() * 15 - 5, 1)]})
        for i in range(6, 12):
            preds.append({"player_index": i, "probability": max(0.01, round(rng() * 0.08, 2)),
                          "is_attacker": False, "position": [round(base_x + rng() * 20 - 5, 1), round(base_y + rng() * 20 - 10, 1)]})
        preds.sort(key=lambda p: p["probability"], reverse=True)
        return {"success": True, "predictions": preds, "top_receiver": preds[0]["player_index"], "top_probability": preds[0]["probability"]}
```

- [ ] **Step 3: Commit**

```bash
git add agents/tactical_extractor/
git commit -m "feat(agents): extract tactical_extractor Agent from phase_bridge.py"
```

---

### Task 1.4: Extract `agents/video_composer/` from `src/video_overlay.py` + `src/mg_renderer.py`

**Files:**
- Create: `agents/video_composer/__init__.py`
- Create: `agents/video_composer/config.yaml`
- Create: `agents/video_composer/schema.py`
- Create: `agents/video_composer/agent.py`
- Create: `agents/video_composer/overlays/highlight.py`
- Create: `agents/video_composer/overlays/caption.py`
- Create: `agents/video_composer/overlays/border.py`
- Create: `agents/video_composer/animations/mg_renderer.py`

- [ ] **Step 1: Write config.yaml**

```yaml
# agents/video_composer/config.yaml
width: 1280
height: 720
font_path: "C:/Windows/Fonts/msyh.ttc"
fps: 30
tmp_dir: "outputs/_ffmpeg_assets"
```

- [ ] **Step 2: Write agent.py (orchestrator, delegates to overlays/ and animations/)**

```python
"""Agent 5: Video composition — overlays, titles, animations, final export."""
import subprocess
import uuid
from pathlib import Path

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger

logger = get_logger("video_composer")


class VideoComposer(BaseAgent):
    """Compose final video with overlays, captions, and MG animations."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/video_composer/config.yaml")

    def run(self, input: AgentInput) -> AgentOutput:
        video_path = input.data.get("video_path")
        audio_path = input.data.get("audio_path")
        timeline = input.data.get("timeline", [])
        segments = input.data.get("segments", [])
        match_info = input.data.get("match_info", "AI Tactical Commentary")
        mg_clips = input.data.get("mg_clips", {})
        predictions = input.data.get("predictions", [])

        if not video_path or not audio_path:
            return AgentOutput(status="skipped", data={}, agent_name="video_composer",
                             error="Missing video_path or audio_path")

        output_path = input.data.get("output_path", "outputs/corner_story.mp4")
        self._render(video_path, audio_path, timeline, segments, match_info,
                    mg_clips, predictions, output_path)

        return AgentOutput(
            status="ok",
            data={"output_video": output_path},
            agent_name="video_composer",
        )

    def validate(self, output: AgentOutput) -> bool:
        path = output.data.get("output_video", "")
        return bool(path) and Path(path).exists()

    def _render(self, video_path, audio_path, timeline, segments, match_info,
                mg_clips, predictions, output_path):
        """Delegate to overlays and animations. For now, call existing functions."""
        # Phase 1: delegate to old src/video_overlay.py for backward compat
        from src.video_overlay import create_titled_video, parse_script, build_timeline
        create_titled_video(
            video_path=video_path, audio_path=audio_path, timeline=timeline,
            output_path=output_path, match_info=match_info,
            tacticai_predictions=predictions, mg_clips=mg_clips,
        )
```

- [ ] **Step 3: Commit**

```bash
git add agents/video_composer/
git commit -m "feat(agents): extract video_composer Agent shell"
```

---

## Phase 2: New Agents (Priority for 7/20)

### Task 2.1: Create `agents/video_analyzer/` (VLM Agent — NEW)

**Files:**
- Create: `agents/video_analyzer/__init__.py`
- Create: `agents/video_analyzer/config.yaml`
- Create: `agents/video_analyzer/schema.py`
- Create: `agents/video_analyzer/agent.py`
- Create: `agents/video_analyzer/prompts/frame_analysis.txt`

- [ ] **Step 1: Write config.yaml**

```yaml
# agents/video_analyzer/config.yaml
model: "gemini-2.5-flash"
fps: 1
max_frames: 10
resolution: [1920, 1080]
timeout: 30
```

- [ ] **Step 2: Write schema.py**

```python
"""VideoAnalyzer Agent data types."""
from dataclasses import dataclass, field


@dataclass
class VideoFrame:
    path: str
    timestamp: float
    width: int = 1920
    height: int = 1080


@dataclass
class TacticalJSON:
    """Output schema matching TacticAI format for downstream agents."""
    players: list[dict] = field(default_factory=list)
    ball_position: tuple[float, float] | None = None
    corner_type: str = ""
    formation: str = ""
    phase: str = "corner_kick"
```

- [ ] **Step 3: Write agent.py**

```python
"""Agent 1: VLM video frame analysis → tactical JSON."""
import base64
import subprocess
from pathlib import Path
from typing import Optional

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger
from core.exceptions import ModelCallError

logger = get_logger("video_analyzer")

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    logger.warning("google-generativeai not installed. VideoAnalyzer will use stub mode.")


class VideoAnalyzer(BaseAgent):
    """Extract tactical JSON from video keyframes using VLM."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/video_analyzer/config.yaml")

    def run(self, input: AgentInput) -> AgentOutput:
        video_path = input.data.get("video_path")
        frames_data = input.data.get("frames", [])

        if not video_path and not frames_data:
            return AgentOutput(status="error", data={}, agent_name="video_analyzer",
                             error="No video_path or frames provided")

        # Extract keyframes if not provided
        if not frames_data and video_path:
            frames_data = self._extract_keyframes(video_path)

        # Analyze frames with VLM
        if HAS_GEMINI and frames_data:
            tactical_json = self._analyze_with_vlm(frames_data)
        else:
            tactical_json = self._stub_analysis(frames_data)

        return AgentOutput(
            status="ok",
            data={"tactical_json": tactical_json, "frames": frames_data},
            agent_name="video_analyzer",
        )

    def validate(self, output: AgentOutput) -> bool:
        tj = output.data.get("tactical_json", {})
        return "players" in tj and len(tj.get("players", [])) > 0

    def _extract_keyframes(self, video_path: str) -> list[dict]:
        """Extract keyframes at configured FPS using ffmpeg."""
        fps = self.config.get("fps", 1)
        max_frames = self.config.get("max_frames", 10)
        output_dir = Path("outputs/_keyframes")
        output_dir.mkdir(parents=True, exist_ok=True)

        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"fps={fps}", "-frames:v", str(max_frames),
            "-q:v", "2", f"{output_dir}/frame_%03d.jpg",
        ], capture_output=True, timeout=60)

        frames = []
        for f in sorted(output_dir.glob("frame_*.jpg")):
            frames.append({"path": str(f), "timestamp": 0.0})
        return frames

    def _analyze_with_vlm(self, frames: list[dict]) -> dict:
        """Call Gemini Vision to analyze keyframes."""
        api_key = self.config.get("api_key", "")
        if not api_key:
            raise ModelCallError("video_analyzer", "No GEMINI_API_KEY configured")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.config.get("model", "gemini-2.5-flash"))

        prompt = self._load_prompt("frame_analysis.txt")
        image_parts = []
        for frame in frames[:self.config.get("max_frames", 10)]:
            with open(frame["path"], "rb") as f:
                image_parts.append({"mime_type": "image/jpeg", "data": base64.b64encode(f.read()).decode()})

        content = [prompt] + image_parts
        response = model.generate_content(content, request_options={"timeout": self.config.get("timeout", 30) * 1000})

        # Parse JSON from response
        import json
        text = response.text
        # Extract JSON block if wrapped in markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())

    def _stub_analysis(self, frames: list[dict]) -> dict:
        """Stub mode: return empty tactical JSON when VLM not available."""
        return {"players": [], "ball_position": None, "corner_type": "", "formation": "4-4-2", "phase": "corner_kick"}

    def _load_prompt(self, filename: str) -> str:
        path = Path(__file__).parent / "prompts" / filename
        return path.read_text(encoding="utf-8")
```

- [ ] **Step 4: Write prompts/frame_analysis.txt**

```
You are a football tactical analyst AI. Analyze the following video keyframes from a corner kick.

For each keyframe, identify:
1. Players and their approximate positions on the field (use normalized coordinates 0-100 for x and y)
2. Which team is attacking and which is defending
3. The corner kick type (in-swinging, out-swinging, short corner, etc.)
4. Player formation
5. Any notable tactical patterns

Output as JSON:
{
  "players": [
    {"id": "player_1", "team": "attack", "position": [65, 40], "role": "forward"}
  ],
  "ball_position": [95, 0],
  "corner_type": "in-swinging",
  "formation": "4-3-3",
  "phase": "corner_kick",
  "tactical_notes": "Near-post cluster with late runner from edge of box"
}

IMPORTANT:
- Only describe what you can actually see in the frames
- If unsure about something, mark it with [uncertain]
- Do not fabricate player names or match details
```

- [ ] **Step 5: Add google-generativeai to requirements.txt**

```
google-generativeai>=0.8.0
```

- [ ] **Step 6: Commit**

```bash
git add agents/video_analyzer/ requirements.txt
git commit -m "feat(agents): create video_analyzer Agent (VLM keyframe analysis)"
```

---

### Task 2.2: Create `agents/fusion/` (Orchestrator — NEW)

**Files:**
- Create: `agents/fusion/__init__.py`
- Create: `agents/fusion/config.yaml`
- Create: `agents/fusion/schema.py`
- Create: `agents/fusion/agent.py`

- [ ] **Step 1: Write config.yaml**

```yaml
# agents/fusion/config.yaml
parallel: true
fusion_strategy: "sequential"  # "sequential" | "parallel"
```

- [ ] **Step 2: Write agent.py (full pipeline orchestrator)**

```python
"""Agent 6: Decision-level fusion — orchestrates all Agents and merges outputs."""
import time
from pathlib import Path

from core.interfaces import BaseAgent, AgentInput, AgentOutput
from core.config_loader import load_yaml_and_env
from core.logging import get_logger

logger = get_logger("fusion")


class FusionAgent(BaseAgent):
    """Orchestrate all 5 Agents and produce the final video."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/fusion/config.yaml")

    def run(self, input: AgentInput) -> AgentOutput:
        t0 = time.time()

        # Phase A: Analyze + Extract (sequential — extractor needs analyzer output)
        video_path = input.data.get("video_path")
        corner_entry = input.data.get("corner_entry")
        article = input.data.get("article", {})
        output_prefix = input.data.get("output_prefix", "")

        from agents.video_analyzer.agent import VideoAnalyzer
        from agents.tactical_extractor.agent import TacticalExtractor

        analyzer = VideoAnalyzer()
        analyzer_result = analyzer.run(AgentInput(data={"video_path": video_path}))

        extractor = TacticalExtractor()
        extractor_result = extractor.run(AgentInput(data={
            "corner_entry": corner_entry,
            "tacticai_json": analyzer_result.data.get("tactical_json"),
        }))

        if extractor_result.status != "ok":
            return extractor_result  # propagate error

        formatted = extractor_result.data["formatted"]
        predictions = extractor_result.data["predictions"]
        mapping = extractor_result.data.get("mapping")

        # Phase B: Commentary + Voice (sequential — voice needs script)
        from agents.commentary_gen.agent import CommentaryGenerator

        commentary = CommentaryGenerator()
        commentary_result = commentary.run(AgentInput(data={
            "fact_section": formatted.get("fact_section", ""),
            "tactic_section": formatted.get("tactic_section", ""),
        }))
        script = commentary_result.data.get("script", "")

        # Parse script into segments
        from src.video_overlay import parse_script
        segments = parse_script(script) or [{"speaker": "A", "text": script}]

        # Phase C: Voice + Video (parallel via config)
        from agents.voice_gen.agent import VoiceGenerator
        from agents.video_composer.agent import VideoComposer

        voice = VoiceGenerator()
        prefix = output_prefix + "_" if output_prefix else ""
        audio_dir = f"outputs/{prefix}audio_segs"
        audio_path_out = f"outputs/{prefix}narration.mp3"

        voice_result = voice.run(AgentInput(data={
            "segments": [{"narration": s["text"]} for s in segments],
            "output_dir": audio_dir,
            "audio_path": audio_path_out,
        }))

        # Build timeline
        from src.video_overlay import build_timeline
        timeline = build_timeline(
            segments,
            [s["actual_duration_sec"] for s in voice_result.data.get("segments", [])],
        )

        # Render MG clips for ai_scene segments
        mg_clips = {}
        if predictions and mapping:
            from src.mg_renderer import render_all_mg_clips
            ai_scenes = [
                {**seg, "actual_duration_sec": d}
                for seg, d in zip(segments, [s["actual_duration_sec"] for s in voice_result.data.get("segments", [])])
                if seg.get("visual_type") == "ai_scene"
            ]
            if ai_scenes:
                mg_clips = render_all_mg_clips(ai_scenes, predictions, mapping, corner_entry or {}, prefix)

        output_video = f"outputs/{prefix}corner_story.mp4"
        composer = VideoComposer()
        composer_result = composer.run(AgentInput(data={
            "video_path": video_path,
            "audio_path": voice_result.data.get("audio_path"),
            "timeline": timeline,
            "segments": segments,
            "match_info": f"{corner_entry.get('match', '')} — {corner_entry.get('goal_scorer', '')} ({corner_entry.get('minute', '')}')" if corner_entry else "AI Tactical Commentary",
            "mg_clips": mg_clips,
            "predictions": predictions,
            "output_path": output_video,
        }))

        return AgentOutput(
            status="ok",
            data={
                "output_video": composer_result.data.get("output_video"),
                "script": script,
                "audio_path": voice_result.data.get("audio_path"),
                "elapsed_sec": time.time() - t0,
            },
            agent_name="fusion",
        )

    def validate(self, output: AgentOutput) -> bool:
        video = output.data.get("output_video", "")
        return bool(video) and Path(video).exists()
```

- [ ] **Step 3: Commit**

```bash
git add agents/fusion/
git commit -m "feat(agents): create fusion Agent (pipeline orchestrator)"
```

---

## Phase 3: Integration & Cleanup

### Task 3.1: Rewrite `app.py` to use Fusion Agent

**Files:**
- Modify: `src/app.py` (or create new `app.py` at project root)

- [ ] **Step 1: Write simplified app.py**

```python
"""SURF-2026 Streamlit App v4 — Agent-Based Architecture."""
import streamlit as st
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.interfaces import AgentInput
from agents.fusion.agent import FusionAgent

DATA = ROOT / "src" / "data"
VIDEO_DIR = ROOT / "data" / "videos"

st.set_page_config(page_title="SURF-2026 · AI 角球翻译官 v4", page_icon="⚽", layout="wide")

st.title("⚽ AI 角球翻译官 — Agent 架构 (v4)")
st.caption("VLM 帧分析 → 战术提取 → 二人转生成 → TTS 配音 → 视频融合")

# Load dataset
with open(DATA / "corner_kicks_2026.json", "r", encoding="utf-8") as f:
    entries = json.load(f)["entries"]

selected = st.selectbox(
    "选择角球场景",
    [f"#{e['id'].replace('wc2026-corner-','')} {e['match']} — {e['goal_scorer']} ({e['minute']}')" for e in entries],
)
eid = f"wc2026-corner-{selected.split('#')[1].split()[0]}"
entry = next(e for e in entries if e["id"] == eid)

video_path = None
for f in VIDEO_DIR.glob(f"{eid}*.mp4"):
    video_path = str(f)
    break

col1, col2 = st.columns(2)

with col1:
    st.json({"entry_id": eid, "match": entry["match"], "minute": entry["minute"],
             "goal_scorer": entry["goal_scorer"], "tactical_note": entry.get("tactical_note", "")})
    if video_path:
        st.video(video_path)

with col2:
    if st.button("🚀 全自动 Agent 管线", use_container_width=True, type="primary"):
        with st.status("6 Agent 协作中...", expanded=True) as status:
            st.write("① VideoAnalyzer: VLM 关键帧分析...")
            st.write("② TacticalExtractor: 战术数据提取...")

            fusion = FusionAgent()
            result = fusion.run(AgentInput(data={
                "video_path": video_path,
                "corner_entry": entry,
                "output_prefix": f"demo_{eid}",
            }))

            st.write(f"③ CommentaryGen: 二人转生成 ({len(result.data.get('script',''))} 字)")
            st.write("④ VoiceGen: TTS 配音完成")
            st.write("⑤ VideoComposer: 视频合成完成")
            st.write("⑥ Fusion: 决策融合完成 ✅")
            status.update(label="✅ Agent 管线完毕！", state="complete")

        output_video = result.data.get("output_video")
        if output_video:
            st.video(output_video)

        script = result.data.get("script", "")
        if script:
            st.markdown("### 二人转脚本")
            lines = script.split("\n")
            html = []
            for l in lines:
                if l.startswith("A:"):
                    html.append(f'<p style="color:#d32f2f;font-weight:600">🧑 懂哥：{l[2:].strip()}</p>')
                elif l.startswith("B:"):
                    html.append(f'<p style="color:#1976d2;font-weight:600">🤔 小白：{l[2:].strip()}</p>')
            st.markdown(f'<div style="background:#fafafa;padding:1rem;border-radius:8px">{"".join(html)}</div>', unsafe_allow_html=True)

st.divider()
st.caption("SURF-2026-0154 · Agent-Based Architecture v4 · 6 Agents | Multi-Modal | Late Fusion")
```

- [ ] **Step 2: Test that app launches**

Run: `streamlit run app.py --server.headless true 2>&1 | head -5`
Expected: No crash on import

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat(app): rewrite Streamlit UI to use Fusion Agent"
```

---

### Task 3.2: Create `configs/` directory

**Files:**
- Create: `configs/dev.yaml`
- Create: `configs/prod.yaml`
- Create: `configs/secrets.env.example`

- [ ] **Step 1: Write dev.yaml and prod.yaml**

`configs/dev.yaml`:
```yaml
log_level: DEBUG
output_dir: outputs/
parallel: false
```

`configs/prod.yaml`:
```yaml
log_level: INFO
output_dir: outputs/
parallel: true
```

- [ ] **Step 2: Write secrets.env.example**

```bash
# SURF-2026 API Keys (copy to secrets.env and fill in)
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
GEMINI_API_KEY=your-gemini-key-here
```

- [ ] **Step 3: Ensure .gitignore covers secrets**

Add to `.gitignore`:
```
configs/secrets.env
```

- [ ] **Step 4: Commit**

```bash
git add configs/ .gitignore
git commit -m "feat(config): add dev/prod configs + secrets template"
```

---

## Phase 4: Partner Tasks (Parallel — 大一搭档)

These tasks are designed for the first-year partner. Each is self-contained and does not touch core pipeline code.

### Partner Task A: Write Tests for `core/`

**Files:**
- Create: `tests/test_core_interfaces.py`
- Create: `tests/test_core_config_loader.py`
- Create: `tests/test_core_exceptions.py`

**Task Card:**
```
任务：为 core/ 包写 pytest 测试
文件：tests/test_core_*.py

具体要求：
1. tests/test_core_interfaces.py — 测试 AgentInput/Output 创建、BaseAgent 子类化
2. tests/test_core_config_loader.py — 测试 YAML 加载 + 环境变量覆盖优先级
3. tests/test_core_exceptions.py — 测试每种异常类型的构造和继承关系

成功标准：pytest tests/test_core_*.py -v 全部 PASS
```

### Partner Task B: Write Tests for Each Agent

**Files:**
- Create: `tests/test_agent_voice_gen.py`
- Create: `tests/test_agent_commentary_gen.py`
- Create: `tests/test_agent_video_analyzer.py`

### Partner Task C: Update Documentation

**Files:**
- Modify: `docs/project-structure-and-workflow.md`
- Create: `docs/agent-architecture-guide.md`

---

## Execution Order (Priority for 7/20)

```
Phase 0 (Foundation)
  Task 0.1 → 0.2 → 0.3 → 0.4
    ↓
Phase 1 (Extract Existing)
  Task 1.1 (voice_gen) → 1.2 (commentary_gen)
  Task 1.3 (tactical_extractor) → 1.4 (video_composer)
  (These can run in parallel once core/ is done)
    ↓
Phase 2 (New Agents — PRIORITY)
  Task 2.1 (video_analyzer) + 2.2 (fusion)  ← Must be done by 7/20
    ↓
Phase 3 (Integration)
  Task 3.1 (app.py) → 3.2 (configs/)
    ↓
Phase 4 (Partner — parallel throughout)
  Task A + B + C (anytime after Phase 0)
```

---

*Plan generated 2026-06-30. Agent architecture design: `docs/superpowers/specs/2026-06-30-agent-architecture-design.md`*
