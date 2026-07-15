# ADR-N-03: Custom Marker Normalisation

**Datum:** 2026-07-15  
**Status:** Accepted  
**Bezug:** [#199](https://github.com/Sturmi77/correlcore/issues/199) · [#197](https://github.com/Sturmi77/correlcore/issues/197)

## Kontext

Users may define free-text custom markers (max 32 chars) alongside the v1 taxonomy.
Without normalisation, `Stress` / `stress` / ` stress ` duplicate the same concept and
break marker-summary aggregations.

## Optionen

- **A — Normalise server-side:** lowercase, trim, collapse whitespace, dedupe on write.
  Display may still use a preferred label if stored separately.
- **B — Store verbatim:** preserves user intent, simpler backend, taxonomy fragmentation.

## Entscheidung

**Option A** — normalise on write:

1. Unicode NFKC
2. Strip leading/trailing whitespace
3. Collapse internal whitespace to a single space
4. Lowercase for the stored `marker` key
5. Reject empty / > 32 chars after normalisation

Predefined taxonomy keys are already lowercase snake_case and pass through unchanged.

## Konsequenzen

- `POST /entries/{id}/note-markers` returns the normalised key.
- Suggestions and `marker-summary` group by normalised key.
- UI chips may title-case for display; persistence always uses the normalised form.
