"""Deterministic HMAC-SHA256 slugs for custom symptoms (ADR-0039, Issue #62).

Custom symptom slugs are never stored in semantic form (e.g. ``migraene_mit_aura``).
Instead the server persists a keyed HMAC over ``user_id`` and the client-supplied
semantic slug so backups and read-only DB access cannot infer symptom names from
the slug column alone.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import uuid

from app.core.config import settings

_SLUG_HEX_LEN = 64
_HMAC_SLUG_PATTERN = re.compile(rf"^[a-f0-9]{{{_SLUG_HEX_LEN}}}$")


def hmac_custom_symptom_slug(
    *,
    user_id: uuid.UUID,
    semantic_slug: str,
    key: str | None = None,
) -> str:
    """Return the storage slug for a custom symptom.

    The digest is deterministic for a given ``user_id``, ``semantic_slug``,
    and ``SLUG_HMAC_KEY`` so retries and migrations remain stable.
    """
    secret = (key if key is not None else settings.SLUG_HMAC_KEY).encode("utf-8")
    message = f"{user_id}:{semantic_slug}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def is_hmac_symptom_slug(slug: str) -> bool:
    """Return ``True`` when ``slug`` already looks like an HMAC storage slug."""
    return bool(_HMAC_SLUG_PATTERN.match(slug))


__all__ = ["hmac_custom_symptom_slug", "is_hmac_symptom_slug"]
