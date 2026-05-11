# Documentation Language Plan

CorrelCore uses English as the default language for repository collaboration. This keeps GitHub issues, pull requests, technical reviews and external contributor onboarding accessible to a wider audience while preserving German as a maintained UI locale.

## Policy

- GitHub-facing artifacts are English by default: issues, pull requests, review comments, commit messages, changelog entries and release notes.
- Technical documentation is English by default.
- UI text is handled through i18n. English is the source locale; German remains a maintained translation.
- Internal planning may happen in German or another language, but published GitHub summaries should be translated to English.
- Existing German documents are migrated when they are touched, with contributor and designer workflows first.

## Priority 1: External Collaboration Docs

These documents should be translated or rewritten first because they are the entry points for external developers and UI designers.

| Document                  | Target State                                    | Notes                                                                                                                            |
| ------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`               | Full English rewrite                            | Product pitch, roadmap, quickstart, docs index and contribution section should be readable without German context.               |
| `CONTRIBUTING.md`         | English policy source                           | Completed as the canonical collaboration and language policy.                                                                    |
| `docs/DEVELOPMENT.md`     | Create in English                               | Add local setup, quality gates, branch workflow, PR expectations, test commands and release/image workflow notes.                |
| `docs/FRONTEND.md`        | English rewrite                                 | Important for UI designers: design principles, accessibility, i18n, component structure and chart rules.                         |
| `docs/DESIGN_DOCUMENT.md` | English executive rewrite or phased translation | Keep it as the product source of truth, but prioritize sections 0, 1, 4, 6 and 9 before translating the full long-form document. |

## Priority 2: Engineering Reference Docs

These documents support implementation work and should move to English after the external collaboration docs.

| Document                       | Target State    | Notes                                                                        |
| ------------------------------ | --------------- | ---------------------------------------------------------------------------- |
| `docs/ARCHITECTURE.md`         | English rewrite | Architecture diagrams, deployment topology and sync/security assumptions.    |
| `docs/API.md`                  | English rewrite | Endpoint contracts, auth behavior, examples and privacy constraints.         |
| `docs/RUNBOOK_DEPLOYMENT.md`   | English rewrite | Keep local deployment examples concrete; avoid environment-specific secrets. |
| `docs/RUNBOOK_KEY_ROTATION.md` | English rewrite | Security runbook should be precise and globally readable.                    |
| `docs/DATA_EXPORT_FORMAT.md`   | Already English | Keep as the export-format reference.                                         |

## Priority 3: Historical and Decision Docs

ADRs and quality-gate notes may remain in their original language until they are touched, but new ADRs should be English.

| Document Group            | Target State                                                        | Notes                                                                           |
| ------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `docs/adr/*.md`           | New ADRs in English; migrate old ADRs opportunistically             | Preserve decision history. Do not rewrite meaning while translating.            |
| `docs/quality/*.md`       | New notes in English                                                | Existing quality notes can be translated when referenced by current milestones. |
| `docs/DSGVO.md`           | English title/content with German legal term preserved where useful | Consider renaming to `docs/GDPR.md` with a compatibility link or reference.     |
| `docs/MARKET_ANALYSIS.md` | English rewrite when product/positioning work resumes               | Lower priority than contributor onboarding.                                     |

## Suggested Sprint Plan

1. **Documentation Sprint A: Contributor Onboarding**
   - Rewrite `README.md` in English.
   - Create `docs/DEVELOPMENT.md`.
   - Keep `CONTRIBUTING.md` as the language-policy source.
   - Add a short docs index that tells external contributors where to start.

2. **Documentation Sprint B: UI and Product Collaboration**
   - Rewrite `docs/FRONTEND.md` in English.
   - Extract designer-facing rules from `docs/DESIGN_DOCUMENT.md` into a concise section or companion doc.
   - Verify all UI copy continues to live in `en.json` and `de.json`.

3. **Documentation Sprint C: Architecture and Operations**
   - Rewrite `docs/ARCHITECTURE.md`, `docs/API.md` and deployment runbooks.
   - Normalize examples, commands and release-image instructions.
   - Make sure GHCR image tags, digest handling and developer-view diagnostics are documented in one place.

4. **Documentation Sprint D: ADR and Quality Archive**
   - Translate only ADRs and quality notes that are still active references.
   - Leave historical docs untouched unless they confuse current contributors.

## Review Checklist

- The document is understandable without German project context.
- GitHub issue and PR references use English summaries.
- UI text changes update both English and German locale files.
- Medical, privacy and GDPR wording remains precise.
- No secrets, host-specific values or private deployment details are introduced.
