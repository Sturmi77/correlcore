"""010 add insight and preference foundations for M3

Revision ID: 010
Revises: 009
Create Date: 2026-05-11

This sprint creates storage only: no worker, API endpoint, onboarding route or
public insight generation logic is introduced here.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_INSIGHT_TYPE_VALUES = ("pointbiserial", "spearman", "weekday_pattern")
_INSIGHT_TIER_VALUES = ("none", "early", "preliminary", "developing", "robust")


def upgrade() -> None:
    insight_type = postgresql.ENUM(*_INSIGHT_TYPE_VALUES, name="insight_type")
    insight_tier = postgresql.ENUM(*_INSIGHT_TIER_VALUES, name="insight_tier")
    insight_type.create(op.get_bind(), checkfirst=True)
    insight_tier.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "insights",
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
        sa.Column(
            "insight_type",
            postgresql.ENUM(*_INSIGHT_TYPE_VALUES, name="insight_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "tier",
            postgresql.ENUM(*_INSIGHT_TIER_VALUES, name="insight_tier", create_type=False),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_label", sa.String(length=128), nullable=True),
        sa.Column("effect_size", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("sample_n", sa.Integer(), nullable=False),
        sa.Column("statement_enc", sa.LargeBinary(), nullable=True),
        sa.Column(
            "flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("generated_for_date", sa.Date(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
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
        sa.CheckConstraint("sample_n >= 0", name="ck_insights_sample_n_nonnegative"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_insights_confidence_range",
        ),
    )
    op.create_index("ix_insights_user_id", "insights", ["user_id"])
    op.create_index("ix_insights_user_generated_at", "insights", ["user_id", "generated_at"])
    op.create_index(
        "ix_insights_user_type_metric",
        "insights",
        ["user_id", "insight_type", "metric"],
    )
    op.execute(
        """
        CREATE TRIGGER insights_updated_at
        BEFORE UPDATE ON insights
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )

    op.create_table(
        "user_preferences",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "analytics_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "onboarding_retro_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "onboarding_profile_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "dismissed_insight_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "reached_milestone_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("last_seen_insight_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.execute(
        """
        CREATE TRIGGER user_preferences_updated_at
        BEFORE UPDATE ON user_preferences
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )

    for table in ("insights", "user_preferences"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_owner_select ON {table}
            FOR SELECT
            USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_owner_insert ON {table}
            FOR INSERT
            WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_owner_update ON {table}
            FOR UPDATE
            USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_owner_delete ON {table}
            FOR DELETE
            USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
            """
        )


def downgrade() -> None:
    for table in ("user_preferences", "insights"):
        for policy in (
            f"{table}_owner_delete",
            f"{table}_owner_update",
            f"{table}_owner_insert",
            f"{table}_owner_select",
        ):
            op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP TRIGGER IF EXISTS user_preferences_updated_at ON user_preferences")
    op.drop_table("user_preferences")

    op.execute("DROP TRIGGER IF EXISTS insights_updated_at ON insights")
    op.drop_index("ix_insights_user_type_metric", table_name="insights")
    op.drop_index("ix_insights_user_generated_at", table_name="insights")
    op.drop_index("ix_insights_user_id", table_name="insights")
    op.drop_table("insights")

    insight_tier = postgresql.ENUM(*_INSIGHT_TIER_VALUES, name="insight_tier")
    insight_type = postgresql.ENUM(*_INSIGHT_TYPE_VALUES, name="insight_type")
    insight_tier.drop(op.get_bind(), checkfirst=True)
    insight_type.drop(op.get_bind(), checkfirst=True)
