# Backend tests

Run the full suite the way CI does (`.github/workflows/ci-api.yml`, the
`pytest` job):

```bash
uv run --python 3.12 --extra dev --extra analytics pytest
```

Target a single file without the coverage gate while iterating:

```bash
uv run --python 3.12 pytest tests/test_worker_fault_injection.py -q --no-cov
```

## Fault-injection tests (`test_worker_fault_injection.py`, #759)

These verify the analytics worker's robustness by deliberately breaking the
two external dependencies it relies on and asserting it **recovers** instead
of dying:

- **Database connection faults** — the per-user insight loop must retry a
  _transient_ disconnect on a fresh session (#758 K), isolate a _persistent_
  fault to the one user while the rest of the batch still runs (#752), and
  never let one user's failure abort the scheduled run.
- **Redis connection faults** — the on-demand regenerate cooldown fails _open_
  (a Redis outage must not 500 the endpoint), and the post-batch debounce
  _skips_ rather than crash the bulk-import request or start a regeneration
  storm (#759).

Faults are injected at the mock boundary — a session or Redis client that
raises a connection error at a chosen point — not by tearing down a live
container. That keeps the suite fast and deterministic while still driving the
real recovery code paths. The tests run in the standard `pytest` collection,
so they execute on every backend CI run with no extra wiring.

### Adding a new fault-injection case

1. Pick the seam where the fault enters. For the scheduled worker that is the
   `session_factory` / `generate_insights_for_job` boundary (patch it to raise);
   for Redis it is `redis.asyncio.Redis.from_url` (patch it to return a client
   whose `set`/`aclose` raises, or to raise on connect).
2. Use the shaped error helpers (`_killed_connection_error`,
   `_invalidated_connection_error`) or a `redis.exceptions.RedisError` subclass
   so the classifier (`app.workers.analytics._is_transient_error`) sees a
   realistic failure.
3. Assert the **recovery behaviour**, not just that an exception was caught:
   the healthy work still completed, the retry budget was spent as expected,
   the run did not propagate, or the endpoint degraded gracefully.
4. Set `settings.WORKER_TRANSIENT_RETRY_BACKOFF_SECONDS` to `0` via `patch` so
   retries do not add real sleep to the test.
