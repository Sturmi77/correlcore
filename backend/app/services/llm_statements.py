"""Optional Ollama-backed insight statement refinement (#148)."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_LLM_TIMEOUT_SECONDS = 10.0


def _build_prompt(ctx: dict[str, Any], *, locale: str) -> str:
    statement = ctx.get("statement") or ""
    return (
        "Rewrite the following neutral wellness journal insight in "
        f"{locale}. Keep it factual, non-diagnostic, and under 220 characters. "
        "Do not add medical claims.\n\n"
        f"Insight type: {ctx.get('insight_type', 'unknown')}\n"
        f"Metric: {ctx.get('metric', 'unknown')}\n"
        f"Draft: {statement}"
    )


async def generate_llm_statement(ctx: dict[str, Any], locale: str = "en") -> str | None:
    """Call Ollama to refine a statement, returning None when disabled or on failure."""

    if not settings.INSIGHTS_LLM_ENABLED:
        return None

    # Lazy import: production images install ``.[analytics]`` (includes httpx);
    # keep the module importable when the optional LLM path is disabled.
    import httpx

    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": _build_prompt(ctx, locale=locale),
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=_LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError:
        logger.warning("ollama statement generation failed", exc_info=True)
        return None

    text = str(data.get("response", "")).strip()
    return text or None
