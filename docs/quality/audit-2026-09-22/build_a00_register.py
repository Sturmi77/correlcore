"""Build A00's traceable registers from the archived audit evidence.

Run from the repository root. This script deliberately preserves unknown
technical outcomes instead of treating a resolved GitHub thread as a fix.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
PLAN = (AUDIT / "REMEDIATION_PLAN.md").read_text(encoding="utf-8")
ARCHIVE = json.loads((AUDIT / "review-evidence.json").read_text(encoding="utf-8"))
THREADS = json.loads((AUDIT / "review-threads-current.json").read_text(encoding="utf-8"))

PACKAGE_ROLE = {
    "A00": "Release-Verantwortung", "A01": "Backend / Datenbank",
    "A02": "Backend / Security", "A03": "Backend + Frontend",
    "A04": "Backend + Frontend / Produkt", "A05": "Backend + Frontend / Security",
    "A06": "Frontend / Produkt", "A07": "Frontend + Backend",
    "A08": "Frontend", "A09": "Backend + Frontend / Lokalisierung",
    "A10": "Release-Verantwortung / CI / Security", "A11": "Release-Verantwortung / Produkt",
    "A12": "Release-Verantwortung / Betrieb / Geräte-QA",
}

# Specific affected paths for each matrix item. These are starting points,
# not a claim that the entire fix scope has already been proven.
FILES = {
    "R1": "backend/migrations/env.py; backend/migrations/versions/048_add_tag_is_pinned.py; backend/migrations/versions/049_drop_entry_note_markers.py; backend/app/services/marker_tag_backfill_service.py",
    "S1": "backend/app/api/v1/endpoints/stats.py; backend/app/services/stats_service.py",
    "R2": "backend/app/services/insight_sections.py; apps/web/src/lib/utils/insightSections.ts",
    "R3": "backend/app/services/insight_dismissal_service.py; backend/app/services/insight_service.py",
    "R4": "apps/web/src/lib/utils/insightMatrixExport.ts; apps/web/src/routes/insights/report/+page.svelte; backend/app/services/export_service.py",
    "S2": "apps/web/src/lib/utils/insightMatrixExport.ts; backend/app/services/export_service.py",
    "R5": "apps/web/src/routes/insights/signal/[id]/+page.svelte; apps/web/src/lib/components/insights/SymptomCooccurrenceHeatmap.svelte; apps/web/src/lib/components/insights/SignalScatter.svelte",
    "R6": "apps/web/src/routes/insights/+page.svelte; apps/web/src/routes/trends/+page.svelte; apps/web/src/lib/components/trends/TrendsComparePanel.svelte",
    "R7": "apps/web/src/lib/components/insights/TagCooccurrenceHeatmap.svelte; backend/app/services/stats_service.py",
    "R8": "backend/app/services/insights/belastung.py; apps/web/src/lib/components/insights/BelastungOverlay.svelte",
    "R9": "backend/app/services/insight_service.py; apps/web/src/lib/i18n/locales/de.json; apps/web/src/lib/i18n/locales/en.json",
    "Wartbarkeit": "backend/app/services/insight_service.py; apps/web/src/routes/insights/+page.svelte; apps/web/src/routes/insights/report/+page.svelte",
    "Tests": "backend/tests; apps/web/src; apps/web/tests/e2e",
    "Zu früher": "docs/frontend/INSIGHT_SURFACE_LAYERS_ROLLOUT_PLAN.md; docs/adr/0043-insight-surface-layers.md",
    "Doku-": "DESIGN_DOCUMENT.md; docs/adr/0043-insight-surface-layers.md",
    "Fehlende": ".github/workflows; backend/tests; apps/web/tests/e2e",
    "Nicht blockierende": ".github/workflows",
}

# Concrete current review findings; historic comments remain explicitly queued
# for technical reassessment in A11 rather than silently being declared fixed.
RECENT = {
    "4070128060": "AUD-12", "4070128068": "AUD-40", "4070128073": "AUD-13",
    "4070128082": "AUD-14", "4070128091": "AUD-04", "4070128097": "AUD-36",
    "4057277069": "AUD-06", "4057276851": "AUD-07", "4057276856": "AUD-08",
    "4057276859": "AUD-09", "4057276861": "AUD-10",
    "4057279391": "AUD-22", "4057279392": "AUD-23", "4057279394": "AUD-35",
    "4057288833": "AUD-20", "4057288837": "AUD-20", "4057288839": "AUD-19",
    "4057288840": "AUD-15", "4057288842": "AUD-21", "4057288844": "AUD-37",
}

# The older PR stack contains many replies and automation comments. These
# links identify the closest audit workstream, with technical relevance still
# explicitly pending until A11 checks the individual comment.
PR_CONTEXT = {
    888: "AUD-33", 889: "AUD-12", 893: "AUD-33", 894: "AUD-36", 899: "AUD-01",
    900: "AUD-01", 902: "AUD-01", 904: "AUD-33", 905: "AUD-36", 906: "AUD-01",
    907: "AUD-36", 911: "AUD-36", 913: "AUD-20", 914: "AUD-20", 915: "AUD-13",
    916: "AUD-13", 921: "AUD-12", 922: "AUD-12", 923: "AUD-20",
    924: "AUD-20", 925: "AUD-20", 926: "AUD-12", 927: "AUD-36", 929: "AUD-36", 932: "AUD-36",
    940: "AUD-12", 941: "AUD-16", 942: "AUD-38", 943: "AUD-14",
    944: "AUD-14", 945: "AUD-07", 946: "AUD-04", 947: "AUD-13",
    948: "AUD-24", 949: "AUD-36", 950: "AUD-22", 951: "AUD-12",
    952: "AUD-14", 953: "AUD-14", 954: "AUD-13", 961: "AUD-24",
    962: "AUD-23", 963: "AUD-35", 968: "AUD-06", 969: "AUD-07",
    970: "AUD-22", 971: "AUD-19", 972: "AUD-13", 973: "AUD-07",
    974: "AUD-35",
}

thread_by_url = {}
for thread in THREADS:
    for comment in thread["comments"]:
        thread_by_url[comment["url"]] = thread

matrix = []
in_matrix = False
for line in PLAN.splitlines():
    if line == "## Vollständige Abdeckungsmatrix":
        in_matrix = True
        continue
    if in_matrix and line.startswith("## "):
        break
    if not in_matrix or not line.startswith("| ") or "Audit-Unterpunkt" in line:
        continue
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    if len(cells) != 3 or all(re.fullmatch(r"-+", cell) for cell in cells):
        continue
    title, packages, acceptance = cells
    prefix = next((key for key in FILES if title.startswith(key)), "")
    matrix.append({
        "id": f"AUD-{len(matrix)+1:02d}", "auditUnterpunkt": title,
        "paket": packages, "zielverhalten": acceptance,
        "betroffeneDateien": FILES.get(prefix, "Zuordnung in A11 prüfen"),
        "verantwortlicheRolle": "; ".join(PACKAGE_ROLE.get(p, p) for p in packages.split("/")),
        "status": "offen – technische Abnahme ausstehend", "fixCommit": "",
        "regressionstest": "ausstehend", "ciAbnahmenachweis": "ausstehend",
        "reviewUrls": [],
    })

reviews = []
for comment in ARCHIVE["comments"]:
    url = comment["url"]
    match = re.search(r"discussion_r(\d+)", url)
    audit_id = RECENT.get(match.group(1)) if match else None
    mapping_type = "konkreter Audit-Unterpunkt" if audit_id else "PR-Kontext, Einzelprüfung A11 offen"
    audit_id = audit_id or PR_CONTEXT.get(comment["pr"])
    row = next((item for item in matrix if item["id"] == audit_id), None)
    if row and mapping_type == "konkreter Audit-Unterpunkt":
        row["reviewUrls"].append(url)
    thread = thread_by_url.get(url)
    reviews.append({
        "pr": comment["pr"], "url": url, "art": "Inline" if comment.get("path") else "Review/Antwort",
        "pfadImReview": comment.get("path") or "", "auditZuordnung": row["id"] if row else "A11 historische Review-Triage",
        "zuordnungTyp": mapping_type,
        "threadId": thread["id"] if thread else "",
        "isResolved": str(thread["isResolved"]).lower() if thread else "unbekannt/nicht anwendbar",
        "technischerStatus": "offen – Fix/Regressionstest prüfen" if row else "historisch – fachliche Relevanz in A11 prüfen",
        "fixCommit": "", "testOderGegenbeleg": "",
        "kurztext": re.sub(r"\s+", " ", comment.get("body") or "")[:180].strip(),
    })

def write_csv(name: str, rows: list[dict]) -> None:
    with (AUDIT / name).open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

write_csv("A00_BEFUNDREGISTER.csv", matrix)
write_csv("A00_REVIEWREGISTER.csv", reviews)

existing_path = os.environ.get("A00_EXISTING_WORKTREE")
if not existing_path:
    raise SystemExit("Set A00_EXISTING_WORKTREE to the pre-existing working tree")
existing = Path(existing_path)
changed = subprocess.check_output(
    ["git", "-C", str(existing), "diff", "--name-only"], text=True,
    stderr=subprocess.DEVNULL,
).splitlines()

def candidate_package(path: str) -> str:
    p = path.lower()
    if "insightmatrixexport" in p or "report/" in p or "export_service" in p:
        return "A05"
    if "insightsections" in p or "dismissal" in p or "user_preferences" in p:
        return "A03"
    if "belastung" in p or "signal/[id]" in p or "stats" in p or "habits" in p or "habit" in p:
        return "A04/A06"
    if "trendwindowdays" in p or "analysisrange" in p or "/insights/+page" in p:
        return "A07"
    if "/trends/" in p or "sync" in p:
        return "A08"
    if "i18n" in p:
        return "A09"
    if "test" in p:
        return "A10"
    return "A04 – fachliche Zuordnung prüfen"

local_fixes = [{
    "pfad": path, "quelleBranch": "feat/928-phase14-sleep-next-day",
    "quelleHead": "2e8a7f8f5e4217c61a54b344b202e5aeb52fba73",
    "urheber": "nicht aus uncommittetem Diff bestimmbar",
    "arbeitsstand": "lokal modifiziert, nicht committet, nicht in A00 übernommen",
    "vorlaeufigesPaket": candidate_package(path),
    "status": "Fix-Kandidat – Zielverhalten/Regressionstest auf Integrationsstand offen",
    "fixCommit": "", "testnachweis": "",
} for path in changed]
write_csv("A00_LOKALE_FIXES.csv", local_fixes)

source_head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
summary = f"""# A00 – Ausgangsstand und Befundregister

