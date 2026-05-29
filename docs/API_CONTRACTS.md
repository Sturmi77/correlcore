# API Contracts

This document records the current API contract strategy after the M4/M5
documentation sync.

## Current State

- FastAPI remains the source for the OpenAPI document at runtime.
- The web client still uses hand-written API wrappers.
- Schema-sensitive frontend constants live in
  `apps/web/src/lib/contracts/apiContract.ts`.
- Backend test `backend/tests/test_api_contract.py` compares that frontend
  contract against the backend Entry enums and Pydantic ranges.
- Dedicated backend tests cover newer surfaces separately:
  - `backend/tests/test_habits.py` — habit stats and tag habit fields
  - `backend/tests/test_onboarding.py` — guided onboarding endpoints
  - `backend/tests/test_entries.py` — batch create, delta, `cycle_day`, slots

Entry enum/range values remain contract-tested via `apiContract.ts` even before
an OpenAPI TypeScript client generator is introduced.

## Generator Evaluation

Recommended next step is `openapi-typescript` because it can generate pure
TypeScript types from FastAPI's OpenAPI JSON without imposing a runtime client.
That fits the existing `apiFetch` wrapper and keeps cookie refresh behavior in
one place.

Candidate workflow:

1. Export OpenAPI JSON from the backend in CI.
2. Run `openapi-typescript openapi.json -o apps/web/src/lib/api/generated.d.ts`.
3. Keep `apiFetch` as the runtime transport.
4. Replace hand-written DTO interfaces module by module.

Do not introduce a generated runtime client until it can preserve the current
single-flight refresh behavior and HttpOnly-cookie defaults.
