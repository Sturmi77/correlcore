"""Insights-Familie: M05 Matrix, M06 InsightCard, M07 Lag-Heatmap, M08 Kookkurrenz."""

from lib import divergent, lerp_hex

MATRIX = [
    ("Sport", "Stimmung", 0.62, 0.78, "pos"),
    ("Schlechter Schlaf", "Energie", -0.54, 0.71, "neg"),
    ("Homeoffice", "Stress", -0.41, 0.66, "neg"),
    ("Kopfschmerz", "Stimmung", -0.38, 0.62, "neg"),
    ("Kaffee > 3", "Stress", 0.33, 0.55, "pos"),
    ("Spaziergang", "Stimmung", 0.29, 0.51, "pos"),
]


def effect_bar(value):
    width = min(1.0, abs(value)) * 100
    col = "var(--energy)" if value > 0 else "var(--stress)"
    return (
        f'<span style="display:inline-block;width:86px;height:6px;border-radius:3px;'
        f'background:#2c2925;vertical-align:middle;margin-right:8px">'
        f'<span style="display:block;width:{width:.0f}%;height:6px;border-radius:3px;'
        f'background:{col}"></span></span>'
    )


def m05():
    rows = ""
    for subject, metric, effect, conf, _tone in MATRIX:
        rows += f"""
    <tr>
      <td style="color:var(--text)">{subject}</td>
      <td class="muted">{metric}</td>
      <td class="mono">{effect_bar(effect)}{effect:+.2f}</td>
      <td class="mono muted">{conf * 100:.0f} %</td>
    </tr>"""
    return 760, f"""
<div class="card">
  <div class="between">
    <div><h2>Korrelations-Matrix</h2>
      <p class="sub">Tags, Symptome und Habits nach Effektstärke sortiert.
        Stand: 17.09.2026</p></div>
    <span class="chip sm">Als PNG exportieren</span>
  </div>
  <div class="hr"></div>
  <table class="grid">
    <tr><th>Merkmal</th><th>Metrik</th><th>Effekt</th><th>Konfidenz</th></tr>
    {rows}
  </table>
  <details style="margin-top:10px">
    <summary class="faint" style="font-size:11px;cursor:pointer">
      4 schwächere Zusammenhänge anzeigen</summary>
  </details>
  <p class="caption">M05 · <b>„Korrelations-Matrix“</b> (InsightMatrix) — trotz des Namens
    eine sortierte <i>Tabelle</i>, keine Matrix: eine Zeile je Merkmal×Metrik-Paar.</p>
</div>"""


def lag_bars(profile, peak):
    """Signierte Mini-Bars (±) wie auf der InsightCard."""
    h = 34
    out = []
    maxabs = max(abs(v) for v in profile) or 1
    for i, r in enumerate(profile):
        x = i * 20
        bh = abs(r) / maxabs * (h / 2 - 2)
        active = (i + 1) == peak
        col = "var(--primary)" if active else "rgba(124,106,245,0.45)"
        if r >= 0:
            y = h / 2 - bh
        else:
            y = h / 2
        out.append(
            f'<rect x="{x + 3}" y="{y:.1f}" width="12" height="{bh:.1f}" rx="2" fill="{col}"/>'
        )
        out.append(
            f'<text x="{x + 9}" y="{h + 11}" font-size="9" text-anchor="middle" '
            f'fill="{"var(--text)" if active else "var(--faint)"}">{i + 1}</text>'
        )
    axis = f'<line x1="0" y1="{h / 2}" x2="{len(profile) * 20}" y2="{h / 2}" stroke="var(--border)"/>'
    return f'<svg width="{len(profile) * 20}" height="{h + 14}">{axis}{"".join(out)}</svg>'


def dots(n_full, n_total=5):
    out = ""
    for i in range(n_total):
        fill = "var(--primary)" if i < n_full else "#2c2925"
        out += (
            f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;'
            f'background:{fill};margin-right:3px"></span>'
        )
    return out


