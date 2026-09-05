"""Async SQLAlchemy session factory and request-scoped DB context."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def _make_engine():
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        echo=settings.DEBUG,
        future=True,
        # #753 (J): hard server-side ceilings so a stuck query or a lock wait
        # cannot hold a pooled connection forever. asyncpg applies these via
        # SET on every new connection (server_settings), not just the first.
        connect_args={
            "server_settings": {
                "statement_timeout": str(settings.DB_STATEMENT_TIMEOUT_MS),
                "lock_timeout": str(settings.DB_LOCK_TIMEOUT_MS),
            }
        },
    )


def _make_session_factory(bind):
    return async_sessionmaker(
        bind,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


engine = _make_engine()
AsyncSessionLocal = _make_session_factory(engine)


def reset_engine() -> None:
    """Replace the module-level engine after ``engine.dispose()``.

    Integration tests dispose the shared engine between cases to avoid
    connection leaks across pytest-asyncio loops. ``AsyncSessionLocal`` is
    reconfigured in place so modules that imported the sessionmaker at
    load time keep working on the new pool.
    """
    global engine
    engine = _make_engine()
    AsyncSessionLocal.configure(bind=engine)


async def bind_rls_current_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Bind the authenticated user id to the current transaction for RLS.

    PostgreSQL policies read ``app.current_user_id`` via ``current_setting``.
    ``set_config(..., true)`` is transaction-local, so the value is cleared by
    the commit/rollback in ``get_session`` before the pooled connection can be
    reused by another request.
    """
    await session.execute(
        text("SELECT set_config('app.current_user_id', :user_id, true)"),
        {"user_id": str(user_id)},
    )


async def get_session() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency — yields a DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
