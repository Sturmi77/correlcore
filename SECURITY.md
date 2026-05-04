# Security Policy

## Unterstützte Versionen

| Version         | Support |
| --------------- | ------- |
| latest (main)   | ✅      |
| Ältere Releases | ❌      |

## Sicherheitslücke melden

**Bitte keine Security-Issues öffentlich im Issue-Tracker anlegen.**

Sicherheitslücken an: **security@moodsync.app** (oder direkt an den Maintainer)

Bitte folgende Informationen angeben:

- Beschreibung der Schwachstelle
- Betroffene Komponente (API, Frontend, Infra, Auth)
- Schritte zur Reproduktion
- Potenzielle Auswirkung

Wir reagieren innerhalb von **72 Stunden** und koordinieren einen koordinierten Disclosure-Prozess.

## Datenschutz-Vorfälle

Bei Datenpannen die Gesundheitsdaten betreffen gilt zusätzlich:

- Meldepflicht an die österreichische Datenschutzbehörde (DSB) innerhalb 72h
- Information der betroffenen Nutzer wenn hohes Risiko besteht
- Details: `docs/DSGVO.md` Sektion 8

## Bekannte Sicherheitsmaßnahmen

Architektur-relevante Security-Entscheidungen sind dokumentiert in:

- `docs/ARCHITECTURE.md` Sektion 7 (Datensicherheit)
- `docs/DSGVO.md` (Datenschutz-Schutzkonzept)
- `docs/adr/` (Architecture Decision Records)
