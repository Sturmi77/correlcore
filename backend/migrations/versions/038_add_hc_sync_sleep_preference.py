"""038 health_connect_sync_sleep_enabled preference

Revision ID: 038
Revises: 037
Create Date: 2026-08-02

M8 Sprint 4 (#172): per-field toggle to disable Health Connect sleep sync.
Defaults to true so consenting users get sleep import; flipping it off stops
future imports without touching already-imported values.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "038"
down_revision: str | None = "037"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column(
            "health_connect_sync_sleep_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "health_connect_sync_sleep_enabled")
