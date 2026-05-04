"""Application-level encryption for at-rest Art. 9 GDPR data (Issue #26, ADR-0005).

Two-tier key model
------------------
- Master key (KEK): :data:`Settings.ENCRYPTION_KEY` or :data:`Settings.ENCRYPTION_KEYS`
  (list, used during rotation). Wraps per-user DEKs in
  :class:`app.models.user_encryption_key.UserEncryptionKey.wrapped_dek`.
- Data Encryption Key (DEK): one Fernet key per user, generated at registration.
  Encrypts/decrypts user payload fields (currently :attr:`Entry.note_enc`,
  custom :attr:`Symptom.name`).

Why ``MultiFernet`` for the master?
-----------------------------------
:class:`cryptography.fernet.MultiFernet` accepts a *list* of keys: the first key
is used for new encryptions, all keys are tried for decryption. That gives us a
clean rotation story (ADR-0005 §"Schlüssel-Rotation") without downtime — a new
key is prepended, a background job iterates over wrapped DEKs calling
:meth:`MultiFernet.rotate`, then the old key can be removed.

Request-scoped DEK cache
------------------------
:func:`set_current_user_dek` stores the unwrapped DEK in a :class:`contextvars.ContextVar`
that is set by :func:`app.api.v1.deps.auth.get_current_user`. The
:class:`EncryptedString` SQLAlchemy ``TypeDecorator`` reads from that var on
flush/load, so service-layer code keeps using plain strings — encryption is
transparent.

Privacy
-------
This module never logs ciphertext, plaintext, DEKs or the master key. The only
exposed surface is exception types (``DekUnavailableError``, ``DecryptionError``)
which are caught by the API layer and translated to 5xx without leaking details.
"""

from __future__ import annotations

import contextvars
import logging
import uuid
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy import LargeBinary
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CryptoError(Exception):
    """Base for crypto failures. Never carries plaintext or key material."""


class DekUnavailableError(CryptoError):
    """No DEK is bound to the current request context.

    Raised when a service tries to read/write an encrypted field without an
    authenticated user (or before the auth dependency ran). Indicates a bug:
    encrypted fields must always be accessed inside a request that loaded
    the DEK via the auth dependency.
    """


class DecryptionError(CryptoError):
    """Ciphertext could not be decrypted with any active master/DEK key.

    Most likely causes: wrong master key, rotated-out key removed too early,
    or tampered ciphertext (Fernet has built-in HMAC). The original
    :class:`InvalidToken` is suppressed to avoid leaking timing/length info.
    """


# ---------------------------------------------------------------------------
# Master-Fernet (KEK) — singleton, lazily built
# ---------------------------------------------------------------------------


_master_fernet: MultiFernet | None = None


def _build_master() -> MultiFernet:
    keys = settings.effective_encryption_keys()
    if not keys:
        raise RuntimeError("No encryption key configured (ENCRYPTION_KEY missing)")
    fernets: list[Fernet] = []
    for raw in keys:
        try:
            fernets.append(Fernet(raw.encode("ascii") if isinstance(raw, str) else raw))
        except (ValueError, TypeError) as exc:
            # Don't log the key itself.
            raise RuntimeError(
                "ENCRYPTION_KEY/ENCRYPTION_KEYS contains an invalid Fernet key "
                "(must be 32 random bytes, URL-safe base64 encoded). "
                "Generate with: python -c 'from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())'"
            ) from exc
    return MultiFernet(fernets)


def get_master_fernet() -> MultiFernet:
    """Return the process-wide master MultiFernet (lazy-built, cached)."""
    global _master_fernet
    if _master_fernet is None:
        _master_fernet = _build_master()
    return _master_fernet


def reset_master_fernet_cache() -> None:
    """Drop the cached master. Tests use this to swap keys mid-run."""
    global _master_fernet
    _master_fernet = None


# ---------------------------------------------------------------------------
# DEK helpers
# ---------------------------------------------------------------------------


def generate_dek() -> bytes:
    """Generate a fresh Fernet DEK (32 random bytes, URL-safe base64)."""
    return Fernet.generate_key()


