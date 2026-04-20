# ADR-0004: Auth-Strategie: Native JWT in Phase 1, Authentik ab Phase 2

**Datum:** 2026-04-20
**Status:** Accepted

---

## Kontext

- **Authentik** ist im Stack als optionales Docker-Compose-Profile definiert und war ursprünglich für alle Phasen als Auth-Lösung vorgesehen.
- **Authentik-Ressourcenbedarf:** ~500 MB RAM + eigene PostgreSQL-Instanz → zu schwergewichtig für den Selfhost-Betrieb in Phase 1. Viele Selfhost-User akzeptieren nicht, eine zweite Datenbank ausschließlich für Auth betreiben zu müssen.
- **FastAPI** kann sauber eine vollständige native JWT-Auth-Lösung implementieren: `python-jose` für JWT, Refresh-Token-Rotation, sichere Cookie-Flags.
- **Für SaaS-Phase (M12+)** ist Authentik für SSO, SAML 2.0 und LDAP-Integration sinnvoll und deckt Enterprise-Anforderungen ab.
- Ziel: Schlanker Selfhost-Stack in Phase 1, späterer Migration Path zu Authentik ohne Breaking Changes.

---

## Entscheidung

### Phase 1 – Native JWT Auth in FastAPI (Selfhost, bis M10)

- **JWT-Generierung:** `python-jose` mit HS256 (symmetrisch, kein Key-Infrastruktur-Overhead)
- **Refresh-Token-Rotation:** Redis-backed, 30 Tage TTL; bei jeder Nutzung wird ein neues Refresh-Token ausgestellt, das alte invalidiert
- **Cookie-Flags:** `HttpOnly`, `Secure`, `SameSite=Strict` – kein Token-Zugriff via JavaScript, CSRF-Schutz
- **Rate-Limiting:** Max. 5 Login-Versuche / Minute pro IP via SlowAPI; nach 10 Fehlversuchen temporärer Account-Lock
- **Passwort-Hashing:** PBKDF2-HMAC-SHA256 (via `passlib`) mit Argon2 als bevorzugtem Algorithmus; bcrypt als Fallback
- **E-Mail-Verifikation:** Pflicht bei Registrierung (Token per E-Mail, 24h TTL)
- **MFA:** TOTP via `pyotp` (Google Authenticator / Authy kompatibel) – optionales Opt-in ab M3

### Phase 2 – Authentik als OIDC-Provider (SaaS, M12+)

- Authentik wird als OIDC-Provider vor FastAPI geschaltet
- FastAPI validiert OIDC-Tokens statt selbst ausgestellte JWTs
- Authentik bleibt im `docker-compose.yml` als **auskommentierter optionaler Block** erhalten (kein Entfernen, nur deaktiviert)

---

## Alternativen erwogen

| Option | Vorteile | Nachteile |
|---|---|---|
| **Native JWT (FastAPI)** ✅ | Kein Ressourcen-Overhead, keine zweite Datenbank, vollständige Kontrolle, Selfhost-freundlich | MFA und SSO müssen selbst implementiert werden |
| **Authentik** | Vollständiges IAM-System, SSO, SAML, LDAP, SCIM out-of-the-box | ~500 MB RAM + eigene Postgres-Instanz, zu schwergewichtig für Phase 1 Selfhost |
| **Logto** | Modernes OIDC/OAuth2-System, gute DX, geringerer Overhead als Authentik | Noch weniger ausgereift als Authentik, proprietäre Hosted-Option, weniger Selfhost-Community |
| **PocketBase** | All-in-One Backend + Auth, sehr leichtgewichtig | Go-basiert (kein Python-Ökosystem), kein nativer FastAPI-Fit, würde den Stack umstrukturieren |
| **Keycloak** | Enterprise-grade, SAML/LDAP/SSO, große Community | Noch schwergewichtiger als Authentik (~1 GB RAM), JVM-basiert, Selfhost-Overhead inakzeptabel |

---

## Konsequenzen

- **Selfhost-Stack wird schlanker:** Kein `authentik`- und kein `authentik-postgres`-Container in der Standard-Compose-Konfiguration.
- **MFA selbst implementieren:** TOTP via `pyotp` ist überschaubar, deckt den Großteil der MFA-Anforderungen ab (kein FIDO2/WebAuthn in Phase 1).
- **Authentik bleibt optional:** Im `docker-compose.yml` bleibt ein auskommentierter `authentik`-Block erhalten; Power-User können ihn aktivieren.
- **Migration Phase 1 → Phase 2:** Bei OIDC-Aktivierung werden Nutzer-Passwörter bei der ersten OIDC-Anmeldung in das Authentik-Passwort-System migriert (Hash-Transfer oder Re-Hashing bei nächstem Login).
- **Security-Baseline:** Die native JWT-Implementierung erfüllt OWASP-Empfehlungen für Session-Management (Rotation, HttpOnly, Rate-Limiting).

---

## Umsetzung

| Meilenstein | Aufgabe |
|---|---|
| **M0** | Auth-Grundgerüst: JWT-Ausstellung, Refresh-Token-Rotation, Passwort-Hashing, E-Mail-Verifikation |
| **M1** | Vollständige Auth-Integration: alle Endpunkte abgesichert, Rate-Limiting aktiv, Login/Logout/Register UI fertig |
| **M3** | TOTP-MFA als optionales Opt-in |
| **M12+** | Authentik OIDC-Integration für SaaS-Phase |
