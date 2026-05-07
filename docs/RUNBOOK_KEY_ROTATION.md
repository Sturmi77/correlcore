# Runbook: Master-Key-Rotation (`ENCRYPTION_KEY`)

**Bezug:** [ADR-0005](adr/0005-verschluesselung-at-rest.md), Issue #26
**Status:** M1 — Online-Setup, ein Postgres, ein FastAPI-Worker

Dieses Runbook beschreibt, wie der **Master-Key** (`ENCRYPTION_KEY`) ohne Downtime getauscht wird. Er wrappt die per-User Data-Encryption-Keys (DEKs) in der Tabelle `user_encryption_keys`. Die DEKs selbst bleiben bei der Rotation unverändert — nur ihr Wrapping wird re-encryptet.

---

## Wann rotieren?

- **Verdacht auf Kompromittierung** des aktuellen Master-Keys (Leak in Logs, Backup-Diebstahl, Insider-Vorfall).
- **Geplante Routine-Rotation** (empfohlen alle 12 Monate, ab M9 als regelmäßiger Maintenance-Task im Selfhost-Guide dokumentiert).
- **Nach Key-Format-Migration** (z. B. zukünftige Aufrüstung auf Fernet-Nachfolge).

---

## Voraussetzungen

- Schreibzugriff auf `.env` bzw. das Secrets-Backend (Vaultwarden / Bitwarden Secrets / Hardware-Token).
- Datenbank-Snapshot **vor** der Rotation (`pg_dump`-Vollbackup, restic-Snapshot).
- Ein Maintenance-Fenster ist **nicht erforderlich** — die Rotation läuft online; alte und neue Keys werden während der Übergangsphase parallel akzeptiert.

---

## Vorgehen

### 1. Neuen Master-Key generieren

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Das Ergebnis ist ein 44-Zeichen-URL-safe-base64-String. Er muss **vor** dem nächsten Schritt sicher abgelegt sein (Secrets-Backend, **nicht** in Git).

### 2. `ENCRYPTION_KEYS` auf Liste umstellen

In `.env` (bzw. dem Secrets-Backend) den alten Single-Key durch eine Liste ersetzen — **neuer Key zuerst, alter Key dahinter**:

```env
# vorher:
ENCRYPTION_KEY=<alter_key>

# nachher:
ENCRYPTION_KEYS=<neuer_key>,<alter_key>
```

> **Hinweis:** Beide Variablen werden vom Settings-Loader unterstützt (`effective_encryption_keys()`). `ENCRYPTION_KEYS` hat Vorrang, wenn beide gesetzt sind. Die Liste wird in der Reihenfolge ausgewertet, in der sie steht — der erste Key wird für **neue** Verschlüsselungen genutzt, alle weiteren nur zum **Entschlüsseln** existierender Tokens.

### 3. App neu starten

```bash
docker compose restart backend  # oder gleichwertig
```

Die App liest die neuen Keys, baut den `MultiFernet` mit beiden auf. **Bestehende Sessions / DEKs entwrappen weiter mit dem alten Key.** Neue DEK-Wrappings (z. B. neue Registrierungen) verwenden bereits den neuen Key.

### 4. Re-Wrap aller DEKs (Online-Job)

In einer laufenden Backend-Shell oder einem One-Shot-Container:

```python
# scripts/rotate_master_key.py
import asyncio
from sqlalchemy import select, update
from cryptography.fernet import Fernet, MultiFernet

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.user_encryption_key import UserEncryptionKey

async def main() -> None:
    keys = settings.effective_encryption_keys()
    if len(keys) < 2:
        raise SystemExit("ENCRYPTION_KEYS must contain new and old key")

    mf = MultiFernet([Fernet(k.encode()) for k in keys])
    rotated = 0

    async with async_session_factory() as db:
        result = await db.execute(select(UserEncryptionKey))
        for row in result.scalars().all():
            row.wrapped_dek = mf.rotate(bytes(row.wrapped_dek))
            row.key_version += 1
            row.rotated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            rotated += 1
        await db.commit()
    print(f"rotated {rotated} DEK wrappings")

asyncio.run(main())
```

Skript ausführen:

```bash
docker compose exec backend python scripts/rotate_master_key.py
```

`MultiFernet.rotate()` re-encryptet jedes Wrapping unter dem **ersten** Key (= neuer Key). Der ursprüngliche Token-Timestamp bleibt erhalten. Die Operation ist idempotent: ein bereits unter dem neuen Key liegendes Wrapping wird einfach erneut unter dem neuen Key gewrappt.

### 5. Alten Key entfernen

Wenn das Skript erfolgreich durchgelaufen ist (Output: `rotated N DEK wrappings`, N = Anzahl User), kann der alte Key aus `ENCRYPTION_KEYS` entfernt werden:

```env
ENCRYPTION_KEYS=<neuer_key>
```

App nochmal neu starten. Ab jetzt akzeptiert der `MultiFernet` nur noch den neuen Key.

### 6. Verifikation

- `pytest backend/tests/test_crypto.py -q` (lokal) — alle Roundtrips müssen grün sein.
- `curl -fsS http://<host>:<api-port>/health/ready | jq '.components[] | select(.name=="encryption")'` — muss `"status": "ok"` liefern (siehe Abschnitt **Healthcheck-Verhalten**).
- Login-Flow als Testuser durchspielen, Custom-Symptom anlegen, Note schreiben → in der DB sollten neue Ciphertext-Bytes erscheinen, die NICHT mit dem alten Key entschlüsselbar sind.
- `SELECT key_version, COUNT(*) FROM user_encryption_keys GROUP BY key_version` → alle Rows sollten auf der neuen Version liegen.