def wrap_dek(plaintext_dek: bytes) -> bytes:
    """Encrypt a DEK with the master key. Used at user registration."""
    return get_master_fernet().encrypt(plaintext_dek)


def unwrap_dek(wrapped: bytes | memoryview) -> bytes:
    """Decrypt a DEK from storage. Tries all master keys (rotation-safe).

    Raises :class:`DecryptionError` on failure — never leaks the inner
    :class:`InvalidToken` or any key material.
    """
    raw = bytes(wrapped) if isinstance(wrapped, memoryview) else wrapped
    try:
        return get_master_fernet().decrypt(raw)
    except InvalidToken as exc:
        raise DecryptionError("DEK could not be unwrapped with any master key") from exc


def encrypt_with_dek(plaintext: str, dek: bytes) -> bytes:
    """Encrypt a UTF-8 string with the given DEK. Returns Fernet token bytes."""
    return Fernet(dek).encrypt(plaintext.encode("utf-8"))


def decrypt_with_dek(ciphertext: bytes | memoryview, dek: bytes) -> str:
    """Decrypt a Fernet token to UTF-8 string. Raises :class:`DecryptionError`."""
    raw = bytes(ciphertext) if isinstance(ciphertext, memoryview) else ciphertext
    try:
        return Fernet(dek).decrypt(raw).decode("utf-8")
    except InvalidToken as exc:
        raise DecryptionError("Ciphertext could not be decrypted with the user DEK") from exc


# ---------------------------------------------------------------------------
# Request-scoped DEK
# ---------------------------------------------------------------------------


# Tuple (user_id, dek) so we can detect a leaked DEK from another request:
# if the contextvar still holds a DEK with a different user_id, that's a bug.
_current_dek: contextvars.ContextVar[tuple[uuid.UUID, bytes] | None] = contextvars.ContextVar(
    "moodsync_current_dek",
    default=None,
)


def set_current_user_dek(
    user_id: uuid.UUID, dek: bytes
) -> contextvars.Token[tuple[uuid.UUID, bytes] | None]:
    """Bind the DEK for *user_id* to the current request context.

    The returned token must be passed to :func:`reset_current_user_dek` (typically
    in the auth dependency's cleanup path).
    """
    return _current_dek.set((user_id, dek))


def reset_current_user_dek(token: contextvars.Token[tuple[uuid.UUID, bytes] | None]) -> None:
    """Reset the DEK contextvar to its previous value."""
    _current_dek.reset(token)


def get_current_user_dek() -> bytes:
    """Return the DEK bound to the current request, or raise.

    Used by :class:`EncryptedString` and (rarely) by service code that needs
    to encrypt outside the ORM (e.g. raw SQL).
    """
    bound = _current_dek.get()
    if bound is None:
        raise DekUnavailableError(
            "No DEK in request context. Ensure get_current_user() ran before "
            "touching encrypted fields."
        )
    return bound[1]


def get_current_user_id_for_dek() -> uuid.UUID | None:
    """Return the user_id whose DEK is currently bound (or ``None``)."""
    bound = _current_dek.get()
    return bound[0] if bound else None


# ---------------------------------------------------------------------------
# SQLAlchemy TypeDecorator: transparent encrypt/decrypt
# ---------------------------------------------------------------------------


class EncryptedString(TypeDecorator[str]):
    """SQLAlchemy column type that encrypts a string with the request DEK.

    Storage: ``BYTEA`` (Fernet token). Python-side: ``str | None``.

    Behaviour
    ---------
    - ``None`` round-trips unchanged.
    - On INSERT/UPDATE: the Python string is encrypted with the *current*
      request DEK and stored as bytes.
    - On SELECT: the bytes are decrypted with the current DEK.
    - If no DEK is bound (e.g. background job, migration), raises
      :class:`DekUnavailableError`. Use plain ``LargeBinary`` for those paths.
    """

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> bytes | None:
        if value is None:
            return None
        if isinstance(value, bytes):
            # Allow passing pre-encrypted ciphertext (used by migrations).
            return value
        if not isinstance(value, str):
            raise TypeError(f"EncryptedString expects str, got {type(value).__name__}")
        return encrypt_with_dek(value, get_current_user_dek())

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return decrypt_with_dek(value, get_current_user_dek())
