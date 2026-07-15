# ADR-N-01: `note_summary_short` Computation Location

**Datum:** 2026-07-15  
**Status:** Accepted  
**Bezug:** [#199](https://github.com/Sturmi77/correlcore/issues/199) · [`docs/features/notes-in-analysis.md`](../features/notes-in-analysis.md)

## Kontext

Insight cards, timeline tooltips and export previews need a short preview of a note
(`note_summary_short`, max 120 chars). The question is whether truncation/extractive
summarisation runs in the browser or on the server.

## Optionen

- **A — Client-side:** First sentence / truncated plain text to 120 chars in the web app.
  Offline-capable, no server cost, weaker quality.
- **B — Server-side extractive summary:** Better quality, requires API round-trip, breaks
  offline-first for previews.

## Entscheidung

**Option A for v1** — compute `note_summary_short` client-side on write and optionally
mirror the same helper server-side when the API receives `note` / `note_raw` without an
explicit summary (idempotent truncate).

Rationale: aligns with offline-first (ADR-0036) and the 60-second rule. Revisit in M8+ if
quality becomes a product blocker.

## Konsequenzen

- Shared truncate helper in web (`noteSummary.ts`) and backend (`note_summary.py`).
- Column `entries.note_summary_short` stores the preview for API/export without re-decrypting
  full note text in list endpoints when visibility allows.
- No external NLP dependency.
