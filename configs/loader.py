"""Config loader — reads YAML config files from the configs/ directory.

The YAML files ``agent_prompts.yaml`` and ``domain_configs.yaml`` are
reference / override companions to the Python domain classes and agent
code.  This module provides a single function to load them so that
other parts of the codebase (e.g. ``core/llm_config.py``) can pull
prompts and domain overrides from YAML without duplicating load logic.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).resolve().parent


def _load_yaml(filename: str) -> dict[str, Any]:
    """Load and parse a YAML file from the configs directory.

    Args:
        filename: Name of the YAML file (e.g. ``agent_prompts.yaml``).

    Returns:
        Parsed YAML content as a dict.  Returns an empty dict if the
        file is missing or unparseable.
    """
    try:
        import yaml  # pyyaml is already a project dependency
    except ImportError:
        logger.warning("PyYAML not installed — cannot load %s", filename)
        return {}

    path = _CONFIGS_DIR / filename
    if not path.exists():
        logger.warning("Config file not found: %s", path)
        return {}

    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.error("Failed to parse %s: %s", path, exc)
        return {}


@lru_cache(maxsize=1)
def load_agent_prompts() -> dict[str, Any]:
    """Load agent system prompts from ``configs/agent_prompts.yaml``.

    Returns:
        Dict mapping agent name -> prompt config (role, instructions, output_format).
    """
    return _load_yaml("agent_prompts.yaml")


@lru_cache(maxsize=1)
def load_domain_configs() -> dict[str, Any]:
    """Load domain configurations from ``configs/domain_configs.yaml``.

    Returns:
        Dict mapping domain name -> domain config dict.
    """
    return _load_yaml("domain_configs.yaml")


def get_agent_prompt(agent_name: str) -> dict[str, Any]:
    """Return the prompt config for a single agent.

    Args:
        agent_name: Key in agent_prompts.yaml (e.g. ``orchestrator``).

    Returns:
        Dict with ``role``, ``instructions``, ``output_format`` keys,
        or empty dict if not found.
    """
    prompts = load_agent_prompts()
    return prompts.get(agent_name, {})
