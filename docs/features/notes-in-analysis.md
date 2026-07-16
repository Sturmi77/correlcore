# Feature Spec: Notes in Analysis

**Status:** Approved  
**Version:** 1.1.0  
**Created:** 2026-05-16  
**Updated:** 2026-05-16  
**Owner:** @Sturmi77  
**Milestone Coverage:** M1 (retroactive) → M2 (retroactive) → M3 (retroactive) → M4 → M7 → M9–M11

---

## Overview

This document specifies the **Notes in Analysis** feature for CorrelCore. The goal is to make
free-text notes visible across the UI, enrich them with optional structured markers, extract
normalized signals from them, and use those signals to power explainable insights.

Milestones M1–M3 are already completed. All work marked **[RETROACTIVE]** must be backported into
the existing codebase without breaking current functionality. Work marked **[NEW]** follows the
normal sprint cadence from M4 onward.

---

## Motivation

Raw numeric data (mood scores, sleep hours, activity counts) alone cannot explain _why_ patterns
emerge. Notes already exist as a freeform field on entries, but they are currently invisible in
charts, analysis views, and insights. Surfacing notes as first-class contextual evidence closes this
gap without introducing opaque AI inference.

This feature follows three principles already documented in `DESIGN_DOCUMENT.md`:

- **Explainability first:** every insight references the specific days and signals it is based on.
- **60-second rule:** note entry must never add friction to the daily logging flow.
- **Privacy by design:** free-text is never sent to external services; analysis runs on structured
  signals only.

---

## Non-Goals

- No LLM inference on raw free-text as the primary analysis step.
- No medical or diagnostic claims derived from note content.
- No automatic sentiment scoring without transparent, auditable rules.
- No dependency on external NLP APIs.
- No retroactive rewrite of milestone M1–M3 history or sprint records.

---

## Product Principles

| #   | Principle                        | Rationale                                                    |
| --- | -------------------------------- | ------------------------------------------------------------ |
| 1   | Notes remain optional            | Preserve the 60-second daily logging promise                 |
| 2   | Visibility before automation     | First value = seeing notes in analysis context, not NLP      |
| 3   | Structured signals over raw text | Insights use normalized markers/signals, never raw free text |
| 4   | Explainability first             | Every note-derived insight must be traceable to evidence     |

---

## Data Model

### New / Extended Fields

```sql
-- Extend existing entries table (additive migration, no data loss)
ALTER TABLE entries
  ADD COLUMN note_raw           TEXT,
  ADD COLUMN note_summary_short TEXT,          -- max 120 chars, UI preview
  ADD COLUMN note_visibility    TEXT NOT NULL DEFAULT 'full'
    CHECK (note_visibility IN ('full', 'analysis_only', 'hidden')),
  ADD COLUMN note_updated_at    TIMESTAMPTZ;

-- New table: user-defined and system-suggested markers
CREATE TABLE entry_note_markers (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_id    UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  marker      TEXT NOT NULL,                   -- e.g. 'work', 'social', 'stress'
  source      TEXT NOT NULL DEFAULT 'user'
    CHECK (source IN ('user', 'suggestion')),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- New table: normalized signals extracted from notes
CREATE TABLE entry_note_signals (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entry_id     UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
  signal       TEXT NOT NULL,                  -- normalized term, e.g. 'konflikt'
  confidence   NUMERIC(4,3) NOT NULL,          -- 0.000–1.000
  source_span  TEXT,                           -- original substring that triggered this signal
  extractor_v  TEXT NOT NULL,                  -- version tag of extraction ruleset
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_note_markers_entry   ON entry_note_markers(entry_id);
CREATE INDEX idx_note_signals_entry   ON entry_note_signals(entry_id);
CREATE INDEX idx_note_signals_signal  ON entry_note_signals(signal);
```

### Offline / Dexie Sync

Dexie stores `note_raw`, `note_markers[]` (user-sourced only), and a `note_pending_sync: boolean`
flag. System signals are computed server-side after sync; the client never stores
`entry_note_signals` locally beyond a cache TTL of 24 h.

Sync conflict strategy: field-level last-write-wins for `note_raw`, consistent with the existing
entry sync model. Marker sets are merged as union sets on conflict (no deletions silently lost).

---

## API Endpoints

All endpoints are prefixed with `/api/v1`.

### Entry Note CRUD (extend existing)

```
PATCH  /entries/{entry_id}
       body: { note_raw?: string, note_summary_short?: string, note_visibility?: string }

GET    /entries/{entry_id}
       response includes: note_raw, note_summary_short, note_visibility,
                          note_markers[], note_signals[]
```

### Markers

```
POST   /entries/{entry_id}/note-markers
       body: { marker: string, source: "user" }

DELETE /entries/{entry_id}/note-markers/{marker_id}

GET    /users/me/note-markers/suggestions
       response: string[]   // last 20 user-defined markers, most-used first
```

### Signals (read-only for frontend)

