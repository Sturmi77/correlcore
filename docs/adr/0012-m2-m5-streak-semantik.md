# ADR-0012: Abgrenzung der Streak-Semantik zwischen M2 und M5 + Schema-Vorgriff für Habit-Felder

**Datum:** 2026-05-08
**Status:** Accepted
**Geplante Umsetzung:** Schema-Vorgriff in M2 (Migration), volle Habit-Funktionalität in M5

---

## M5 Update 2026-05-28

Der urspruengliche Habit-Streak-Teil dieser ADR ist durch den
No-Gamification-Promise ersetzt. M5 implementiert keine Habit-Streaks, keine
Badges und keine Punkte. Die kanonische Habit-Metrik ist **Adherence Rate**:
`build` misst Fortschritt zum Wochenziel, `reduce` misst neutral, ob die
Haeufigkeit im Zielbereich bleibt. Die bestehenden Spalten `tags.habit_type` und
`tags.target_frequency` bleiben die Grundlage; API/UI werden in M5 aktiviert.

---

## Kontext

Beim Review der M1-Doku im Vorfeld des Milestone-Reviews wurde aufgefallen, dass der Roadmap-Block in `docs/DESIGN_DOCUMENT.md` zwischen M2 (Visualisierung) und M5 (Habits & Ziele) unsauber abgegrenzt ist:

- **M2 — Visualisierung (Woche 6–7)** enthält bereits:
  - „Tag-Frequenz-Heatmap"
  - „Streak-Widgets"
  - Akzeptanzkriterium: „Streak-Berechnung korrekt bei fehlenden Tagen"
- **M5 — Habits & Ziele (Woche 13–14)** enthält erneut:
  - „Streak-Logik, Erfolgs-Badges"
  - „Habit-Dashboard"
  - Akzeptanzkriterium: „Streak-Reset-Logik korrekt bei fehlendem Tag vs. bewusstem Aussetzen"
  - Akzeptanzkriterium: „Zielfrequenz konfigurierbar (täglich / x-mal pro Woche)"

Beide Milestones beanspruchen das Wort „Streak", aber meinen unterschiedliche Dinge. Das DESIGN_DOCUMENT §2.3 löst den Konflikt nur halb auf:

> „Habit ≠ Tag: Habits brauchen Ziele („5×/Woche Sport") und Streaks, Tags nur Ja/Nein. […] **Entscheidung:** Tag kann Flag `habit_type: none|build|reduce` + `target_frequency` haben. Streak-Logik separat."

Aus dieser Stelle geht nicht klar hervor, **welche Streak-Variante in M2 und welche in M5** gehört. Zusätzlich fehlt das Schema (`habit_type`, `target_frequency`) auf der `tags`-Tabelle bisher vollständig — Migration `004_create_tags.py` enthält weder die Spalten noch CHECK-Constraints. Wenn M2 eine Heatmap baut, die später für Habits ausgewertet werden soll, müssten die Daten rückwirkend über ein Schema-Upgrade laufen.

### Konkrete Risiken ohne Klarstellung

1. **Doppel-Implementierung:** M2 baut Streaks naiv über alle Tags, M5 muss sie als „nicht zielbezogen" wegwerfen oder doppelt zeigen.
2. **Daten-Backfill nötig:** Wenn `habit_type` erst in M5 hinzukommt, müssen alle bis dahin angelegten Tags ein Default zugewiesen bekommen — kein Drama, aber vermeidbarer Migrations-Aufwand mit Live-Daten.
3. **UI-Konsistenz:** Nutzer könnten in M2 ein „Streak"-Widget sehen, dessen Semantik in M5 schweigend wechselt (vorher: aktivste Tags; nachher: Ziele erreicht).

## Entscheidung

### Teil 1 — Klare Streak-Semantik

**M2 liefert ausschließlich „aktivitäts-basierte" Visualisierungen, die keinerlei Habit-Semantik kennen:**

| M2-Komponente        | Was sie zählt                                                                                  | Datenquelle                            |
| -------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------- |
| Eintrags-Streak      | Aufeinanderfolgende Tage mit mindestens einem `entries`-Datensatz für den User                 | `entries.entry_date`                   |
| Tag-Frequenz-Heatmap | Häufigkeit jedes Tags pro Tag/Woche (alle `entry_tags`-Vorkommen, unabhängig von `habit_type`) | `entry_tags` JOIN `entries.entry_date` |

**Begriffliche Schärfung:** Das Akzeptanzkriterium in M2 lautet künftig „**Eintrags-Streak**-Berechnung korrekt bei fehlenden Tagen" (statt nur „Streak-Berechnung"). Der Begriff „Habit-Streak" ist M5 vorbehalten.

