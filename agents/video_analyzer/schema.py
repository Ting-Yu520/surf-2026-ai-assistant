"""VideoAnalyzer Agent data types."""
from dataclasses import dataclass, field


@dataclass
class VideoFrame:
    """A single extracted keyframe from the video."""
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
    tactical_notes: str = ""
