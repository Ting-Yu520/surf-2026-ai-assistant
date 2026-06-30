"""CommentaryGen Agent data types."""
from dataclasses import dataclass, field


@dataclass
class ScriptSegment:
    """A single line of duo-commentary dialogue."""
    speaker: str          # "A" (懂哥) or "B" (小白)
    text: str
    visual: str | None = None
    visual_type: str | None = None  # "ai_scene" | "highlight" | "clear"


@dataclass
class GeneratedScript:
    """Full duo-commentary script output."""
    raw: str
    segments: list[dict] = field(default_factory=list)
    char_count: int = 0