### 7. Alten Key sicher vernichten

Nach erfolgreicher Verifikation den alten Key aus dem Secrets-Backend löschen (Vault-Eintrag entfernen, Hardware-Token überschreiben). **Nicht in Backups behalten** — sonst neutralisiert die Rotation ihren eigenen Zweck.

---

## Healthcheck-Verhalten während Rotation

`/health/ready` enthält seit Issue #68 (M1-Quality-Gate, SA-5) eine `encryption`-Probe, die einen kompletten Master-Fernet-Roundtrip ausführt: `generate_dek()` → `wrap_dek()` → `unwrap_dek()` → Byte-Vergleich. Damit fällt eine fehlerhafte Master-Key-Konfiguration sofort auf (vorher hätte `200 OK` Traffic auf einen Knoten geroutet, der bei jedem authentifizierten Request still 401 gibt).

| Phase                                                                      | `components[encryption].status`      | Anmerkung                                                                                                                                                |
| -------------------------------------------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Stabil** (alter Key alleine)                                             | `ok`                                 | Wrap mit altem Key, Unwrap mit altem Key.                                                                                                                |
| **Phase 2** — `ENCRYPTION_KEYS=NEW,OLD` nach App-Restart                   | `ok`                                 | `MultiFernet` wrapt mit `NEW` (erster in der Liste), `unwrap_dek` versucht beide. Probe ist grün, sobald **mindestens ein** Key valide ist.              |
| **Phase 4** — Re-Wrap-Job läuft                                            | `ok`                                 | Probe ist von User-DEKs entkoppelt — sie testet nur den Master-Key, nicht einzelne `wrapped_dek`-Rows. Der Re-Wrap-Status wird gesondert geloggt.        |
| **Phase 5** — alten Key aus Liste entfernt + Restart                       | `ok`                                 | Neuer Key alleine, Roundtrip funktioniert.                                                                                                               |
| **Fehlkonfiguration** — `ENCRYPTION_KEY` leer / fehlt                      | `down` (`detail=RuntimeError`)       | `wrap_dek` wirft `"No encryption key configured"`. Probe loggt nur den Klassennamen (ADR-0007), niemals den fehlenden Variablennamen oder Settings-Dump. |
| **Fehlkonfiguration** — ungültige Fernet-Bytes (32-Byte-Base64-URL falsch) | `down` (`detail=RuntimeError`)       | `_build_master` wirft generische Fehlermeldung ohne Key-Material.                                                                                        |
| **Schwerer Crypto-Bug** — Roundtrip liefert andere Bytes                   | `down` (`detail=roundtrip_mismatch`) | Defensive Prüfung. Sollte in Praxis nie passieren — wenn doch, sofort eskalieren.                                                                        |

**Operative Konsequenz während Rotation:**

- Wenn nach Restart in Phase 2 oder 5 die Probe auf `down` springt, ist der Restart auf einen Knoten gegangen, der die ENV-Variable nicht gelesen hat (häufig: Compose-Override mit veraltetem File, Container-Cache). Sofort `docker compose config | grep -A2 ENCRYPTION` prüfen, **bevor** der Re-Wrap-Job in Phase 4 gestartet wird — dieser würde sonst alle DEKs in einen nicht-rekonstruierbaren Zustand bringen.
- Uptime-Kuma / Traefik werten `/health/ready` als 503, sobald **eine** Komponente nicht-OK ist — Traffic wird während einer Fehlkonfiguration also automatisch vom Service abgezogen.
- Die Probe ist **synchron** (Fernet ist CPU-bound, Mikrosekunden) — sie verzögert `/health/ready` nicht messbar.

---

## Rollback

Solange der alte Key noch in `ENCRYPTION_KEYS` steht (Phase 2–4), ist Rollback trivial:

1. Neuen Key aus der Liste entfernen.
2. App neu starten.

Nach Schritt 5 ist Rollback **nur über das DB-Backup** vor Schritt 4 möglich — alle DEK-Wrappings sind dann nur noch unter dem neuen Key entschlüsselbar.

---

## Was wenn der Master-Key verloren geht?

Ohne Master-Key sind die DEKs in `user_encryption_keys` unentschlüsselbar — und damit alle `entries.note_enc` / `symptoms.name_enc` der betroffenen User. Es gibt **keinen** Recovery-Pfad. Genau das ist die "cryptographic erasure"-Eigenschaft, die wir bei DSGVO-Art.-17-Löschungen ausnutzen — sie wirkt aber genauso unabwendbar bei versehentlichem Key-Verlust.

**Daher:** Master-Key separat von DB-Backups, in einem Hardware-Token / Vault sichern. Mehrere unabhängige Kopien (mind. zwei) an getrennten physischen Orten. **Niemals** im selben Backup-Set wie die Datenbank.

---

## Referenzen

- [ADR-0005 — Datenverschlüsselung at-rest](adr/0005-verschluesselung-at-rest.md)
- [`cryptography.io` — MultiFernet.rotate()](https://cryptography.io/en/latest/fernet/#cryptography.fernet.MultiFernet.rotate)
- Issue #26 — App-Level Fernet at-rest (M1)
