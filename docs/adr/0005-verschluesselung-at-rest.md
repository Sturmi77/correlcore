# ADR-0005: Datenverschlüsselung at-rest: Zweistufige Strategie

**Datum:** 2026-04-20 (Initial), 2026-05-04 (Re-Evaluierung & Nachschärfung)
**Status:** Accepted (re-evaluiert und bestätigt)
**Bezug:** D-011 (DESIGN_DOCUMENT.md §7)

---

## Kontext

- **MoodSync verarbeitet Daten nach Art. 9 DSGVO:** Gesundheitsdaten, Stimmungsdaten und Symptomdaten gelten als besondere Kategorien personenbezogener Daten, für die erhöhte Schutzpflichten gelten.
- **Ohne Verschlüsselung at-rest** sind Daten bei physischem Serverzugriff, Datenbank-Dump (`pg_dump`) oder Backup-Diebstahl im Klartext lesbar – ein inakzeptables Risiko für Art.-9-Daten.
- **Vollständige E2E-Verschlüsselung** (clientseitig, kein Server-Zugriff auf Klartextdaten) würde serverseitige Korrelationsanalysen und ML-Insights unmöglich machen – ein zentrales Feature von MoodSync.
- **Kompromiss:** Selektive Feld-Verschlüsselung für die sensibelsten Felder auf App-Ebene kombiniert mit Storage-Level-Verschlüsselung für alle Daten.

### Bedrohungsmodell (welche Angriffe wir abdecken)

| Bedrohung                                                                              | Mitigation durch Stufe 1 (LUKS+SSE) | Mitigation durch Stufe 2 (Fernet) |
| -------------------------------------------------------------------------------------- | ----------------------------------- | --------------------------------- |
| Diebstahl Backup-Datei (`pg_dump.sql.gz`, restic-Snapshot ohne Verschlüsselung)        | ❌                                  | ✅                                |
| Diebstahl Festplatte aus **abgeschaltetem** Server                                     | ✅                                  | ✅                                |
| Diebstahl Festplatte aus laufendem Server                                              | ❌                                  | ❌                                |
| Read-Only-Postgres-Zugriff (Angreifer bekommt SQL-Zugang, App-Server unkompromittiert) | ❌                                  | ✅                                |
| Kompromittierter App-Server (Klartext im RAM zugänglich)                               | ❌                                  | ❌                                |
| Insider-DBA bei SaaS-Betrieb (Cloud, M12+)                                             | ❌                                  | ✅                                |

→ **Stufe 1 allein deckt die für Art.-9-Daten relevanten Backup-Szenarien nicht ab.** Feld-Verschlüsselung ist daher Pflicht, nicht Kür.

---

## Entscheidung: Zweistufige Strategie

### Stufe 1 – Infrastruktur-Ebene (sofort, bis M1)

| Maßnahme                          | Implementierung                                                                                                                                 |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **MinIO SSE-S3**                  | Server-Side Encryption für alle Buckets aktivieren (`MINIO_KMS_AUTO_ENCRYPTION: 'on'` im Compose-File) – reine Konfiguration, kein Code-Aufwand |
| **PostgreSQL-Volumes**            | Hetzner-LUKS-verschlüsselte Volumes nutzen (in der Deployment-Anleitung dokumentiert); Encryption at-rest auf Block-Ebene                       |
| **TLS erzwingen**                 | Traefik HTTPS-Redirect für alle Services; HSTS mit `max-age=31536000` (1 Jahr), `includeSubDomains`                                             |
| **restic-Backup-Verschlüsselung** | Backup-Tool mit AES-256-GCM, Repo-Passwort separat von DB-Credentials                                                                           |

### Stufe 2 – App-Ebene (M1)

