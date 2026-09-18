"""Symptom-Familie + Ereignis-Ausrichtung: M09–M12."""

from lib import RNG, divergent, lerp_hex, polyline, series

WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS = ["Apr", "Mai", "Jun", "Jul", "Aug", "Sep"]


def m09():
    weeks = 26
    cell, gap = 13, 3
    x0 = 30
    y0 = 18
    RNG.seed(7)
    grid = ""
    for w in range(weeks):
        for d in range(7):
            present = RNG.random() < (0.18 + 0.22 * (w > 14))
            fill = "#6279d6" if present else "#242322"
            x = x0 + w * (cell + gap)
            y = y0 + d * (cell + gap)
            grid += f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{fill}"/>'
    for d, lab in enumerate(WEEKDAYS):
        if d % 2 == 0:
            grid += (
                f'<text x="{x0 - 6}" y="{y0 + d * (cell + gap) + 10}" font-size="9" '
                f'text-anchor="end" fill="var(--faint)">{lab}</text>'
            )
    for i, m in enumerate(MONTHS):
        x = x0 + (i * weeks / len(MONTHS)) * (cell + gap)
        grid += f'<text x="{x:.0f}" y="{y0 - 6}" font-size="9" fill="var(--faint)">{m}</text>'
    h = y0 + 7 * (cell + gap) + 6
    w = x0 + weeks * (cell + gap) + 6
    return 640, f"""
<div class="card">
  <div class="between">
    <div><h2>Symptom-Kalender · Kopfschmerzen</h2>
      <p class="sub">23 Vorkommen in diesem Zeitraum</p></div>
    <span class="chip sm">6 Monate</span>
  </div>
  <div class="hr"></div>
  <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{grid}</svg>
  <div class="row" style="gap:10px;margin-top:6px">
    <span class="legend"><i class="sw" style="background:#242322"></i> nicht vorhanden</span>
    <span class="legend"><i class="sw" style="background:#6279d6"></i> vorhanden</span>
    <span class="faint" style="font-size:10px;margin-left:auto">
      Tippe auf eine Zelle für die Einträge des Tages</span>
  </div>
  <p class="caption">M09 · <b>SymptomCalendarHeatmap</b> — binäre Präsenz, Wochentag-Zeilen ×
    Wochen-Spalten. Zeigt Saisonalität und Häufungen, aber keine Intensität.</p>
</div>"""


def m10():
    n = 40
    freq = [max(0, min(1, 0.15 + 0.5 * (i / n) + RNG.uniform(-0.09, 0.09))) for i in range(n)]
    mood = series(n, 3.3, 0.5, 13, 1.0, noise=0.18)
    w, h = 470, 150
    px, py = 34, 12
    pw, ph = w - 2 * px, h - py - 26
    band_up = [min(1, v + 0.13) for v in freq]
    band_dn = [max(0, v - 0.13) for v in freq]
    up = polyline(band_up, px, py, pw, ph, 0, 1).split(" ")
    dn = polyline(band_dn, px, py, pw, ph, 0, 1).split(" ")
    ribbon = " ".join(up) + " " + " ".join(reversed(dn))
    freq_line = polyline(freq, px, py, pw, ph, 0, 1)
    mood_line = polyline(mood, px, py, pw, ph, 1, 5)
    grid = "".join(
        f'<line x1="{px}" y1="{py + ph * i / 4:.0f}" x2="{px + pw}" y2="{py + ph * i / 4:.0f}" '
        f'stroke="var(--border)" opacity="0.35"/>' for i in range(5)
    )
    return 620, f"""
<div class="card">
  <h2>Symptom- und Stimmungsverlauf · Kopfschmerzen</h2>
  <p class="sub">Rollierendes 7-Tage-Fenster über die letzten 90 Tage</p>
  <div class="hr"></div>
  <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">
    {grid}
    <polygon points="{ribbon}" fill="rgba(124,106,245,0.16)"/>
    <polyline points="{freq_line}" fill="none" stroke="var(--primary)" stroke-width="2"/>
    <polyline points="{mood_line}" fill="none" stroke="var(--energy)" stroke-width="2"
      stroke-dasharray="5 3"/>
    <text x="{px - 6}" y="{py + 4}" font-size="9" text-anchor="end" fill="var(--faint)">100%</text>
    <text x="{px - 6}" y="{py + ph + 3}" font-size="9" text-anchor="end" fill="var(--faint)">0%</text>
    <text x="{px + pw + 6}" y="{py + 4}" font-size="9" fill="var(--faint)">5</text>
    <text x="{px + pw + 6}" y="{py + ph + 3}" font-size="9" fill="var(--faint)">1</text>
    <text x="{px}" y="{h - 8}" font-size="9" fill="var(--faint)">vor 90 Tagen</text>
    <text x="{px + pw}" y="{h - 8}" font-size="9" text-anchor="end" fill="var(--faint)">heute</text>
  </svg>
  <div class="row" style="gap:14px;margin-top:2px">
    <span class="legend"><i class="sw" style="background:var(--primary)"></i> Freq (Symptomtage)</span>
    <span class="legend"><i class="sw" style="background:var(--energy)"></i> Stimmung</span>
    <span class="legend"><i class="sw" style="background:rgba(124,106,245,0.3)"></i>
      Unsicherheitsband (bis Phase „robust“)</span>
  </div>
  <p class="caption">M10 · <b>SymptomTrendOverlay</b> — die einzige Darstellung mit
    explizitem Unsicherheitsband. Zwei Achsen (Häufigkeit %, Stimmung 1–5).</p>
</div>"""


