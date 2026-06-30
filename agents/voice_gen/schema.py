"""VoiceGen Agent data types."""
from dataclasses import dataclass


@dataclass
class VoiceSegment:
    """A single TTS-generated audio segment."""
    narration: str
    audio_path: str = ""
    actual_duration_sec: float = 0.0
