# ADR-N-02: Signal Confidence Threshold for Insight Inclusion

**Datum:** 2026-07-15  
**Status:** Accepted  
**Bezug:** [#199](https://github.com/Sturmi77/correlcore/issues/199) · [#201](https://github.com/Sturmi77/correlcore/issues/201) · [`docs/features/notes-in-analysis.md`](../features/notes-in-analysis.md)

## Kontext

Derived note signals carry a `confidence` score (0.0–1.0). Marker/signal evidence on
insight cards must not surface low-quality matches as “findings”.

## Optionen

- **0.60** — more coverage, more false positives
- **0.70** — higher precision, fewer signals

## Entscheidung

**Minimum confidence = 0.70** for inclusion in insight evidence blocks and
signal-correlation analytics.

Dictionary-layer hits (confidence 0.90) and strong regex hits (≥ 0.70) qualify.
Weaker regex / future LLM candidates below 0.70 may still be stored for operator
debugging but are excluded from user-facing evidence.

Configurable via `settings.NOTE_SIGNAL_MIN_CONFIDENCE` (default `0.70`).

## Konsequenzen

- `NoteSignalExtractor` tags every signal with `extractor_v` and `confidence`.
- Insight workers filter `confidence >= NOTE_SIGNAL_MIN_CONFIDENCE`.
- Soft “add notes” prompts remain thresholded separately on `sample_size >= 20`.
