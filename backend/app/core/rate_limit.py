"""Shared SlowAPI Limiter — single source of truth for rate-limiting.

Why this lives here
-------------------
SlowAPI's exception handler reads the limiter from ``app.state.limiter``
(set in :mod:`app.main`). The same limiter instance must back every
``@limiter.limit(...)`` decorator across the codebase, otherwise each
import site builds its own private state bucket — fine with the default
in-memory backend, but it silently breaks the moment a shared backend
(Redis, Memcached) is introduced because each instance would track its
own counters.

Endpoint modules import :data:`limiter` from here; :mod:`app.main`
imports it once and binds it to ``app.state.limiter``.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

#: Process-wide Limiter instance. Do **not** create a second one.
limiter = Limiter(key_func=get_remote_address)
