# ESLint & Svelte-Check Guardrails

Last updated: 2026-05-14

This document captures permanent guardrails derived from type errors and
lint regressions encountered during M3 / M3.1. Follow these rules to avoid
repeating the same class of failures.

## 1. Always use `<dialog>` for modal elements

**Rule:** Any component that calls `.showModal()`, `.close()`, or
`.requestClose()` on a bound element **must** use `<dialog>`, not `<div>`.

**Why it fails:** `bind:this={dialogEl}` where `dialogEl: HTMLDialogElement`
and the rendered element is `<div>` produces a TypeScript mismatch:

```
Error: Type 'HTMLDivElement' is missing the following properties from type
'HTMLDialogElement': open, returnValue, close, requestClose, and 2 more.
```

**Fix:**
```svelte
<!-- ❌ wrong -->
<div bind:this={dialogEl} class="cd-modal">

<!-- ✅ correct -->
<dialog bind:this={dialogEl} class="cd-modal" aria-labelledby="cd-title">
```

Always add `aria-labelledby` pointing to the modal heading and handle `Escape`
via the native `close` event rather than a manual `keydown` listener.

## 2. Do not use `component.$on()` in Svelte 5 tests

**Rule:** `component.$on('eventName', handler)` is not available in Svelte 5 /
SvelteKit with `@testing-library/svelte`. The method resolves to `never`,
causing:

```
Error: This expression is not callable. Type 'never' has no call signatures.
```

**Fix:** Use DOM events via `@testing-library/svelte` instead:

```typescript
// ❌ Svelte 4 pattern — does not work in Svelte 5
const handler = vi.fn();
component.$on('close', handler);
await fireEvent.click(screen.getByTestId('cd-close'));
expect(handler).toHaveBeenCalledOnce();

// ✅ Svelte 5 pattern
const handler = vi.fn();
const { container } = render(CorrelationDisclaimer, { props: { open: true } });
container.addEventListener('close', handler);
await fireEvent.click(screen.getByTestId('cd-close'));
expect(handler).toHaveBeenCalledOnce();
```

Alternatively, test observable side-effects (DOM state, store values) rather
than the raw event dispatch.

## 3. Export types consistently from API modules

**Rule:** If a component or test imports a type from `$lib/api/<module>`, that
type **must** be explicitly exported from the module's `index.ts` or the module
file itself.

**Failure pattern encountered:**
```
Error: Module '"$lib/api/insights"' has no exported member 'InsightDto'.
```

**Root cause:** The type was renamed from `InsightDto` → `InsightRead` during
the M3 analytics refactor but tests were not updated.

**Fix & prevention:**
1. After any type rename, run `grep -r 'InsightDto' apps/web/src` to catch all
   stale references before committing.
2. Keep a single canonical re-export in `$lib/api/insights/index.ts`:
   ```typescript
   export type { InsightRead } from './types';
   // Legacy alias for a transition period only — remove after M3.1
   export type { InsightRead as InsightDto } from './types';
   ```
3. Remove the legacy alias once all consumers are updated.

## 4. Run the full quality gate locally before pushing

Run this sequence before every push to a feature branch:

```bash
# From repo root
pnpm --filter @correlcore/web typecheck   # svelte-check + tsc
pnpm --filter @correlcore/web lint        # eslint
pnpm --filter @correlcore/web test -- --run  # vitest
pnpm --filter @correlcore/web build       # production build
```

All four commands must exit 0. A green CI that hides a red local build is a
code smell — fix locally first.

## 5. svelte-check is the authoritative type checker for `.svelte` files

**Rule:** `tsc --noEmit` does **not** check `.svelte` component internals.
Only `svelte-check --tsconfig ./tsconfig.json` catches errors like the
`HTMLDivElement` / `HTMLDialogElement` mismatch above.

Do not skip `svelte-check` in CI even if `tsc` is green.

## 6. Insights component file location

All Insights-related components belong under:

```
apps/web/src/lib/components/insights/
```

Do not place them in `components/home/` or `components/ui/`. Components
shared with the Home screen are re-exported via a barrel file:

```typescript
// components/insights/index.ts
export { default as InsightCard } from './InsightCard.svelte';
export { default as InsightConfidenceScale } from './InsightConfidenceScale.svelte';
export { default as CorrelationDisclaimer } from './CorrelationDisclaimer.svelte';
```
