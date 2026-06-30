"""VideoComposer Agent data types."""
from dataclasses import dataclass, field


@dataclass
class VideoClip:
    """A single rendered video clip."""
    path: str
    duration_sec: float
    start_time: float = 0.0


@dataclass
class TimelineEntry:
    """A single entry in the video timeline."""
    start: float
    end: float
    speaker: str
    text: str
    visual: str | None = None
