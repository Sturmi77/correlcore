# ADR-0013 — Auto-Save für Day-Entries (M1.5)

**Status:** Akzeptiert
**Datum:** 2026-05-09
**Bezug:** Issue #117 (Tagesansicht-Hydration), ADR-0009 (Offline-Sync nach M4), DESIGN_DOCUMENT.md §3 M1

## Kontext

Die Tagesansicht (`/entries/new`) hat nach PR #117 zwei Modi:

- **Neuer Tag:** POST über `submitEntry` → erstellt `Entry`, anschließend Tag-/Symptom-Replace-Sets
- **Bestehender Tag:** PATCH über `updateEntry` (Loader hydratisiert das Formular aus dem bestehenden Eintrag)

Der Submit-Flow ist aktuell **manuell**: ein „Speichern"/„Aktualisieren"-Button löst den Save aus. Aus dem produktiven Test (2026-05-09) kam die Frage, ob ein Speichern-Button im Tagebuch-Workflow überhaupt nötig ist — vergleichbare Apps (Day One, Daylio, Reflectly) speichern Eingaben automatisch und zeigen nur einen Status („Gespeichert um 14:32").

Argumente für Auto-Save:

- Tagebuch-Pattern auf Mobile: kein „vergessen zu speichern" mehr
- Matcht den `existingEntryId`-Flip (POST→PATCH) den wir bereits etabliert haben
- Reduziert kognitive Last (kein Submit-Moment, kein Bestätigen-Dialog)

Argumente gegen reinen Auto-Save:

- Keine klare „fertig"-Bestätigung
- Validierungsfehler überraschen den User
- Race-Conditions bei parallelen Edits in mehreren Tabs

Der **Hybrid-Ansatz** (Auto-Save mit sichtbarer Status-Anzeige, kein Button) löst beide Seiten: das System speichert automatisch, der User sieht jederzeit den Save-State.

## Entscheidung

**Hybrid Auto-Save mit State-Machine und sichtbarem Status.**

### State-Machine

```
       field-change
idle ──────────────▶ dirty
                       │
                       │ debounce 800 ms
                       ▼
                    saving
                    │     │
              success     fail
                    │     │
                    ▼     ▼
                 saved   error
                    │     │
        field-change│     │ retry / field-change
                    └─▶ dirty
```

- **`idle`** — Initial-Zustand nach Hydration. Kein Status-Badge sichtbar.
- **`dirty`** — Eine Eingabe wurde geändert, Save-Timer läuft. Badge: „Wird in Kürze gespeichert…".
- **`saving`** — Request läuft. Badge: „Wird gespeichert…", `aria-busy="true"` auf Form.
- **`saved`** — Request erfolgreich. Badge: „Gespeichert um HH:MM" (5 s sichtbar, dann zurück zu `idle`).
- **`error`** — Request gescheitert. Badge: „Fehler beim Speichern. Erneut versuchen?", manueller Retry-Button erscheint einmalig.

### Trigger-Punkte

Auto-Save löst aus bei jeder semantischen Änderung im Formular:

- Slider (Mood, Energy, Stress) → on-change
- Notes-Textfeld → on-input mit zusätzlichem 800 ms-Debounce
- Tags toggle → sofort dirty, debounced save
- Symptome toggle / Intensität → sofort dirty, debounced save
- Work-Context → on-change
- Datumswechsel → **kein Auto-Save**, stattdessen Hydration des neuen Tages (siehe PR #117)

### Debounce-Window

**800 ms** nach letzter Änderung. Begründung:

- 200–300 ms wäre für Slider-Drag zu aggressiv (jeder Tick → Request)
- 1500 ms+ fühlt sich träge an, und der User verliert das Gefühl dass etwas passiert
- 800 ms ist Industrie-Standard (Notion, Linear, Figma)

Slider werden zusätzlich mit `requestIdleCallback` koalesziert: Drag-End triggert sofort `dirty`, aber der Save-Timer startet erst nach Loslassen.

### POST → PATCH-Flip

Erste Save-Operation eines Tages bleibt POST über `submitEntry`. Sobald `existingEntryId` gesetzt ist, wechselt der Save-Pfad permanent auf PATCH `updateEntry` (idempotent, Replace-Set für Tags/Symptome).

Race-Schutz: zwei parallele POSTs für denselben Tag würden den `409 entry_exists`-Fehler triggern, den der Backend-`UNIQUE(user_id, entry_date)`-Constraint erzwingt. Wir blocken überlappende Saves clientseitig: während `saving` werden weitere `dirty`-Trigger gepuffert; sobald der laufende Save zurückkommt, startet der nächste Save automatisch (re-flush), aber nur wenn das Formular weiterhin `dirty` ist.

### Konfliktauflösung

**Last-Write-Wins (LWW)** — analog zu ADR-0003. Konsequenz aus M1-Scope (Single-Device-Browser): zwei parallele Tabs sind möglich, aber selten. LWW ist semantisch korrekt; das `sync_conflicts`-Log aus ADR-0003 deckt erst den Multi-Device-Sync ab M4 ab.

### Offline-Verhalten

**Online-Only im aktuellen Scope.** Konsequenz aus ADR-0009 (Offline-Sync nach M4):

- Bei Netzwerk-Fehler bleibt das Formular im `error`-Zustand
- Eingaben gehen **nicht** in `localStorage` oder IndexedDB (würde ADR-0009-Scope vorgreifen)
- Status-Badge zeigt deutsch „Keine Verbindung — Eingaben werden nicht gespeichert"
- Der User entscheidet selbst, wann er retry drückt oder wartet
- **Wichtig:** Bei `error`-State bleiben die Form-Felder editierbar, der `dirty`-Counter läuft weiter — sobald der Retry erfolgreich ist, wird der finale Stand gespeichert

Offline-Buffering wird mit M4 (ADR-0009) nachgereicht; die Auto-Save-State-Machine ist so designt, dass sie offline-fähig erweitert werden kann (`saved` → `synced`, neuer Zustand `pending-sync`).

### UI-Konsequenzen

- **Submit-Button entfernt.** Der bisherige „Speichern"/„Aktualisieren"-Button verschwindet aus `routes/entries/new/+page.svelte`.
- **Cancel-Button bleibt** (führt zurück auf `/`, verwirft keine Daten — auto-save speichert ja).
- **Status-Badge** rechts neben der Page-Headline, `aria-live="polite"` für Screenreader.
- **Beim Verlassen ungespeicherter Daten** (`dirty` oder `saving`): `beforeunload`-Listener warnt mit Browser-Native-Dialog.

### Aufwand & Tests

- ~120 Zeilen TS in `routes/entries/new/+page.svelte` (State-Machine + Debounce + Watcher)
- 5–7 neue Vitest-Tests:
  - Debounce-Window respektiert
  - POST→PATCH-Flip nach erstem Save
  - Konkurrierender Save während `saving` wird korrekt re-flushed
  - Fehlerpfad zeigt Retry-Button
  - Datumswechsel triggert kein Save (nur Hydration)
- Integration-Test (Vitest mit msw): Slider-Drag löst genau einen Save aus, nicht einen pro Tick

## Konsequenzen

### Positiv

- Mobil-natives Tagebuch-Erlebnis
- 409-Fehler aus PR #117 sind komplett ausgeschlossen (Auto-Save flippt automatisch auf PATCH)
- Weniger UI-Elemente, klarere Visual-Hierarchie auf der Tagesansicht
- State-Machine bereitet ADR-0009 (Offline-Sync) sauber vor

### Negativ / Trade-offs

- Mehr Backend-Last: jeder Slider-Drag löst einen Save aus (mitigiert durch 800 ms-Debounce; Tag mit 5 Slidern × 3 Edits = ~15 Saves vs. heute 1)
- Bei flakey Netzwerk fühlen sich Save-Errors häufiger an
- `beforeunload`-Dialog ist UX-Krücke, aber notwendig für Edge-Cases (Tab-Close während `saving`)

### Abgrenzung zu anderen ADRs

- **ADR-0003 (Sync-Conflict-Log):** Auto-Save ist Single-Device, kein Konflikt-Trigger. Conflict-Log greift erst bei Multi-Device-Sync (M4).
- **ADR-0009 (Offline-Sync nach M4):** Auto-Save bleibt online-only; localStorage-Buffer ist explizit out-of-scope. Die State-Machine ist offline-fähig erweiterbar.
- **ADR-0006 (Cookie-Auth):** unverändert, Auto-Save nutzt denselben `apiFetch`-Pfad wie der bisherige Submit.

## Status-Übergang

`Vorgeschlagen` → `Akzeptiert` mit Implementierung in PR „feat(web): auto-save day entry“ (M1.5).