**M5 liefert die ziel- und habit-bezogenen Visualisierungen:**

| M5-Komponente         | Was sie zählt                                                                                                                     | Datenquelle                                                |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Habit-Streak (build)  | Aufeinanderfolgende Perioden, in denen `target_frequency` für einen Tag mit `habit_type='build'` erreicht wurde                   | `entry_tags` + `tags.habit_type` + `tags.target_frequency` |
| Habit-Streak (reduce) | Aufeinanderfolgende Perioden, in denen ein Tag mit `habit_type='reduce'` höchstens `target_frequency`-mal vorkam (oder gar nicht) | dito                                                       |
| Habit-Dashboard       | Aggregierte Build-/Reduce-Erfolgsquoten, Erfolgs-Badges                                                                           | dito                                                       |

**Konsequenz für M5-Akzeptanzkriterien:** Das bestehende Kriterium „Streak-Reset-Logik korrekt bei fehlendem Tag vs. bewusstem Aussetzen" bleibt M5, bezieht sich aber explizit auf Habit-Streaks. Eintrags-Streaks aus M2 sind davon nicht betroffen.

### Teil 2 — Schema-Vorgriff in M2

Die Tabelle `tags` bekommt im Rahmen von M2 (vor oder zusammen mit der Heatmap-Implementierung) zwei nullable Spalten:

```python
sa.Column(
    "habit_type",
    sa.String(length=8),
    nullable=False,
    server_default=sa.text("'none'"),
),
sa.Column(
    "target_frequency",
    sa.Integer(),
    nullable=True,
),
```

Plus CHECK-Constraints:

```sql
CHECK (habit_type IN ('none', 'build', 'reduce'))
CHECK (
  (habit_type = 'none' AND target_frequency IS NULL)
  OR (habit_type IN ('build', 'reduce') AND target_frequency BETWEEN 1 AND 7)
)
```

`target_frequency` interpretiert sich initial als „mal pro Woche" (siehe DESIGN_DOCUMENT §2.3 mit Beispiel „5×/Woche Sport"). Eine spätere Erweiterung auf andere Perioden (täglich/monatlich) erfordert ein zusätzliches `target_period`-Feld und wäre ein eigenes ADR.

**Wichtig:** Das Schema kommt in M2, die **API**, **UI** und **Streak-Logik** kommen erst in M5. Bestehende `tags`-Endpoints (`POST/PATCH /tags`) ignorieren die neuen Felder zunächst (Server-Default = `'none'`, kein Pflichtfeld in Pydantic-Schemas). Die Felder werden erst in M5 in Pydantic-Modelle und CRUD-Endpoints aufgenommen.

### Teil 3 — Doku-Updates parallel zu diesem ADR

Mit Annahme dieses ADRs werden im selben PR-Kontext aktualisiert:

1. `docs/DESIGN_DOCUMENT.md`:
   - §2.3 erhält einen Verweis auf ADR-0012 für die Streak-Abgrenzung.
   - M2-Akzeptanzkriterium „Streak-Berechnung" wird zu „**Eintrags-Streak**-Berechnung".
   - M5-Akzeptanzkriterium „Streak-Reset-Logik" erhält den Zusatz „(Habit-Streak, siehe ADR-0012)".
2. `docs/ARCHITECTURE.md`: Erwähnung der neuen `tags`-Spalten im ER-Diagramm-Kommentar (sofern dort die Tag-Tabelle dokumentiert ist).
3. `docs/adr/README.md`: Index-Eintrag + Kurzübersicht.

## Alternativen

### A — Status quo belassen (verworfen)

Streak bleibt zwischen M2 und M5 mehrdeutig, Schema kommt erst in M5. Risiken siehe oben (Doppel-Implementierung, Daten-Backfill, UI-Inkonsistenz). Würde M5 zu einer harten Schema-Migration mit Daten-Touch zwingen.

### B — Habit-Funktionalität nach M2 vorziehen (verworfen)

Volle M5-Funktion (UI, Service, Streak-Logik, Dashboard) zusammen mit M2 ausliefern. Verletzt die Roadmap-Phasierung, M2 ist mit Zeitreihe + Heatmap + Streak + Export bereits ambitioniert. Zudem braucht M5 nicht nur Schema, sondern auch UX-Entscheidungen (Onboarding-Flow für Ziele, Build-/Reduce-Wording-Tests), die in M2-Scope nicht enthalten sind.

