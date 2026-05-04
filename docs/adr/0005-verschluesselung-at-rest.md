# ADR-0005: Datenverschlüsselung at-rest: Zweistufige Strategie

**Datum:** 2026-04-20
**Status:** Accepted

---

## Kontext

- **MoodSync verarbeitet Daten nach Art. 9 DSGVO:** Gesundheitsdaten, Stimmungsdaten und Symptomdaten gelten als besondere Kategorien personenbezogener Daten, für die erhöhte Schutzpflichten gelten.
- **Ohne Verschlüsselung at-rest** sind Daten bei physischem Serverzugriff, Datenbank-Dump oder Backup-Diebstahl im Klartext lesbar – ein inakzeptables Risiko für Art.-9-Daten.
- **Vollständige E2E-Verschlüsselung** (clientseitig, kein Server-Zugriff auf Klartextdaten) würde serverseitige Korrelationsanalysen und ML-Insights unmöglich machen – ein zentrales Feature von MoodSync.
- **Kompromiss:** Selektive Feld-Verschlüsselung für die sensibelsten Felder auf App-Ebene kombiniert mit Storage-Level-Verschlüsselung für alle Daten.

---

## Entscheidung: Zweistufige Strategie

### Stufe 1 – Infrastruktur-Ebene (sofort, bis M1)

| Maßnahme               | Implementierung                                                                                                                                     |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **MinIO SSE-S3**       | Server-Side Encryption für alle Buckets aktivieren (`mc admin config set myminio api sse_default_key=...`) – reine Konfiguration, kein Code-Aufwand |
| **PostgreSQL-Volumes** | Hetzner-LUKS-verschlüsselte Volumes nutzen (in der Deployment-Anleitung dokumentiert); Encryption at-rest auf Block-Ebene                           |
| **TLS erzwingen**      | Traefik HTTPS-Redirect für alle Services; HSTS mit `max-age=31536000` (1 Jahr), `includeSubDomains`                                                 |

### Stufe 2 – App-Ebene (M1)

**Verschlüsselte Felder:**

- `entries.note` (Stimmungsnotizen)
- `entry_symptoms.details` (Symptom-Freitextbeschreibungen)
- `insights.statement` (KI-generierte Insights, die Nutzertext enthalten können)

**Implementierung:**

- **Fernet** (symmetrische Verschlüsselung, `python-cryptography`): AES-128-CBC + HMAC-SHA256, authenticated encryption
- **Pro-User-Key:** Jeder Nutzer erhält einen individuellen Encryption-Key (verhindert, dass ein kompromittierter Key alle Nutzer betrifft)
- **Key-Storage:** User-Keys werden in PostgreSQL gespeichert, verschlüsselt mit einem Master-Key aus der Umgebungsvariable `ENCRYPTION_KEY`
- **Suche:** PostgreSQL Full-Text-Search (FTS) bleibt für nicht-verschlüsselte Felder (`mood_score`, `tags`, `habits`) voll funktionsfähig. Volltext-Suche in Notizen erfolgt über den lokalen **Dexie.js**-Index (Offline-DB im Browser/Capacitor) – kein Server-seitiger FTS auf verschlüsselten Feldern

### E2E-Verschlüsselung (Backlog / M12+)

- **Opt-in** für Power-User, die volle Client-Side-Kontrolle wünschen
- **Implementierung:** `libsodium` via Web Crypto API (clientseitig), Server speichert nur Ciphertext
- **Trade-off:** Bricht serverseitige Insights für betroffene Felder vollständig → sinnvoll nur für `notes`, nicht für `mood_score` / `symptoms`

---

## Alternativen erwogen

| Option                                 | Vorteile                                                                              | Nachteile                                                                                                |
| -------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Kein Encryption at-rest**            | Kein Aufwand, volle FTS-Funktionalität                                                | Art.-9-DSGVO-Risiko, Daten bei Backup-Diebstahl im Klartext, inakzeptabel                                |
| **pgcrypto Column-Level**              | Direkt in PostgreSQL, kein App-Code                                                   | Schlechtere Performance als App-Level, Key-Management in DB schwieriger, kein pro-User-Key ohne Overhead |
| **App-Level Fernet (pro-User-Key)** ✅ | Gute Performance (~0.1 ms/Feld), pro-User-Key, authenticated encryption, Python-nativ | FTS auf verschlüsselten Feldern nicht möglich (Workaround via Dexie.js)                                  |
| **E2E Client-Side (libsodium)**        | Maximaler Schutz, Server sieht keine Klartextdaten                                    | Bricht serverseitige Insights, höchste Implementierungskomplexität, für Phase 1 überdimensioniert        |

---

## Konsequenzen

- **Key-Management:**
  - `ENCRYPTION_KEY` als Umgebungsvariable (mindestens 32 Bytes, Base64-encoded), nie in der Codebase
  - Key-Rotation: Dokumentiertes Verfahren – neuer Master-Key wird gesetzt, alle User-Keys werden re-encrypted (Background-Job), kein Downtime
- **Backup-Sicherheit:**
  - Backups enthalten verschlüsselte Daten – **ohne `ENCRYPTION_KEY` nicht wiederherstellbar**
  - Kritischer Hinweis in der Deployment-Dokumentation: **`ENCRYPTION_KEY` separat und sicher backuppen** (z. B. Vaultwarden / Bitwarden Secrets)
- **Performance:** Fernet-Verschlüsselung ~0.1 ms pro Feld bei typischen Dateigrößen (Notizen < 10 KB) – vernachlässigbar gegenüber DB-Latenz
- **DSGVO-Compliance:** Verschlüsselung at-rest ist eine der ausdrücklich empfohlenen technischen Maßnahmen gemäß **Art. 32 DSGVO** (Sicherheit der Verarbeitung); dokumentiert als Teil des TOM-Verzeichnisses

---

## Umsetzung

| Meilenstein | Aufgabe                                                                                                                                          |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **M0**      | Stufe 1: MinIO SSE aktivieren, LUKS-Volume-Dokumentation, Traefik HSTS-Konfiguration                                                             |
| **M1**      | Stufe 2: Fernet-Integration, pro-User-Key-Generierung bei Registrierung, Alembic-Migration für verschlüsselte Felder, Key-Rotation-Dokumentation |
| **M12+**    | E2E-Verschlüsselung als Opt-in für Power-User (Backlog)                                                                                          |