Stand: 22.09.2026. Audit-Basis: `71d1089ff77388cadf2253ac67d1471dfa99fa40`.

## Isolierter Implementierungsstand

- Worktree-Branch: `codex/audit-a00-register`, erstellt aus `origin/main` = `{source_head}`.
- Lokaler `main` beim Start: `50ef171336edfd03f92466167fb81dd7e81e3b19` (älter als der abgerufene Remote-Main).
- Vorhandener Arbeitsbranch: `feat/928-phase14-sleep-next-day` auf `2e8a7f8f5e4217c61a54b344b202e5aeb52fba73` mit {len(local_fixes)} modifizierten, nicht committeten Dateien und einem unversionierten Audit-Verzeichnis. Diese Änderungen wurden nicht als Release-Fix übernommen oder überschrieben. Urheber der nicht committeten Änderungen ist aus Git allein nicht bestimmbar; Arbeitsstand und Pfade siehe `A00_LOKALE_FIXES.csv`.
- Dokumentationsquelle: der durch PR #987 versionierte Plan auf aktuellem Main sowie das zuvor unversionierte `AUDIT.md` und `review-evidence.json` aus dem vorhandenen Arbeitsstand. `review-threads-current.json` ist der aktuelle GraphQL-Abgleich.

## Register und Bewertung

