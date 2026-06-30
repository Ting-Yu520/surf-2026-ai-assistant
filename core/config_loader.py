"""YAML + env var unified config loader. Zero hardcoding."""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load .env files once at module level (project root first, then configs/)
_PROJECT_ROOT = Path(__file__).parent.parent
for _env_path in [
    _PROJECT_ROOT / ".env",
    _PROJECT_ROOT / "configs" / "secrets.env",
]:
    if _env_path.exists():
        load_dotenv(_env_path, override=False)


def load_yaml_and_env(yaml_path: str, project_root: Path | None = None) -> dict:
    """Load config from YAML file, merge with environment variables.

    Priority (highest last):
    1. YAML defaults
    2. secrets.env values
    3. OS environment variables

    Args:
        yaml_path: Relative path from project root to config.yaml
        project_root: Auto-detected if None

    Returns:
        Merged config dict
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent

    full_path = project_root / yaml_path
    config = {}

    # Layer 1: YAML defaults
    if full_path.exists():
        with open(full_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Layer 2+3: env vars override (secrets.env already loaded by dotenv)
    for key in list(config.keys()):
        env_val = os.getenv(key.upper())
        if env_val is not None:
            config[key] = env_val

    return config
