"""Fusion Agent data types."""
from dataclasses import dataclass, field


@dataclass
class PipelineResult:
    """Full pipeline output from Fusion Agent."""
    output_video: str = ""
    script: str = ""
    audio_path: str = ""
    elapsed_sec: float = 0.0
    agent_traces: list[dict] = field(default_factory=list)