def m06():
    return 720, f"""
<div class="card" style="border-left:3px solid var(--primary)">
  <div class="between">
    <span class="chip sm" style="border-color:var(--primary);color:var(--primary)">
      Zusammenhang</span>
    <span class="row" style="gap:6px"><span class="pill prov">vorläufig</span>
      <span class="faint" style="font-size:11px">✕</span></span>
  </div>
  <p style="font-size:14px;line-height:1.45;margin:10px 0 4px">
    An Tagen mit <b>Sport</b> liegt deine <b>Stimmung</b> im Schnitt
    <b>0,6 Punkte höher</b> als an Tagen ohne — in 34 von 90 Tagen.</p>
  <div class="row" style="gap:10px;margin:8px 0 2px">
    <span class="pill prov">vorläufig</span>
    <span>{dots(3)}</span>
    <span class="faint" style="font-size:11px">Basierend auf 90 Einträgen</span>
  </div>
  <div class="hr"></div>
  <div class="row" style="gap:12px;align-items:flex-end">
    <div>
      <div class="faint" style="font-size:10px;margin-bottom:2px">
        Zusammenhang je Verzögerung (Tage)</div>
      {lag_bars([0.12, 0.34, 0.41, 0.22, -0.08, -0.11, 0.05], peak=3)}
    </div>
    <div class="muted" style="font-size:11px;padding-bottom:16px">
      Am stärksten bei <b>+3 Tagen</b> (gleichläufig)</div>
  </div>
  <div class="row" style="gap:8px;margin-top:6px">
    <span class="chip sm" style="border-color:var(--primary);color:var(--primary)">
      Ausgerichtete Ereignisse erkunden</span>
    <span class="chip sm">Details ▾</span>
  </div>
  <p class="caption">M06 · <b>InsightCard</b> — Aussage (Level 1), Evidenz-Zeile
    (Reife-Chip + Konfidenz-Punkte + n) und signiertes Lag-Profil als Mini-Balken.</p>
</div>"""


LAG_ROWS = [
    ("Sport → Stimmung", [0.12, 0.34, 0.41, 0.22, -0.08, -0.11, 0.05], 3),
    ("Wenig Schlaf → Energie", [-0.48, -0.31, -0.12, 0.02, 0.08, 0.04, -0.02], 1),
    ("Kaffee > 3 → Schlafqualität", [-0.21, -0.35, -0.18, -0.05, 0.03, 0.01, 0.06], 2),
    ("Homeoffice → Stress", [-0.11, -0.19, -0.26, -0.33, -0.18, -0.07, 0.02], 4),
    ("Kopfschmerz → Stimmung", [-0.29, -0.22, -0.09, -0.03, 0.05, 0.02, 0.01], 1),
]


def m07():
    cell, gap = 44, 5
    x0 = 210
    body = ""
    y = 0
    for label, prof, peak in LAG_ROWS:
        body += f'<text x="0" y="{y + 19}" font-size="11" fill="var(--text)">{label}</text>'
        for i, r in enumerate(prof):
            x = x0 + i * (cell + gap)
            stroke = ' stroke="var(--primary)" stroke-width="2"' if (i + 1) == peak else ""
            body += (
                f'<rect x="{x}" y="{y + 2}" width="{cell}" height="26" rx="3" '
                f'fill="{divergent(r, 0, 1.2)}"{stroke}/>'
                f'<text x="{x + cell / 2}" y="{y + 19}" font-size="9.5" text-anchor="middle" '
                f'fill="#e8e7e5">{r:+.2f}</text>'
            )
        y += 34
    heads = "".join(
        f'<text x="{x0 + i * (cell + gap) + cell / 2}" y="-6" font-size="10" '
        f'text-anchor="middle" fill="var(--faint)">+{i + 1}d</text>'
        for i in range(7)
    )
    return 700, f"""
<div class="card">
  <h2>Zeitversatz-Muster</h2>
  <p class="sub">Zusammenhangsstärke je Paar und Verzögerung (1–7 Tage). Kein Kausalnachweis.</p>
  <div class="hr"></div>
  <svg width="560" height="{y + 16}" viewBox="0 0 560 {y + 16}">
    <g transform="translate(0,14)">{heads}{body}</g>
  </svg>
  <div class="row" style="gap:10px;margin-top:6px">
    <span class="legend"><i class="sw" style="background:{divergent(-0.6, 0, 1.2)}"></i>
      gegenläufig</span>
    <span class="legend"><i class="sw" style="background:{divergent(0.6, 0, 1.2)}"></i>
      gleichläufig</span>
    <span class="legend" style="margin-left:auto">
      <i class="sw" style="background:transparent;border:2px solid var(--primary)"></i>
      gewählter Lag der Insight-Karte</span>
  </div>
  <p class="caption">M07 · <b>LagCorrelationHeatmap</b> — dieselben lag_profile-Daten wie M06,
    nur für mehrere Paare gleichzeitig.</p>
</div>"""


