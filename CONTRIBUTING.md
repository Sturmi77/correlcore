# Contributing to MoodSync

MoodSync ist aktuell ein Solo-Projekt. Contributions sind willkommen, sobald v1.0 released ist. Bis dahin gelten folgende Regeln:

## Issues & Diskussionen

- **Bug Reports:** Issue-Template verwenden
- **Feature-Requests:** Erst in Discussions diskutieren, dann als Issue
- **Fragen:** GitHub Discussions

## Pull Requests (ab v1.0)

1. Fork erstellen
2. Feature-Branch: `git checkout -b feat/kurze-beschreibung`
3. Definition of Done prüfen (siehe [DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md))
4. PR gegen `main` öffnen
5. Mindestens ein Reviewer (ab Team-Größe > 1)

## Code-Style

- Python: `ruff` (Linting + Formatting)
- TypeScript/Svelte: `prettier` + `eslint`
- Commit-Messages: [Conventional Commits](https://www.conventionalcommits.org/)

## Medizinischer Disclaimer

MoodSync verarbeitet Gesundheitsdaten. Jeder Beitrag, der Korrelationsaussagen, medizinische Begriffe oder Diagnosefunktionen betrifft, muss extra reviewt werden. Im Zweifel Issue öffnen und nachfragen.
