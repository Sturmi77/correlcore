"""004 create tags + entry_tags tables (M1, Issue #8)

Revision ID: 004
Revises: 003
Create Date: 2026-05-04

Notes
-----
- ``tags`` holds both curated defaults (``user_id IS NULL``,
  ``is_default = TRUE``) and user-owned custom tags. A CHECK constraint
  forbids any other combination so neither side can drift.
- Two partial unique indexes guard slug uniqueness:
    * ``ux_tags_default_slug`` on ``(slug)`` WHERE ``is_default``: one
      curated tag per slug across the whole system.
    * ``ux_tags_user_slug`` on ``(user_id, slug)`` WHERE NOT
      ``is_default``: a user may not own two tags with the same slug,
      but two users can.
- ``entry_tags`` is the M:N link with a denormalised ``user_id`` so the
  RLS policy can filter without a join on ``entries``.
- Seed: 30 curated default tags. Slug is the canonical key; ``name`` is
  the human-readable German default. Frontend i18n maps slug → label.
- RLS:
    * On ``tags`` we allow public SELECT for default tags (``is_default
      = TRUE``) and owner-scoped CRUD for custom tags.
    * On ``entry_tags`` four owner-scoped policies, identical pattern
      to migration 003.
- Both tables ship the policies inactive in the sense that the
  application binds ``app.current_user_id`` per request only as an M1
  follow-up (same caveat as migration 003).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_TAG_CATEGORY_VALUES = (
    "sport",
    "social",
    "work",
    "leisure",
    "consumption",
    "health",
    "other",
)

# Curated default tags. ``slug`` is the stable key the frontend uses for
# i18n; ``name`` is the German default the seed inserts. Categories
# match :class:`app.models.tag.TagCategory`. Icons are Lucide names —
# the frontend resolves them.
_DEFAULT_TAGS: tuple[tuple[str, str, str, str, str], ...] = (
    # (slug,            name,             category,       icon,           color)
    # Sport
    ("sport", "Sport", "sport", "dumbbell", "#10b981"),
    ("running", "Laufen", "sport", "footprints", "#10b981"),
    ("cycling", "Radfahren", "sport", "bike", "#10b981"),
    ("yoga", "Yoga", "sport", "flower", "#10b981"),
    ("strength", "Kraftraining", "sport", "dumbbell", "#10b981"),
    # Social
    ("family", "Familie", "social", "users", "#3b82f6"),
    ("friends", "Freunde", "social", "users", "#3b82f6"),
    ("partner", "Partner:in", "social", "heart", "#3b82f6"),
    ("conflict", "Konflikt", "social", "alert-triangle", "#ef4444"),
    ("date", "Date", "social", "heart", "#3b82f6"),
    # Work
    ("work_intense", "Arbeit intensiv", "work", "briefcase", "#f59e0b"),
    ("meeting_heavy", "Viele Meetings", "work", "calendar", "#f59e0b"),
    ("focus_time", "Fokus-Zeit", "work", "target", "#f59e0b"),
    ("commute", "Pendeln", "work", "train", "#f59e0b"),
    ("deadline", "Deadline", "work", "alarm-clock", "#f59e0b"),
    # Leisure
    ("music", "Musik", "leisure", "music", "#8b5cf6"),
    ("reading", "Lesen", "leisure", "book-open", "#8b5cf6"),
    ("gaming", "Gaming", "leisure", "gamepad-2", "#8b5cf6"),
    ("nature", "Natur", "leisure", "tree-pine", "#8b5cf6"),
    ("travel", "Reisen", "leisure", "plane", "#8b5cf6"),
    # Consumption
    ("alcohol", "Alkohol", "consumption", "wine", "#dc2626"),
    ("caffeine_high", "Viel Koffein", "consumption", "coffee", "#dc2626"),
    ("sugar_high", "Viel Zucker", "consumption", "candy", "#dc2626"),
    ("fast_food", "Fast Food", "consumption", "pizza", "#dc2626"),
    ("nicotine", "Nikotin", "consumption", "cigarette", "#dc2626"),
    # Health / mindfulness
    ("meditation", "Meditation", "health", "brain", "#14b8a6"),
    ("therapy", "Therapie", "health", "stethoscope", "#14b8a6"),
    ("medication", "Medikament", "health", "pill", "#14b8a6"),
    ("good_sleep", "Guter Schlaf", "health", "moon", "#14b8a6"),
    ("nap", "Mittagsschlaf", "health", "bed", "#14b8a6"),
)


def upgrade() -> None:
    # Enum type
    tag_category = postgresql.ENUM(*_TAG_CATEGORY_VALUES, name="tag_category")
    tag_category.create(op.get_bind(), checkfirst=True)

    # tags table
    op.create_table(
        "tags",
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
        sa.Column(
            "category",
            postgresql.ENUM(*_TAG_CATEGORY_VALUES, name="tag_category", create_type=False),
            nullable=False,
        ),
        sa.Column("icon", sa.String(length=32), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=True),
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
            name="ck_tags_default_owner_consistency",
        ),
    )

    op.create_index("ix_tags_user_id", "tags", ["user_id"])
    op.create_index(
        "ux_tags_default_slug",
        "tags",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.create_index(
        "ux_tags_user_slug",
        "tags",
        ["user_id", "slug"],
        unique=True,
        postgresql_where=sa.text("NOT is_default"),
    )

    op.execute(
        """
        CREATE TRIGGER tags_updated_at
        BEFORE UPDATE ON tags
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # entry_tags link table
    op.create_table(
        "entry_tags",
        sa.Column(
            "entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entries.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("entry_id", "tag_id", name="uq_entry_tags_entry_tag"),
    )
    op.create_index("ix_entry_tags_user_id", "entry_tags", ["user_id"])
    op.create_index("ix_entry_tags_tag_id", "entry_tags", ["tag_id"])

    # ---- Row-Level-Security ------------------------------------------------
    # tags: public read for defaults, owner-scoped CRUD for custom tags.
    op.execute("ALTER TABLE tags ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tags_default_or_owner_select ON tags
        FOR SELECT
        USING (
            is_default = TRUE
            OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )
    op.execute(
        """
        CREATE POLICY tags_owner_insert ON tags
        FOR INSERT
        WITH CHECK (
            is_default = FALSE
            AND user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )
    op.execute(
        """
        CREATE POLICY tags_owner_update ON tags
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
        CREATE POLICY tags_owner_delete ON tags
        FOR DELETE
        USING (
            is_default = FALSE
            AND user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
        )
        """
    )

    # entry_tags: owner-scoped on the denormalised user_id column.
    op.execute("ALTER TABLE entry_tags ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY entry_tags_owner_select ON entry_tags
        FOR SELECT
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entry_tags_owner_insert ON entry_tags
        FOR INSERT
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entry_tags_owner_update ON entry_tags
        FOR UPDATE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        WITH CHECK (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY entry_tags_owner_delete ON entry_tags
        FOR DELETE
        USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid)
        """
    )

    # ---- Seed default tags -------------------------------------------------
    # ``category`` MUST be typed as the existing ENUM, not as ``sa.String``.
    # alembic's bulk_insert binds parameters with their declared SQLAlchemy
    # type — a ``String`` column emits ``$N::VARCHAR``, and PostgreSQL refuses
    # the implicit cast from ``character varying`` to a custom enum, raising
    # ``DatatypeMismatchError: column "category" is of type tag_category but
    # expression is of type character varying``. ``create_type=False`` avoids
    # a duplicate ``CREATE TYPE`` (the ENUM was already created above).
    tags_table = sa.table(
        "tags",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column(
            "category",
            postgresql.ENUM(*_TAG_CATEGORY_VALUES, name="tag_category", create_type=False),
        ),
        sa.column("icon", sa.String),
        sa.column("color", sa.String),
        sa.column("is_default", sa.Boolean),
        sa.column("user_id", postgresql.UUID(as_uuid=True)),
    )
    op.bulk_insert(
        tags_table,
        [
            {
                "slug": slug,
                "name": name,
                "category": category,
                "icon": icon,
                "color": color,
                "is_default": True,
                "user_id": None,
            }
            for slug, name, category, icon, color in _DEFAULT_TAGS
        ],
    )


def downgrade() -> None:
    # Policies
    for pol in (
        "entry_tags_owner_delete",
        "entry_tags_owner_update",
        "entry_tags_owner_insert",
        "entry_tags_owner_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {pol} ON entry_tags")
    op.execute("ALTER TABLE entry_tags DISABLE ROW LEVEL SECURITY")

    for pol in (
        "tags_owner_delete",
        "tags_owner_update",
        "tags_owner_insert",
        "tags_default_or_owner_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {pol} ON tags")
    op.execute("ALTER TABLE tags DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_entry_tags_tag_id", table_name="entry_tags")
    op.drop_index("ix_entry_tags_user_id", table_name="entry_tags")
    op.drop_table("entry_tags")

    op.execute("DROP TRIGGER IF EXISTS tags_updated_at ON tags")
    op.drop_index("ux_tags_user_slug", table_name="tags")
    op.drop_index("ux_tags_default_slug", table_name="tags")
    op.drop_index("ix_tags_user_id", table_name="tags")
    op.drop_table("tags")

    tag_category = postgresql.ENUM(*_TAG_CATEGORY_VALUES, name="tag_category")
    tag_category.drop(op.get_bind(), checkfirst=True)
