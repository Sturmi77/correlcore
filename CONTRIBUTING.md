# Contributing to CorrelCore

CorrelCore is currently maintained as a solo project. Contributions are welcome once the project reaches v1.0. Until then, issues, discussions and pull requests should follow the rules below.

## Language Policy

Repository artifacts are written in English by default:

- GitHub issues, pull requests, review comments, commit messages, changelog entries and technical documentation.
- Source code, tests, API names, internal identifiers and Architecture Decision Records.
- UI copy is managed through i18n keys, with English as the source locale and German as a maintained translation.

Project planning may happen in another language, but GitHub-facing summaries should be translated to English before publication.

Existing German documentation should be migrated opportunistically when it is touched. Contributor-facing and designer-facing documents have priority; see [Documentation Language Plan](docs/DOCUMENTATION_LANGUAGE_PLAN.md).

## Issues & Discussions

- **Bug reports:** use the issue template.
- **Feature requests:** discuss larger product changes first, then open an issue with clear acceptance criteria.
- **Questions:** use GitHub Discussions when available.

## Pull Requests

1. Create a fork or feature branch.
2. Use a short English branch name, for example `feat/tag-settings` or `fix/export-scale-legend`.
3. Check the Definition of Done in [DESIGN_DOCUMENT.md](docs/DESIGN_DOCUMENT.md).
4. Open the pull request against `main`.
5. Use English for the PR title, summary, test plan and review comments.
6. Request at least one review once the project has more than one active maintainer.

## Code Style

- Python: `ruff` for linting and formatting.
- TypeScript/Svelte: `prettier`, `eslint` and `svelte-check`.
- Commit messages: [Conventional Commits](https://www.conventionalcommits.org/).
- UI strings: no hardcoded user-facing strings in Svelte templates; add or update i18n keys instead.

## Medical Disclaimer

CorrelCore processes health-related data. Any contribution that touches correlation claims, medical language, symptom interpretation or diagnosis-adjacent functionality needs extra review. When in doubt, open an issue and ask before implementing.
