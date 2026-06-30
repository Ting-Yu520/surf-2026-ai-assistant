"""Unified exception types for all Agents."""


class AgentError(Exception):
    """Base exception for all Agent failures."""
    def __init__(self, agent_name: str, message: str, original: Exception | None = None):
        self.agent_name = agent_name
        self.message = message
        self.original = original
        super().__init__(f"[{agent_name}] {message}")


class ConfigError(AgentError):
    """Configuration loading or validation failure."""


class ModelCallError(AgentError):
    """LLM/VLM API call failure."""


class ValidationError(AgentError):
    """Output validation failure."""
