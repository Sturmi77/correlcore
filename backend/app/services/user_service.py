"""User account management service.

Currently provides DSGVO-Art.-17-Erasure (Issue #66, ADR-0005). The hard
delete relies on database ON DELETE CASCADE on every table that references
``users.id`` plus the ``user_encryption_keys`` row, which makes the delete
**cryptographically irreversible** for ``entries.note_enc`` and
``symptoms.name_enc`` (Custom): once the wrapped DEK row is gone, the
ciphertexts are mathematically unrecoverable.

Cascade reach (kept in sync with the model layer; verified by
``test_user_service.py::test_delete_user_cascade_reach`` whenever a new FK
is introduced):

- ``entries``                       — ON DELETE CASCADE
- ``entry_tags``                    — ON DELETE CASCADE
- ``entry_symptoms``                — ON DELETE CASCADE
- ``tags`` (custom only)            — ON DELETE CASCADE (default tags have user_id NULL and stay)
- ``symptoms`` (custom only)        — ON DELETE CASCADE (default symptoms have user_id NULL and stay)
- ``email_verification_tokens``     — ON DELETE CASCADE
- ``user_encryption_keys``          — ON DELETE CASCADE  ← cryptographic erasure

Refresh tokens live in Redis, not Postgres, and must therefore be revoked
explicitly by the service.

Privacy
-------
- The constant-time password verification protects against timing-based
  account-existence checks via this endpoint when the caller is *not*
  the legitimate user. (The endpoint is auth-gated, so this is mostly
  defense-in-depth — see ADR-0005 §"Account-Löschung".)
- Logs only ever contain ``user_id``; email and any free-text fields
  must never be logged here.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.db.redis_client import TokenStore
from app.models.user import User

logger = logging.getLogger(__name__)


class UserDeletionError(Exception):
    """Raised when account deletion is refused (e.g. wrong password)."""


async def delete_user_account(
    db: AsyncSession,
    token_store: TokenStore,
    user: User,
    password: str,
) -> None:
    """Hard-delete ``user`` and revoke all of their refresh tokens.

    Verifies the supplied password against the stored hash before any
    destructive action — this is defense-in-depth re-authentication so
    that a stolen access token alone cannot wipe an account (also
    mitigates CSRF via cookie even though the access cookie already
    uses ``SameSite=strict``).

    Order of operations (chosen so a partial failure leaves the system
    in the safest possible state):

    1. **Password check** — raises :class:`UserDeletionError` on mismatch.
       Nothing has been touched yet.
    2. **Revoke refresh tokens in Redis.** Even if the DB-side delete
       below fails afterwards, the user is force-logged out.
    3. **DELETE FROM users WHERE id = :user_id** — Cascades take it from
       there. ``user_encryption_keys`` row goes with it; the moment the
       transaction commits, ciphertexts are unrecoverable.
    4. ``db.commit()`` is intentionally **not** called here — the FastAPI
       session dependency owns commit/rollback so the caller can compose
       multiple operations in a single transaction if needed. The auth
       endpoint commits via the session middleware.
    """
    if not verify_password(password, user.hashed_password):
        # Do not log the email here. ``user_id`` is enough for forensics;
        # the email is the only piece of PII tied to the row and we want
        # to keep it out of structured logs (Issue #69 / log-scrubbing).
        logger.warning(
            "account deletion refused: wrong password",
            extra={"user_id": str(user.id)},
        )
        raise UserDeletionError("Invalid credentials")

    await purge_user_account(db, token_store, user)


async def purge_user_account(
    db: AsyncSession,
    token_store: TokenStore,
    user: User,
) -> None:
    """Destructive hard-delete: revoke refresh tokens + cascade-delete the row.

    Performs **no** authorization on its own — callers must authorize first:
    self-service via password re-auth (:func:`delete_user_account`) or an admin
    via ``require_admin`` (#677 admin console). ``db.commit()`` is left to the
    session dependency so the caller can compose (e.g. write an audit row in the
    same transaction).
    """
    user_id_str = str(user.id)

    # Kill every refresh token JTI for this user. ``revoke_all`` is idempotent
    # and a no-op if nothing is stored.
    await token_store.revoke_all(user_id_str)

    # Hard-delete the row. The ON DELETE CASCADE chain on every FK to
    # ``users.id`` (see module docstring) takes care of all dependent rows,
    # including the ``user_encryption_keys`` row that holds the wrapped DEK —
    # that single row going away is what turns all of this user's ciphertexts
    # into permanent garbage.
    await db.execute(delete(User).where(User.id == user.id))

    logger.info(
        "user account deleted (DSGVO Art. 17)",
        extra={"user_id": user_id_str},
    )
