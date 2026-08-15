"""Admin-console service layer (#677). Callers must already be authorized
via ``require_admin`` — this module performs no auth of its own.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_audit_log import AdminAuditLog
from app.models.entry import Entry
from app.models.user import User

logger = logging.getLogger(__name__)

MAX_ADMIN_PAGE = 100


async def list_users(
    db: AsyncSession,
    *,
    query: str | None = None,
    active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[User], int]:
    """Paginated user list with optional email substring + active-status filter."""
    limit = max(1, min(limit, MAX_ADMIN_PAGE))
    offset = max(0, offset)

    conditions = []
    if query:
        conditions.append(func.lower(User.email).like(f"%{query.strip().lower()}%"))
    if active is not None:
        conditions.append(User.is_active.is_(active))

    stmt = select(User)
    count_stmt = select(func.count()).select_from(User)
    for cond in conditions:
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()
    return list(rows), total


async def get_user_with_entry_count(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[User, int] | None:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        return None
    count = (
        await db.execute(select(func.count()).select_from(Entry).where(Entry.user_id == user_id))
    ).scalar_one()
    return user, count


async def set_user_active(db: AsyncSession, user: User, *, is_active: bool) -> User:
    user.is_active = is_active
    await db.flush()
    return user


async def record_admin_action(
    db: AsyncSession,
    *,
    actor: User,
    action: str,
    target: User | None = None,
    detail: str | None = None,
) -> None:
    """Append one audit row. For a delete, call this BEFORE the target row is
    removed so ``target_email`` is still readable (the row itself survives the
    deletion — the audit columns carry no FK)."""
    db.add(
        AdminAuditLog(
            actor_user_id=actor.id,
            actor_email=actor.email,
            action=action,
            target_user_id=target.id if target is not None else None,
            target_email=target.email if target is not None else None,
            detail=detail,
        )
    )
    await db.flush()
    logger.info(
        "admin action",
        extra={
            "actor_user_id": str(actor.id),
            "action": action,
            "target_user_id": str(target.id) if target is not None else None,
        },
    )