```
GET    /entries/{entry_id}/note-signals
POST   /admin/entries/{entry_id}/note-signals/reprocess   // operator only
```

### Analysis Endpoints

```
GET    /analysis/notes/marker-summary
       query: { from: date, to: date, markers?: string[] }
       response: { marker: string, count: number, avg_mood: number, entries: uuid[] }[]

GET    /analysis/notes/signal-correlation
       query: { signal: string, metric: "mood"|"energy"|"symptom", min_entries?: number }
       response: { signal, metric, correlation, sample_size, example_entry_ids[] }
```

---

## Frontend Components

### Entry Composer — Note Section

- Expandable text area, collapsed by default to preserve the 60-second flow.
- Chip row below text area showing the predefined marker taxonomy (see below) plus recent user
  markers.
- Chips are multi-selectable; selected chips are persisted as `entry_note_markers` with
  `source: 'user'`.
- Character limit: 2 000 for `note_raw`, 120 autogenerated for `note_summary_short` (first sentence
  or truncated).

### Marker Taxonomy (v1)

| Key           | Display Label (DE / EN)        |
| ------------- | ------------------------------ |
| `work`        | Arbeit / Work                  |
| `homeoffice`  | Homeoffice / Remote            |
| `social`      | Sozial / Social                |
| `movement`    | Bewegung / Exercise            |
| `sleep_bad`   | Schlechter Schlaf / Poor Sleep |
| `sleep_good`  | Guter Schlaf / Good Sleep      |
| `stress`      | Stress                         |
| `conflict`    | Konflikt / Conflict            |
| `symptom`     | Symptom                        |
| `travel`      | Reise / Travel                 |
| `achievement` | Erfolg / Achievement           |

Custom markers are free-text, max 32 chars, stored alongside predefined ones.

### Timeline / Calendar — Note Indicator

- Days with a note show a small dot indicator (color: `--color-primary`).
- Days with at least one derived signal show a second dot (color: `--color-warning`).
- Tooltip on hover / tap: `note_summary_short`.

### Analysis Drilldown — Entry Drawer

- Clicking any data point opens a side drawer showing full entry detail including `note_raw`,
  markers as chips, and up to 5 top signals with confidence bars.
- Filter chip in analysis view: **"Nur Einträge mit Notizen"** and **"Nur markierte Einträge"**.

### Insights — Evidence Block

Added to all insight cards from M7 onward:

```
┌──────────────────────────────────────────────────┐
│ 💡 An Tagen mit Marker "Stress" lag dein Mood    │
│    im Schnitt 1.4 Punkte unter deinem Mittelwert │
│                                                  │
│    Basis: 14 Tage · Konfidenz: 0.82              │
│    Beispiele: 12. März, 3. April, 9. Mai         │
└──────────────────────────────────────────────────┘
```

Insights only activate when `sample_size >= 20` entries have notes. Below that threshold the UI
shows a soft prompt: _"Füge Notizen hinzu, um Zusammenhänge besser zu verstehen."_

---

## Signal Extraction (M7)

Signal extraction runs as a FastAPI background task (`BackgroundTasks`) triggered on
`PATCH /entries/{id}` when `note_raw` is updated.

### Extractor Architecture

```
note_raw
  └─► Preprocessing (lowercase, strip HTML)
       └─► Dictionary Lookup       → signals with confidence 0.90
            └─► Regex Pattern Match → signals with confidence 0.60–0.85
                 └─► (Optional, M12+) Local LLM via Ollama
                      → additional signals with confidence 0.40–0.70
```

All extractor rules are version-tagged (`extractor_v`). Re-processing old entries is possible via
the operator endpoint without data loss.

### Example Dictionary Rules (v1)

```python
SIGNAL_DICT = {
    "konflikt":    ["konflikt", "streit", "auseinandersetzung", "argument"],
    "isolation":   ["alleine", "niemand", "isoliert", "einsam"],
    "spaziergang": ["spazieren", "spaziergang", "walk", "draußen"],
    "kopfschmerz": ["kopfschmerzen", "migräne", "headache"],
}
```

Signals are language-agnostic normalized keys; source text can be German or English.

---

## Privacy & Consent

| `note_visibility` value | Effect                                                                                |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `full` (default)        | Full display and analysis                                                             |
| `analysis_only`         | Used in signal extraction and insights; `note_raw` hidden in shared views and exports |
| `hidden`                | Stored but excluded from all analysis, display, and exports                           |

- Setting is per-entry; a global user preference sets the default.
- All signal extraction runs server-side within the selfhosted instance — no external API calls.
- Export includes `note_raw` and signals only when `note_visibility != 'hidden'`.

---

## Milestone Mapping

