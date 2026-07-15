# ADR-0039: Slug-HMAC für Custom-Symptome

**Datum:** 2026-07-15  
**Status:** Accepted  
**Bezug:** ADR-0005 (Verschlüsselung at-rest), ADR-0008 (Symptom-Master-Tabelle), Issue #62

---

## Kontext

ADR-0005 ließ `symptoms.slug` auch für Custom-Symptome bewusst im Klartext, weil der Slug aus dem Nutzernamen abgeleitet wird (z. B. `migraene_mit_aura`) und Operability (Debugging, Recovery, eindeutige Fehler-Logs) für M1 wichtiger war als der zusätzliche semantische Leak.

Mit M9+ / vor Public-Selfhost-Release steht ein Hardening an: Der semantische Slug darf nicht in der Datenbank, Backups oder Read-Only-DB-Zugriffen lesbar bleiben. `symptoms.name_enc` ist bereits Fernet-verschlüsselt (Issue #26); der Slug war die verbleibende plaintext-Spur.

`entry_symptoms` referenziert Symptome per `symptom_id` (UUID), nicht per Slug — eine Slug-Umstellung ist daher ohne FK-Risiko möglich.

---

## Entscheidung

1. **Separater Key:** `SLUG_HMAC_KEY` (Umgebungsvariable), unabhängig von `ENCRYPTION_KEY`.
2. **Algorithmus:** Deterministisches HMAC-SHA256 über `"{user_id}:{semantic_slug}"`, gespeichert als 64-Zeichen-Hex-Digest (passt in `String(64)` und das bestehende Slug-Format).
3. **Scope:** Nur Custom-Symptome (`user_id IS NOT NULL`, `is_default = FALSE`). Curated Defaults behalten ihre kuratierten Slugs (`headache`, …).
4. **API-Vertrag:** Clients senden weiterhin einen semantischen Slug bei `POST /symptoms`; der Server persistiert den HMAC-Slug. Antworten liefern den gespeicherten (HMAC-)Slug — Clients nutzen `symptom_id` für Zuweisungen.
5. **Migration 026:** Bestehende Custom-Symptom-Slugs werden in-place auf HMAC-Form remapped. Erfordert gesetztes `SLUG_HMAC_KEY` (idempotent: bereits-HMAC-Slugs werden übersprungen).

Implementierung: `app/services/slug_hmac.py`, Aufruf in `symptom_service.create_custom_symptom`.

---

## Alternativen erwogen

| Option                             | Vorteile                                        | Nachteile                                                       |
| ---------------------------------- | ----------------------------------------------- | --------------------------------------------------------------- |
| Slug plaintext lassen (Status quo) | Einfach, debuggbar                              | Semantischer Leak in DB/Backups                                 |
| Zufälliger Slug (UUID/Random)      | Kein Leak                                       | Nicht idempotent; Duplikat-Erkennung bei Retry schwieriger      |
| **HMAC deterministisch** ✅        | Kein Leak, idempotent, Unique pro User+Semantik | Key-Rotation erfordert Re-Migration; Downgrade nicht reversibel |
| Slug aus `name_enc` ableiten       | Ein Feld weniger                                | Braucht DEK zum Lesen; bricht Default-Reads                     |

---

## Konsequenzen

- **Key-Management:** `SLUG_HMAC_KEY` mindestens 32 Bytes Entropie, separat von `ENCRYPTION_KEY` sichern. Rotation: neuen Key setzen, Re-Migration aller Custom-Slugs (bewusster Ops-Schritt).
- **Uniqueness:** Partial-Index `(user_id, slug)` bleibt gültig; gleicher semantischer Slug desselben Users liefert denselben HMAC → 409 wie bisher.
- **Default-Kollision:** Semantischer Slug wird vor HMAC gegen Default-Slugs geprüft (`headache` → 409).
- **Logs:** Custom-Slugs bleiben aus Logs ausgeschlossen (bereits maskiert in `Symptom.__repr__`).
- **Downgrade:** Migration 026 ist nicht reversibel (semantischer Slug geht verloren).

---

## Umsetzung

| Artefakt             | Beschreibung                                           |
| -------------------- | ------------------------------------------------------ |
| `SLUG_HMAC_KEY`      | Settings + `.env.example`                              |
| `slug_hmac.py`       | `hmac_custom_symptom_slug()`, `is_hmac_symptom_slug()` |
| `symptom_service.py` | HMAC bei `create_custom_symptom`                       |
| Migration `026`      | Remap bestehender Custom-Slugs                         |
| Tests                | Determinismus, Defaults unverändert                    |
