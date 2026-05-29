# -*- coding: utf-8 -*-
"""Token counting utilities for PawBench benchmark transcripts.

Provides lightweight, offline token estimation using tiktoken so that
``usage`` statistics are always populated even when the agent SDK does not
return token counts from the API.

Encoding selection
------------------
* tiktoken ``o200k_base``  — used by GPT-4o / o-series / Qwen3 family
  (Qwen3 shares the same extended BPE vocabulary).
* Falls back to ``cl100k_base`` (GPT-4 / GPT-3.5) when o200k_base is
  unavailable (older tiktoken versions).
* If tiktoken is not installed at all a simple whitespace-split heuristic is
  used (≈ 0.75× word count, accurate to ±15 %).

Counting convention
-------------------
For each conversation turn we count:
  prompt_tokens     — tokens in all user / system / toolResult messages
  completion_tokens — tokens in all assistant messages

This approximates the actual API cost without needing per-call usage data.
Tool call argument JSON and thinking blocks are included in their respective
roles (assistant outputs, tool results as inputs).

Usage
-----
    from pawbench.utils.token_counter import estimate_usage_from_transcript

    usage = estimate_usage_from_transcript(transcript, model="qwen3.6-plus")
    # -> {"prompt_tokens": 12480, "completion_tokens": 3210, "total_tokens": 15690, "estimated": True}
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

# ── tiktoken setup ────────────────────────────────────────────────────────────

_TIKTOKEN_AVAILABLE = False
_FALLBACK_ENCODER = None

try:
    import tiktoken as _tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    pass


@lru_cache(maxsize=8)
def _get_encoder(model: str | None = None):
    """Return a cached tiktoken encoder appropriate for *model*.

    Selection order
    ---------------
    1. Model-specific prefix alias (Qwen / GPT families).
    2. ``cl100k_base`` — ships bundled with tiktoken, always available offline.
       Accurate for GPT-4 / GPT-3.5 / Qwen2 / Qwen3 (≈ ±5 % vs Qwen BPE).
    3. ``o200k_base``  — requires a one-time network download (~1.7 MB).
       More accurate for Qwen3 / GPT-4o but will fail if offline.
    4. ``None``        — tiktoken not installed; caller uses word heuristic.
    """
    if not _TIKTOKEN_AVAILABLE:
        return None

    if model:
        # Qwen3 vocabulary is close to cl100k_base for most content; no need
        # to force o200k_base which requires a network download.
        _MODEL_ALIASES = {
            "qwen":  "cl100k_base",
            "gpt-4": "cl100k_base",
            "gpt-3": "cl100k_base",
        }
        for prefix, enc_name in _MODEL_ALIASES.items():
            if model.lower().startswith(prefix):
                try:
                    return _tiktoken.get_encoding(enc_name)
                except Exception:
                    break  # fall through to generic search

    # cl100k_base first — bundled, no download needed
    for enc_name in ("cl100k_base", "o200k_base"):
        try:
            return _tiktoken.get_encoding(enc_name)
        except Exception:
            continue
    return None


def count_tokens(text: str, model: str | None = None) -> int:
    """Count tokens in *text* for the given *model*.

    Args:
        text:  Plain text or serialised JSON string to count.
        model: Optional model name used to select the best encoder.

    Returns:
        Integer token count.  When tiktoken is unavailable the count is
        estimated as ``ceil(len(text.split()) / 0.75)``.
    """
    if not text:
        return 0
    enc = _get_encoder(model)
    if enc is not None:
        return len(enc.encode(text))
    # Heuristic fallback: ~0.75 words per token on English; slightly generous
    # for mixed Chinese/English content.
    words = len(re.findall(r"\S+", text))
    return max(1, int(words / 0.75))


# ── transcript-level estimation ───────────────────────────────────────────────

def _extract_text_from_content(content: Any) -> str:
    """Flatten message content blocks to a single string."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                btype = block.get("type", "")
                if btype in ("text", "thinking"):
                    txt = block.get("text") or block.get("thinking") or ""
                    if txt:
                        parts.append(str(txt))
                elif btype in ("toolCall", "tool_use"):
                    name = block.get("name", "")
                    args = block.get("arguments") or block.get("input") or {}
                    if isinstance(args, dict):
                        args_str = json.dumps(args, ensure_ascii=False)
                    else:
                        args_str = str(args)
                    parts.append(f"{name}({args_str})")
                elif btype == "tool_result":
                    out = block.get("output") or block.get("content") or ""
                    parts.append(str(out))
        return "\n".join(parts)
    return str(content)


def estimate_usage_from_transcript(
    transcript: list[dict[str, Any]],
    model: str | None = None,
) -> dict[str, Any]:
    """Estimate token usage from a PawBench transcript event list.

    Iterates over all events and sums token counts by role:

    * ``user`` / ``system`` / ``toolResult`` / ``tool`` → prompt_tokens
    * ``assistant``                                     → completion_tokens

    Args:
        transcript: List of transcript events in the PawBench/OpenClaw format.
        model:      Model name used to pick the best tiktoken encoder.

    Returns:
        Dict with keys ``prompt_tokens``, ``completion_tokens``,
        ``total_tokens``, and ``estimated: True``.  Returns ``{}`` when the
        transcript is empty or contains no text.
    """
    if not transcript:
        return {}

    prompt = 0
    completion = 0

    for event in transcript:
        if not isinstance(event, dict):
            continue

        # Support both {type, message} envelope and bare message dicts
        msg = event.get("message") if "message" in event else event
        if not isinstance(msg, dict):
            continue

        role = msg.get("role", "")
        content = msg.get("content")
        text = _extract_text_from_content(content)
        if not text:
            continue

        n = count_tokens(text, model)
        if role == "assistant":
            completion += n
        elif role in ("user", "system", "toolResult", "tool", "function"):
            prompt += n

    if not (prompt or completion):
        return {}

    return {
        "prompt_tokens":     prompt,
        "completion_tokens": completion,
        "total_tokens":      prompt + completion,
        "estimated":         True,   # flag: derived from text, not API usage field
    }


def is_available() -> bool:
    """Return True when tiktoken is installed and usable."""
    return _TIKTOKEN_AVAILABLE and _get_encoder() is not None
