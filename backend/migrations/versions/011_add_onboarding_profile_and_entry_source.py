"""011 add onboarding profile and entry source

Revision ID: 011
Revises: 010
Create Date: 2026-05-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

ENTRY_SOURCE_VALUES = ("direct", "retrospective", "import", "wearable")
SLEEP_VALUES = ("5h", "6h", "7h", "8h", "9h_plus")
WORK_VALUES = ("office", "hybrid", "remote", "other")
SPORT_VALUES = ("rarely", "1_2_week", "3_4_week", "daily")
CURIOSITY_VALUES = ("work_life", "energy_sleep", "habits_sport", "wellbeing")


def upgrade() -> None:
    entry_source = postgresql.ENUM(*ENTRY_SOURCE_VALUES, name="entry_source")
    sleep = postgresql.ENUM(*SLEEP_VALUES, name="sleep_hours_typical")
    work = postgresql.ENUM(*WORK_VALUES, name="work_context_typical")
    sport = postgresql.ENUM(*SPORT_VALUES, name="sport_frequency")
    curiosity = postgresql.ENUM(*CURIOSITY_VALUES, name="insight_curiosity")
    for enum in (entry_source, sleep, work, sport, curiosity):
        enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "entries",
        sa.Column(
            "source",
            postgresql.ENUM(*ENTRY_SOURCE_VALUES, name="entry_source", create_type=False),
            nullable=False,
            server_default=sa.text("'direct'"),
        ),
    )

    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "sleep_hours_typical",
            postgresql.ENUM(*SLEEP_VALUES, name="sleep_hours_typical", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "work_context_typical",
            postgresql.ENUM(*WORK_VALUES, name="work_context_typical", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "sport_frequency",
            postgresql.ENUM(*SPORT_VALUES, name="sport_frequency", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "insight_curiosity",
            postgresql.ENUM(*CURIOSITY_VALUES, name="insight_curiosity", create_type=False),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.execute("ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY user_profiles_owner_policy ON user_profiles
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true))
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS user_profiles_owner_policy ON user_profiles")
    op.drop_table("user_profiles")
    op.drop_column("entries", "source")
    for name in (
        "insight_curiosity",
        "sport_frequency",
        "work_context_typical",
        "sleep_hours_typical",
        "entry_source",
    ):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