- `A00_BEFUNDREGISTER.csv`: {len(matrix)} Zeilen, exakt eine je Unterpunkt der Abdeckungsmatrix. Zielverhalten, betroffene Pfade, Rolle und benötigte Nachweise sind eingetragen. Fix-Commit und Release-CI bleiben leer, solange sie nicht existieren.
- `A00_REVIEWREGISTER.csv`: {len(reviews)} archivierte Review-Kommentare einzeln mit URL, Thread-Status und technischem Status. Davon {sum(bool(r['pfadImReview']) for r in reviews)} Inline-Kommentare. {sum(r['zuordnungTyp'] == 'konkreter Audit-Unterpunkt' for r in reviews)} aktuelle Review-Findings sind direkt einem Matrix-Unterpunkt zugeordnet; ältere Kommentare erhalten eine explizit vorläufige Zuordnung anhand ihres PR-Kontexts und bleiben in A11 zur Einzelprüfung offen. Aktuelle GraphQL-Daten enthalten {len(THREADS)} Threads, {sum(not t['isResolved'] for t in THREADS)} ungelöst. `isResolved` belegt nur den GitHub-Threadzustand.
- `A00_LOKALE_FIXES.csv`: Kandidaten im anderen, nicht committeten Arbeitsstand. Das Register kennzeichnet sie als Kandidaten; A01–A09 müssen Zielverhalten und Tests auf dem späteren Integrationsstand prüfen.

## Prüfung vorhandener Fix-Kandidaten

Auf dem unveränderten Arbeitsbranch `feat/928-phase14-sleep-next-day` liefen am 22.09.2026 gezielte Regressionstests: 24/24 Vitest-Tests (`insightSections`, `insightMatrixExport`, `trendWindowDays`, Insights-Seite) und 66/66 Pytest-Tests (`test_insight_sections.py`, `test_insights.py`, `test_stats_service.py`). Für den gezielten Pytest-Lauf wurde `--no-cov` verwendet, da die globale 70-Prozent-Schwelle bei einer kleinen Testauswahl naturgemäß nicht erreicht wird; der erste Lauf hatte 66 erfolgreiche Tests, aber 47,43 Prozent Gesamtabdeckung und daher Exit 1. Ein erster Vitest-Lauf mit mehreren Forks scheiterte an Worker-Timeouts; der Einzel-Worker-Lauf bestand. Das sind Tests des fremden, nicht committeten Stands und keine Freigabe der 61 Kandidaten. Wegen fehlender End-to-End- und finaler Release-SHA-Nachweise bleiben diese im Register offen.

## Abschlussgrenzen

Dieses A00-Register ist eine nachvollziehbare Ausgangsbasis. Es bestätigt noch keinen Produkt-Fix und keine Freigabe. Die {len(matrix)} Audit-Zeilen und die historischen Kommentare brauchen die jeweiligen Fix-Commits, Regressionstests und Nachweise am finalen Release-Kandidaten. A11 klärt die fachliche Relevanz historischer Antworten. Kein bestätigter Befund wird hier als akzeptiertes Risiko klassifiziert; eine Widerlegung erfordert konkreten Test oder Gegenbeleg.
"""
(AUDIT / "A00_STATUS.md").write_text(summary, encoding="utf-8")
print(f"matrix={len(matrix)} reviews={len(reviews)} threads={len(THREADS)}")
