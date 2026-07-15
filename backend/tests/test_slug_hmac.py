"""Tests for custom symptom slug HMAC (ADR-0039, Issue #62)."""

from __future__ import annotations

import uuid

from app.services.slug_hmac import hmac_custom_symptom_slug, is_hmac_symptom_slug


def test_hmac_custom_symptom_slug_is_deterministic() -> None:
    user_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
    key = "test-slug-hmac-key-for-correlcore-unit-tests"
    first = hmac_custom_symptom_slug(
        user_id=user_id,
        semantic_slug="migraine_with_aura",
        key=key,
    )
    second = hmac_custom_symptom_slug(
        user_id=user_id,
        semantic_slug="migraine_with_aura",
        key=key,
    )
    assert first == second
    assert is_hmac_symptom_slug(first)
    assert len(first) == 64


def test_hmac_custom_symptom_slug_differs_by_user() -> None:
    key = "test-slug-hmac-key-for-correlcore-unit-tests"
    slug_a = hmac_custom_symptom_slug(
        user_id=uuid.UUID("11111111-1111-4111-8111-111111111111"),
        semantic_slug="tinnitus",
        key=key,
    )
    slug_b = hmac_custom_symptom_slug(
        user_id=uuid.UUID("22222222-2222-4222-8222-222222222222"),
        semantic_slug="tinnitus",
        key=key,
    )
    assert slug_a != slug_b


def test_is_hmac_symptom_slug_rejects_semantic_slugs() -> None:
    assert is_hmac_symptom_slug("tinnitus") is False
    assert is_hmac_symptom_slug("headache") is False
