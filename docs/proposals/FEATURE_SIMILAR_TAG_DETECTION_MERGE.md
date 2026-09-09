# [FEATURE] Ähnliche Tags erkennen, aufzeigen und nach Freigabe zusammenführen

> Analyse- und Optionsdokument (kein finaler Umsetzungsplan).
> Labels: `enhancement`, `analysis`
> Milestone: Backlog / Tag-Lifecycle
> Status: **Vorgeschlagen** — Entscheidung offen (siehe [§10 Empfehlung](#10-empfehlung))

---

## 1. Feature-Beschreibung

Über die Zeit sammeln Nutzer semantisch überlappende Tags an, die dasselbe
meinen, aber unterschiedlich benannt sind — z. B. der Health-Tag **„krank"**
und ein eigener Tag **„Krankheitstag"**, oder **„Sport"** vs. **„Training"**,
**„Arbeit"** vs. **„Büro"**. Solche Dubletten:

- **verwässern die Statistik** — Co-Occurrence, Korrelationen und Cluster
  rechnen zwei Tags getrennt, obwohl es ein Signal ist. Effektstärke und
  Konfidenz sinken, weil sich die Datenpunkte aufteilen.
- **verwirren die Erfassung** — im [`TagPicker`](../../apps/web/src/lib/components/entries/TagPicker.svelte)
  stehen mehrere fast identische Chips; der Nutzer weiß nicht, welchen er
  „richtig" wählen soll, und die Aufteilung wird schlimmer.

Gewünscht sind **zwei** zusammenhängende Fähigkeiten:

1. **Retrospektive Erkennung + Merge:** Ähnlichkeiten unter bestehenden Tags
   erkennen, dem Nutzer **aufzeigen** und nach **expliziter Freigabe**
   zu einem kanonischen Tag **zusammenführen** (inkl. Umhängen aller
   historischen Einträge).
2. **Präventive Prüfung bei Anlage:** Beim Anlegen eines neuen Custom-Tags
   ähnliche existierende Tags prüfen und aufzeigen, bevor die Dublette
   überhaupt entsteht (Vorschlag: „Meintest du **krank**?").

Dieses Dokument **analysiert** die Ausgangslage, stellt **Umsetzungs­optionen
gegenüber** und **bewertet** sie. Es legt noch keinen Code fest.

---

## 2. Ausgangslage im Code (was wir schon haben)

Die gute Nachricht: der Merge ist zu großen Teilen **schon einmal gebaut** —
für den Copy-on-Write-Override-Mechanismus. Die Bausteine sind wiederverwendbar.

### 2.1 Datenmodell

[`app/models/tag.py`](../../backend/app/models/tag.py):

- `Tag` — `id`, `user_id` (`NULL` = kuratierter Default), `slug` (kanonischer
  Kebab-Case-Key), `name` (freier Anzeigename), `category`
  (`sport | social | work | leisure | consumption | health | cycle | other`),
  `icon`, `color`, `is_default`, `is_hidden`, `include_in_analytics`,
  `habit_type`, `target_frequency`.
- `EntryTag` — dünne M:N-Verknüpfung `(entry_id, tag_id, user_id)`,
  `UniqueConstraint(entry_id, tag_id)`. `user_id` ist für RLS denormalisiert.

**Wichtig:** Der `slug` ist bewusst **nicht** patchbar (siehe
[`schemas/tag.py`](../../backend/app/schemas/tag.py) `TagUpdate`-Docstring),
weil ein Slug-Wechsel alle historischen Verknüpfungen bräche. Genau das ist der
Grund, warum ein *Merge* (Tag löschen, Einträge umhängen) und **kein** Rename
der richtige Weg ist.

### 2.2 Der wiederverwendbare Merge-Primitiv

[`app/services/tag_service.py`](../../backend/app/services/tag_service.py) enthält
bereits die Kernoperation, die ein Merge braucht — heute genutzt, um
historische Links von einem Default-Tag auf dessen persönlichen Override
umzuhängen:

```python
async def remap_entry_tags_from_default_to_override(
    db, *, user_id, default_tag_id, override_tag_id
) -> int:
    # Löscht Kollisions-Links (Eintrag hat beide Tags → dedupe),
    # hängt die restlichen Links per UPDATE auf das Ziel um,
    # idempotent, mit Struktur-Logging.
```

Ein Tag-Merge ist **exakt diese Operation**, nur ohne die Einschränkung
„Default → gleicher Slug-Override". Auch `canonicalize_tags_by_slug()`
(Kollabieren mehrerer Tag-Zeilen auf eine kanonische) und
`remap_all_tag_alias_entry_links()` liefern erprobte Muster.

### 2.3 Offline-Sync-Korrektheit (der eigentlich harte Teil)

CorrelCore ist offline-fähig mit Last-Write-Wins-Sync
([ADR-0036](../adr/0036-offline-sync-v1-scope.md)). `tag_service` zeigt das
Pflichtprogramm, das jeder Schreibpfad einhalten muss:

- `record_tag_revision(...)` — Tag-Änderung ins `sync_revision_log` schreiben
  (`upsert`/`delete`), sonst kennen Offline-Clients den gemergten Zustand nicht.
- `record_entry_upsert_revision(...)` **und** `entry.updated_at` anheben für
  jeden umgehängten Eintrag — sonst überschreibt ein späterer Offline-Push mit
  neuerem Client-Timestamp den Merge per LWW und **stellt die Dublette wieder her**.

→ **Ein Merge, der diese Revisions nicht schreibt, ist auf Offline-Clients
kaputt.** Das ist die zentrale Fallgrube.

### 2.4 Verhaltensbasierte Ähnlichkeit ist bereits vorhanden

[`app/services/tag_cluster_service.py`](../../backend/app/services/tag_cluster_service.py)
(M7) berechnet Co-Occurrence-Vektoren pro Tag und clustert sie (KMeans +
Silhouette). Die **`pgvector`-Extension ist aktiv** und Migration
[`016_add_tag_vectors`](../../backend/migrations/versions/016_add_tag_vectors.py)
speichert pro `(user_id, tag_id)` ein `embedding vector` (Co-Occurrence-Profil).

Das ist *eine* Ähnlichkeitsdimension „diese Tags treten in denselben Einträgen
auf" — orthogonal zur *lexikalischen* Ähnlichkeit „diese Namen sehen ähnlich aus".

### 2.5 Symptome sind das analoge Schwesterproblem

[`app/models/symptom.py`](../../backend/app/models/symptom.py) /
[`symptom_service.py`](../../backend/app/services/symptom_service.py) sind
strukturgleich (`Symptom`/`EntrySymptom`, Default vs. Custom). **Aber:**
Custom-Symptomnamen sind DSGVO-Art.-9-Daten und liegen **verschlüsselt** als
`name_enc` (Fernet, [ADR-0005](../adr/0005-verschluesselung-at-rest.md) /
[ADR-0039](../adr/0039-slug-hmac-custom-symptoms.md)). Lexikalische
Ähnlichkeit auf Symptomnamen ist **serverseitig nicht möglich** → siehe
[§8 Datenschutz](#8-datenschutz-impact).

### 2.6 Frontend-Anknüpfpunkte

- Erfassung/Anlage: [`TagPicker.svelte`](../../apps/web/src/lib/components/entries/TagPicker.svelte)
  (`showCustomForm`, `autoSlugFromName`, `onSubmitCustom`).
- API-Client: [`api/tags.ts`](../../apps/web/src/lib/api/tags.ts)
  (`createTag`/`updateTag`/`deleteTag`).
- Verwaltung: Tag-Liste in den Settings (Kandidat für den „Ähnliche Tags"-Review-Screen).

### 2.7 „Arbeitskontext" — Scope-Klärung

Der Request nennt „Kontext krank" und „Tag Krankheitstag". Im Datenmodell gibt
es **keine** eigene Entität „Kontext" — es gibt Tags (mit `category`) und
Symptome. „Kontext krank" ist am ehesten der Health-Tag `krank`, „Krankheitstag"
ein Custom-Tag. Die Ähnlichkeit läuft also **quer über Kategorien** (`health`
vs. `other`). Das muss die Erkennung berücksichtigen (Kategorie nicht als
harter Filter, nur als schwaches Signal). Ein tag↔symptom-Merge ist bewusst
**out of scope** für V1 (verschiedene Entitäten, Verschlüsselung, andere
Semantik) — als Folge-Ausbau vermerkt.

---

## 3. Teilproblem A — Ähnlichkeit erkennen

Vier Ansätze, einzeln bewertet. Sie schließen sich nicht aus (Hybrid empfohlen).

### Option A1 — Lexikalische Ähnlichkeit (String-Distanz)

Vergleich von `slug`/`name` über normalisierte Distanzmaße.

- **Normalisierung (für Deutsch entscheidend):** Lowercase, Umlaut-Faltung
  (`ä→ae`, `ö→oe`, `ü→ue`, `ß→ss`) **und** Akzent-Strip, Whitespace/Bindestrich
  vereinheitlichen. Optional leichtes Stemming (Suffixe wie `-tag`, `-heit`,
  `-en` — „Krankheitstag" → Stamm „krank").
- **Maße:** Normalisierte Levenshtein-Distanz **plus** Token-Jaccard
  (Wortmengen-Überlappung, fängt „Krankheits**tag**" ↔ „krank" über den Stamm),
  **plus** Substring-/Präfix-Check.
- **Umsetzung:** entweder in Python (`rapidfuzz`, klein & schnell, kein
  Netzwerk) **oder** in Postgres via `pg_trgm` (`similarity()`, GIN-Index).
  `pg_trgm` ist aktuell **nicht** aktiviert (nur `pgcrypto`, `vector`) → bräuchte
  `CREATE EXTENSION`. Bei ~30–100 Tags/Nutzer ist der O(n²)-Vergleich in Python
  trivial (< 10k Paare) — **kein** DB-Index nötig.

| | |
|---|---|
| **Stärken** | Löst genau den genannten Fall („krank"/„Krankheitstag"). Deterministisch, erklärbar („89 % Namensähnlichkeit"). Kein Netzwerk, keine Modelle, DSGVO-neutral (Tag-Namen sind für Default-Tags ohnehin unkritisch). Läuft on-demand, kein Worker. |
| **Schwächen** | Erkennt **keine** Synonyme ohne Zeichenüberlappung („Sport"/„Bewegung", „Arbeit"/„Büro"). Deutsche Komposita brauchen Handarbeit beim Stemming. Fehlalarme bei kurzen Slugs („bad"/„rad"). |
| **Aufwand** | **Niedrig** (Python) / mittel (`pg_trgm`-Migration). |

### Option A2 — Verhaltensbasierte Ähnlichkeit (Co-Occurrence)

`tag_vectors`-Embeddings bzw. `tag_cluster_service`-Cofrequenzen nutzen:
Tags, die in denselben Einträgen auftreten, sind verhaltensähnlich.

| | |
|---|---|
| **Stärken** | Infrastruktur existiert (`pgvector`, Vektoren pro Nutzer). Findet Synonyme, die A1 entgehen, wenn sie gemeinsam/abwechselnd genutzt werden. |
| **Schwächen** | **Falsche Richtung für Dubletten:** echte Synonyme werden vom Nutzer meist *alternativ* verwendet (mal „krank", mal „Krankheitstag"), tauchen also **selten gemeinsam** auf → niedrige Co-Occurrence. Braucht Datenreife (min. ~30–90 Einträge, sonst `insufficient_data`). Nur schwaches Zusatzsignal. |
| **Aufwand** | Niedrig (wiederverwenden), aber geringer Nutzen als Primärsignal. |

### Option A3 — Semantische Text-Embeddings

Multilinguales Embedding der Tag-Namen (z. B. Sentence-Transformer), Kosinus-
Ähnlichkeit; `pgvector` könnte die Vektoren speichern.

| | |
|---|---|
| **Stärken** | Einziger Ansatz, der echte Synonyme **ohne** Zeichenüberlappung erkennt („Bewegung"/„Sport"). |
| **Schwächen** | **Konflikt mit Kernprinzipien:** privacy-first, self-hosted, offline-fähig. Ein lokales Modell (~100–400 MB) bläht das Backend-Image; eine externe Embedding-API scheidet für Gesundheitsdaten aus. Betrieblich schwer, für ~50 Tags stark überdimensioniert. |
| **Aufwand** | **Hoch** (Modell-Hosting, Image-Größe, Inferenz-Pfad). |

### Option A4 — Kuratiertes Synonym-Wörterbuch

Gepflegte Synonym-Gruppen für die **Default-Tags** (`krank`↔`krankheitstag`,
`sport`↔`training`↔`bewegung`, `arbeit`↔`büro`…), analog zu den kuratierten
Onboarding-Vorschlägen ([ADR-0030](../adr/0030-onboarding-tag-suggestions.md)).

| | |
|---|---|
| **Stärken** | Höchste Präzision für die häufigsten Fälle, null Fehlalarme, komplett offline/deterministisch, DSGVO-neutral, trivial zu testen. Sofort wirksam als „Bootstrap". |
| **Schwächen** | Deckt nur kuratierte Begriffe ab, nicht beliebige Custom-Namen. Pflegeaufwand; nur Deutsch (i18n-Erweiterung nötig). |
| **Aufwand** | Niedrig. |

### Empfehlung Teilproblem A — **Hybrid A1 + A4**

Primär **A1 (lexikalisch, in Python mit `rapidfuzz` + deutscher
Normalisierung)** als generischer Motor, angereichert um **A4 (Synonym-Lexikon)**
für die kuratierten Default-Begriffe. **A2** optional als schwaches Zusatzsignal
zum Re-Ranking, **wenn** genug Daten da sind. **A3 bewusst zurückstellen**
(Prinzipienkonflikt, Aufwand) — als späteres, opt-in Self-Host-Feature denkbar.

Score-Modell (Vorschlag): `score = max(lexikalisch, lexikon) ` und Kandidaten
ab Schwellwert `τ` (z. B. 0.82) vorschlagen, nie automatisch mergen.

---

## 4. Teilproblem B — Merge-Mechanik

Kanonisches Ziel `T_keep` schlucken `T_drop`. Ablauf serverseitig, in **einer**
Transaktion:

1. **Zielwahl** — Default schlägt Custom; sonst der Tag mit mehr
   `entry_tags`-Links; Tie-Break stabil (Name, ID). Nutzer kann im UI umschalten.
2. **Feld-Reconciliation** — `T_keep` behält `slug`. Für `habit_type` /
   `target_frequency` / `include_in_analytics` / `color` / `icon`: bei Konflikt
   die Werte von `T_keep` behalten, dem Nutzer aber im Dialog anzeigen
   („Habit-Ziel von ‚Krankheitstag' wird verworfen"). Kein stiller Datenverlust
   ohne Anzeige.
3. **Links umhängen** — Kern via bestehendem
   `remap_entry_tags_from_default_to_override`-Muster (verallgemeinert auf
   beliebige `from_tag_id → to_tag_id`): Kollisionen (Eintrag hat beide)
   deduplizieren, Rest per `UPDATE` umhängen. Idempotent.
4. **COW/Hidden-Kanten** — falls `T_drop` ein Default mit persönlichem Override
   ist, `canonicalize_tags_by_slug`-Logik beachten, damit keine verwaisten
   Slug-Aliase entstehen.
5. **`T_drop` löschen** (Custom) bzw. per Override ausblenden (Default lässt
   sich nicht löschen → `is_hidden`-Override).
6. **Sync-Revisions** — `record_tag_revision(delete)` für `T_drop`,
   `record_tag_revision(upsert)` für `T_keep`, **und für jeden umgehängten
   Eintrag** `entry.updated_at` anheben + `record_entry_upsert_revision`
   (siehe [§2.3](#23-offline-sync-korrektheit-der-eigentlich-harte-teil)).
7. **Audit** — optional Eintrag ins `admin_audit_log`-Muster bzw. eine eigene
   `tag_merge_log`-Zeile für Nachvollziehbarkeit/Undo (siehe unten).

### Reversibilität — zwei Optionen

- **B-i (kein Undo, empfohlen für V1):** Merge ist destruktiv, aber
  Bestätigungsdialog zeigt Umfang („142 Einträge werden umgehängt, ‚Krankheitstag'
  gelöscht"). Einfachste Variante.
- **B-ii (Undo-fähig):** neue Tabelle `tag_merge_log` (welche Einträge hatten
  `T_drop`, Feldwerte-Snapshot). Erlaubt Rückgängig innerhalb X Tagen.
  **Mehraufwand**, mit Offline-Sync heikel (Undo muss ebenfalls Revisions
  schreiben). Für V1 zurückstellen.

---

## 5. Teilproblem C — Prüfung bei Anlage (präventiv)

Beim Anlegen eines Custom-Tags gegen bestehende sichtbare Tags prüfen.

- **Server:** entweder `POST /tags` liefert bei Treffern **statt** 201 einen
  „soft conflict" (`409` mit Kandidatenliste) — riskant, weil legitime Anlage
  blockiert würde — **oder** (empfohlen) ein separater, nicht-blockierender
  Endpoint `GET /tags/similar?name=…&slug=…`, den der `TagPicker` **vor** dem
  Submit aufruft. Anlage bleibt immer möglich (der Nutzer entscheidet).
- **Frontend:** in [`TagPicker.svelte`](../../apps/web/src/lib/components/entries/TagPicker.svelte)
  bei Namenseingabe (debounced) Vorschläge zeigen: „Ähnlich zu **krank** —
  diesen verwenden?" mit Buttons *[krank wählen]* / *[trotzdem neu anlegen]*.
  Rein additiv, kein Merge nötig — verhindert die Dublette an der Quelle.

---

## 6. Vorgeschlagene API

Alle unter `/api/v1`, auth + verified, Rate-Limits analog Tag-Endpoints.

| Methode & Pfad | Zweck |
|---|---|
| `GET /tags/similar?name=…&slug=…` | Präventiv: Ähnlichkeitskandidaten zu einem (noch nicht angelegten) Namen. Nicht-blockierend. |
| `GET /tags/duplicates` | Retrospektiv: Liste erkannter Ähnlichkeitspaare/-gruppen des Nutzers mit Score & Vorschlags-Zielwahl. |
| `POST /tags/{keep_id}/merge` | Body `{ "drop_ids": [...] }` — führt Merge aus (§4), gibt `T_keep` + Zähler (umgehängt/dedupliziert) zurück. |

Schemas: `SimilarTagCandidate { tag, score, reason }`,
`DuplicateGroup { candidates[], suggested_keep_id }`,
`TagMergeResult { tag, remapped_count, deduped_count, dropped_ids }`.

---

## 7. Frontend-UX

1. **Settings → „Ähnliche Tags"** (Review-Screen): Karten je erkanntem Paar/
   Gruppe, Score/Begründung, Radiobutton für Zieltag, „Zusammenführen"-Button
   mit Bestätigungsdialog (zeigt betroffene Eintragszahl + verworfene Felder).
   Nichts passiert ohne expliziten Klick → **Freigabe** wie gefordert.
2. **TagPicker-Inline-Hinweis** bei Anlage (§5).
3. **i18n** (de/en), a11y (Fokus, Screenreader-Text für Score), Optimistic-Update
   der Tag-Stores nach Merge.

---

## 8. Datenschutz-Impact

- **Tags:** Namen/Slugs von **Default**-Tags sind nicht-personenbezogen;
  Custom-Tag-Namen sind Verhaltens-nah, liegen aber im Klartext (kein Art. 9).
  Lexikalische Ähnlichkeit auf Tag-Namen ist damit **serverseitig zulässig**.
  **Kein** Logging von Slug/Name (bestehende Scrubbing-Regel in
  `test_tags.py` einhalten) — nur `user_id`, Counts, Scores.
- **Symptome (out of scope V1):** `name_enc` ist verschlüsselt (Art. 9). Ein
  Symptom-Ähnlichkeitscheck müsste **client-seitig** laufen (Namen nur dort
  entschlüsselt) — eigener Sprint, hier nur als Ausblick.
- **Merge** erzeugt keine neuen Trackingdaten, nur Re-Mapping bestehender
  Aggregate. `tag_merge_log` (falls B-ii) enthielte Tag-IDs → RLS + kein
  Klartext-Logging.

---

## 9. Bewertungsmatrix (Gesamt)

Erkennungs-Ansätze:

| Ansatz | Deckt „krank/Krankheitstag" | Deckt Synonyme o. Überlappung | Offline/Privacy | Aufwand | Empfehlung |
|---|:---:|:---:|:---:|:---:|:---:|
| A1 Lexikalisch (rapidfuzz) | ✅ | ❌ | ✅ | Niedrig | **Kern** |
| A2 Co-Occurrence | ⚠️ | ⚠️ | ✅ | Niedrig* | Optional |
| A3 Semantic Embeddings | ✅ | ✅ | ❌ | Hoch | Zurückstellen |
| A4 Synonym-Lexikon | ✅ | ✅ (kuratiert) | ✅ | Niedrig | **Bootstrap** |

<sub>*wiederverwendbar, aber schwacher Nutzen als Dubletten-Signal.</sub>

Merge-Reversibilität:

| Variante | Aufwand | Offline-Risiko | Empfehlung |
|---|:---:|:---:|:---:|
| B-i ohne Undo (Bestätigungsdialog) | Niedrig | Gering | **V1** |
| B-ii mit `tag_merge_log`/Undo | Mittel–Hoch | Mittel | Später |

---

## 10. Empfehlung

**Phasierter Vorschlag:**

- **Phase 1 (MVP, geringes Risiko):** Erkennung **A1 + A4** in Python;
  Endpoints `GET /tags/similar` (präventiv) und `GET /tags/duplicates`
  (retrospektiv); Merge `POST /tags/{keep}/merge` auf Basis des bestehenden
  Remap-Primitivs **mit korrekten Sync-Revisions**; Variante **B-i** (kein
  Undo, aber Bestätigungsdialog). Frontend: Settings-Review-Screen +
  TagPicker-Inline-Hinweis.
- **Phase 2 (optional):** A2 als Re-Ranking-Signal; `tag_merge_log` + Undo
  (B-ii); Symptom-Dubletten client-seitig.
- **Phase 3 (nur wenn nachgefragt):** A3 semantische Embeddings als opt-in,
  rein self-hosted-lokal.

**Kernaussagen der Analyse:**
- Der Merge ist **kein Greenfield** — `remap_entry_tags_from_default_to_override`
  + `canonicalize_tags_by_slug` liefern die erprobte Mechanik.
- Der **eigentliche Fallstrick ist Offline-Sync-LWW**, nicht die Erkennung: ohne
  `updated_at`-Bump + Entry-Revisions kehrt die Dublette zurück.
- Für den genannten Fall reicht **lexikalische Ähnlichkeit + Synonym-Lexikon**;
  schwere ML/Embeddings widersprächen dem Privacy-/Offline-/Self-Host-Prinzip
  und sind überdimensioniert.

## 11. Offene Fragen

1. Merge **irreversibel** (B-i) für V1 akzeptabel, oder Undo (B-ii) gewünscht?
2. Ähnlichkeits-**Schwellwert** `τ` und ob Kandidaten *nur* auf Nachfrage
   (Settings) oder auch **proaktiv** (Badge) gezeigt werden.
3. Sollen **Gruppen** (>2 ähnliche Tags) in einem Schritt mergebar sein, oder
   nur paarweise?
4. **Symptom-Dubletten** in denselben Sprint ziehen (Verschlüsselung → Client)
   oder klar V2?
5. Merge über **Kategoriegrenzen** (health↔other) immer erlauben — welche
   Kategorie „gewinnt"?

## 12. Alternativen (verworfen)

- **Auto-Merge ohne Freigabe** — widerspricht dem Request ausdrücklich
  („nach Freigabe") und dem No-Surprise-Prinzip bei Gesundheitsdaten.
- **Slug patchbar machen statt Merge** — bricht historische `entry_tags`
  (genau der Grund, warum `slug` heute read-only ist).
- **Nur `pg_trgm` in der DB** — zieht eine Extension-Migration nach sich, ohne
  Mehrwert gegenüber Python bei ~50 Tags/Nutzer; deutsche Umlaut-/Komposita-
  Normalisierung ist in Python flexibler.
