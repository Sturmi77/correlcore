"""055 canonicalize persisted insight dismissal keys.

Revision ID: 055
Revises: 054

Historical changepoint labels, association types/metrics and per-lag subjects
must resolve to the same key as newly generated insights. Collisions keep the
most recently dismissed row, then a stable id tie break. The transform is
idempotent and never crosses users.
"""

from __future__ import annotations

from collections import defaultdict

import sqlalchemy as sa
from alembic import op

from app.services.insight_dismissal_service import canonical_dismissal_subject_key

revision: str = "055"
down_revision: str | None = "054"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    rows = list(
        conn.execute(
            sa.text("SELECT id, user_id, subject_key, dismissed_at FROM insight_dismissals")
        ).mappings()
    )
    groups: dict[tuple[object, str], list[object]] = defaultdict(list)
    for row in rows:
        groups[(row["user_id"], canonical_dismissal_subject_key(row["subject_key"]))].append(row)

    for (_, key), members in groups.items():
        members.sort(key=lambda row: (row["dismissed_at"], str(row["id"])))
        survivor = members[-1]
        losers = [row["id"] for row in members[:-1]]
        if losers:
            conn.execute(
                sa.text("DELETE FROM insight_dismissals WHERE id IN :ids").bindparams(
                    sa.bindparam("ids", expanding=True)
                ),
                {"ids": losers},
            )
        if survivor["subject_key"] != key:
            conn.execute(
                sa.text("UPDATE insight_dismissals SET subject_key = :key WHERE id = :id"),
                {"key": key, "id": survivor["id"]},
            )


def downgrade() -> None:
    # Earlier labels, type names and individual lag values cannot be recovered.
    pass
