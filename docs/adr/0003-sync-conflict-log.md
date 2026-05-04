# ADR-0003: Sync-Protokoll: Conflict-Log statt stilles LWW

**Datum:** 2026-04-20
**Status:** Accepted

---

## Kontext

- **Aktueller Ansatz:** Last-Write-Wins (LWW) pro Feld mit `updated_at`-Timestamp. Bei einem Sync-Konflikt gewinnt der Schreibvorgang mit dem neueren Timestamp, der ältere Wert wird verworfen.
- **Problem:** Bei Multi-Device-Nutzung (z. B. Stimmungseintrag auf Handy editieren, gleichzeitig auf Desktop editieren) können Daten **still überschrieben** werden, ohne dass der User es bemerkt.
- **Kritische Felder:** `mood_score`, `notes`, `symptoms` – einmal überschrieben gibt es ohne Konflikt-Log keine Möglichkeit zur Wiederherstellung oder Nachvollziehbarkeit.
- **LWW** ist für die meisten Felder das korrekte und performante Merge-Prinzip; das Problem ist die fehlende Transparenz, nicht das Merge-Verhalten selbst.
- **CRDT** (Conflict-free Replicated Data Types) wäre eine Alternative, bringt jedoch erheblichen Framework-Overhead und Lock-in für einen Use-Case, bei dem Konflikte selten sind (Mood-App, kein kollaborativer Editor).

---

## Entscheidung

**LWW bleibt das Merge-Prinzip.** Zusätzlich werden alle Felder, bei denen ein Konflikt auftritt (d. h. `client_ts` und `server_ts` unterscheiden sich bei gleichem Feld), in einer dedizierten `sync_conflicts`-Tabelle geloggt.

### Datenbankschema

```sql
CREATE TABLE sync_conflicts (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  entity_id    UUID NOT NULL,
  entity_type  TEXT NOT NULL CHECK (entity_type IN ('entry','tag','habit')),
  field_name   TEXT NOT NULL,
  client_value JSONB,
  server_value JSONB,
  client_ts    TIMESTAMPTZ NOT NULL,
  server_ts    TIMESTAMPTZ NOT NULL,
  resolved_at  TIMESTAMPTZ,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON sync_conflicts (user_id, created_at);
CREATE INDEX ON sync_conflicts (entity_id);
```

---

## Alternativen erwogen

| Option                          | Vorteile                                                                                         | Nachteile                                                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| **Stilles LWW (Status quo)**    | Kein zusätzlicher Storage, maximale Einfachheit                                                  | Datenverlust ohne jede Transparenz, keine Recovery möglich, schlechtes UX bei Multi-Device                              |
| **LWW + Conflict-Log** ✅       | Transparenz für User, Recovery möglich, kein Framework-Overhead, LWW-Performance bleibt erhalten | Minimaler Storage-Overhead, Bereinigungsjob nötig                                                                       |
| **CRDT (z. B. Automerge, Yjs)** | Automatisches, verlustfreies Merging auch für komplexe Datenstrukturen                           | Hoher Implementierungsaufwand, Framework-Lock-in, Overhead für seltene Konflikte in einer Mood-App nicht gerechtfertigt |
| **Operational Transform (OT)**  | Bewährt für kollaborative Editoren                                                               | Sehr hohe Komplexität, für strukturierte Mood-Daten (einzelne Felder) überdimensioniert                                 |

---

## Konsequenzen

- **User-sichtbar:** In „Einstellungen > Sync-Verlauf" können Konflikte eingesehen werden (welches Gerät hat welchen Wert geschrieben, wann, was wurde behalten).
- **Automatische Bereinigung:** Einträge in `sync_conflicts` werden nach **90 Tagen** via Worker-Job (APScheduler) gelöscht.
- **Storage-Overhead:** Minimal – ca. 1–2 KB pro Konflikt-Eintrag (JSONB-Werte für Mood-Felder sind klein). Bei 100 Konflikten/User/Monat ≈ 200 KB/User/Monat, deutlich unter 1 MB.
- **Kein CRDT-Overhead:** Das System bleibt framework-unabhängig und skaliert linear.
- **Zukunftspfad:** Ab M8 können Felder mit häufigen Konflikten (z. B. `notes`) selektiv auf CRDT (Automerge) migriert werden, ohne die übrige Sync-Architektur zu berühren.

---

## Umsetzung

| Meilenstein | Aufgabe                                                                               |
| ----------- | ------------------------------------------------------------------------------------- |
| **M0 / M1** | `sync_conflicts`-Tabelle anlegen (Alembic-Migration), Indices erstellen               |
| **M1**      | Sync-Endpunkt (`POST /sync`) schreibt Konflikte bei LWW-Entscheidungen in die Tabelle |
| **M2**      | Admin-UI: Read-only-View der Konflikte im Admin-Panel (für Debugging und Support)     |
| **M4+**     | User-facing „Sync-Verlauf"-Seite in den Einstellungen                                 |
