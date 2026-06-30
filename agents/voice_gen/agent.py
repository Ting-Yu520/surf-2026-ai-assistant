"""Agent 4: TTS voice generation via Edge TTS.

Migrated from src/tts_client.py. Generates per-segment audio files,
extracts precise durations via ffprobe, and concatenates to final mp3.
"""
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
    """Generate TTS audio from script segments using Edge TTS (free)."""

    def load_config(self) -> dict:
        return load_yaml_and_env("agents/voice_gen/config.yaml")

    def run(self, agent_input: AgentInput) -> AgentOutput:
        segments = agent_input.data.get("segments", [])
        output_dir = agent_input.data.get("output_dir", "outputs/audio_segs")
        audio_path_out = agent_input.data.get("audio_path", "outputs/narration.mp3")

        os.makedirs(output_dir, exist_ok=True)
        results = asyncio.run(self._generate_segments(segments, output_dir))

        # Concatenate all segments to final audio
        self._concat_audio(results, audio_path_out)

        return AgentOutput(
            status="ok",
            data={"segments": results, "audio_path": audio_path_out},
            agent_name="voice_gen",
        )

    def validate(self, output: AgentOutput) -> bool:
        segs = output.data.get("segments", [])
        if not segs:
            return False
        return all(
            s.get("audio_path") and os.path.exists(s["audio_path"])
            for s in segs
        )

    async def _generate_segments(
        self, segments: list[dict], output_dir: str
    ) -> list[dict]:
        """Generate TTS audio for each segment asynchronously."""
        voice = self.config.get("voice", "zh-CN-XiaoxiaoNeural")
        rate = self.config.get("rate", "+10%")
        results = []

        for i, seg in enumerate(segments):
            audio_path = os.path.join(output_dir, f"seg_{i:03d}.mp3")
            try:
                communicate = edge_tts.Communicate(
                    text=seg["narration"], voice=voice, rate=rate
                )
                await communicate.save(audio_path)
                duration = self._ffprobe_duration(audio_path)
            except Exception as e:
                logger.warning(f"TTS failed for segment {i}, using silence: {e}")
                duration = 2.0
                self._create_silent_mp3(audio_path, duration)

            results.append({
                **seg,
                "audio_path": audio_path,
                "actual_duration_sec": duration,
            })

        return results

    @staticmethod
    def _ffprobe_duration(path: str) -> float:
        """Get audio duration in seconds using ffprobe.

        Uses ffprobe instead of moviepy to avoid mp3 compatibility issues.
        """
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json", path,
            ],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    @staticmethod
    def _create_silent_mp3(path: str, duration: float = 2.0):
        """Generate a silent mp3 as fallback when TTS fails."""
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=44100:cl=mono", "-t", str(duration),
                "-c:a", "libmp3lame", path,
            ],
            capture_output=True, timeout=15,
        )

    @staticmethod
    def _concat_audio(segments: list[dict], output_path: str):
        """Concatenate audio segments using ffmpeg concat demuxer."""
        list_path = os.path.join(
            os.path.dirname(output_path), "_concat_list.txt"
        )
        with open(list_path, "w", encoding="utf-8") as f:
            for seg in segments:
                ap = seg.get("audio_path", "")
                if ap and os.path.exists(ap):
                    f.write(f"file '{os.path.abspath(ap)}'\n")

        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_path, "-c", "copy", output_path,
            ],
            capture_output=True, timeout=60,
        )

        os.unlink(list_path)
