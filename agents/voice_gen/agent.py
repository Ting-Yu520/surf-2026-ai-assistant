"""Agent 4: TTS voice generation via Edge TTS.

Uses moviepy for audio duration/concatenation, wave for silence — zero external tools.
"""
import asyncio
import os
import wave
import struct

import edge_tts
from moviepy import AudioFileClip, concatenate_audioclips

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

        # Concatenate all segments using moviepy
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
                clip = AudioFileClip(audio_path)
                duration = clip.duration
                clip.close()
            except Exception as e:
                logger.warning(f"TTS failed for segment {i}, using silence: {e}")
                duration = 2.0
                _write_silent_wav(audio_path, duration)

            results.append({
                **seg,
                "audio_path": audio_path,
                "actual_duration_sec": duration,
            })

        return results

    @staticmethod
    def _concat_audio(segments: list[dict], output_path: str):
        """Concatenate audio segments using moviepy concatenate_audioclips."""
        clips = []
        for seg in segments:
            ap = seg.get("audio_path", "")
            if ap and os.path.exists(ap):
                try:
                    clips.append(AudioFileClip(ap))
                except Exception:
                    pass

        if clips:
            combined = concatenate_audioclips(clips)
            combined.write_audiofile(output_path, logger=None)
            combined.close()
            for c in clips:
                c.close()
        else:
            _write_silent_wav(output_path, 1.0)


def _write_silent_wav(path: str, duration: float):
    """Write a silent WAV file using only Python stdlib (wave module)."""
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    # If path ends with .mp3 but we're writing WAV, change extension
    if path.endswith('.mp3'):
        path = path.replace('.mp3', '.wav')
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b'\x00\x00' * n_samples)
