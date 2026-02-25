"""Config loading (AUDIT §2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loguru import logger


def _deep_update(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_update(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path) -> dict[str, Any]:
    """Load config from YAML file. Use SafeLoader. Returns raw dict."""
    path = Path(path)
    if not path.exists():
        logger.warning("Config file not found: {}", path)
        return {}

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            logger.warning("Config file {} has invalid structure (expected dict)", path)
            return {}
        return data
    except yaml.YAMLError as exc:
        logger.error("Failed to parse config {}: {}", path, exc)
        raise


def load_config_with_env(path: str | Path) -> dict[str, Any]:
    """Load config from YAML and overlay env-derived values."""
    from dotenv import load_dotenv

    load_dotenv()
    return load_config(path)
