# Release-Kandidat v1.9.2-rc.1

Stand: 01.10.2026. Dieses Dokument legt fest, **was** der Kandidat ist. Es erteilt keine Freigabe.

## Identität

| Feld            | Wert                                                                                                                                     |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Git-Tag         | `v1.9.2-rc.1` (annotiert)                                                                                                                |
| Commit          | `5de4c1c5a8ab7e10428919c30a9a9168776fed98` (Merge von [#1052](https://github.com/Sturmi77/correlcore/pull/1052))                         |
| Basis           | enthält #1043–#1045 und #1053–#1055; `main` war beim Taggen unverändert                                                                  |
| API-Image       | `ghcr.io/sturmi77/correlcore-api@sha256:fa35cef8cf2d9528a1a488c15fd3d989480445fc0c3b56ae4a1693ac04662d2c`                                |
| Web-Image       | `ghcr.io/sturmi77/correlcore-web@sha256:5760230bfb261336c20cf4adefaa44e0d0bf055c80a54fdde61f68906b2aa770`                                |
| Android         | [Pre-Release](https://github.com/Sturmi77/correlcore/releases/tag/v1.9.2-rc.1) mit `correlcore-1.9.2-rc.1.aab`, `.apk`, `SHA256SUMS.txt` |
| Android-Version | `versionName` 1.9.2-rc.1, `versionCode` 100900201 (neues Schema, siehe CHANGELOG)                                                        |

Maßgeblich sind die **Digests**, nicht die Tags.

## Warum die Digests und nicht `:sha-5de4c1c` oder `:main`

Derselbe Commit wurde zweimal gebaut: beim Push nach `main` und beim Push des Tags. Die Builds sind nicht
bit-gleich, die Tags zeigen deshalb auf verschiedene Digests:

| Tag                | API-Digest (Anfang) | Web-Digest (Anfang) | Herkunft                   |
| ------------------ | ------------------- | ------------------- | -------------------------- |
| `:1.9.2-rc.1`      | `fa35cef8…`         | `5760230b…`         | Tag-Lauf (**Kandidat**)    |
| `:sha-5de4c1c`     | `fa35cef8…`         | `5760230b…`         | vom Tag-Lauf überschrieben |
| `:main`, `:latest` | `b3b4634691…`       | `162b5ac296…`       | Push-Lauf auf `main`       |

`:sha-<short>` ist also nicht unveränderlich. Der Image-Tag wurde bare (`1.9.2-rc.1`) statt `v`-präfixiert
veröffentlicht; die Umschreibung auf `:v1.9.2-rc.1` erledigt der Alias-Job nur bei einem Push nach `main` oder
manuellem Start und wurde bewusst nicht ausgelöst, weil das `:latest` neu bauen würde. Verwendet werden die
Digests.

## Geprüft (lokal, an den Digests)

- Labels: `org.opencontainers.image.revision` = Commit oben, `version` = `1.9.2-rc.1` (API und Web).
- API: `import app.main` erfolgreich; SQLAlchemy 2.0.49 mit `greenlet` 3.5.0, PyJWT 2.15.1,
  `settings.APP_VERSION` = 1.9.2; OpenSSL und PCRE2 auf `deb13u3`; kein System-`pip`; Prozess als `correlcore`.
- Web: `node` 26.10.0 läuft; `npm`/`npx` nicht vorhanden; Prozess als `correlcore`.
- Nicht geprüft: Trivy gegen genau diese Digests (läuft in A10), Start gegen Datenbank, Browser-Journey.

## A10-Eingaben für diesen Kandidaten

```text
release_sha = 5de4c1c5a8ab7e10428919c30a9a9168776fed98
api_image   = ghcr.io/sturmi77/correlcore-api@sha256:fa35cef8cf2d9528a1a488c15fd3d989480445fc0c3b56ae4a1693ac04662d2c
web_image   = ghcr.io/sturmi77/correlcore-web@sha256:5760230bfb261336c20cf4adefaa44e0d0bf055c80a54fdde61f68906b2aa770
staging_url = <isolierte, proxy-gestützte Staging-Instanz, die genau diese Digests ausführt>
```

Die Umgebung `audit-rc` existiert seit dem 01.10.2026 (nur für `main` freigegeben), enthält aber noch **keine**
Secrets und Variablen. Offen bleibt:

- Secrets `A10_SSH_HOST`, `A10_SSH_KEY`, `A10_SSH_KNOWN_HOSTS` (Hostschlüssel unabhängig bestätigen),
  `A10_USER_A_EMAIL`, `A10_USER_A_PASSWORD`, `A10_USER_B_EMAIL`, `A10_USER_B_PASSWORD`.
- Variablen `A10_API_CONTAINER`, `A10_WEB_CONTAINER`.
- Eine Staging-Instanz, die die beiden Digests ausführt, mit Migration von einem v1.9.1-Datenstand.

## A10-Lauf

Der erste Lauf ([Run 36844177924](https://github.com/Sturmi77/correlcore/actions/runs/36844177924)) wurde mit dem
Platzhalter `https://staging.invalid` gestartet, um die Jobs ohne Staging gegen den Kandidaten laufen zu lassen.
Er kann **kein** Manifest erzeugen.

| Job                                                         | Ergebnis                                               |
| ----------------------------------------------------------- | ------------------------------------------------------ |
| Immutable candidate identity                                | bestanden                                              |
| Linux lint, types, unit tests, production build             | bestanden                                              |
| Windows and timezone regression                             | bestanden                                              |
| Migrations, backfills, real PostgreSQL integration          | bestanden                                              |
| Bounded compute and web asset budgets                       | bestanden                                              |
| Production visual, accessibility, download and mobile smoke | **fehlgeschlagen**                                     |
| Real API two-user release journey                           | fehlgeschlagen (erwartet: keine Secrets, kein Staging) |
| Dependency, image and authenticated DAST gates              | übersprungen (hängt am Staging-Job)                    |
| Seal A10 evidence manifest                                  | übersprungen                                           |

### Befund: mobile e2e-Specs veraltet

Im Job „Production visual…“ bestehen `test:e2e:smoke` (inkl. axe: Login, Home, Insights) und `test:e2e:gdpr`.
Vier Specs aus `test:e2e:mobile` schlagen fehl (je mit Retry):

- `m7-insights-mobile.spec.ts` und `mobile-insights-foundation.spec.ts` erwarten `getByText(/Correlation Matrix/i)`
  bzw. `getByTestId('insight-matrix')` auf `/insights`. Die Matrix ist seit Phase 6/D5 nicht mehr Hub-Default.
- `mobile-trends-foundation.spec.ts`: `getByRole('checkbox', { name: 'Mood' })` trifft zwei Elemente (strict mode),
  `getByText('Office')` wird nicht gefunden.

Das ist kein Fehler des Kandidaten: Das Nightly-Workflow `ci-e2e-nightly.yml` ist seit mindestens 26.09. täglich rot.
Die Specs müssen an die aktuelle UI angepasst werden, bevor dieser Job grün werden kann. Bis dahin kann A10 kein
Manifest erzeugen, auch wenn Staging vorhanden ist.
