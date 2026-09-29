"""Scatter verification is only offered for supported day-level comparisons."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services import insight_service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("metric", "payload"),
    [
        ("sleep_minutes", {}),
        ("mood_score", {"method": "lag", "lag_days": 2}),
    ],
)
async def test_verification_rejects_unsupported_series(
    monkeypatch: pytest.MonkeyPatch, metric: str, payload: dict[str, object]
) -> None:
    monkeypatch.setattr(
        insight_service,
        "get_visible_insight_by_id",
        AsyncMock(return_value=SimpleNamespace(subject_type="tag", metric=metric, payload=payload)),
    )

    with pytest.raises(insight_service.InsightEventWindowsUnsupportedError):
        await insight_service.get_insight_verification(
            AsyncMock(), user_id=uuid4(), insight_id=uuid4(), range_="90d"
        )
