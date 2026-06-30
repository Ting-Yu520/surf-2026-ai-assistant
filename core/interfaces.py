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
    """Every Agent must subclass this. Override load_config(), run(), and validate()."""

    def __init__(self, config_override: dict | None = None):
        self.config = self.load_config()
        if config_override:
            self.config.update(config_override)

    @abstractmethod
    def load_config(self) -> dict:
        """Load config from config.yaml + environment variables. No hardcoding."""
        ...

    @abstractmethod
    def run(self, agent_input: AgentInput) -> AgentOutput:
        """Single entry point: input → process → output."""
        ...

    @abstractmethod
    def validate(self, output: AgentOutput) -> bool:
        """Validate output against this Agent's schema."""
        ...
