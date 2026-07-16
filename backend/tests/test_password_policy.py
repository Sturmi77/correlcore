"""Unit tests for shared password policy."""

from __future__ import annotations

import pytest

from app.core.password_policy import MIN_PASSWORD_LENGTH, validate_password_strength


def test_accepts_strong_password() -> None:
    assert validate_password_strength("CorrectHorse1!") == "CorrectHorse1!"


def test_rejects_short_password() -> None:
    with pytest.raises(ValueError, match=str(MIN_PASSWORD_LENGTH)):
        validate_password_strength("Abcd1234")


def test_rejects_letter_only() -> None:
    with pytest.raises(ValueError, match="letter and one digit"):
        validate_password_strength("abcdefghijkl")


def test_rejects_common_password() -> None:
    with pytest.raises(ValueError, match="too common"):
        validate_password_strength("password1234")