**Verschlüsselte Felder (M1 — Issue #26):**

- `entries.note_enc` (Stimmungsnotizen, BYTEA, transparent via `EncryptedString`-TypeDecorator)
- `symptoms.name_enc` für **Custom-Symptome** (Default-Symptome bleiben plaintext, weil deren Namen kuratierte, nicht-personenbezogene Labels sind und ohne aktiven User-Kontext gelesen werden müssen — z. B. für `GET /symptoms/default`)
- _Nicht in M1:_ `entry_symptoms.details`, `insights.statement` — werden mit den jeweiligen Features (M2/M3) eingeführt und nutzen dieselbe Mechanik

**Bewusst nicht verschlüsselt (Trade-off):**

- `symptoms.slug` (auch für Custom-Symptome) — dieser leitet sich aus dem Namen ab und kann den Symptom-Namen im Klartext leaken (z. B. `migraene_mit_aura`). Er bleibt plaintext, weil Slug-basierte Operability (Debugging, Recovery-Heuristik bei Master-Key-Verlust, eindeutige Backend-Logs) für M1 wichtiger ist als die zusätzliche Vertraulichkeit des semantischen Hinweises. **Hardening via deterministischen Slug-HMAC ist als Backlog-Issue für M9+ eingeplant** (vor Public-Selfhost-Release re-evaluieren).

**Implementierung:**

- **Fernet** (symmetrische Verschlüsselung, `python-cryptography`): AES-128-CBC + HMAC-SHA256, **authenticated encryption** (Manipulation am Ciphertext wird beim Entschlüsseln erkannt)
- **Pro-User-Key:** Jeder Nutzer erhält einen individuellen Encryption-Key (verhindert, dass ein kompromittierter Key alle Nutzer betrifft) — generiert bei Registrierung via `Fernet.generate_key()`
- **Master-Key (KEK):** `ENCRYPTION_KEY`-Umgebungsvariable, mindestens 32 Bytes URL-safe-base64. Wrappt die per-User-DEKs (Data Encryption Keys)
- **Key-Storage:** Per-User-DEKs liegen in `user_encryption_keys`-Tabelle, **selbst Fernet-verschlüsselt** mit dem Master-Key
- **Suche:** PostgreSQL Full-Text-Search (FTS) bleibt für nicht-verschlüsselte Felder (`mood_score`, `tags`, `habits`) voll funktionsfähig. Volltext-Suche in Notizen erfolgt über den lokalen **Dexie.js**-Index (Offline-DB im Browser/Capacitor) – kein Server-seitiger FTS auf verschlüsselten Feldern

#### Datenmodell-Erweiterung (Migration `M1-pre`)

```sql
CREATE TABLE user_encryption_keys (
    user_id      UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    wrapped_dek  BYTEA NOT NULL,        -- Fernet-Token: Master-Key wrappt User-DEK
    key_version  INTEGER NOT NULL DEFAULT 1,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rotated_at   TIMESTAMPTZ
);
```

#### SQLAlchemy-Integration (Skizze)

```python
# app/core/crypto.py
from cryptography.fernet import Fernet, MultiFernet
from app.core.config import settings

_master = MultiFernet([Fernet(k) for k in settings.encryption_keys])  # Liste!

def wrap_dek(plaintext_dek: bytes) -> bytes:
    return _master.encrypt(plaintext_dek)

def unwrap_dek(wrapped: bytes) -> bytes:
    return _master.decrypt(wrapped)

def encrypt_field(plaintext: str, dek: bytes) -> bytes:
    return Fernet(dek).encrypt(plaintext.encode("utf-8"))

def decrypt_field(ciphertext: bytes, dek: bytes) -> str:
    return Fernet(dek).decrypt(ciphertext).decode("utf-8")
```

Im Request-Lifecycle: Auth-Dependency lädt den DEK des aktuellen Users einmal pro Request, hält ihn in einer **`ContextVar`** (`app.core.crypto._current_dek`), Service-Layer und der `EncryptedString`-TypeDecorator lesen daraus. Cleanup erfolgt im FastAPI `yield`-Pattern (`finally: reset_current_user_dek(token)`), so dass keine Schlüsselreste über Request-Grenzen hinweg geteilt werden.

**Mischweg Symptom-Modell (Issue #26 / ADR-0008):** Für `symptoms` gibt es zwei Spalten — `name` (plaintext, nur für `is_default=TRUE`) und `name_enc` (BYTEA, nur für `is_default=FALSE`). Eine Tabellen-CHECK-Constraint (`ck_symptoms_name_storage_consistency`) erzwingt die Exklusivität. Auf Modell-Ebene macht `Symptom.display_name` den Polymorphismus transparent für Endpoints/Schemas. Der `EncryptedString`-TypeDecorator wird hier nicht genutzt, weil Default-Reads (z. B. `GET /symptoms/default`) ohne Auth-Kontext funktionieren müssen — die Encrypt/Decrypt-Calls liefen sonst in `DekUnavailableError`.

### Warum nicht pgcrypto?

`pgcrypto` (z. B. `pgp_sym_encrypt`) wäre eine valide Alternative, wurde aber gegen Fernet abgewogen und **verworfen**. Drei entscheidende Gründe:

1. **Connection-Pool-Risiko:** pgcrypto erfordert das Setzen des Schlüssels via `SET myapp.encryption_key = '...'` pro Session. Mit asyncpg-Pool und FastAPI bleibt der Key auf der Connection bestehen, wenn sie in den Pool zurückkehrt — eine andere Anfrage könnte ihn lesen oder mit dem falschen Key arbeiten. Saubere Disziplin via `SET LOCAL` in jeder Transaktion ist möglich, aber fehleranfällig. **Fernet hat dieses Problem nicht**, weil der Key im Application-Process bleibt.
2. **Pro-User-Key ist mit pgcrypto teuer:** Pro Query müsste der DEK des aktiven Users in eine Session-Variable geschrieben werden — pro Verbindungswechsel ein zusätzlicher Roundtrip. Mit Fernet ist der DEK einfach ein Python-`bytes`-Objekt im Request-State.
3. **Schlüssel-Rotation:** Fernet bietet via [`MultiFernet.rotate()`](https://cryptography.io/en/latest/fernet/) ein sauberes, idempotentes Rotationsverfahren — der Master-Key kann iterativ getauscht werden, alte Keys werden zur Decrypt-Phase parallel akzeptiert. Mit pgcrypto müsste eine eigene Re-Encrypt-Loop in SQL gebaut werden, schwer ohne Downtime.

Die Crunchy-Data-Empfehlung „Don't encrypt unless you need it" (siehe [Quellen](#quellen)) gilt für **beide** Ansätze — wir verschlüsseln, weil Art. 9 DSGVO und das Backup-Diebstahl-Szenario es erzwingen, nicht aus Vorsicht.

### Schlüssel-Rotation (Master-Key) — konkretes Verfahren

```python
# 1. Neuen Master-Key generieren
new_key = Fernet.generate_key()

# 2. ENCRYPTION_KEYS in der Konfiguration auf Liste umstellen:
#    ENCRYPTION_KEYS=<new_key>,<old_key>
#    (neue Keys vorne, alte hinten — solange sie noch in Verwendung sind)

# 3. Background-Job über alle Rows in user_encryption_keys:
mf = MultiFernet([Fernet(new_key), Fernet(old_key)])
for row in user_encryption_keys:
    row.wrapped_dek = mf.rotate(row.wrapped_dek)
    row.rotated_at = now()
    row.key_version += 1

# 4. Wenn alle Rows rotiert sind: alten Key aus ENCRYPTION_KEYS entfernen.
```

`MultiFernet.rotate()` re-encryptet unter dem **ersten** Key der Liste, behält den ursprünglichen Timestamp. Kein Downtime, beliebig pausierbar.

### E2E-Verschlüsselung (Backlog / M12+)

- **Opt-in** für Power-User, die volle Client-Side-Kontrolle wünschen
- **Implementierung:** `libsodium` via Web Crypto API (clientseitig), Server speichert nur Ciphertext
- **Migration:** Der DEK wandert vom Server in den Client (per Passphrase abgeleitet via Argon2id). Schema bleibt identisch — `wrapped_dek` wird einfach nicht mehr serverseitig entwrappbar.
- **Trade-off:** Bricht serverseitige Insights für betroffene Felder vollständig → sinnvoll nur für `notes`, nicht für `mood_score` / `symptoms`

---

## Alternativen erwogen

| Option                                 | Vorteile                                                                                                                        | Nachteile                                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Kein Encryption at-rest**            | Kein Aufwand, volle FTS-Funktionalität                                                                                          | Art.-9-DSGVO-Risiko, Daten bei Backup-Diebstahl im Klartext, **inakzeptabel**                      |
| **Nur Stufe 1 (LUKS + SSE)**           | Sehr einfach, transparent                                                                                                       | Schützt nicht vor Backup-/`pg_dump`-Diebstahl der entpackten Daten, nicht vor Read-Only-DB-Zugriff |
| **pgcrypto Column-Level**              | In PostgreSQL eingebaut, kein zusätzlicher App-Code                                                                             | Connection-Pool-Risiko, pro-User-Key teuer, Key-Rotation aufwendig, schwächere Performance         |
| **App-Level Fernet (pro-User-Key)** ✅ | Gute Performance (~0.1 ms/Feld), pro-User-Key trivial, authenticated encryption, saubere Rotation via MultiFernet, Python-nativ | FTS auf verschlüsselten Feldern nicht möglich (Workaround via Dexie.js)                            |
| **E2E Client-Side (libsodium)**        | Maximaler Schutz, Server sieht keine Klartextdaten                                                                              | Bricht serverseitige Insights, höchste Implementierungskomplexität, für Phase 1 überdimensioniert  |

---

## Konsequenzen

- **Key-Management:**
  - `ENCRYPTION_KEY` (oder `ENCRYPTION_KEYS` als Komma-Liste während Rotation) als Umgebungsvariable, nie in der Codebase
  - Generierung: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  - Key-Rotation: dokumentiertes Verfahren via `MultiFernet.rotate()`, Background-Job, kein Downtime
- **Backup-Sicherheit:**
  - Backups enthalten verschlüsselte Daten – **ohne `ENCRYPTION_KEY` nicht wiederherstellbar**
  - Kritischer Hinweis in der Deployment-Dokumentation: **`ENCRYPTION_KEY` separat und sicher backuppen** (z. B. Vaultwarden / Bitwarden Secrets / Hardware-Token)
- **Performance:** Fernet-Verschlüsselung ~0.1 ms pro Feld bei typischen Dateigrößen (Notizen < 10 KB) – vernachlässigbar gegenüber DB-Latenz. Pro Request +1 DB-Roundtrip für `user_encryption_keys`-Lookup, mit Caching auf Request-Ebene auf **einen** Roundtrip pro Request begrenzt
- **DSGVO-Compliance:** Verschlüsselung at-rest ist eine der ausdrücklich empfohlenen technischen Maßnahmen gemäß **Art. 32 DSGVO** (Sicherheit der Verarbeitung); dokumentiert als Teil des TOM-Verzeichnisses
- **Account-Löschung (Art. 17):** Beim `DELETE /api/v1/user/me` (Issue #66) wird die `user_encryption_keys`-Row über `ON DELETE CASCADE` gelöscht — die Ciphertext-Felder sind danach kryptografisch wertlos, selbst wenn sie aus alten Backups rekonstruiert würden („cryptographic erasure")

---

## Umsetzung

| Meilenstein | Aufgabe                                                                                                                                                                        |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **M0** ✅   | Stufe 1: MinIO SSE aktiviert (`MINIO_KMS_AUTO_ENCRYPTION: 'on'`), Traefik HSTS-Konfiguration, `ENCRYPTION_KEY` in `.env.example` dokumentiert                                  |
| **M1**      | Stufe 2: Migration `user_encryption_keys`, `app/core/crypto.py`, SQLAlchemy-`TypeDecorator` für verschlüsselte Felder, DEK-Generierung bei Registrierung, Key-Rotation-Runbook |
| **M9**      | LUKS-Volume-Dokumentation für Selfhost-Deployment, restic-Backup-Konfiguration im Install-Guide                                                                                |
| **M12+**    | E2E-Verschlüsselung als Opt-in für Power-User (Backlog)                                                                                                                        |

---

## Quellen

- [`cryptography.io` — Fernet](https://cryptography.io/en/latest/fernet/) (Algorithmus, MultiFernet-Rotation)
- [Crunchy Data — Postgres pgcrypto](https://www.crunchydata.com/blog/postgres-pgcrypto) (Komplexitäts-Warnung)
- [OneUptime — PostgreSQL Data at Rest Encryption](https://oneuptime.com/blog/post/2026-01-21-postgresql-data-at-rest-encryption/view) (pgcrypto Performance, Filesystem-Vergleich)
- [PostgreSQL-Diskussion zu TDE/LUKS](https://www.reddit.com/r/PostgreSQL/comments/eq3nlp/transparent_data_encryption_for_postgresql/) (Begrenzung von LUKS bei laufender DB)
