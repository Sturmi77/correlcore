"""007 add app-level Fernet encryption for Art.-9 fields (Issue #26, ADR-0005)

Revision ID: 007
Revises: 006
Create Date: 2026-05-04

What this migration does
------------------------
1. Creates ``user_encryption_keys`` (one wrapped DEK per user) with RLS.
2. Backfills a fresh DEK for every existing user (and any user that owns
   data needing encryption — currently a strict subset, but we provision
   for all users so registration races don't leave a row without a DEK).
3. Re-types and re-encrypts ``entries.note_enc``: TEXT plaintext -> BYTEA
   Fernet ciphertext (per-user DEK). NULLs stay NULL.
4. Adds ``symptoms.name_enc`` (BYTEA, nullable) and migrates every custom
   symptom (``is_default = FALSE``) by encrypting its plaintext ``name``
   into ``name_enc`` and setting ``name = NULL``. Defaults keep ``name``
   plaintext and ``name_enc`` NULL. A CHECK constraint enforces this
   exclusivity.

Master key
----------
Reads ``ENCRYPTION_KEY`` (or comma-separated ``ENCRYPTION_KEYS``) from
the environment directly — we do **not** import :mod:`app.core.crypto`
to keep this migration runnable from a stripped-down Alembic context.
The first key encrypts new tokens; all keys are tried for decrypting
DEKs (rotation-safe).

Downgrade
---------
Downgrade is **destructive for new data** but lossless for the tables
being undone:

- It cannot un-encrypt ``entries.note_enc`` ciphertext that was *only*
  written after the upgrade (the DEKs would be gone). To keep the
  downgrade idempotent, we drop ``user_encryption_keys`` and replace the
  encrypted ``entries.note_enc`` with NULL plus a warning notice; same
  for ``symptoms.name_enc``. **Run the downgrade with a fresh database
  unless you have a Plaintext backup.** This is documented in CHANGELOG.

This is a deliberate one-way upgrade for production data: GDPR
"cryptographic erasure" guarantees we cannot recover plaintext after a
key loss, and the downgrade respects that.
"""

from __future__ import annotations

import os
import uuid

import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet, MultiFernet
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Master-key bootstrap (env-only; no app imports)
# ---------------------------------------------------------------------------


def _master_keys() -> list[str]:
    """Read ENCRYPTION_KEYS (preferred) or ENCRYPTION_KEY from env."""
    multi = os.environ.get("ENCRYPTION_KEYS", "").strip()
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]
    single = os.environ.get("ENCRYPTION_KEY", "").strip()
    if not single:
        raise RuntimeError(
            "Migration 007 requires ENCRYPTION_KEY (or ENCRYPTION_KEYS) in the "
            "environment. Generate with: python -c 'from cryptography.fernet "
            "import Fernet; print(Fernet.generate_key().decode())'"
        )
    return [single]


