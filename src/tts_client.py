"""
TTS 客户端 — Edge TTS（免费）
Backward-compatible shim. Logic migrated to agents/voice_gen/agent.py.

Prefer:  from agents.voice_gen.agent import VoiceGenerator
Legacy:  from src.tts_client import generate_audio, generate_timeline_audio, concat_audio_segments
"""
import asyncio
from pathlib import Path

from agents.voice_gen.agent import VoiceGenerator
from core.interfaces import AgentInput


# Singleton instance for legacy API compatibility
_vg = VoiceGenerator()


def generate_audio(text: str, output_path: str) -> str:
    """Single-segment TTS (legacy sync interface)."""
    result = _vg.run(AgentInput(data={
        "segments": [{"narration": text}],
        "audio_path": output_path,
        "output_dir": str(Path(output_path).parent),
    }))
    return output_path


def generate_timeline_audio(segments: list[dict], output_dir: str) -> list[dict]:
    """Per-segment TTS with timing (legacy sync interface)."""
    result = _vg.run(AgentInput(data={
        "segments": segments,
        "output_dir": output_dir,
    }))
    return result.data.get("segments", [])


def concat_audio_segments(segments: list[dict], output_path: str) -> str:
    """Concatenate audio segments (delegates to VoiceGenerator)."""
    _vg._concat_audio(segments, output_path)
    return output_path
