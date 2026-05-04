"""005 create entry_symptoms table (M1, Issue #9)

Revision ID: 005
Revises: 004
Create Date: 2026-05-04

Notes
-----
- Single table: ``entry_symptoms``. There is no master "symptom"
  catalogue in M1 — the standard symptom set is a closed list seeded
  via a CHECK constraint on ``symptom_key``. Adding a custom-symptom
  surface is explicitly deferred (Issue #9 has no such acceptance
  criterion).
- ``intensity`` is constrained 0..3 by a CHECK; the UI maps to a
  visual scale (4 dots), not a raw number input.
- ``user_id`` is denormalised onto every row so the RLS policies can
  filter without a join on ``entries``.
- RLS: four owner-scoped policies, identical pattern to migration 003
  (``entries``) and migration 004 (``entry_tags``).
- ``updated_at`` uses the shared trigger ``update_updated_at_column``
  installed by migration 001.

Privacy
-------
Symptoms are health data under DSGVO Art. 9. The combination
``(symptom_key, intensity)`` must never appear in application logs;
the static log-scrubbing test in ``backend/tests/test_log_scrubbing.py``
enforces this. Issue #26 will swap the plaintext columns for Fernet
ciphertext (ADR-0005); the at-rest encryption is the
M1-DSGVO-Checkpoint item the design doc tracks.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


# Standard symptom keys allowed in M1. Mirrored exactly in
# ``app.models.symptom.STANDARD_SYMPTOM_KEYS``.
_STANDARD_SYMPTOM_KEYS = (
    "headache",
    "digestion",
    "back_pain",
    "fatigue",
    "cold",
)

# Intensity bounds. Mirrored in the schema layer and the model.
_INTENSITY_MIN = 0
_INTENSITY_MAX = 3


def upgrade() -> None:
    # Build the IN-list literal for the CHECK constraint. Quoting is
    # safe because the values are static identifiers controlled here.
    keys_sql = ", ".join(f"'{k}'" for k in _STANDARD_SYMPTOM_KEYS)

    op.create_table(
        "entry_symptoms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symptom_key", sa.String(length=64), nullable=False),
        sa.Column("intensity", sa.Integer, nullable=False),
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
        sa.UniqueConstraint(
            "entry_id",
            "symptom_key",
            name="uq_entry_symptoms_entry_symptom",
        ),
        sa.CheckConstraint(
            f"intensity BETWEEN {_INTENSITY_MIN} AND {_INTENSITY_MAX}",
            name="ck_entry_symptoms_intensity_range",
        ),
        sa.CheckConstraint(
            f"symptom_key IN ({keys_sql})",
            name="ck_entry_symptoms_symptom_key_allowed",
        ),
    )
    op.create_index("ix_entry_symptoms_entry_id", "entry_symptoms", ["entry_id"])
    op.create_index("ix_entry_symptoms_user_id", "entry_symptoms", ["user_id"])

    # updated_at trigger reuses the function from migration 001.
    op.execute(
        """
        CREATE TRIGGER entry_symptoms_updated_at
        BEFORE UPDATE ON entry_symptoms
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """
    )

    # ---- Row-Level-Security ------------------------------------------------
    op.execute("ALTER TABLE entry_symptoms ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY entry_symptoms_owner_select ON entry_symptoms
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entry_symptoms_owner_insert ON entry_symptoms
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entry_symptoms_owner_update ON entry_symptoms
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entry_symptoms_owner_delete ON entry_symptoms
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    for pol in (
        "entry_symptoms_owner_delete",
        "entry_symptoms_owner_update",
        "entry_symptoms_owner_insert",
        "entry_symptoms_owner_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {pol} ON entry_symptoms")
    op.execute("ALTER TABLE entry_symptoms DISABLE ROW LEVEL SECURITY")

    op.execute("DROP TRIGGER IF EXISTS entry_symptoms_updated_at ON entry_symptoms")
    op.drop_index("ix_entry_symptoms_user_id", table_name="entry_symptoms")
    op.drop_index("ix_entry_symptoms_entry_id", table_name="entry_symptoms")
    op.drop_table("entry_symptoms")
