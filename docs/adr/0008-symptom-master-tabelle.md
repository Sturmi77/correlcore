# ADR-0008: Symptom-Master-Tabelle für Custom-Symptome

**Datum:** 2026-05-04
**Status:** Accepted

---

## Kontext

In Issue #9 (PR #56) wurde die Symptom-Checkliste bewusst minimal als **Single-Table-Design** umgesetzt: Die Tabelle `entry_symptoms` enthielt einen String-Spalte `symptom_key`, validiert über eine `CHECK`-Constraint mit einem geschlossenen Set von fünf Standard-Keys (`headache`, `digestion`, `back_pain`, `fatigue`, `cold`). Es gab keine Master-Tabelle für Symptome.

Diese Entscheidung war für den M1-Scope korrekt — sie minimierte Komplexität, RLS-Policies und Migrations-Aufwand. Das DESIGN*DOCUMENT.md (§2.2) und die ursprüngliche Akzeptanzbasis von Issue #9 sahen bewusst \_kein* Custom-Symptom-Feature vor.

**Gegenüber dem Tag-System** (Issue #8 / PR #55) ist das eine Asymmetrie: Tags haben bereits eine Master-Tabelle `tags` mit Owner-Trennung (`user_id NULL = curated`, `is_default=TRUE`), Slug-Uniqueness via Partial-Indexes, RLS-Policies, und vollem CRUD-Endpoint-Set. Nutzer können beliebige Tags anlegen, bearbeiten, löschen.

Issue #57 fordert die gleiche Funktionalität für Symptome: User sollen eigene Symptome wie „Migräne mit Aura", „Tinnitus", „Knieschmerzen" anlegen können. Das ist mit dem Single-Table-Design nicht möglich, ohne entweder die `CHECK`-Constraint zu kippen (dann ist jeder beliebige String erlaubt, ohne Owner-Bindung) oder einen zweiten Validierungspfad in der Service-Schicht aufzubauen, der praktisch eine virtuelle Master-Tabelle simulieren würde.

---

## Entscheidung

Wir führen eine neue Tabelle **`symptoms`** ein, die strukturell `tags` spiegelt, und refactoren `entry_symptoms` so, dass sie diese referenziert.

### 1. Neue Tabelle `symptoms`

| Spalte                      | Typ                                         | Bemerkung                           |
| --------------------------- | ------------------------------------------- | ----------------------------------- |
| `id`                        | UUID PK                                     |                                     |
| `user_id`                   | UUID NULL FK → `users.id` ON DELETE CASCADE | NULL = curated/default              |
| `slug`                      | String(64) NOT NULL                         | Slug-Uniqueness via Partial-Indexes |
| `name`                      | String(64) NOT NULL                         | Anzeigename, Art.-9-relevant        |
| `icon`                      | String(32) NULL                             | Emoji oder Lucide-Icon-Name         |
| `is_default`                | Boolean NOT NULL                            | TRUE nur wenn `user_id IS NULL`     |
| `created_at` / `updated_at` | TIMESTAMPTZ                                 |                                     |

**Owner-Konsistenz:** `CHECK ((is_default = TRUE AND user_id IS NULL) OR (is_default = FALSE AND user_id IS NOT NULL))` — exakt wie bei `tags`.

**Slug-Uniqueness:** Zwei Partial-Indexes (analog `tags`):

- `WHERE is_default = TRUE` → globale Uniqueness für Defaults
- `WHERE user_id IS NOT NULL` → Uniqueness pro User

### 2. Refactor `entry_symptoms`

- Entfernung der Spalte `symptom_key` (String)
- Entfernung der CHECK-Constraint `ck_entry_symptoms_keys_allowed`
- Neue Spalte `symptom_id UUID NOT NULL FK → symptoms.id ON DELETE CASCADE`
- Unique-Constraint wandert von `(entry_id, symptom_key)` auf `(entry_id, symptom_id)`
- `CHECK intensity BETWEEN 0 AND 3` bleibt erhalten
- Daten-Migration (siehe Punkt 4) sorgt dafür, dass alle Bestandsdaten erhalten bleiben

### 3. RLS-Policies

Vier Policies analog `tags` (`SELECT`, `INSERT`, `UPDATE`, `DELETE`), Owner-Match über `user_id = current_setting('app.current_user_id')::uuid OR (is_default = TRUE AND TG_OP = 'SELECT')`. Defaults werden global gelesen, aber von keinem Nutzer geschrieben/gelöscht — Default-Pflege erfolgt ausschließlich über Migrationen.

`entry_symptoms` behält seine eigenen 4 RLS-Policies — die FK auf `symptoms` ändert daran nichts, weil `entry_symptoms.user_id` bereits denormalisiert ist.

### 4. Daten-Migration (Migration 006)

Heikel, weil der Schema-Wechsel String-Key → FK ist. Schritte in **einer Transaktion**:

1. `CREATE TABLE symptoms ...` (inkl. CHECK + Partial-Indexes + RLS)
2. `INSERT INTO symptoms (id, user_id, slug, name, icon, is_default, ...)` für die fünf Standard-Keys (`headache`, `digestion`, `back_pain`, `fatigue`, `cold`) mit deterministischen UUIDs (UUID5 mit `NAMESPACE_DNS` und Slug, damit Migration idempotent gegen Re-Runs ist).
3. `ALTER TABLE entry_symptoms ADD COLUMN symptom_id UUID NULL` (zunächst nullable)
4. `UPDATE entry_symptoms SET symptom_id = (SELECT id FROM symptoms WHERE slug = entry_symptoms.symptom_key AND is_default = TRUE)`
5. `ALTER TABLE entry_symptoms ALTER COLUMN symptom_id SET NOT NULL`
6. `ALTER TABLE entry_symptoms ADD CONSTRAINT fk_entry_symptoms_symptom_id FOREIGN KEY (symptom_id) REFERENCES symptoms(id) ON DELETE CASCADE`
7. `ALTER TABLE entry_symptoms DROP CONSTRAINT uq_entry_symptoms_entry_symptom`
8. `ALTER TABLE entry_symptoms ADD CONSTRAINT uq_entry_symptoms_entry_symptom UNIQUE (entry_id, symptom_id)`
9. `ALTER TABLE entry_symptoms DROP CONSTRAINT ck_entry_symptoms_keys_allowed` (falls in 005 als named constraint angelegt, sonst entfällt)
10. `ALTER TABLE entry_symptoms DROP COLUMN symptom_key`

**Downgrade:** Spiegelbildlich (Spalte zurück, Daten via JOIN auf `symptoms.slug` füllen, FK droppen, Tabelle droppen). Wird im Migrationsfile vollständig implementiert.

### 5. Limits

- `MAX_SYMPTOMS_PER_USER = 50` (analog `MAX_TAGS_PER_USER`)
- `MAX_SYMPTOMS_PER_ENTRY = 32` (unverändert aus #9)

### 6. Privacy / Logging

`symptom_service` darf — wie bisher — **niemals** `symptom_key`, `name` oder `intensity` loggen. Der bestehende statische Log-Scrubbing-Test (`test_log_scrubbing.py`) wird um Patterns erweitert, die auch auf das neue `name`-Feld in `symptom_service` und neuem CRUD-Endpoint matchen.

`symptom_service` darf `symptom_id`, `user_id`, `entry_id` und Aggregat-Counts loggen — das sind keine Art.-9-Daten.

### 7. Verschlüsselung at-rest

Aus ADR-0005 / Issue #26: Stufe 2 (App-Level Fernet) gilt für Felder, die freie Nutzer-Inhalte enthalten. Mit Custom-Symptomen wird `symptoms.name` ein solches Feld (User kann „Migräne nach Streit mit Vater" eintippen — das ist Art.-9). Daher:

- `symptoms.name` wird in M1 als **Plaintext** gespeichert (analog `entries.note` heute)
- Issue #26 wird so erweitert, dass auch `symptoms.name` mit Fernet verschlüsselt wird (Spalte `name_enc` ergänzen, `name` droppen)
- Die DSGVO-Checkliste in DESIGN_DOCUMENT.md Z.654 erhält einen weiteren Eintrag

---

## Konsequenzen

### Positiv

- Symmetrie zwischen Tags und Symptomen — gleiches Ownership-, Slug- und CRUD-Modell, gleiche RLS-Pattern, gleiche UI-Pattern. Reduziert kognitive Last für Entwickler und Nutzer.
- Custom-Symptome erfüllen die User-Anforderung aus Issue #57.
- Default-Symptome bleiben über Migrationen versionierbar — keine Doppelpflege zwischen Code und Datenbank.
- Service-Schicht wird **kleiner**, weil die String-Validierung gegen ein Python-Set entfällt — Postgres-FK übernimmt die Integrität.

### Negativ / Trade-offs

- Eine zusätzliche Tabelle plus FK-JOIN beim Lesen von `entry_symptoms` mit Symptom-Details (gemildert durch denormalisiertes `user_id` auf `entry_symptoms` — der Hot-Path bleibt RLS-effizient ohne JOIN).
- Migration 006 ist die erste Migration im Projekt, die produktive Daten transformiert (alle bisherigen Migrationen waren reine DDL). Erhöhte Sorgfaltspflicht: Idempotenz, Downgrade-Pfad, Test gegen seed-Daten.
- DSGVO-Aufwand wächst: Ein weiteres Art.-9-Feld muss in Issue #26 berücksichtigt werden.

### Neutral

- Die Konstante `STANDARD_SYMPTOM_KEYS` in `app/models/symptom.py` bleibt als Referenz für den Default-Seed bestehen, wird aber nicht mehr für Validierung benutzt.
- Endpoint `GET /symptoms/standard` aus PR #56 bleibt rückwärtskompatibel als Sub-View von `GET /symptoms` (gibt nur Defaults zurück) — Frontend-Code-Migration ist somit minimal-invasiv.

---

## Alternativen erwogen

### A) String-Key behalten, CHECK-Constraint kippen

User-Eingabe wandert direkt in `entry_symptoms.symptom_key`. Pro: keine Migration, keine neue Tabelle. Contra: Keine Owner-Trennung (User A sähe Symptom-Strings von User B als Histogram-Bucket-Kandidaten), keine Slug-Eindeutigkeit, kein zentrales Edit/Delete (Tippfehler-Korrektur unmöglich ohne Mass-Update über alle Entries), keine Defaults-Pflege per Migration. **Verworfen.**

### B) JSON-Spalte mit Custom-Symptom-Liste auf `users`

Pro: Keine neue Tabelle. Contra: Bricht das relationale Modell, RLS-Policies müssten JSON-Pfade prüfen, JOIN auf `entry_symptoms` würde zur Hauptlast. **Verworfen.**

### C) Tags und Symptome zu einer Tabelle vereinen

Symptome wären dann „Tags der Kategorie health". Pro: Eine Tabelle weniger. Contra: `intensity` (0–3) ist symptom-spezifisch und ergibt für Tags keinen Sinn, Frontend-UX ist fundamental anders (Multi-Select-Chips vs. Skala), und die DSGVO-Klassifizierung weicht ab (Tags sind nicht zwingend Art.-9, Symptome immer). **Verworfen.**

---

## Implementierung

- Issue: [#57](https://github.com/Sturmi77/moodsync/issues/57)
- Branch: `feature/57-custom-symptoms`
- Migration: `backend/migrations/versions/006_add_symptom_master_table.py`
- Models: `backend/app/models/symptom.py` (erweitert), neue `Symptom`-Klasse + refactorter `EntrySymptom`
- Tests: `backend/tests/test_symptoms.py` (erweitert), `backend/tests/test_log_scrubbing.py` (erweitert)
- Frontend: `apps/web/src/lib/components/entries/SymptomChecker.svelte` (Custom-Hinzufügen-Dialog), neuer Symptom-Manager unter `apps/web/src/routes/settings/symptoms`
