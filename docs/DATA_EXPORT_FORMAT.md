# CorrelCore Data Export Format

CorrelCore M2 exposes three self-service export downloads:

- `GET /api/v1/user/export` returns `correlcore-export-YYYY-MM-DD.zip`
- `GET /api/v1/export/json` returns `correlcore-export-YYYY-MM-DD.json`
- `GET /api/v1/export/csv` returns `correlcore-export-YYYY-MM-DD.csv`

The ZIP export is the canonical DSGVO Art. 20 portability export. It contains:

- `export.json` with the complete machine-readable payload.
- `README.txt` with a short sensitivity and format note.

## JSON Shape

```json
{
  "export_date": "2026-05-09T14:00:00Z",
  "app_version": "0.0.1",
  "format_version": "1.3",
  "score_legend": {
    "mood_score": {
      "min": 1,
      "max": 5,
      "min_label": "very bad",
      "max_label": "very good"
    },
    "energy": {
      "min": 1,
      "max": 5,
      "min_label": "drained",
      "max_label": "full of energy"
    },
    "stress": {
      "min": 1,
      "max": 5,
      "min_label": "relaxed",
      "max_label": "very stressed"
    }
  },
  "user": {
    "email": "user@example.test",
    "display_name": "User",
    "created_at": "2026-05-01T08:00:00Z"
  },
  "entries": [
    {
      "date": "2026-05-09",
      "slot": "day",
      "source": "direct",
      "cycle_day": 12,
      "mood_score": 4,
      "energy": 3,
      "stress": 2,
      "work_context": "homeoffice",
      "note": "Plaintext note after per-user DEK decryption",
      "created_at": "2026-05-09T08:00:00Z",
      "updated_at": "2026-05-09T08:30:00Z",
      "tags": [
        {
          "slug": "sport",
          "name": "Sport",
          "category": "sport",
          "color": "#10b981",
          "is_default": true
        }
      ],
      "symptoms": [
        {
          "slug": "headache",
          "name": "Kopfschmerzen",
          "icon": "🤕",
          "is_default": true,
          "intensity": 2
        }
      ]
    }
  ],
  "tags": [],
  "symptoms": [],
  "habits": [],
  "insights": [
    {
      "insight_type": "spearman",
      "tier": "developing",
      "metric": "mood_score",
      "subject_type": "metric",
      "subject_label": "energy",
      "subject_key": "{\"insight_type\":\"spearman\",\"metric\":\"mood_score\",\"subject\":\"energy\",\"subject_type\":\"metric\"}",
      "effect_size": 0.4,
      "confidence": 0.7,
      "sample_n": 20,
      "statement": "Mood lines up with energy.",
      "flags": {},
      "payload": {},
      "visibility": "active",
      "generated_for_date": "2026-05-14",
      "generated_at": "2026-05-14T00:00:00Z",
      "created_at": "2026-05-14T00:00:00Z",
      "updated_at": "2026-05-14T00:00:00Z"
    }
  ],
  "insight_dismissals": [
    {
      "subject_key": "{\"insight_type\":\"spearman\",\"metric\":\"mood_score\",\"subject\":\"energy\",\"subject_type\":\"metric\"}",
      "dismissed_at": "2026-05-15T12:00:00Z",
      "created_at": "2026-05-15T12:00:00Z"
    }
  ],
  "photos": [],
  "sleep": [
    {
      "date": "2026-05-14",
      "slot": "day",
      "sleep_minutes": 450,
      "sleep_quality": 3,
      "source": "direct"
    }
  ]
}
```

Since format `1.4` (M8 Sprint 1), each entry also carries `sleep_minutes`
(0..1440) and `sleep_quality` (1..5); the top-level `sleep` array is a
per-day projection of those values for entries that recorded sleep.

Internal database IDs and `user_id` values are intentionally omitted. Tags in
the export may include `habit_type` (`none`, `build`, `reduce`) and
`target_frequency` (1..7) when configured. The top-level `habits` array is
reserved for a future dedicated habit export section and is currently empty.

`insights` contains the full insight history for the account (not feed-filtered),
including decrypted statements and a `visibility` of `active` or `dismissed`.
`insight_dismissals` lists subject-stable hide intents (#601). The `photos`
array stays empty until M13 photo/media support ships. Other future domains
that do not exist yet are represented as empty arrays so importers can depend
on a stable top-level shape.

## CSV Shape

CSV is a flat entry table for spreadsheet and doctor-visit workflows. It
contains:

`date, slot, source, cycle_day, mood_score, energy, stress, mood_scale, energy_scale, stress_scale, work_context, note, tags, symptoms, created_at, updated_at`

Tags are comma-separated names. Symptoms are comma-separated `name:intensity`
pairs. The `*_scale` columns repeat the 1..5 endpoint meaning per row so the
spreadsheet remains self-describing when separated from the JSON export. The CSV
is encoded as UTF-8 with BOM for spreadsheet compatibility.