SYMPTOMS = ["Kopfschmerz", "Müdigkeit", "Verdauung", "Rückenschmerz"]
TAGCOLS = ["Kaffee", "Sport", "Alkohol", "Meeting", "Wenig Schlaf", "Homeoffice"]
LIFT = [
    [1.8, 0.6, 1.4, 1.9, 2.3, 0.9],
    [0.9, 0.5, 1.6, 1.2, 2.6, 1.0],
    [1.5, 0.8, 1.9, 1.0, 1.1, 0.95],
    [1.0, 0.4, 0.9, 1.7, 1.3, 1.6],
]
SIG = {(0, 4), (1, 4), (0, 3), (2, 2)}
CONF = {(3, 3), (3, 5)}


def m11():
    cell, gap = 72, 5
    x0 = 122
    y0 = 40
    grid = ""
    for r, row in enumerate(LIFT):
        for c, v in enumerate(row):
            x = x0 + c * (cell + gap)
            y = y0 + r * (cell + gap)
            fill = divergent(v, midpoint=1.0, rng=2.4)
            dash = ' stroke="var(--faint)" stroke-width="1.5" stroke-dasharray="4 3"' \
                if (r, c) in CONF else ""
            star = "*" if (r, c) in SIG else ""
            grid += (
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell - 28}" rx="3" '
                f'fill="{fill}"{dash}/>'
                f'<text x="{x + cell / 2}" y="{y + 28}" font-size="11" text-anchor="middle" '
                f'fill="#ecebe9">{v:.1f}{star}</text>'
            )
        grid += (
            f'<text x="114" y="{y0 + r * (cell + gap) + 27}" font-size="10.5" '
            f'text-anchor="end" fill="var(--text)">{SYMPTOMS[r]}</text>'
        )
    for c, t in enumerate(TAGCOLS):
        x = x0 + c * (cell + gap) + cell / 2
        grid += (
            f'<text x="{x}" y="{y0 - 10}" font-size="10" text-anchor="middle" '
            f'fill="var(--faint)">{t}</text>'
        )
    h = y0 + len(LIFT) * (cell + gap) + 4
    w = x0 + len(TAGCOLS) * (cell + gap) + 6
    return 760, f"""
<div class="card">
  <h2>Symptom- und Tag-Muster</h2>
  <p class="sub">Lift markiert Symptome und Tags, die häufiger oder seltener gemeinsam
    auftreten als erwartet.</p>
  <div class="hr"></div>
  <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{grid}</svg>
  <div class="row" style="gap:12px;margin-top:4px;flex-wrap:wrap">
    <span class="legend"><i class="sw" style="background:{divergent(0.4, 1, 2.4)}"></i>
      seltener als erwartet (Lift &lt; 1)</span>
    <span class="legend"><i class="sw" style="background:{divergent(2.0, 1, 2.4)}"></i>
      häufiger als erwartet</span>
    <span class="legend">* FDR-korrigiertes p &lt; 0,10</span>
    <span class="legend"><i class="sw" style="background:transparent;border:1.5px dashed var(--faint)"></i>
      möglicher Confounder (Kalender/Arbeitskontext)</span>
  </div>
  <p class="caption">M11 · <b>SymptomCooccurrenceHeatmap</b> — einzige Darstellung mit
    Signifikanzmarkierung und Confounder-Hinweis direkt in der Zelle.</p>
</div>"""


