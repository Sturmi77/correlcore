# Architecture Decision Records (ADR)

Jede signifikante Architekturentscheidung wird hier als ADR dokumentiert.

## Format

Dateiname: `NNNN-kurzer-titel.md`
Status: `Vorgeschlagen | Accepted | Abgelehnt | Ersetzt durch ADR-XXXX`

## Index

| ADR | Titel | Status | Datum |
|---|---|---|---|
| [ADR-0001](0001-sveltekit-vs-nextjs.md) | SvelteKit als Web-Framework (statt Next.js) | Accepted | – |
| [ADR-0002](0002-capacitor-statt-twa.md) | Capacitor statt TWA als Mobile-Strategie | Accepted | 2026-04-20 |
| [ADR-0003](0003-sync-conflict-log.md) | Sync-Protokoll: Conflict-Log statt stilles LWW | Accepted | 2026-04-20 |
| [ADR-0004](0004-auth-strategie.md) | Auth-Strategie: Native JWT in Phase 1, Authentik ab Phase 2 | Accepted | 2026-04-20 |
| [ADR-0005](0005-verschluesselung-at-rest.md) | Datenverschlüsselung at-rest: Zweistufige Strategie | Accepted | 2026-04-20 |

## Kurzübersicht der Entscheidungen

### ADR-0001 – SvelteKit als Web-Framework
SvelteKit wird gegenüber Next.js bevorzugt: kleinere Bundle-Größen, bessere PWA-Integration, kein React-Overhead.

### ADR-0002 – Capacitor statt TWA
TWA/Bubblewrap wird aufgegeben. Capacitor wrappt die SvelteKit-Codebase mit nativen Android-Bridges für Health Connect und FCM.

### ADR-0003 – Sync: LWW + Conflict-Log
Last-Write-Wins bleibt das Merge-Prinzip. Alle Konflikte werden in der Tabelle `sync_conflicts` geloggt und sind für den User in den Einstellungen einsehbar (90-Tage-Retention).

### ADR-0004 – Auth: Native JWT → Authentik
Phase 1 (Selfhost, bis M10): Native JWT Auth in FastAPI mit Refresh-Token-Rotation, HttpOnly-Cookies, Rate-Limiting und TOTP-MFA. Phase 2 (SaaS, M12+): Authentik als OIDC-Provider.

### ADR-0005 – Verschlüsselung at-rest
Zweistufig: Stufe 1 = MinIO SSE + LUKS-Volumes + HSTS (Infrastruktur, M0). Stufe 2 = App-Level Fernet-Verschlüsselung mit pro-User-Keys für `entries.note`, `entry_symptoms.details`, `insights.statement` (M1).

---

## Neue ADRs hinzufügen

1. Nächste freie Nummer ermitteln
2. Datei `NNNN-kurzer-titel.md` in diesem Verzeichnis anlegen
3. Eintrag in den Index oben sowie in die Kurzübersicht aufnehmen
4. Status initial auf `Vorgeschlagen`, nach Team-Review auf `Accepted` oder `Abgelehnt` setzen
