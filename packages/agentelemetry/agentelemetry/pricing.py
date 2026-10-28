"""Model → USD/token pricing tables."""

from __future__ import annotations

# Approximate list prices (USD per 1M tokens). Deployment names map via aliases.
_PRICES: dict[str, tuple[float, float]] = {
    # model: (input_per_1m, output_per_1m)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-5": (1.25, 10.00),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
    "o1": (15.00, 60.00),
    "o1-mini": (1.10, 4.40),
    "o3-mini": (1.10, 4.40),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-sonnet-4": (3.00, 15.00),
    "default": (1.00, 3.00),
}

_ALIASES: dict[str, str] = {
    "gpt-4o-2024-08-06": "gpt-4o",
    "gpt-4o-mini-2024-07-18": "gpt-4o-mini",
}


def normalize_model(model: str) -> str:
    key = (model or "default").strip().lower()
    if key in _PRICES:
        return key
    if key in _ALIASES:
        return _ALIASES[key]
    # Prefer longer model names first (gpt-4o-mini before gpt-4o)
    for known in sorted((k for k in _PRICES if k != "default"), key=len, reverse=True):
        if known in key:
            return known
    return "default"


def estimate_cost_usd(
    model: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> float:
    """Return estimated USD cost for a single LLM call."""
    input_per_1m, output_per_1m = _PRICES[normalize_model(model)]
    cost = (prompt_tokens / 1_000_000) * input_per_1m
    cost += (completion_tokens / 1_000_000) * output_per_1m
    return round(cost, 8)
