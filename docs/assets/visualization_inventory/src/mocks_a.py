"""Compare-Familie: M01 Linien, M02 Streifen, M03 Overlays, M04 Achsen-Zoom."""

from lib import RNG, cells_row, divergent, heat, polyline, series

N = 26          # Spalten (Buckets)
CELL = 24
GAP = 4
LABEL_W = 110
X0 = LABEL_W
PITCH = CELL + GAP
PLOT_W = N * PITCH - GAP

MONTHS = ["Apr", "Mai", "Jun", "Jul", "Aug", "Sep"]

mood = series(N, 3.4, 0.55, 9, 0.0)
energy = series(N, 3.1, 0.65, 11, 1.2)
stress = series(N, 2.9, 0.7, 8, 2.4)

ROWS = [
    ("Sport", [0, 1, 2, 3, 2, 4, 3, 2, 1, 0, 2, 3, 4, 3, 2, 2, 1, 3, 4, 4, 3, 2, 1, 2, 3, 4]),
    ("Kaffee > 3", [3, 4, 3, 2, 4, 3, 4, 4, 3, 2, 3, 4, 2, 3, 4, 3, 2, 3, 4, 3, 3, 4, 3, 2, 3, 3]),
    ("Kopfschmerz", [0, 1, 0, 2, 1, 0, 0, 3, 2, 1, 0, 0, 1, 2, 3, 1, 0, 0, 1, 0, 2, 1, 0, 1, 0, 0]),
    ("Homeoffice", [4, 3, 4, 4, 2, 3, 4, 3, 4, 4, 3, 2, 4, 4, 3, 4, 2, 3, 4, 4, 3, 3, 4, 4, 2, 3]),
    ("Wenig Schlaf", [0, 2, 1, 3, 2, 0, 1, 3, 3, 2, 0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 0, 1, 2, 1, 0]),
]


def month_ticks(y):
    out = []
    for i, m in enumerate(MONTHS):
        x = X0 + (i * (N / len(MONTHS))) * PITCH
        out.append(f'<text class="tick" x="{x:.0f}" y="{y}">{m}</text>')
    return "".join(out)


def toolbar(mode_lines=True, extra=""):
    return f"""
<div class="between" style="margin-bottom:10px">
  <div class="row">
    <span class="chip on">Vergleichen</span>
    <span class="chip">Gewohnheiten</span>
  </div>
  <div class="row">
    <span class="faint" style="font-size:10px">Zeitachsen-Zoom</span>
    <span class="chip sm">−</span><span class="chip sm mono">7 Tage / Zelle</span><span class="chip sm">+</span>
  </div>
</div>
<div class="row" style="flex-wrap:wrap;gap:6px;margin-bottom:12px">
  <span class="faint" style="font-size:10px">Darstellung</span>
  <span class="chip sm {'on' if mode_lines else ''}">Linien</span>
  <span class="chip sm {'' if mode_lines else 'on'}">Streifen</span>
  <span style="width:10px"></span>
  <span class="faint" style="font-size:10px">Sortierung</span>
  <span class="chip sm">Nach Häufigkeit ▾</span>
  <span style="width:10px"></span>
  <span class="faint" style="font-size:10px">Ebenen</span>
  <span class="chip sm on">Tags</span>
  <span class="chip sm on">Arbeitssituation</span>
  <span class="chip sm on">Symptome</span>
  {extra}
</div>"""


