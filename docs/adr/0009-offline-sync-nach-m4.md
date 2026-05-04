# ADR-0009 — Offline-Sync nach M4 verschieben

**Status:** Accepted
**Datum:** 2026-05-04
**Bezug:** Issues #10, #24, #26 · Milestones M1, M4 · ADR-0003 (Sync-Conflict-Log)

## Kontext

Im Original-Scope von **M1 — Core Entry** war Offline-Sync (Dexie.js +
`/sync/push` + `/sync/pull`) als Akzeptanzkriterium gesetzt:

- DESIGN_DOCUMENT §3 M1, Bullet "Offline-Fähigkeit via IndexedDB +
  Sync-Endpoint"
- Akzeptanzkriterium "Offline-Sync mit Conflict-Log-Tabelle implementiert"
- Akzeptanzkriterium "Sync-Endpunkt (`/sync/push` + `/sync/pull`)
  funktioniert mit Offline-Queue"

Gleichzeitig steht in **M4 — Mobile Polish & PWA-Hardening** bereits:

- Akzeptanzkriterium "Offline-Modus: Eintrag erstellen ohne Netzverbindung,
  Sync beim nächsten Online-Start"

Diese **Doppelung** hat sich als historisch unsauberes Scoping erwiesen.
Vor dem geplanten Eigen-User-Test nach M1-Abschluss stellt sich die Frage,
ob Offline-Sync wirklich M1-blockierend ist.

## Entscheidung

**Issues #10 (Offline-Sync) und #24 (Sync-Conflict-Log) werden auf
Milestone M4 verschoben.** M1-Scope wird entsprechend reduziert:

- Bullet "Offline-Fähigkeit via IndexedDB + Sync-Endpoint" entfällt aus
  M1-Scope-Liste
- Akzeptanzkriterien zu Offline-Sync und `/sync/push` + `/sync/pull`
  entfallen aus M1
- M4 erhält explizite Sync-Akzeptanzkriterien (Sync-Endpunkte,
  Conflict-Log) zusätzlich zum bereits vorhandenen Offline-Modus-Punkt
- §3.5 (Sync-Protokoll) bleibt unverändert dokumentiert — der Plan ist
  identisch, nur der Lieferzeitpunkt verschiebt sich

**M1-Exit wird geschärft auf:** "Produktive Online-Nutzung durch
Entwickler selbst möglich (inkl. Login im Browser)".

**Issue #26 (App-Level Fernet at-rest) bleibt M1.** Das ist der
DSGVO-blocking Punkt für realen Eigen-Use mit echten Symptom-Namen,
unabhängig von Offline-Sync.

## Begründung

### M1-Exit ist online erreichbar

Der M1-Exit lautet "Produktive Nutzung durch Entwickler selbst möglich
(inkl. Login im Browser)". Der Owner nutzt seine Synology-gehostete
Instanz primär aus dem Heimnetz (Tailscale), praktische Connectivity
ist faktisch immer gegeben. Offline-First ist ein Produkt-Prinzip
(§2.11), aber kein zwingendes M1-Akzeptanzkriterium für den
Eigen-User-Test.

### Aufwand und Risiko

Issue #10 umfasst:

- Dexie.js Setup im SvelteKit-Frontend
- Lokale `change_log`-Tabelle mit monotoner Sequenz
- Zwei neue Backend-Endpoints (`/sync/push`, `/sync/pull?since=`)
- Last-Write-Wins-Merge pro Feld auf Server-Seite
- Retry-Queue im Frontend für Netzwerkfehler
- Konflikt-Handling (Server gewinnt) + Merge-Report an Client
- Tests für Multi-Device-Szenarien

Realistischer Aufwand: ≥ 3–5 Tage netto, mit umfassenden Tests
(Race-Conditions, Konflikt-Szenarien, Idempotenz-Garantien) deutlich
mehr. Das blockiert den User-Test substantiell und erhöht das Risiko
für unentdeckte Sync-Bugs, die in einer Single-Device-Eigennutzung
nicht reproduzierbar sind.

### M4 ist der natürliche Ort

M4 ist explizit "Mobile Polish & PWA-Hardening". Erst hier wird
echtes Multi-Device-Szenario relevant: Smartphone-PWA installiert,
Mobile Hotspot, U-Bahn-Fahrt, Reise-Modus. M4 hat bereits einen
Offline-Modus-Punkt in den Akzeptanzkriterien — die Verschmelzung
ist sauber, nicht erzwungen.

### #26 hat höhere DSGVO-Priorität für M1

Custom-Symptom-Namen (`symptoms.name` für Custom-Rows) und
`entries.note` enthalten Art.-9-Gesundheitsdaten. Für den Eigen-Use
mit echten Symptomnamen ist At-Rest-Verschlüsselung nach
[ADR-0005](0005-verschluesselung-at-rest.md) zwingend, unabhängig
vom Sync-Pfad.

## Alternativen erwogen

### Alternative A: Reduzierter Offline-Sync in M1

Nur Push-Queue, keine Pull-Sync, keine Konflikt-Logik. **Verworfen**,
weil es ein Halbprodukt erzeugt, das ohne Pull-Sync keinen echten
Multi-Device-Wert liefert und vollständig ersetzt werden müsste,
sobald M4 echtes Sync braucht. Sunk-Cost ohne Nutzen.

### Alternative B: Neuer Milestone M1.5 — Polish

Ein dedizierter M1.5-Milestone zwischen M1 und M2 für Sync +
weitere Polish-Items. **Verworfen**, weil M4 bereits den
Offline-Modus-Akzeptanztest enthält und ein Milestone-Split nur
Verwaltungs-Overhead erzeugt, ohne ein neues Exit-Kriterium zu
liefern. Issues bleiben sichtbar im Backlog mit klarem
Milestone-Label.

### Alternative C: Offline-Sync in M2 (Visualisierung)

**Verworfen**, weil Visualisierung thematisch unabhängig ist und
Sync-Implementierung den M2-Scope unnötig aufblähen würde.

## Folgen

### Positiv

- M1-Abschluss in absehbarer Zeit erreichbar → realer Eigen-User-Test
  beschleunigt
- Erkenntnisse aus dem User-Test fließen in M2/M3-Priorisierung
- Sync-Implementierung in M4 profitiert vom Multi-Device-Druck
  (Smartphone wird tatsächlich genutzt) → echter Test statt synthetischem
- Konsistenz zwischen DESIGN_DOCUMENT M4 (bereits vorhanden) und
  Issue-Tracking (jetzt aligned)

### Negativ

- Browser-Tab-Reload während Eintrag-Erstellung kann nicht
  gespeicherte Werte verlieren (akzeptabel für M1-Eigenuser, mitigiert
  durch SvelteKit-Form-Persistence falls nötig als M1-Followup)
- Keine echte Offline-Fähigkeit zwischen M1 und M4 (≈ 6 Wochen)

### Neutral

- §3.5 Sync-Protokoll bleibt dokumentiert wie spezifiziert
- ADR-0003 (Sync-Conflict-Log) bleibt gültig, wird mit #24 in M4
  realisiert
- Keine Architekturänderung — nur Scheduling

## Folge-Aktionen

1. Issues #10 und #24 auf Milestone M4 setzen (Label + Milestone-Field) ✓
2. DESIGN_DOCUMENT §3 M1 + M4 entsprechend anpassen
3. CHANGELOG-Eintrag unter `[Unreleased] → Changed`
4. Issue #26 (Fernet) als nächstes M1-Item priorisieren
