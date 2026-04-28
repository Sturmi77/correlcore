"""Redis client factory and token store.

Provides:
- ``get_redis()``          — FastAPI dependency yielding an async Redis client
- ``TokenStore``           — Single-use refresh-token rotation backed by Redis

Token storage layout
--------------------
Key:   ``rt:<user_id>:<jti>``
Value: ``"1"``  (presence == valid)
TTL:   ``JWT_REFRESH_TOKEN_EXPIRE_DAYS`` days

On rotation the old key is deleted and a new one is written atomically
via a pipeline. This prevents replay attacks: a stolen refresh token can
only be used once before it is invalidated.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level pool — created once at startup, reused across requests.
_redis_pool: aioredis.Redis | None = None


def _get_pool() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency — yields a Redis client from the shared pool."""
    yield _get_pool()


# ---------------------------------------------------------------------------
# Token store
# ---------------------------------------------------------------------------

class TokenStore:
    """Manages single-use refresh tokens in Redis."""

    _TTL_SECONDS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86_400

    def __init__(self, redis: aioredis.Redis) -> None:
        self._r = redis

    @staticmethod
    def _key(user_id: str, jti: str) -> str:
        return f"rt:{user_id}:{jti}"

    async def store(self, user_id: str, jti: str) -> None:
        """Persist a new refresh token JTI."""
        await self._r.set(self._key(user_id, jti), "1", ex=self._TTL_SECONDS)

    async def is_valid(self, user_id: str, jti: str) -> bool:
        """Return True if the token JTI exists in Redis."""
        return bool(await self._r.exists(self._key(user_id, jti)))

    async def rotate(self, user_id: str, old_jti: str, new_jti: str) -> None:
        """Atomically invalidate old JTI and store new one."""
        async with self._r.pipeline(transaction=True) as pipe:
            pipe.delete(self._key(user_id, old_jti))
            pipe.set(self._key(user_id, new_jti), "1", ex=self._TTL_SECONDS)
            await pipe.execute()

    async def revoke(self, user_id: str, jti: str) -> None:
        """Invalidate a refresh token (logout)."""
        await self._r.delete(self._key(user_id, jti))

    async def revoke_all(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user (force-logout all devices)."""
        pattern = f"rt:{user_id}:*"
        keys = await self._r.keys(pattern)
        if keys:
            await self._r.delete(*keys)
