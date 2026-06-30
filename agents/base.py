"""Re-export BaseAgent from core for convenience."""
from core.interfaces import BaseAgent, AgentInput, AgentOutput

__all__ = ["BaseAgent", "AgentInput", "AgentOutput"]