def heatmap_rows(pinned=(), highlight_cols=(), lag_cols=()):
    h = 0
    out = []
    for idx, (label, vals) in enumerate(ROWS):
        y = h
        pin = "📌" if label in pinned else "○"
        pincol = "var(--primary)" if label in pinned else "var(--faint)"
        out.append(
            f'<text x="0" y="{y + 17}" font-size="11" fill="{pincol}">{pin}</text>'
            f'<text x="16" y="{y + 17}" font-size="11" fill="var(--text)">{label}</text>'
        )
        out.append(cells_row(vals, X0, y + 4, CELL, GAP, heat))
        h += CELL + 10
    bands = ""
    for c in highlight_cols:
        x = X0 + c * PITCH - 2
        bands += (
            f'<rect x="{x:.0f}" y="-4" width="{CELL + 4}" height="{h + 2}" rx="3" '
            f'fill="rgba(124,106,245,0.16)" stroke="rgba(124,106,245,0.55)"/>'
        )
    lines = ""
    for c in lag_cols:
        x = X0 + c * PITCH + CELL / 2
        lines += (
            f'<line x1="{x:.0f}" y1="-4" x2="{x:.0f}" y2="{h - 4}" stroke="var(--marker)" '
            f'stroke-width="1.5" stroke-dasharray="4 3"/>'
            f'<line x1="{x:.0f}" y1="-4" x2="{x + PITCH:.0f}" y2="-4" stroke="var(--marker)" '
            f'stroke-width="1.5" stroke-dasharray="4 3"/>'
        )
    return bands + "".join(out) + lines, h


def lines_svg(markers=True, cursor_col=17):
    h = 140
    grid = "".join(
        f'<line class="axis" x1="{X0}" y1="{h * i / 4:.0f}" x2="{X0 + PLOT_W}" '
        f'y2="{h * i / 4:.0f}" opacity="0.35"/>'
        for i in range(5)
    )
    mk = ""
    if markers:
        for c, lab in ((6, ""), (14, "")):
            x = X0 + c * PITCH + CELL / 2
            mk += (
                f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{h}" stroke="var(--marker)" '
                f'stroke-width="1" stroke-dasharray="2 3"/>'
            )
    cx = X0 + cursor_col * PITCH + CELL / 2
    cur = (
        f'<line x1="{cx:.0f}" y1="-4" x2="{cx:.0f}" y2="{h + 4}" stroke="#cdccca" '
        f'stroke-width="1.5" opacity="0.8"/>'
    )
    pl = ""
    for vals, col in ((mood, "var(--mood)"), (energy, "var(--energy)"), (stress, "var(--stress)")):
        pl += (
            f'<polyline points="{polyline(vals, X0 + CELL / 2, 4, PLOT_W - CELL, h - 12)}" '
            f'fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round"/>'
        )
    ylab = "".join(
        f'<text class="tick" x="{X0 - 8}" y="{h * i / 4 + 3:.0f}" text-anchor="end">{5 - i}</text>'
        for i in range(5)
    )
    return f'<g transform="translate(0,6)">{grid}{ylab}{mk}{pl}{cur}</g>', h + 12


def strips_svg():
    h = 0
    out = []
    for label, vals, in (("Stimmung", mood), ("Energie", energy), ("Stress", stress)):
        out.append(f'<text x="0" y="{h + 16}" font-size="11" fill="var(--text)">{label}</text>')
        out.append(
            f'<rect x="{X0}" y="{h + 2}" width="{PLOT_W}" height="{CELL}" rx="3" fill="#201f1d"/>'
        )
        out.append(
            cells_row(vals, X0, h + 2, CELL, GAP, lambda v: divergent(v, midpoint=3.0, rng=4.0))
        )
        h += CELL + 12
    return "".join(out), h


def legend_metrics():
    return """
<div class="row" style="gap:14px;margin-top:6px">
  <span class="legend"><i class="sw" style="background:var(--mood)"></i>Stimmung</span>
  <span class="legend"><i class="sw" style="background:var(--energy)"></i>Energie</span>
  <span class="legend"><i class="sw" style="background:var(--stress)"></i>Stress</span>
  <span class="legend" style="margin-left:auto"><i class="sw" style="background:#1f2a44"></i>
    <i class="sw" style="background:#2e3f6f"></i><i class="sw" style="background:#415aa3"></i>
    <i class="sw" style="background:#6279d6"></i> Häufigkeit / Tag</span>
</div>"""


