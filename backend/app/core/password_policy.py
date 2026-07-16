"""Shared password strength policy for registration and reset.

Art. 9 health data warrants a higher floor than generic consumer apps.
Keep the rules in one module so Register/Reset stay in lockstep.
Test fixtures use CorrectHorse123! (see tests.conftest.TEST_PASSWORD).
"""

from __future__ import annotations

# Short denylist of extremely common passwords (case-insensitive).
# Not a substitute for HIBP; blocks the worst offline-guessable defaults.
_COMMON_PASSWORDS = frozenset(
    {
        # Entries must be >= MIN_PASSWORD_LENGTH so the denylist is reachable.
        "password1234",
        "password12345",
        "123456789012",
        "qwertyuiop12",
        "letmein12345",
        "welcome12345",
        "admin1234567",
        "correlcore12",
        "changeme1234",
        "iloveyou1234",
        "monkey123456",
        "dragon123456",
        "master123456",
        "abc123456789",
        "passw0rd1234",
        "passw0rd12345",
    }
)

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


def validate_password_strength(password: str) -> str:
    """Raise ``ValueError`` when ``password`` fails CorrelCore policy."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters")
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        raise ValueError("Password must contain at least one letter and one digit")
    if password.casefold() in _COMMON_PASSWORDS:
        raise ValueError("Password is too common; choose a stronger password")
    return password
