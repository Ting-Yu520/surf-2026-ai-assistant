"""TacticalExtractor Agent data types."""
from dataclasses import dataclass, field


@dataclass
class PlayerPrediction:
    """A single player position/probability prediction from TacticAI."""
    player_index: int
    probability: float
    is_attacker: bool
    position: list[float]
    role: str = ""


@dataclass
class TacticalScene:
    """Normalized tactical scene ready for CommentaryGen consumption."""
    fact_section: str
    tactic_section: str
    predictions: list[dict] = field(default_factory=list)
    mapping: dict | None = None
