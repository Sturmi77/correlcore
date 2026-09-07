"""045 collapse lag insight dismissals onto (target, feature) pairs

Revision ID: 045
Revises: 044
Create Date: 2026-09-07

#853 P-balanced (Q2): a dismiss now hides a whole ``(target, feature)`` pair, so
the insight subject key drops its per-lag ``lag_days`` element. Rewrite existing
lag dismissal rows to the pair-scoped key and dedupe rows that collapse onto the
same ``(user_id, subject_key)`` — keeping the most recently dismissed — so the
``uq_insight_dismissals_user_subject`` constraint still holds.
"""

from __future__ import annotations

from collections import defaultdict

import sqlalchemy as sa
from alembic import op

from app.services.insight_dismissal_service import rewrite_lag_dismissal_subject_key

revision: str = "045"
down_revision: str | None = "044"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    rows = list(
        conn.execute(
            sa.text("SELECT id, user_id, subject_key, dismissed_at FROM insight_dismissals")
        ).mappings()
    )
    if not rows:
        return

    current_key: dict[object, str] = {}
    final_key: dict[object, str] = {}
    dismissed_at: dict[object, object] = {}
    user_of: dict[object, object] = {}
    for row in rows:
        rid = row["id"]
        current_key[rid] = row["subject_key"]
        rewritten = rewrite_lag_dismissal_subject_key(row["subject_key"])
        final_key[rid] = rewritten if rewritten is not None else row["subject_key"]
        dismissed_at[rid] = row["dismissed_at"]
        user_of[rid] = row["user_id"]

    # Group by the post-rewrite identity so colliding lag dismissals of one pair
    # resolve to a single surviving row.
    groups: dict[tuple[object, str], list[object]] = defaultdict(list)
    for rid in current_key:
        groups[(user_of[rid], final_key[rid])].append(rid)

    delete_ids: list[object] = []
    update_pairs: list[tuple[object, str]] = []
    for members in groups.values():
        # Survivor = latest dismissed_at (NULL sorts first), tie-broken by id for
        # determinism.
        members.sort(
            key=lambda rid: (
                dismissed_at[rid] is not None,
                dismissed_at[rid].timestamp() if dismissed_at[rid] is not None else 0.0,
                str(rid),
            )
        )
        survivor = members[-1]
        delete_ids.extend(members[:-1])
        if current_key[survivor] != final_key[survivor]:
            update_pairs.append((survivor, final_key[survivor]))

    # Delete losers first so a survivor's key update cannot transiently violate
    # the unique constraint.
    if delete_ids:
        conn.execute(
            sa.text("DELETE FROM insight_dismissals WHERE id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": delete_ids},
        )
    for rid, new_key in update_pairs:
        conn.execute(
            sa.text("UPDATE insight_dismissals SET subject_key = :k WHERE id = :i"),
            {"k": new_key, "i": rid},
        )


def downgrade() -> None:
    # Irreversible: the per-lag ``lag_days`` element cannot be reconstructed once
    # collapsed onto the pair. New dismissals are pair-scoped by design.
    pass
