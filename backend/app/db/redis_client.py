"""Redis client factory and token store.

Provides:
- ``get_redis()``          — FastAPI dependency yielding an async Redis client
- ``TokenStore``           — Single-use refresh-token rotation backed by Redis

Token storage layout
--------------------
Key:   ``rt:<user_id>:<jti>``
Value: ``"1"``  (presence == valid)
TTL:   ``JWT_REFRESH_TOKEN_EXPIRE_DAYS`` days

Rotation uses a Lua script so consume+store is atomic: a stolen refresh
token can only mint one successor session under concurrent refresh.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level pool — created once at startup, reused across requests.
_redis_pool: aioredis.Redis | None = None

# Atomic rotate: delete old JTI only if present, then SET new JTI with TTL.
# Returns 1 on success, 0 if the old key was already missing (reuse / revoke).
_ROTATE_LUA = """
if redis.call('EXISTS', KEYS[1]) == 1 then
  redis.call('DEL', KEYS[1])
  redis.call('SET', KEYS[2], '1', 'EX', ARGV[1])
  return 1
end
return 0
"""


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

    async def rotate(self, user_id: str, old_jti: str, new_jti: str) -> bool:
        """Atomically invalidate old JTI and store new one.

        Returns ``True`` when the old JTI was present and rotation succeeded.
        Returns ``False`` when the old JTI was already missing (reuse/revoked).
        """
        result = await self._r.eval(
            _ROTATE_LUA,
            2,
            self._key(user_id, old_jti),
            self._key(user_id, new_jti),
            self._TTL_SECONDS,
        )
        return bool(result)

    async def revoke(self, user_id: str, jti: str) -> None:
        """Invalidate a refresh token (logout)."""
        await self._r.delete(self._key(user_id, jti))

    async def revoke_all(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user (force-logout all devices)."""
        pattern = f"rt:{user_id}:*"
        cursor: int | bytes = 0
        while True:
            cursor, keys = await self._r.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await self._r.delete(*keys)
            if cursor == 0 or cursor == b"0":
                break