### C — Zwei separate Streak-Tabellen (verworfen)

Eine `entry_streaks`-Materialized-View für M2 und eine `habit_streaks` für M5. Architektonisch sauber, aber operativer Overkill: Eintrags-Streaks lassen sich aus `entries.entry_date` mit einem Window-Query in <50 ms berechnen, Caching/Materialization erst nötig, wenn das User-Volumen es rechtfertigt. Wird als Backlog-Item für M9+ (Performance-Hardening) notiert, falls Insights-Queries unter Last langsam werden.

### D — Gewählt: Semantik-Trennung + Schema-Vorgriff

Klare Begriffstrennung im Design-Doc, Schema landet in M2 (nullable, default `'none'`), API/UI in M5. Vorteile:

- Kein Daten-Backfill in M5 nötig — neue Tags werden ab M2 mit `habit_type='none'` angelegt, M5 kann sie inkrementell auf `'build'`/`'reduce'` umflaggen.
- M2-Visualisierungen sind eindeutig „aktivitätsorientiert", keine UX-Verwirrung beim Übergang nach M5.
- Schema-Migration ist klein und ohne Risiko (zwei nullable Spalten + CHECKs, kein Datenfluss).
- M5 wird zu reiner Frontend-/Service-Lieferung, einfacher zu reviewen und zu testen.

## Konsequenzen

### Positiv

- **Klare Roadmap-Trennung:** Reviewer und zukünftige Mitwirkende verstehen sofort, wo welche Streak-Variante hingehört.
- **Keine Migration mit Live-Daten in M5:** Der Schema-Vorgriff ist defensiv ausgelegt (nullable, default).
- **API-stabilität:** Die `/tags`-Endpoints ändern sich in M2 nicht; M5 erweitert nur additiv.
- **Operative Sicherheit:** CHECK-Constraints verhindern Inkonsistenzen (z. B. `habit_type='build'` ohne `target_frequency`).

### Negativ / Aufzunehmen

- **Mini-Mehraufwand in M2:** Eine Migration extra (~30 Zeilen Alembic + Test). Unter 1 PR-Nachmittag.
- **Risiko „toter Spalten":** Falls Habits in M5 doch nicht so umgesetzt werden, sind zwei ungenutzte Spalten in der Tabelle. Mitigation: ADR-Status auf `Accepted` erst nach M5-Kickoff setzen, vorher bleibt er `Vorgeschlagen`. Bei Re-Scope kann der Vorgriff in M5 noch zurückgerollt werden.
- **Begriffsschärfung muss durchgehalten werden:** „Eintrags-Streak" und „Habit-Streak" werden zur kanonischen Terminologie. Reviewer sollten in PRs auf Inkonsistenzen achten.

### Offen / Folge-Entscheidungen

- **`target_period`-Erweiterung:** Falls in M5 oder später Tages-/Monatsziele gewünscht sind, neuer ADR.
- **„Bewusstes Aussetzen" (Pause-Modus):** M5-Akzeptanzkriterium nennt „Streak-Reset bei fehlendem Tag vs. bewusstem Aussetzen". Die UX dafür ist nicht in diesem ADR. Vorgeschlagen wird ein UI-Toggle pro Habit („Pause heute"), der einen Eintrag in einer separaten `habit_pauses`-Tabelle erzeugt — Detail-Spec in M5.
- **Verschlüsselung:** `habit_type` und `target_frequency` sind nicht-personenbezogene Konfigurationswerte und bleiben plaintext (analog `tags.slug`). DSGVO-Checkpoint M5 (Verschlüsselung Habit-Daten) bezieht sich auf die User-erstellten Tag-**Namen**, die bereits über `tags`-Verschlüsselung in M1 abgedeckt sind, sofern Custom-Tags ebenfalls verschlüsselt werden. Falls Tag-Namen aktuell noch plaintext gespeichert sind (im Gegensatz zu `symptoms.name_enc`), wäre das ein eigener Issue für M5 — aber außerhalb des Scopes dieses ADRs.

## Referenzen

- `docs/DESIGN_DOCUMENT.md` §2.3 (Good/Bad Habits) und Roadmap-Blöcke M2 / M5
- ADR-0008 (Symptom-Master-Tabelle) — analoges Schema-Muster für `tags`-Erweiterung
- Issue #11 (Mood-Zeitreihe), #12 (Tag-Frequenz-Heatmap), #13 (Streak-Widgets) — M2-Backlog
- M5-Issues bisher nicht angelegt — werden mit M5-Kickoff aus diesem ADR abgeleitet
