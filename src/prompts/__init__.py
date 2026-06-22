"""
Prompt Templates — SURF-2026 AI Tactical Assistant 核心 IP

所有 Prompt 设计遵循 [[surf-2026-project-init]] 中定义的 5 项原则。
"""

from .templates import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    build_user_prompt,
    build_messages,
)

__all__ = [
    "SYSTEM_PROMPT",
    "USER_PROMPT_TEMPLATE",
    "build_user_prompt",
    "build_messages",
]