def m01():
    ls, lh = lines_svg()
    hm, hh = heatmap_rows(pinned=("Sport", "Kopfschmerz"))
    total = lh + hh + 34
    return 900, f"""
<div class="card">
  <div class="between" style="margin-bottom:8px">
    <div><h2>Vergleichen</h2>
      <p class="sub">Stimmung, Energie und Stress liegen auf derselben Zeitachse wie Tag-,
        Arbeitskontext- und Symptomzeilen.</p></div>
    <span class="chip sm">Zeitraum: 6 Monate</span>
  </div>
  {toolbar()}
  <svg width="868" height="{total}" viewBox="0 0 868 {total}">
    {ls}
    <g transform="translate(0,{lh + 14})">
      <text x="0" y="-4" font-size="10" fill="var(--faint)">Kontextzeilen</text>
      {hm}
    </g>
    <g transform="translate(0,{lh + hh + 22})">{month_ticks(8)}</g>
  </svg>
  {legend_metrics()}
  <p class="caption">M01 · <b>Compare / Linien</b> — MetricTimeseries + ComparisonHeatmap auf
    gemeinsamer Achse, Zeilen pinnbar (📌), synchronisierter Zeit-Cursor.</p>
</div>"""


def m02():
    st, sh = strips_svg()
    hm, hh = heatmap_rows()
    total = sh + hh + 34
    return 900, f"""
<div class="card">
  <div class="between" style="margin-bottom:8px">
    <div><h2>Vergleichen — Streifen</h2>
      <p class="sub">Divergente Streifen statt Linien: lesbar, wenn sich viele Tage überlagern
        (ADR-0035).</p></div>
    <span class="chip sm">Zeitraum: 6 Monate</span>
  </div>
  {toolbar(mode_lines=False)}
  <svg width="868" height="{total}" viewBox="0 0 868 {total}">
    {st}
    <g transform="translate(0,{sh + 12})">
      <text x="0" y="-4" font-size="10" fill="var(--faint)">Kontextzeilen</text>
      {hm}
    </g>
    <g transform="translate(0,{sh + hh + 20})">{month_ticks(8)}</g>
  </svg>
  <div class="row" style="gap:14px;margin-top:6px">
    <span class="legend"><i class="sw" style="background:#3a5a8a"></i> niedriger</span>
    <span class="legend"><i class="sw" style="background:#2a2825"></i> Mitte</span>
    <span class="legend"><i class="sw" style="background:#9587ff"></i> höher</span>
  </div>
  <p class="caption">M02 · <b>Compare / Streifen</b> — UnifiedStripChart, gleiche Achse,
    gleiche Kontextzeilen, andere Kodierung (Farbe statt Position).</p>
</div>"""


def m03():
    hl = (7, 13, 19)
    lag = (9, 15)
    hm, hh = heatmap_rows(pinned=("Sport", "Kopfschmerz"), highlight_cols=hl, lag_cols=lag)
    total = hh + 30
    return 900, f"""
<div class="card">
  <div class="between" style="margin-bottom:10px">
    <div><h2>Overlays auf der Compare-Achse</h2>
      <p class="sub">Zwei Zeilen gepinnt → Koinzidenz (A∩B) und Folgetag-Sequenz (A→B +1d)
        werden freigeschaltet.</p></div>
  </div>
  <div class="row" style="gap:8px;margin-bottom:12px;flex-wrap:wrap">
    <span class="faint" style="font-size:10px">Hervorheben</span>
    <span class="chip sm on">Koinzidenz hervorheben</span>
    <span class="chip sm on">Nächster-Tag-Sequenz hervorheben</span>
    <span class="legend" style="margin-left:8px">
      <i class="sw" style="background:rgba(124,106,245,.22);border:1px solid rgba(124,106,245,.6)"></i>
      A∩B — Band</span>
    <span class="legend"><svg width="22" height="10"><line x1="0" y1="5" x2="22" y2="5"
      stroke="var(--marker)" stroke-width="1.5" stroke-dasharray="4 3"/></svg> Lag-1 — gestrichelt</span>
  </div>
  <svg width="868" height="{total}" viewBox="0 0 868 {total}">
    <g transform="translate(0,6)">{hm}</g>
    <g transform="translate(0,{hh + 10})">{month_ticks(8)}</g>
  </svg>
  <div class="hr"></div>
  <p style="font-size:11px;margin:0" class="muted">
    Beide an <b>6</b> von 14 Tagen mit Sport · <b>6</b> von 11 Tagen mit Kopfschmerz<br>
    Sport dann Kopfschmerz: <b>4</b> von 14 · Kopfschmerz dann Sport: <b>1</b> von 11
  </p>
  <p class="caption">M03 · <b>Compare-Overlays</b> — reine Präsenzrechnung im Client,
    keine Statistik, keine Kausalaussage (#908 / #910 / #917).</p>
</div>"""