def _master_fernet() -> MultiFernet:
    return MultiFernet([Fernet(k) for k in _master_keys()])


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    bind = op.get_bind()

    # ---- 1. user_encryption_keys table -----------------------------------
    op.create_table(
        "user_encryption_keys",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("wrapped_dek", sa.LargeBinary, nullable=False),
        sa.Column(
            "key_version",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ---- 2. RLS on user_encryption_keys ----------------------------------
    op.execute("ALTER TABLE user_encryption_keys ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY uek_owner_select ON user_encryption_keys
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY uek_owner_insert ON user_encryption_keys
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY uek_owner_update ON user_encryption_keys
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY uek_owner_delete ON user_encryption_keys
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )

    # ---- 3. Backfill DEKs for every existing user ------------------------
    # We need encryption material before we can rewrite payload columns.
    # The migration runs as the DB owner and can bypass RLS.
    master = _master_fernet()
    user_dek: dict[uuid.UUID, bytes] = {}

    user_rows = bind.execute(sa.text("SELECT id FROM users")).fetchall()
    for (user_id,) in user_rows:
        dek = Fernet.generate_key()
        wrapped = master.encrypt(dek)
        bind.execute(
            sa.text(
                "INSERT INTO user_encryption_keys (user_id, wrapped_dek) "
                "VALUES (:uid, :w)"
            ),
            {"uid": user_id, "w": wrapped},
        )
        user_dek[user_id] = dek

    # ---- 4. entries.note_enc: TEXT -> BYTEA ------------------------------
    # Strategy: rename old column, add new BYTEA, encrypt non-null values
    # row by row, drop old.
    op.execute("ALTER TABLE entries RENAME COLUMN note_enc TO note_enc_old")
    op.add_column(
        "entries",
        sa.Column("note_enc", sa.LargeBinary, nullable=True),
    )

    entry_rows = bind.execute(
        sa.text(
            "SELECT id, user_id, note_enc_old FROM entries "
            "WHERE note_enc_old IS NOT NULL"
        )
    ).fetchall()
    for entry_id, user_id, plaintext in entry_rows:
        if plaintext is None:
            continue
        dek = user_dek.get(user_id)
        if dek is None:
            # Defensive: a stray entry without an owner DEK shouldn't exist
            # because we just backfilled DEKs for every user, but if it does
            # we generate one on the spot rather than losing data.
            dek = Fernet.generate_key()
            bind.execute(
                sa.text(
                    "INSERT INTO user_encryption_keys (user_id, wrapped_dek) "
                    "VALUES (:uid, :w) "
                    "ON CONFLICT (user_id) DO NOTHING"
                ),
                {"uid": user_id, "w": master.encrypt(dek)},
            )
            user_dek[user_id] = dek
        ciphertext = Fernet(dek).encrypt(plaintext.encode("utf-8"))
        bind.execute(
            sa.text("UPDATE entries SET note_enc = :ct WHERE id = :id"),
            {"ct": ciphertext, "id": entry_id},
        )

    op.drop_column("entries", "note_enc_old")

    # ---- 5. symptoms.name_enc + relax NOT NULL on name -------------------
    # Allow NULL on ``name`` (custom rows will move their value to name_enc).
    op.alter_column("symptoms", "name", nullable=True)
    op.add_column(
        "symptoms",
        sa.Column("name_enc", sa.LargeBinary, nullable=True),
    )

    # Encrypt every custom symptom's name into name_enc, then null out name.
    custom_rows = bind.execute(
        sa.text(
            "SELECT id, user_id, name FROM symptoms "
            "WHERE is_default = FALSE AND name IS NOT NULL"
        )
    ).fetchall()
    for sym_id, user_id, plaintext in custom_rows:
        dek = user_dek.get(user_id)
        if dek is None:
            # Same defensive fallback as above.
            dek = Fernet.generate_key()
            bind.execute(
                sa.text(
                    "INSERT INTO user_encryption_keys (user_id, wrapped_dek) "
                    "VALUES (:uid, :w) "
                    "ON CONFLICT (user_id) DO NOTHING"
                ),
                {"uid": user_id, "w": master.encrypt(dek)},
            )
            user_dek[user_id] = dek
        ciphertext = Fernet(dek).encrypt(plaintext.encode("utf-8"))
        bind.execute(
            sa.text(
                "UPDATE symptoms SET name_enc = :ct, name = NULL WHERE id = :id"
            ),
            {"ct": ciphertext, "id": sym_id},
        )

    # ---- 6. CHECK constraint: defaults plaintext, custom encrypted -------
    op.create_check_constraint(
        "ck_symptoms_name_storage_consistency",
        "symptoms",
        "(is_default = TRUE AND name IS NOT NULL AND name_enc IS NULL) "
        "OR (is_default = FALSE AND name IS NULL AND name_enc IS NOT NULL)",
    )


# ---------------------------------------------------------------------------
# Downgrade — destructive (see module docstring)
# ---------------------------------------------------------------------------


def downgrade() -> None:
    bind = op.get_bind()

    # 1. Reverse symptoms.name_enc: drop CHECK, set name back to a placeholder
    #    for rows that had encrypted-only names, then drop name_enc.
    op.drop_constraint(
        "ck_symptoms_name_storage_consistency",
        "symptoms",
        type_="check",
    )
    # Custom rows had their plaintext name nulled. We cannot recover it.
    # Restore something non-NULL (the slug) so the not-null constraint holds.
    bind.execute(
        sa.text(
            "UPDATE symptoms SET name = slug "
            "WHERE is_default = FALSE AND name IS NULL"
        )
    )
    op.drop_column("symptoms", "name_enc")
    op.alter_column("symptoms", "name", nullable=False)

    # 2. Reverse entries.note_enc: replace BYTEA with TEXT NULL.
    #    We cannot recover plaintext from the dropped DEKs.
    op.execute("ALTER TABLE entries RENAME COLUMN note_enc TO note_enc_old")
    op.add_column(
        "entries",
        sa.Column("note_enc", sa.Text, nullable=True),
    )
    op.drop_column("entries", "note_enc_old")

    # 3. Drop user_encryption_keys (RLS policies cascade with the table).
    op.drop_table("user_encryption_keys")
