"""002 create email_verification_tokens table

Revision ID: 002
Revises: 001
Create Date: 2026-05-04

Notes
-----
- Stores hashed verification tokens (SHA-256). Plaintext tokens never
  hit the DB — only the hash, so a DB dump cannot be replayed against
  the verification endpoint.
- Single-use semantics: ``used_at`` is set on first successful verify;
  any subsequent use of the same token is rejected.
- Cascade delete on user removal — DSGVO Art. 17 (Right to Erasure).
- 24h TTL is enforced at application level (ADR-0004 § "E-Mail-Verifikation").
- ``ix_email_verification_tokens_user_id`` lets the resend flow cheaply
  invalidate any prior unused tokens for a given user.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "email_verification_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SHA-256 hex digest of the plaintext token (64 chars). The plaintext
        # is sent only via email and never persisted.
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Lookup by token_hash is the hot path on /verify-email
    op.create_index(
        "ix_email_verification_tokens_token_hash",
        "email_verification_tokens",
        ["token_hash"],
        unique=True,
    )

    # Lookup by user_id is used by /resend-verification to invalidate older
    # tokens for the same user.
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_email_verification_tokens_user_id",
        table_name="email_verification_tokens",
    )
    op.drop_index(
        "ix_email_verification_tokens_token_hash",
        table_name="email_verification_tokens",
    )
    op.drop_table("email_verification_tokens")
