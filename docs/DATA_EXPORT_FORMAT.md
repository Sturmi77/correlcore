# MoodSync Data Export Format

MoodSync M2 exposes three self-service export downloads:

- `GET /api/v1/user/export` returns `moodsync-export-YYYY-MM-DD.zip`
- `GET /api/v1/export/json` returns `moodsync-export-YYYY-MM-DD.json`
- `GET /api/v1/export/csv` returns `moodsync-export-YYYY-MM-DD.csv`

The ZIP export is the canonical DSGVO Art. 20 portability export. It contains:

- `export.json` with the complete machine-readable payload.
- `README.txt` with a short sensitivity and format note.

## JSON Shape

```json
{
  "export_date": "2026-05-09T14:00:00Z",
  "moodsync_version": "0.0.1",
  "format_version": "1.0",
  "user": {
    "email": "user@example.test",
    "display_name": "User",
    "created_at": "2026-05-01T08:00:00Z"
  },
  "entries": [
    {
      "date": "2026-05-09",
      "slot": "day",
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
  "insights": [],
  "photos": [],
  "sleep": []
}
```

Internal database IDs and `user_id` values are intentionally omitted. Future
domains that do not exist yet are represented as empty arrays so importers can
depend on a stable top-level shape.

## CSV Shape

CSV is a flat entry table for spreadsheet and doctor-visit workflows. It
contains:

`date, slot, mood_score, energy, stress, work_context, note, tags, symptoms, created_at, updated_at`

Tags are comma-separated names. Symptoms are comma-separated `name:intensity`
pairs. The CSV is encoded as UTF-8 with BOM for spreadsheet compatibility.
