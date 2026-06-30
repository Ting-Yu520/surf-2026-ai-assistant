"""Unified logging for all Agents."""
import logging
import sys


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Create a standardized logger with agent name prefix.

    Args:
        name: Agent name (e.g., "video_analyzer")
        level: Log level string

    Returns:
        Configured logger
    """
    logger = logging.getLogger(f"surf.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)-7s] %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
