# -*- coding: utf-8 -*-
"""Model-identifier helpers shared by pawbench's runners.

Pure-function utilities for converting / classifying provider-qualified
model IDs (e.g. ``openai/gpt-5.4``).  Has no runtime dependencies on
OpenClaw / Docker / qwenpaw.
"""

from __future__ import annotations

import logging
import re
from typing import Optional


logger = logging.getLogger(__name__)


THINKING_LEVELS = ("off", "minimal", "low", "medium", "high", "xhigh", "adaptive")

_XHIGH_MODELS = {
    "openai/gpt-5.4", "openai/gpt-5.4-pro", "openai/gpt-5.2",
    "openai-codex/gpt-5.4", "openai-codex/gpt-5.3-codex",
    "openai-codex/gpt-5.3-codex-spark", "openai-codex/gpt-5.2-codex",
    "openai-codex/gpt-5.1-codex",
    "github-copilot/gpt-5.2-codex", "github-copilot/gpt-5.2",
}
_XHIGH_MODELS_LOWER = {m.lower() for m in _XHIGH_MODELS}
_XHIGH_MODEL_IDS_LOWER = {m.split("/")[-1].lower() for m in _XHIGH_MODELS}

_ADAPTIVE_PROVIDER = "anthropic"
_ADAPTIVE_MODEL_PREFIXES = (
    "claude-opus-4-6", "claude-opus-4.6",
    "claude-sonnet-4-6", "claude-sonnet-4.6",
)


def slugify_model(model_id: str) -> str:
    return model_id.replace("/", "-").replace(".", "-")


def normalize_model_id(model_id: str) -> str:
    """Return *model_id* unchanged; OpenClaw accepts provider-qualified IDs as-is."""
    return model_id


def supports_xhigh_thinking(model_id: str) -> bool:
    """Return True if *model_id* supports the ``xhigh`` thinking level."""
    normalized = normalize_model_id(model_id).lower()
    if normalized in _XHIGH_MODELS_LOWER:
        return True
    parts = normalized.split("/")
    if len(parts) == 3 and parts[0] == "openrouter":
        if f"{parts[1]}/{parts[2]}" in _XHIGH_MODELS_LOWER:
            return True
    if "/" not in model_id:
        return model_id.lower() in _XHIGH_MODEL_IDS_LOWER

    model_part = normalized.split("/", 1)[-1]
    bare_model = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", model_part)
    if bare_model in _XHIGH_MODEL_IDS_LOWER:
        return True
    canonical = model_part.replace(".", "/", 1)
    canonical = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", canonical)
    if canonical in _XHIGH_MODELS_LOWER:
        return True
    return canonical.split("/")[-1] in _XHIGH_MODEL_IDS_LOWER


def supports_adaptive_thinking(model_id: str) -> bool:
    """Return True if *model_id* supports adaptive thinking."""
    normalized = normalize_model_id(model_id).lower()
    parts = normalized.split("/")
    if len(parts) == 3 and parts[0] == "openrouter":
        provider, model = parts[1], parts[2]
    elif len(parts) >= 2:
        provider, model = parts[-2], parts[-1]
    else:
        return False
    if provider != _ADAPTIVE_PROVIDER:
        return False
    return any(model.startswith(p) for p in _ADAPTIVE_MODEL_PREFIXES)


def validate_thinking_level(level: str, model_id: Optional[str] = None) -> Optional[str]:
    """Validate *level* and check model compatibility.  Returns the validated level or ``None``."""
    level_lower = level.lower().strip()
    if level_lower not in THINKING_LEVELS:
        logger.warning("Invalid thinking level %r. Valid: %s", level, ", ".join(THINKING_LEVELS))
        return None
    if level_lower == "xhigh" and model_id and not supports_xhigh_thinking(model_id):
        logger.warning("Thinking level 'xhigh' not supported by model %r", model_id)
        return None
    if level_lower == "adaptive" and model_id and not supports_adaptive_thinking(model_id):
        logger.warning("Thinking level 'adaptive' not supported by model %r", model_id)
        return None
    return level_lower
