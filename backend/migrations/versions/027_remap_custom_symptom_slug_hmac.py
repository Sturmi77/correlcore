"""027 remap custom symptom slugs to HMAC form (ADR-0039, Issue #62)

Revision ID: 027
Revises: 026
Create Date: 2026-07-15

Remaps ``symptoms.slug`` for user-owned rows from semantic plaintext to a
deterministic HMAC-SHA256 hex digest. ``entry_symptoms`` references
``symptoms.id`` (UUID), so no FK updates are required.

Requires ``SLUG_HMAC_KEY`` in the environment (loaded via app settings).
Idempotent: rows whose slug already matches the 64-char hex pattern are skipped.
Downgrade is intentionally a no-op — semantic slugs cannot be recovered.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.core.config import settings
from app.services.slug_hmac import hmac_custom_symptom_slug, is_hmac_symptom_slug

revision: str = "027"
down_revision: str | None = "026"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    key = settings.SLUG_HMAC_KEY
    if not key or key.startswith("CHANGE_ME"):
        raise RuntimeError(
            "SLUG_HMAC_KEY must be set before running migration 027. "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, user_id, slug FROM symptoms "
            "WHERE user_id IS NOT NULL AND is_default = FALSE"
        )
    ).fetchall()

    for row in rows:
        symptom_id, user_id, slug = row.id, row.user_id, row.slug
        if is_hmac_symptom_slug(slug):
            continue
        new_slug = hmac_custom_symptom_slug(
            user_id=user_id,
            semantic_slug=slug,
            key=key,
        )
        conn.execute(
            sa.text("UPDATE symptoms SET slug = :new_slug WHERE id = :id"),
            {"new_slug": new_slug, "id": symptom_id},
        )


def downgrade() -> None:
    # Irreversible: semantic slugs are not recoverable from HMAC digests.
    pass
