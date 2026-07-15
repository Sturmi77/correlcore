from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import settings
from app.services.llm_statements import generate_llm_statement


@pytest.mark.asyncio
async def test_generate_llm_statement_disabled_makes_no_http_call() -> None:
    with patch.object(settings, "INSIGHTS_LLM_ENABLED", False):
        with patch("app.services.llm_statements.httpx.AsyncClient") as client_cls:
            result = await generate_llm_statement({"statement": "Draft"}, locale="en")

    assert result is None
    client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_generate_llm_statement_http_500_returns_none() -> None:
    response = httpx.Response(500, request=httpx.Request("POST", "http://ollama/api/generate"))
    error = httpx.HTTPStatusError("server error", request=response.request, response=response)

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post.side_effect = error

    with patch.object(settings, "INSIGHTS_LLM_ENABLED", True):
        with patch("app.services.llm_statements.httpx.AsyncClient", return_value=mock_client):
            result = await generate_llm_statement(
                {"statement": "Mood rises on Mondays.", "insight_type": "weekday_pattern"},
                locale="en",
            )

    assert result is None