def m12():
    radius = 7
    days = radius * 2 + 1
    cell, gap = 26, 3
    x0 = 130
    rows = [
        ("12.04.", [3.4, 3.2, 3.5, 3.1, 2.8, 2.4, 2.1, 1.9, 2.3, 2.9, 3.2, 3.4, 3.5, 3.6, 3.5]),
        ("28.05.", [3.6, 3.5, 3.3, 3.0, 2.9, 2.5, 2.2, 2.0, 2.4, 2.7, 3.0, 3.3, 3.4, 3.5, 3.6]),
        ("03.07.", [3.2, 3.3, 3.1, 2.9, 2.7, 2.6, 2.3, 2.1, 2.2, 2.6, 2.9, 3.1, 3.3, 3.4, 3.3]),
        ("19.08.", [3.5, 3.4, 3.2, 3.3, 3.0, 2.7, 2.4, 2.2, 2.5, 2.8, 3.1, 3.2, 3.4, 3.5, 3.4]),
    ]
    median = [3.45, 3.35, 3.2, 3.05, 2.85, 2.55, 2.25, 2.05, 2.35, 2.75, 3.05, 3.25, 3.4, 3.5, 3.45]
    partner_days = {(0, 6), (0, 7), (1, 7), (2, 5), (2, 7), (3, 7), (3, 8)}
    body = ""
    y = 0

    def row(label, vals, ypos, bold=False, marks=()):
        weight = ' font-weight="600"' if bold else ""
        fill = "var(--text)" if bold else "var(--muted)"
        size = 11.5 if bold else 11
        out = (
            f'<text x="0" y="{ypos + 17}" font-size="{size}" fill="{fill}"{weight}>'
            f"{label}</text>"
        )
        for i, v in enumerate(vals):
            x = x0 + i * (cell + gap)
            out += (
                f'<rect x="{x}" y="{ypos + 2}" width="{cell}" height="{cell}" rx="3" '
                f'fill="{divergent(v, midpoint=3, rng=2.6)}"/>'
            )
            if i in marks:
                out += (
                    f'<circle cx="{x + cell - 5}" cy="{ypos + 7}" r="3.2" '
                    f'fill="none" stroke="#e8e7e5" stroke-width="1.4"/>'
                )
        return out

    body += row("Median (n=4)", median, y, bold=True)
    y += cell + 12
    body += (
        f'<line x1="{x0 - 6}" y1="{y - 4}" x2="{x0 + days * (cell + gap)}" y2="{y - 4}" '
        f'stroke="var(--border)"/>'
    )
    for idx, (label, vals) in enumerate(rows):
        marks = {c for (r, c) in partner_days if r == idx}
        body += row("Onset " + label, vals, y, marks=marks)
        y += cell + 6
    ticks = ""
    for i in range(days):
        d = i - radius
        lab = "T0" if d == 0 else f"{d:+d}"
        x = x0 + i * (cell + gap) + cell / 2
        col = "var(--text)" if d == 0 else "var(--faint)"
        ticks += (
            f'<text x="{x}" y="{y + 12}" font-size="9" text-anchor="middle" fill="{col}">{lab}</text>'
        )
    t0x = x0 + radius * (cell + gap) - 2
    band = (
        f'<rect x="{t0x}" y="-4" width="{cell + 4}" height="{y + 2}" rx="3" fill="none" '
        f'stroke="rgba(124,106,245,0.6)" stroke-width="1.5"/>'
    )
    return 780, f"""
<div class="card">
  <div class="between">
    <div>
      <span class="chip sm">Ereignis-Ausrichtung</span>
      <h2 style="margin-top:6px">Tage rund um jeden Onset</h2>
      <p class="sub">Metrik: Stimmung · T0 = Onset von „Kopfschmerz“</p>
    </div>
    <span class="chip sm">Partner-Overlay: Wenig Schlaf ▾</span>
  </div>
  <div class="hr"></div>
  <svg width="600" height="{y + 22}" viewBox="0 0 600 {y + 22}">
    <g transform="translate(0,6)">{band}{body}{ticks}</g>
  </svg>
  <p style="font-size:11px;margin:8px 0 0" class="muted">
    Im gewählten Zeitraum: <b>4</b> Fenster mit Wenig Schlaf · <b>5</b> ohne<br>
    Median <i>mit</i> Partner: Tiefpunkt 1,9 bei T0 · <i>ohne</i>: Tiefpunkt 2,4 bei T+1
  </p>
  <div class="row" style="gap:12px;margin-top:8px;flex-wrap:wrap">
    <span class="legend"><i class="sw" style="background:{divergent(1.2, 3, 2.6)}"></i> schlechter</span>
    <span class="legend"><i class="sw" style="background:{divergent(4.8, 3, 2.6)}"></i> besser</span>
    <span class="legend"><svg width="12" height="12"><circle cx="6" cy="6" r="4"
      fill="none" stroke="#e8e7e5" stroke-width="1.4"/></svg> Partner am Tag vorhanden</span>
  </div>
  <p class="caption">M12 · <b>EventAlignedSmallMultiplesSheet (ESM)</b> — Episoden an T0
    ausgerichtet, Median-Zeile oben, optional geteilt nach Partner-Präsenz (#920).</p>
</div>"""


MOCKS = {"m09_symptom_kalender": m09, "m10_symptom_trend": m10,
         "m11_symptom_tag_lift": m11, "m12_esm": m12}
