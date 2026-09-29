# Audit A02: interactive co-occurrence budgets

Issue #988 moves tag×tag and symptom×tag analysis out of the API event loop and
defines deterministic admission limits. These values bound CPU and memory use;
they are not inferred from an HTTP timeout.

## Production defaults

| Control                |                   Default | Behaviour at the boundary                                                          |
| ---------------------- | ------------------------: | ---------------------------------------------------------------------------------- |
| Eligible tags          |                        28 | Whole request returns `limit_exceeded`; signals are not truncated                  |
| Eligible symptoms      |                        20 | Whole request returns `limit_exceeded`                                             |
| Supplied tags          |                       200 | Input catalog is rejected before per-signal preprocessing                          |
| Supplied symptoms      |                       100 | Input catalog is rejected before per-signal preprocessing                          |
| Fisher/FDR pairs       |                       400 | Checked before the first Fisher test; the FDR family remains complete              |
| Work units             |                   100,000 | `logged days × eligible pairs`                                                     |
| Worker processes       |         2 per API process | CPU work does not run on the asyncio event loop                                    |
| Waiting jobs           |         4 per API process | Further distinct jobs return `busy`                                                |
| Distinct jobs per user |                         1 | Exact duplicates share the existing job; other jobs return `busy`                  |
| Job wall time          |                 8 seconds | HTTP wait and cooperative worker deadline both apply                               |
| Cache                  | 128 results for 5 minutes | Key includes user, exact window, content digest, thresholds, and algorithm version |

The content digest covers every daily signal set and work context plus tag and
symptom identity, slug, and label. Any relevant entry, assignment, context, or
signal metadata change therefore misses the old cache entry. User ID is part of
the key, so results cannot be reused across accounts.

The worker checks its own monotonic deadline between candidate pairs. A timed-out
job remains in admission accounting until its process future actually completes,
so repeated requests cannot oversubscribe the pool while old work winds down.
A broken process pool is discarded and recreated by the next admitted request.

## Reproducible capacity measurement

Run from `backend/` with the project environment:

```bash
python scripts/benchmark_cooccurrence.py --days 60 --tags 20 --symptoms 20
python scripts/benchmark_cooccurrence.py --days 90 --tags 20 --symptoms 20
python scripts/benchmark_cooccurrence.py --days 250 --tags 20 --symptoms 20
```

Measurements recorded on 2026-09-23 on the development Windows host, Python
3.12, one process, warm package imports:

| Fixture                 | Analysis    | Pairs | Work units | Elapsed |
| ----------------------- | ----------- | ----: | ---------: | ------: |
| 60 days, 20×20 signals  | tag×tag     |   190 |     11,400 | 0.522 s |
| 60 days, 20×20 signals  | symptom×tag |   400 |     24,000 | 1.129 s |
| 90 days, 20×20 signals  | tag×tag     |   190 |     17,100 | 0.664 s |
| 90 days, 20×20 signals  | symptom×tag |   400 |     36,000 | 1.437 s |
| 250 days, 20×20 signals | tag×tag     |   190 |     47,500 | 0.660 s |
| 250 days, 20×20 signals | symptom×tag |   400 |    100,000 | 1.650 s |

These measurements calibrate the default budget and demonstrate that legal
60-day and larger fixtures complete well below the worker ceiling on this host.
They do not define the production latency SLO. Concurrent staging load, health
endpoint responsiveness, mobile QA, observability, and rollback verification
remain release gates tracked in #988.

## Response states

Both endpoints return a typed `analysis_status`:

- `ok`: analysis completed, including the valid empty-result case.
- `insufficient_data`: the selected window cannot support the analysis.
- `limit_exceeded`: full candidate family exceeds a documented budget;
  `analysis_limit` identifies the first limit and reports all measured counts.
- `busy`: per-user or process queue capacity is occupied.
- `timeout`: the admitted job exhausted its wall-clock budget.
- `unavailable`: the worker failed; the pool is recreated after a broken pool.

## Security diff review

Reviewed on 2026-09-23 against `origin/main`, covering both authenticated API
routes, database-to-analysis transformation, admission planning, process and
queue lifecycle, cache identity and invalidation, statistical refactoring,
typed API responses, and frontend rendering.

Threats considered were authenticated resource exhaustion, work continuing
after a client timeout, queue amplification through duplicate requests,
cross-user cache reuse, stale results after data changes, incomplete FDR
families through silent truncation, and process-pool failure. No reportable new
security finding remained after review. Focused tests cover each control and the
legacy-versus-precomputed pair statistics equivalence.
