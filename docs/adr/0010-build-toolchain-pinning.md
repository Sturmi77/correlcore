# ADR-0010: Build-Toolchain-Pinning (pnpm-Version)

**Datum:** 2026-05-07
**Status:** Accepted

---

## Kontext

Während der Vorbereitung des ersten User-Test-Deployments (PRs #76 ff.) brach
der Web-CI-Workflow auf jedem frisch erzeugten Feature- oder Fix-Branch
reproduzierbar mit `ERR_PNPM_IGNORED_BUILDS` ab, sobald pnpm beim Install
auf einen Build-Script-Lifecycle stieß (`esbuild@0.19.12`, `esbuild@0.21.5`,
`es5-ext@0.10.64`):

```text
[ERR_PNPM_IGNORED_BUILDS] Ignored build scripts: es5-ext@0.10.64,
                          esbuild@0.19.12, esbuild@0.21.5
Run "pnpm approve-builds" to pick which dependencies should be allowed to
run scripts.
```

`main` lief dagegen anstandslos durch — der Bug trat ausschließlich auf
neuen Branches auf. Diese Diskrepanz hatte zwei kombinierte Ursachen:

### Ursache 1: pnpm-Version war nicht gepinnt

Sowohl der GitHub-Actions-Job-Step (`pnpm/action-setup@v4` mit
`version: 'latest'`) als auch das Web-Dockerfile (`corepack enable` ohne
`packageManager`-Feld in `package.json`) zogen jeweils die zum Zeitpunkt
des Runs neueste pnpm-Version. Innerhalb weniger Tage wechselte das von
pnpm 10.x auf pnpm 11.x — und pnpm 11 bringt eine ganze Reihe von
Breaking Changes mit, die das Verhalten unterschiedlich machten.

### Ursache 2: pnpm 10/11 lesen Build-Script-Allowlist unterschiedlich

- **pnpm 9 und früher**: implizit erlaubt, Build-Scripts laufen ohne
  Allowlist. Das war der Stand, mit dem das Repo ursprünglich aufgesetzt
  wurde (`engines.pnpm: ">=9.0.0"`).
- **pnpm 10.x** (ab 10.0): Build-Scripts werden _ignoriert_ und brechen
  in non-interaktiven Umgebungen den Install ab; Allowlist via
  `onlyBuiltDependencies` in `pnpm-workspace.yaml`.
- **pnpm 10.26+**: zusätzlich `allowBuilds`-Map verfügbar (Migration vor v11).
- **pnpm 11.0**: `onlyBuiltDependencies` entfernt, **nur noch**
  `allowBuilds` wird gelesen.

Auf `main` half der GitHub-Actions-Cache, weil dort `node_modules` mit
bereits ausgeführten Build-Scripts vorgehalten wurde — pnpm musste bei
einem Cache-Hit gar nicht erst install ausführen. Frische Branches
hatten keinen Cache und liefen in den Build-Script-Check.

In Summe: ein und derselbe Workflow-Code war auf zwei Branches
nicht-deterministisch reproduzierbar, je nachdem ob (a) der Cache
griff und (b) welche pnpm-Version `latest` an dem Tag bedeutete.

---

## Entscheidung

### 1. pnpm-Version explizit pinnen

**Single Source of Truth:** `packageManager`-Feld in der Root-`package.json`:

```json
"packageManager": "pnpm@11.0.8"
```

Corepack im Web-Dockerfile (`RUN corepack enable`) liest dieses Feld und
installiert genau diese Version. Damit ist der Production-Image-Build
reproduzierbar.

**Sekundär:** in `.github/workflows/ci-web.yml` werden alle vier
`pnpm/action-setup@v4`-Steps auf dieselbe Version gepinnt:

```yaml
- name: Setup pnpm
  uses: pnpm/action-setup@v4
  with:
    version: '11.0.8'
```

Doppelt-explizit, weil `pnpm/action-setup@v4` das `packageManager`-Feld
zwar respektiert, aber das `version:`-Argument Vorrang hat — wenn das
auf `latest` stünde, würde es den Pin überschreiben.

### 2. `engines.pnpm` auf `>=11.0.0` heben

Lokale Installationen ohne Corepack (z. B. globale `npm i -g pnpm`)
werden vor dem Install eine pnpm-Version verlangt, die mit der
v11-Konfigurationssyntax (`allowBuilds`) umgehen kann.

### 3. `pnpm-workspace.yaml` auf v11-Syntax bereinigen

Die Übergangs-Lösung mit beiden Schlüsseln (`onlyBuiltDependencies` für
pnpm 10, `allowBuilds` für pnpm 11) wurde durch reine v11-Syntax ersetzt:

```yaml
allowBuilds:
  esbuild: true
  es5-ext: true
```

`esbuild` lädt sein Native-Binary in einem postinstall-Script,
`es5-ext` registriert Polyfill-Hooks transitiv über die ESLint-Toolchain.
Andere Build-Scripts werden weiterhin ignoriert (Allowlist-Prinzip).

### 4. Update-Pfad

Wenn pnpm einen neuen Patch- oder Minor-Release veröffentlicht:

1. Lokal `corepack use pnpm@<version>` ausführen → schreibt
   `packageManager`-Feld in `package.json` neu.
2. In `.github/workflows/ci-web.yml` die Version manuell anpassen
   (vier Stellen, Repo-grep auf `pnpm/action-setup`).
3. CI auf einem Test-Branch laufen lassen, dann mergen.

Major-Updates (z. B. v11 → v12) erfordern zusätzlich eine Prüfung der
`pnpm-workspace.yaml`-Settings gegen die jeweilige Migrations-Doku.

---

## Konsequenzen

### Positiv

- **Reproduzierbarkeit:** CI- und Image-Builds liefern unabhängig vom
  Tag oder Cache-Status dasselbe Ergebnis.
- **Explizite Update-Kontrolle:** Pnpm-Updates werden zu bewussten
  Änderungen mit eigenem Commit + PR + CI-Verifikation, nicht zu
  stillen Drift-Effekten.
- **Klarere Fehler bei Allowlist-Issues:** Wenn ein neues Package
  Build-Scripts mitbringt, scheitert der Install reproduzierbar (auf
  jedem Branch gleich) — und der Fix steht in genau einer Datei
  (`pnpm-workspace.yaml`).

### Negativ / Risiko

- **Manueller Update-Aufwand:** Patch-Updates müssen aktiv eingespielt
  werden, statt automatisch durchzulaufen. Mitigation: Renovate/Dependabot
  kann das `packageManager`-Feld und Workflow-Strings tracken, sobald
  der Maintenance-Aufwand spürbar wird.
- **Risiko bei sehr frischen Versionen:** pnpm 11.0.x hat in der ersten
  Maiwoche 2026 acht Patch-Releases in acht Tagen erhalten. Der Pin
  auf 11.0.8 friert die heutige (`2026-05-07`) Spitze fest; bei einem
  Regressions-Patch muss aktiv hochgezogen werden.

### Neutral

- Das vorhandene Lockfile (`pnpm-lock.yaml`) bleibt unverändert; pnpm 11
  liest 10er-Lockfiles ohne Migration.

---

## Alternativen erwogen

### A. `version: 'latest'` lassen, nur `packageManager` setzen

**Verworfen.** Der `version:`-Parameter im Action-Setup hat Vorrang vor
`packageManager`, wodurch der Pin nur halb wirken würde. CI- und
Image-Toolchain könnten weiter divergieren.

### B. Range-Pin (`>=11 <12`) statt exakter Version

**Verworfen.** Range-Pins re-introduzieren genau das Drift-Problem,
das wir hier loswerden wollen. Bei einer Major-Migration ist
expliziter Hand-Lift mit ADR-Update sowieso nötig; bei Patches ist
ein händischer Bump günstiger als nicht-deterministische CI-Runs.

### C. pnpm 10.x (LTS-artig) statt 11.x pinnen

**Verworfen.** pnpm 10 hat keine offizielle LTS-Garantie und wird ab
Q3 2026 nur noch Security-Fixes erhalten. Der Migration-Aufwand auf v11
ist marginal (`onlyBuiltDependencies` → `allowBuilds`, einmalig). Wir
fahren auf der aktiven Major-Linie und akzeptieren dafür den höheren
Patch-Update-Takt.

---

## Referenzen

- [pnpm 11.0 Release Notes](https://pnpm.io/blog/releases/11.0)
- [pnpm 10.26 Release Notes](https://pnpm.io/blog/releases/10.26) — Einführung von `allowBuilds`
- [pnpm-Settings: `allowBuilds`](https://pnpm.io/settings#allowbuilds)
- PR #84 — Backend-Dockerfile-Hotfix (auf den der Bug zuerst aufschlug)
- PR #85 — pnpm-Allowlist-Hotfix (Übergangs-Konfig mit beiden Schlüsseln)
- `docs/RUNBOOK_DEPLOYMENT.md` — Deployment-Erkenntnisse aus dem ersten User-Test
