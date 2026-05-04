"""006 add symptom master table + refactor entry_symptoms (Issue #57, ADR-0008)

Revision ID: 006
Revises: 005
Create Date: 2026-05-04

Notes
-----
- Creates the new master table ``symptoms`` analog to ``tags`` (curated
  defaults with ``user_id IS NULL``, ``is_default = TRUE``; user-owned
  custom symptoms with ``user_id`` set, ``is_default = FALSE``). A CHECK
  constraint forbids any other combination.
- Two partial unique indexes guard slug uniqueness:
    * ``ux_symptoms_default_slug`` on ``(slug)`` WHERE ``is_default``: one
      curated symptom per slug across the whole system.
    * ``ux_symptoms_user_slug`` on ``(user_id, slug)`` WHERE NOT
      ``is_default``: a user may not own two symptoms with the same slug,
      but two users can.
- Seed: 5 curated default symptoms with deterministic UUID5 (so re-running
  the migration on a fresh DB yields identical UUIDs and the seed is
  idempotent against historical data references).
- ``entry_symptoms`` is refactored from String-key to FK:
    * Add nullable ``symptom_id`` column.
    * Backfill from existing ``symptom_key`` via JOIN on
      ``symptoms.slug`` AND ``is_default = TRUE``.
    * Make ``symptom_id`` NOT NULL, add FK and unique-on-(entry_id,
      symptom_id), drop the old String-key constraints + column.
- RLS on ``symptoms``: public read for defaults, owner-scoped CRUD for
  custom rows (mirror of migration 004's ``tags`` pattern). RLS on
  ``entry_symptoms`` was created in migration 005 — unchanged here.

Privacy
-------
The ``Symptom.name`` column is Art.-9-relevant for **custom** rows
(user-supplied free text). Plaintext storage in M1 is ADR-0005 stage 1;
Issue #26 will swap it to Fernet ciphertext (alongside ``entries.note``).
The static log-scrubbing test (``test_log_scrubbing.py``) is the runtime
guardrail until then.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


# Curated default symptoms. Slug is the canonical key the frontend uses
# for i18n; ``name`` is the German default the seed inserts. Frontend
# i18n maps slug → label (``symptom.default.<slug>``).
_DEFAULT_SYMPTOMS: tuple[tuple[str, str, str], ...] = (
    # (slug,        name,           icon)
    ("headache", "Kopfschmerzen", "🤕"),
    ("digestion", "Verdauung", "🌀"),
    ("back_pain", "Rückenschmerzen", "🦴"),
    ("fatigue", "Erschöpfung", "😴"),
    ("cold", "Erkältung", "🤧"),
)


def _default_symptom_uuid(slug: str) -> uuid.UUID:
    """Mirror of :func:`app.models.symptom.default_symptom_uuid`.

    Replicated here so the migration has no import dependency on the app
    package (Alembic best practice — migrations should be runnable even
    if the app code has drifted).
    """
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"moodsync.symptom.{slug}")


def upgrade() -> None:
    # ---- Create ``symptoms`` master table ---------------------------------
    op.create_table(
        "symptoms",
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
            nullable=True,
        ),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("icon", sa.String(length=32), nullable=True),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "(is_default = TRUE AND user_id IS NULL) "
            "OR (is_default = FALSE AND user_id IS NOT NULL)",
            name="ck_symptoms_default_owner_consistency",
        ),
    )

    op.create_index("ix_symptoms_user_id", "symptoms", ["user_id"])
    op.create_index(
        "ux_symptoms_default_slug",
        "symptoms",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.create_index(
        "ux_symptoms_user_slug",
        "symptoms",
        ["user_id", "slug"],
        unique=True,
        postgresql_where=sa.text("NOT is_default"),
    )

    op.execute(
        """
        CREATE TRIGGER symptoms_updated_at
        BEFORE UPDATE ON symptoms
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # ---- RLS policies on ``symptoms`` -------------------------------------
    op.execute("ALTER TABLE symptoms ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY symptoms_default_or_owner_select ON symptoms
        FOR SELECT
        USING (
            is_default = TRUE
            OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )
    op.execute(
        """
        CREATE POLICY symptoms_owner_insert ON symptoms
        FOR INSERT
        WITH CHECK (
            is_default = FALSE
            AND user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )
    op.execute(
        """
        CREATE POLICY symptoms_owner_update ON symptoms
        FOR UPDATE
        USING (
            is_default = FALSE
            AND user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        WITH CHECK (
            is_default = FALSE
            AND user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )
    op.execute(
        """
        CREATE POLICY symptoms_owner_delete ON symptoms
        FOR DELETE
        USING (
            is_default = FALSE
            AND user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )

    # ---- Seed default symptoms --------------------------------------------
    symptoms_table = sa.table(
        "symptoms",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("icon", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("user_id", postgresql.UUID(as_uuid=True)),
    )
    op.bulk_insert(
        symptoms_table,
        [
            {
                "id": _default_symptom_uuid(slug),
                "slug": slug,
                "name": name,
                "icon": icon,
                "is_default": True,
                "user_id": None,
            }
            for slug, name, icon in _DEFAULT_SYMPTOMS
        ],
    )

    # ---- Refactor ``entry_symptoms``: add FK column -----------------------
    op.add_column(
        "entry_symptoms",
        sa.Column(
            "symptom_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # Backfill: every existing entry_symptoms row carries a String-key
    # that matches one of the seeded default slugs (the old CHECK
    # constraint guaranteed it). Resolve it to the corresponding
    # symptoms.id via JOIN.
    op.execute(
        """
        UPDATE entry_symptoms es
        SET symptom_id = s.id
        FROM symptoms s
        WHERE s.slug = es.symptom_key
          AND s.is_default = TRUE
        """
    )

    # Tighten: NOT NULL + FK + new unique constraint, drop old String-key
    # column and its constraints.
    op.alter_column("entry_symptoms", "symptom_id", nullable=False)
    op.create_foreign_key(
        "fk_entry_symptoms_symptom_id",
        "entry_symptoms",
        "symptoms",
        ["symptom_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "uq_entry_symptoms_entry_symptom",
        "entry_symptoms",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_entry_symptoms_entry_symptom",
        "entry_symptoms",
        ["entry_id", "symptom_id"],
    )
    op.drop_constraint(
        "ck_entry_symptoms_symptom_key_allowed",
        "entry_symptoms",
        type_="check",
    )
    op.drop_column("entry_symptoms", "symptom_key")

    op.create_index(
        "ix_entry_symptoms_symptom_id",
        "entry_symptoms",
        ["symptom_id"],
    )


def downgrade() -> None:
    # Reverse: bring back the old ``symptom_key`` column from the FK.
    op.add_column(
        "entry_symptoms",
        sa.Column("symptom_key", sa.String(length=64), nullable=True),
    )
    op.execute(
        """
        UPDATE entry_symptoms es
        SET symptom_key = s.slug
        FROM symptoms s
        WHERE s.id = es.symptom_id
          AND s.is_default = TRUE
        """
    )
    # Any custom symptom row would lose its key on downgrade — that's
    # expected (the old schema simply couldn't represent custom symptoms).
    # If there are any such rows the next ALTER will fail loudly.
    op.alter_column("entry_symptoms", "symptom_key", nullable=False)

    op.drop_index("ix_entry_symptoms_symptom_id", table_name="entry_symptoms")
    op.drop_constraint(
        "uq_entry_symptoms_entry_symptom",
        "entry_symptoms",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_entry_symptoms_entry_symptom",
        "entry_symptoms",
        ["entry_id", "symptom_key"],
    )
    op.drop_constraint(
        "fk_entry_symptoms_symptom_id",
        "entry_symptoms",
        type_="foreignkey",
    )
    op.drop_column("entry_symptoms", "symptom_id")

    # Restore the original allowed-keys CHECK from migration 005.
    op.create_check_constraint(
        "ck_entry_symptoms_symptom_key_allowed",
        "entry_symptoms",
        "symptom_key IN ('headache', 'digestion', 'back_pain', 'fatigue', 'cold')",
    )

    # Drop ``symptoms`` master table + its policies.
    for pol in (
        "symptoms_owner_delete",
        "symptoms_owner_update",
        "symptoms_owner_insert",
        "symptoms_default_or_owner_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {pol} ON symptoms")
    op.execute("ALTER TABLE symptoms DISABLE ROW LEVEL SECURITY")

    op.execute("DROP TRIGGER IF EXISTS symptoms_updated_at ON symptoms")
    op.drop_index("ux_symptoms_user_slug", table_name="symptoms")
    op.drop_index("ux_symptoms_default_slug", table_name="symptoms")
    op.drop_index("ix_symptoms_user_id", table_name="symptoms")
    op.drop_table("symptoms")