TAGS = ["Sport", "Kaffee", "Homeoffice", "Meeting", "Spaziergang", "Alkohol", "Lesen", "Gaming"]
COOC = [
    [0, 3, 2, 1, 4, 0, 2, 1],
    [3, 0, 4, 4, 1, 2, 1, 2],
    [2, 4, 0, 3, 2, 1, 3, 2],
    [1, 4, 3, 0, 1, 2, 0, 1],
    [4, 1, 2, 1, 0, 0, 3, 0],
    [0, 2, 1, 2, 0, 0, 1, 3],
    [2, 1, 3, 0, 3, 1, 0, 1],
    [1, 2, 2, 1, 0, 3, 1, 0],
]
CLUSTERS = [
    ("Bewegung &amp; Erholung", ["Sport", "Spaziergang", "Lesen"], "stark"),
    ("Arbeitstag", ["Homeoffice", "Meeting", "Kaffee"], "mittel"),
    ("Abendroutine", ["Alkohol", "Gaming"], "schwach"),
]


def m08():
    cell, gap = 34, 4
    x0 = 118
    y0 = 92
    grid = ""
    for r, row in enumerate(COOC):
        for c, v in enumerate(row):
            x = x0 + c * (cell + gap)
            y = y0 + r * (cell + gap)
            if r == c:
                fill = "#232120"
                txt = ""
            else:
                fill = lerp_hex("#1f2a44", "#6279d6", v / 4)
                txt = (
                    f'<text x="{x + cell / 2}" y="{y + cell / 2 + 4}" font-size="10" '
                    f'text-anchor="middle" fill="#e8e7e5">{v * 3}</text>'
                )
            grid += f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fill}"/>{txt}'
    for i, t in enumerate(TAGS):
        y = y0 + i * (cell + gap) + cell / 2 + 4
        grid += f'<text x="110" y="{y}" font-size="10.5" text-anchor="end" fill="var(--text)">{t}</text>'
        x = x0 + i * (cell + gap) + cell / 2
        grid += (
            f'<text x="{x}" y="{y0 - 8}" font-size="10.5" fill="var(--text)" '
            f'transform="rotate(-45 {x} {y0 - 8})">{t}</text>'
        )
    h = y0 + len(TAGS) * (cell + gap) + 6
    chips = ""
    for title, members, band in CLUSTERS:
        chips += (
            f'<div style="margin-bottom:8px"><div class="row" style="gap:6px">'
            f'<b style="font-size:12px">{title}</b>'
            f'<span class="chip sm">{band}</span></div>'
            f'<div class="row" style="gap:4px;margin-top:4px;flex-wrap:wrap">'
            + "".join(f'<span class="chip sm">{m}</span>' for m in members)
            + "</div></div>"
        )
    return 880, f"""
<div class="card">
  <div class="between">
    <div><h2>Muster — Tag-Kookkurrenz</h2>
      <p class="sub">Wie oft Tags gemeinsam auf demselben Entry vorkommen.</p></div>
    <span class="chip sm">Analysezeitraum: 90 Tage</span>
  </div>
  <div class="row" style="gap:6px;margin:8px 0">
    <span class="chip sm on">Nach Ähnlichkeit clustern</span>
    <span class="chip sm">Alphabetisch</span>
    <span class="chip sm">Fokus: Alle Gruppen ▾</span>
    <span class="faint" style="font-size:10px;margin-left:auto">Heatmap-Dichte 8 / 14</span>
  </div>
  <div style="display:flex;gap:18px">
    <svg width="440" height="{h}" viewBox="0 0 440 {h}">{grid}</svg>
    <div style="flex:1">
      <h3>Tag-Gruppen</h3>
      <p class="sub" style="margin-bottom:8px">Merkmale, die häufig zusammen auftreten.</p>
      {chips}
      <div class="gapnote">Dieselbe Rohgröße (gemeinsame Entries) — einmal als Matrix,
        einmal als Gruppenliste. Die Zahl ist eine rohe Zählung; Lift und Signifikanz
        gibt es nur in der Symptom-Variante (M11).</div>
    </div>
  </div>
  <p class="caption">M08 · <b>TagCooccurrenceHeatmap + TagGroupsSection</b> — Zahl = gemeinsame
    Entries, Farbe = Intensität; Zeilen/Spalten clusterbar.</p>
</div>"""


MOCKS = {"m05_korrelations_matrix": m05, "m06_insight_card": m06,
         "m07_lag_heatmap": m07, "m08_tag_kookkurrenz": m08}