def m04():
    fine_n = 21
    fine_cell, fine_gap = 22, 4
    fine_pitch = fine_cell + fine_gap
    rows_fine = [
        ("Sport", [0, 0, 3, 0, 0, 2, 0, 0, 4, 0, 0, 0, 3, 0, 2, 0, 0, 4, 0, 0, 3]),
        ("Kopfschmerz", [0, 2, 0, 0, 3, 0, 0, 1, 0, 0, 2, 0, 0, 3, 0, 0, 1, 0, 0, 2, 0]),
    ]
    body = ""
    y = 0
    for label, vals in rows_fine:
        body += f'<text x="0" y="{y + 16}" font-size="11" fill="var(--text)">{label}</text>'
        body += cells_row(vals, 110, y + 2, fine_cell, fine_gap, heat)
        y += fine_cell + 10
    ticks = "".join(
        f'<text class="tick" x="{110 + i * fine_pitch + fine_cell / 2:.0f}" y="{y + 10}" '
        f'text-anchor="middle">{d}</text>'
        for i, d in enumerate(["1", "", "3", "", "5", "", "7", "", "9", "", "11", "", "13", "",
                               "15", "", "17", "", "19", "", "21"])
    )
    coarse = ""
    yc = 0
    for label, vals in (("Sport", [2, 3, 1, 4, 2, 3, 4]), ("Kopfschmerz", [1, 2, 3, 1, 2, 3, 1])):
        coarse += f'<text x="0" y="{yc + 18}" font-size="11" fill="var(--text)">{label}</text>'
        coarse += cells_row(vals, 110, yc + 2, 30, 6, heat)
        yc += 36
    return 900, f"""
<div class="card">
  <h2>Achsen-Zoom (CAZ)</h2>
  <p class="sub">Eine Achse, fünf Auflösungsstufen: 30 / 14 / 7 / 3 / 1 Tage pro Zelle.
    Heatmap summiert, Linien/Streifen mitteln über Tage mit Eintrag.</p>
  <div class="hr"></div>
  <div class="row" style="justify-content:space-between;margin-bottom:6px">
    <span class="chip sm">7 Tage / Zelle · Übersicht</span>
    <span class="faint" style="font-size:10px">Tippe auf eine Mehr-Tage-Zelle zum Hereinzoomen ↓</span>
  </div>
  <svg width="700" height="{yc + 6}" viewBox="0 0 700 {yc + 6}">{coarse}</svg>
  <div class="hr"></div>
  <div class="row" style="margin-bottom:6px">
    <span class="chip sm on">1 Tag / Zelle · Detail</span>
    <span class="faint" style="font-size:10px;margin-left:8px">Einträge an 9 von 21 Tagen</span>
  </div>
  <svg width="700" height="{y + 18}" viewBox="0 0 700 {y + 18}">{body}{ticks}</svg>
  <p class="caption">M04 · <b>Compare-Zoom</b> — dieselben Daten, andere Aggregation.
    Die Kodierungsregel steht als Hinweistext neben dem Regler.</p>
</div>"""


MOCKS = {"m01_compare_linien": m01, "m02_compare_streifen": m02,
         "m03_compare_overlays": m03, "m04_compare_zoom": m04}
