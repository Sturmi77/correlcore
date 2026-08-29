/**
 * Generated TypeScript types for the CorrelCore API (issue #778, audit Q2).
 *
 * `openapi.json` is exported from the FastAPI app by
 * `backend/scripts/export_openapi.py` and `src/schema.d.ts` is generated from
 * it by `openapi-typescript` (`pnpm --filter @correlcore/api-types generate`).
 * Both are committed and diffed in CI, so the frontend and backend contracts
 * cannot drift silently. Do not hand-edit `src/schema.d.ts`.
 */

export type { components, paths, operations } from './src/schema';
import type { components } from './src/schema';

/** All named response/request schemas, keyed by their OpenAPI name. */
export type Schemas = components['schemas'];

/** Convenience alias: `Schema<'EntryResponse'>` -> the generated type. */
export type Schema<Name extends keyof Schemas> = Schemas[Name];