| Milestone               | Status                         | Work Package                                                                                                                                                                    |
| ----------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **M1** Core Entry       | ✅ Done → **RETROACTIVE**      | Add `note_raw` to entry model, CRUD, Dexie sync, basic UI textarea                                                                                                              |
| **M2** Visualisation    | ✅ Done → **RETROACTIVE**      | Note indicator in Timeline/Calendar, Entry Drawer in Analysis, filter chips                                                                                                     |
| **M3** Insights v1      | ✅ Done → **RETROACTIVE**      | Marker chips in Entry Composer, marker taxonomy, marker-based summary API                                                                                                       |
| **M4** Mobile Polish    | ✅ Foundation shipped (#195+)  | Composer note fields, `note_summary_short` preview (ADR-N-01), visibility; further mobile chrome polish may iterate                                                             |
| **M7** Insights v2      | ✅ Foundation shipped (#201/#202) | Signal extraction, `entry_note_signals`, evidence on insight cards (ADR-N-02); remaining polish tracked separately                                                            |
| **M9** Beta             | ✅ Complete (2026-07-11)       | Threshold review docs under [`quality/M9_ANALYTICS_THRESHOLDS_REVIEW.md`](../quality/M9_ANALYTICS_THRESHOLDS_REVIEW.md). Per-entry `note_visibility` API landed.                 |
| **M10** Public Selfhost | ✅ Complete (2026-07-11) / rest open | Operator reprocess: `POST /admin/entries/{id}/note-signals/reprocess`. Export of notes/signals when `note_visibility != hidden` may still deepen.                           |
| **M11** Play Store      | 🔲 Planned                     | Mobile UX hardening, no health-claim copy in signal descriptions                                                                                                                |

---

## Acceptance Criteria

### M1 Retroactive

- [x] `note_raw` persists on entry create and update via API.
- [x] `note_raw` syncs bidirectionally with Dexie offline store.
- [x] Existing entries without notes are unaffected (nullable field, no migration data loss).
- [x] Unit tests cover note CRUD and offline conflict resolution.
- [x] API remains backward-compatible for clients not sending note fields.

### M2 Retroactive

- [x] Timeline/Calendar renders note indicator dot for days with `note_raw` present.
- [x] Clicking any chart data point opens entry drawer showing `note_raw`.
- [ ] Filter "Nur Einträge mit Notizen" returns correct subset.
- [x] No note content visible on list/card views unless explicitly opened.

### M3 Retroactive

- [x] Entry Composer shows marker chip row with predefined markers.
- [x] Selected markers saved as `entry_note_markers` with `source: 'user'`.
- [x] `GET /analysis/notes/marker-summary` returns correct avg_mood per marker.
- [ ] Suggestions endpoint returns last 20 user-defined markers.
- [x] Marker-based insights / summary path wired (sample thresholds per engine).

### M4

- [ ] Note section collapsed by default; expand tap < 200ms perceived latency.
- [ ] On mobile (375px), chip row scrolls horizontally without wrapping.
- [x] `note_summary_short` auto-generated on save, max 120 chars (ADR-N-01).

### M7

- [x] Signal extraction service for notes (foundation #201/#202).
- [x] Signals stored with `confidence`, `source_span`, `extractor_v`.
- [x] Insight evidence path for note signals (threshold ADR-N-02 = 0.70).
- [x] Hidden / low-sample insights suppressed without error surfacing.

---

## Open Questions / ADR Triggers

| ID       | Question                                                                                                        | Decision Needed By                                                                                      |
| -------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| ADR-N-01 | Should `note_summary_short` be computed client-side (first sentence) or server-side (extractive summarisation)? | **Decided** — [ADR-N-01](../adr/ADR-N-01-note-summary-computation.md) (client truncate + server mirror) |
| ADR-N-02 | Threshold for signal confidence to include in insight evidence: 0.6 or 0.7?                                     | **Decided** — [ADR-N-02](../adr/ADR-N-02-signal-confidence-threshold.md) (0.70)                         |
| ADR-N-03 | Should custom markers be normalised (lowercased, deduplicated) server-side, or stored verbatim?                 | **Decided** — [ADR-N-03](../adr/ADR-N-03-custom-marker-normalisation.md) (normalise on write)           |

---

## Related Documents

- [`docs/DESIGN_DOCUMENT.md`](../DESIGN_DOCUMENT.md) — Architecture, tech stack, roadmap
- [`docs/adr/`](../adr/) — Architecture Decision Records

---

## Related Issues

| Issue                                               | Scope        | Phase                        |
| --------------------------------------------------- | ------------ | ---------------------------- |
| Epic: Notes in Analysis — Retrofit after M3         | Coordination | All                          |
| Backend: entry model + API extension                | Backend      | M1 retroactive               |
| Frontend: note visibility in timeline and drilldown | Frontend     | M2 retroactive               |
| Backend/Frontend: manual markers                    | Full-stack   | M3 retroactive               |
| Insights: marker-aware evidence statements          | Backend      | M3 retroactive               |
| Architecture: ADR-N-01, ADR-N-02, ADR-N-03          | Architecture | Before respective milestones |
| Signal extraction and Insights v2 (foundation)      | Backend      | Shipped (#201/#202)          |
