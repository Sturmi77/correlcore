"""Home/Gewohnheiten/Reife (M13–M15) und Lücken-Vorschläge (G1–G4)."""

import math

from lib import RNG, divergent, lerp_hex, polyline

WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WD_MOOD = [3.1, 3.4, 3.2, 3.6, 4.1, 4.0, 3.3]
WD_SIGNAL = ["Meeting", "Kaffee", "—", "Sport", "Sport", "Spaziergang", "Wenig Schlaf"]
WD_TREND = ["down", "flat", "flat", "up", "up", "flat", "down"]
# Die App färbt den Trendpfeil nicht (TrendDirectionGlyph erbt color) — Richtung ohne Wertung.
GLYPH = {"up": ("▲", "var(--muted)"), "down": ("▼", "var(--muted)"), "flat": ("–", "var(--faint)")}

WORK = [
    ("Homeoffice", 32, [3.8, 3.5, 2.4], ["up", "flat", "down"]),
    ("Büro", 21, [3.1, 3.2, 3.6], ["down", "flat", "up"]),
    ("Wochenende", 26, [4.1, 3.9, 1.9], ["up", "up", "down"]),
    ("Urlaub", 7, [4.4, 4.2, 1.5], ["flat", "flat", "flat"]),
]


def m13():
    cells = ""
    for i, d in enumerate(WD):
        bar = (WD_MOOD[i] - 1) / 4 * 44
        g, col = GLYPH[WD_TREND[i]]
        cells += f"""
    <div style="flex:1;text-align:center">
      <div class="faint" style="font-size:10px">{d}</div>
      <div style="height:48px;display:flex;align-items:flex-end;justify-content:center">
        <div style="width:18px;height:{bar:.0f}px;border-radius:4px 4px 0 0;
          background:{lerp_hex('#3a5a8a', '#9587ff', (WD_MOOD[i] - 2.8) / 1.4)}"></div>
      </div>
      <div class="mono" style="font-size:11px">{str(round(WD_MOOD[i], 1)).replace('.', ',')}
        <span style="color:{col}">{g}</span></div>
      <div class="faint" style="font-size:9.5px;margin-top:2px">{WD_SIGNAL[i]}</div>
    </div>"""

    rows = ""
    for name, days, vals, trends in WORK:
        tds = ""
        for j, v in enumerate(vals):
            # Stress (Index 2) invertiert: stärkere Färbung = besser
            norm = (5 - v) / 4 if j == 2 else (v - 1) / 4
            g, col = GLYPH[trends[j]]
            tds += (
                f'<td><span style="display:inline-block;min-width:54px;padding:3px 6px;'
                f'border-radius:5px;background:{lerp_hex("#232120", "#6279d6", norm)}">'
                f'{str(round(v, 1)).replace(".", ",")} <span style="color:{col}">{g}</span>'
                f"</span></td>"
            )
        rows += (
            f'<tr><td style="color:var(--text)">{name}</td>'
            f'<td class="faint mono">{days} Tage</td>{tds}</tr>'
        )

    return 820, f"""
<div class="card">
  <h2>Deine Woche auf einen Blick</h2>
  <p class="sub">Stimmungsbalken und erste Muster pro Wochentag · Trendpfeil = letzte 28 Tage
    vs. 28 Tage davor</p>
  <div class="row" style="gap:4px;margin-top:10px">{cells}</div>
</div>
<div class="card">
  <h2>Arbeitssituation-Muster</h2>
  <p class="sub">Ø pro Situation · letzte 28 Tage · Farbe relativ zu den gezeigten Zeilen
    (Stress invertiert)</p>
  <table class="grid" style="margin-top:8px">
    <tr><th>Arbeitssituation</th><th>Tage</th><th>Stimmung</th><th>Energie</th><th>Stress</th></tr>
    {rows}
  </table>
  <p class="caption">M13 · <b>HomeWeekdayOverview + HomeWorkContextSummary</b> — zwei
    Mini-Aggregationen auf Home mit festem 28-Tage-Fenster, während der Trends-Screen den
    global gewählten Analysezeitraum nutzt. In der Stress-Spalte zeigen Zellfarbe
    (invertiert: heller = besser) und Pfeil (reine Richtung) in entgegengesetzte Richtungen.</p>
</div>"""


HABITS = [
    ("Sport", "Aufbauen", 18, 20, 0.90, +7, "Im Zielbereich", 0.62),
    ("Spaziergang", "Aufbauen", 12, 20, 0.60, -4, "Richtung Wochenziel", 0.29),
    ("Alkohol", "Reduzieren", 6, 8, 0.75, -11, "Im Zielbereich", None),
]


def m14():
    cards = ""
    for name, typ, tracked, target, adherence, delta, status, corr in HABITS:
        g, col = GLYPH["up" if delta > 0 else "down"]
        corr_line = (
            f'<div class="faint" style="font-size:10.5px;margin-top:4px">'
            f'Korrelationsbeitrag: r={str(corr).replace(".", ",")} Stimmung</div>'
            if corr
            else '<div class="faint" style="font-size:10.5px;margin-top:4px">'
                 'Noch keine Korrelationsdaten</div>'
        )
        cards += f"""
  <div style="border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-top:8px">
    <div class="between">
      <div class="row" style="gap:8px"><b style="font-size:13px">{name}</b>
        <span class="chip sm">{typ}</span></div>
      <span class="mono" style="font-size:12px">{adherence * 100:.0f} %
        <span style="color:{col}">{g} {delta:+d} pp</span></span>
    </div>
    <div style="height:7px;border-radius:4px;background:#2c2925;margin:7px 0 5px">
      <div style="width:{adherence * 100:.0f}%;height:7px;border-radius:4px;
        background:var(--primary)"></div>
    </div>
    <div class="row between" style="font-size:10.5px">
      <span class="muted">{tracked} von {target} Zieltagen · {status}</span>
    </div>
    {corr_line}
  </div>"""
    strip = ""
    vals = [0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1]
    for i, v in enumerate(vals):
        strip += (
            f'<rect x="{i * 17}" y="0" width="14" height="14" rx="3" '
            f'fill="{"#6279d6" if v else "#242322"}"/>'
        )
    return 720, f"""
<div class="card">
  <div class="between">
    <div><h2>Gewohnheiten</h2>
      <p class="sub">Tags, die du als Gewohnheit verfolgst — mit Zielhäufigkeit,
        ohne Belohnungen oder Druck.</p></div>
    <div class="row"><span class="chip sm">28T</span><span class="chip sm">90T</span></div>
  </div>
  {cards}
  <div class="hr"></div>
  <div class="faint" style="font-size:10.5px;margin-bottom:5px">
    Detail „Sport“ — Tagesraster der letzten 28 Tage</div>
  <svg width="480" height="18"><g>{strip}</g></svg>
  <p class="caption">M14 · <b>HabitsPanel + TagHeatmap</b> — Adherence-Balken, Δ zum
    Vorzeitraum und ein einzeiliges Tagesraster; r-Wert kommt aus derselben Engine wie M05.</p>
</div>"""


def m15():
    phases = [("Sammeln", 0, 7), ("Erste Muster", 7, 30), ("Vorläufig", 30, 90), ("Robust", 90, 180)]
    w = 560
    seg = w / 4
    bar = ""
    for i, (label, _s, _e) in enumerate(phases):
        active = i == 2
        fill = "var(--primary)" if i < 2 else ("rgba(124,106,245,.45)" if active else "#2c2925")
        bar += (
            f'<rect x="{i * seg + 2}" y="0" width="{seg - 4}" height="10" rx="5" fill="{fill}"/>'
            f'<text x="{i * seg + seg / 2}" y="26" font-size="10" text-anchor="middle" '
            f'fill="{"var(--text)" if active else "var(--faint)"}">{label}</text>'
        )
    marker = f'<circle cx="{2 * seg + seg * 0.55:.0f}" cy="5" r="6" fill="var(--primary)" ' \
             f'stroke="#1a1815" stroke-width="2"/>'
    cover = [
        ("Eintrags-Abdeckung", 0.86, "78 von 90 Tagen mit Eintrag"),
        ("Symptom-Abdeckung", 0.42, "Symptom-Analysen verfügbar"),
        ("Schlaf-Abdeckung", 0.18, "Sleep-Insights ab 50 % Abdeckung"),
    ]
    rows = ""
    for label, pct, detail in cover:
        col = "var(--energy)" if pct > 0.6 else ("var(--warn)" if pct > 0.3 else "var(--stress)")
        rows += f"""
    <tr><td style="color:var(--text)">{label}</td>
      <td style="width:190px"><span style="display:inline-block;width:170px;height:7px;
        border-radius:4px;background:#2c2925"><span style="display:block;width:{pct * 100:.0f}%;
        height:7px;border-radius:4px;background:{col}"></span></span></td>
      <td class="mono faint">{pct * 100:.0f} % · {detail}</td></tr>"""
    return 700, f"""
<div class="card">
  <div class="between">
    <div><h2>Phase: vorläufig</h2>
      <p class="sub">Noch 12 Einträge bis zur Phase „robust“.</p></div>
    <span class="pill prov">vorläufig</span>
  </div>
  <svg width="{w}" height="34" viewBox="0 0 {w} 34" style="margin-top:10px">{bar}{marker}</svg>
</div>
<div class="card">
  <h2>Datenreife</h2>
  <p class="sub">Wie vollständig deine Gesundheitsdaten sind – und welche Analysen dadurch
    schon bereitstehen.</p>
  <table class="grid" style="margin-top:8px">{rows}</table>
  <p class="caption">M15 · <b>InsightStageHeader + TrendsHealthContext</b> — zwei Antworten auf
    „wie sicher ist das?“: Reifephase (global) und Abdeckung (je Datenquelle).</p>
</div>"""


# ----------------------------------------------------------------------------
# Lücken-Vorschläge
# ----------------------------------------------------------------------------

def g1():
    RNG.seed(3)
    pts_with, pts_without = [], []
    for _ in range(34):
        x = RNG.uniform(0.2, 1.0)
        pts_with.append((x, 3.3 + 1.1 * x + RNG.gauss(0, 0.42)))
    for _ in range(56):
        x = RNG.uniform(0.0, 0.5)
        pts_without.append((x, 3.0 + 0.9 * x + RNG.gauss(0, 0.5)))
    w, h = 400, 250
    px, py, pw, ph = 42, 14, w - 60, h - 46

    def sx(v):
        return px + v * pw

    def sy(v):
        return py + ph - ((max(1, min(5, v)) - 1) / 4) * ph

    dots = ""
    for x, y in pts_without:
        dots += f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3.2" fill="#4b5875" opacity="0.85"/>'
    for x, y in pts_with:
        dots += f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3.6" fill="#9587ff" opacity="0.9"/>'
    fit = f'<line x1="{sx(0):.0f}" y1="{sy(3.0):.0f}" x2="{sx(1):.0f}" y2="{sy(4.3):.0f}" ' \
          f'stroke="var(--primary)" stroke-width="2"/>'
    band = (
        f'<polygon points="{sx(0):.0f},{sy(3.3):.0f} {sx(1):.0f},{sy(4.6):.0f} '
        f'{sx(1):.0f},{sy(4.0):.0f} {sx(0):.0f},{sy(2.7):.0f}" fill="rgba(124,106,245,0.14)"/>'
    )
    grid = "".join(
        f'<line x1="{px}" y1="{py + ph * i / 4:.0f}" x2="{px + pw}" y2="{py + ph * i / 4:.0f}" '
        f'stroke="var(--border)" opacity="0.32"/>'
        f'<text x="{px - 8}" y="{py + ph * i / 4 + 3:.0f}" font-size="9" text-anchor="end" '
        f'fill="var(--faint)">{5 - i}</text>'
        for i in range(5)
    )
    xlab = "".join(
        f'<text x="{sx(v):.0f}" y="{h - 18}" font-size="9" text-anchor="middle" '
        f'fill="var(--faint)">{lab}</text>'
        for v, lab in ((0, "0"), (0.5, "30 min"), (1.0, "60+ min"))
    )
    return 880, f"""
<div class="card">
  <div class="between">
    <div><span class="chip sm" style="border-color:var(--warn);color:var(--warn)">Vorschlag</span>
      <h2 style="margin-top:6px">Signal-Detail: Sport × Stimmung</h2>
      <p class="sub">Ein Punkt = ein Tag. Hover zeigt den Eintrag, Klick öffnet ihn.</p></div>
    <span class="chip sm">Zeitraum: 90 Tage</span>
  </div>
  <div style="display:flex;gap:16px;align-items:flex-start;margin-top:8px">
    <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">
      {grid}{band}{fit}{dots}{xlab}
      <text x="{px - 30}" y="{py + ph / 2}" font-size="9.5" fill="var(--faint)"
        transform="rotate(-90 {px - 30} {py + ph / 2})">Stimmung</text>
      <text x="{px + pw / 2}" y="{h - 4}" font-size="9.5" text-anchor="middle"
        fill="var(--faint)">Sport-Dauer am selben Tag</text>
    </svg>
    <div style="flex:1;font-size:11.5px">
      <p style="margin:0 0 8px"><b>Was die Punktwolke zeigt, die Karte aber nicht:</b></p>
      <ul style="margin:0 0 10px 16px;padding:0;line-height:1.7" class="muted">
        <li>Streuung — wie verlässlich der Zusammenhang je Tag ist</li>
        <li>Ausreißer — einzelne Tage, die r nach oben ziehen</li>
        <li>Form — linear oder Plateau ab 30 Minuten?</li>
        <li>Datendichte — wie viele Tage überhaupt einzahlen</li>
      </ul>
      <div class="row" style="gap:10px">
        <span class="legend"><i class="sw" style="background:#9587ff;border-radius:50%"></i>
          Tage mit Sport (34)</span>
        <span class="legend"><i class="sw" style="background:#4b5875;border-radius:50%"></i>
          ohne (56)</span>
      </div>
      <div class="gapnote">Heute gibt es in CorrelCore <b>kein</b> XY-Diagramm:
        r und Effektstärke erscheinen nur als Zahl oder Balken.</div>
    </div>
  </div>
  <p class="caption">G1 · Vorschlag <b>Streudiagramm / Signal-Detail</b> — deckt Lücke L1
    (keine Rohdaten-Sicht hinter einer Korrelationszahl).</p>
</div>"""


def g2():
    RNG.seed(11)
    w, h = 430, 170
    px, py, pw = 96, 26, w - 120

    def sx(v):
        return px + ((v - 1) / 4) * pw

    rows = ""
    for idx, (label, mu, n, col) in enumerate(
        (("mit Sport", 3.9, 34, "#9587ff"), ("ohne Sport", 3.3, 56, "#4b5875"))
    ):
        y = py + idx * 62
        rows += (
            f'<text x="{px - 10}" y="{y + 16}" font-size="11" text-anchor="end" '
            f'fill="var(--text)">{label}</text>'
            f'<text x="{px - 10}" y="{y + 30}" font-size="9.5" text-anchor="end" '
            f'fill="var(--faint)">n = {n}</text>'
        )
        for _ in range(n):
            v = max(1, min(5, RNG.gauss(mu, 0.55)))
            jitter = RNG.uniform(-9, 9)
            rows += (
                f'<circle cx="{sx(v):.1f}" cy="{y + 14 + jitter:.1f}" r="3" fill="{col}" '
                f'opacity="0.55"/>'
            )
        rows += (
            f'<line x1="{sx(mu):.1f}" y1="{y - 2}" x2="{sx(mu):.1f}" y2="{y + 30}" '
            f'stroke="{col}" stroke-width="2.5"/>'
            f'<text x="{sx(mu):.1f}" y="{y + 44}" font-size="10" text-anchor="middle" '
            f'fill="{col}" class="mono">Ø {str(round(mu, 1)).replace(".", ",")}</text>'
        )
    axis = "".join(
        f'<line x1="{sx(v):.0f}" y1="{py - 8}" x2="{sx(v):.0f}" y2="{h - 26}" '
        f'stroke="var(--border)" opacity="0.3"/>'
        f'<text x="{sx(v):.0f}" y="{h - 12}" font-size="9" text-anchor="middle" '
        f'fill="var(--faint)">{v}</text>'
        for v in (1, 2, 3, 4, 5)
    )
    freq = ""
    for i in range(10):
        for j in range(10):
            idx = i * 10 + j
            fill = "#9587ff" if idx < 62 else "#3a352f"
            freq += (
                f'<rect x="{j * 15}" y="{i * 15}" width="11" height="11" rx="2" fill="{fill}"/>'
            )
    return 900, f"""
<div class="card">
  <div class="between">
    <div><span class="chip sm" style="border-color:var(--warn);color:var(--warn)">Vorschlag</span>
      <h2 style="margin-top:6px">Verteilungsvergleich: mit / ohne Sport</h2>
      <p class="sub">Dieselbe Aussage wie die Insight-Karte — aber mit Streuung und
        Überlappung.</p></div>
  </div>
  <div style="display:flex;gap:22px;align-items:flex-start;margin-top:6px">
    <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{axis}{rows}
      <text x="{px + pw / 2}" y="{h - 1}" font-size="9.5" text-anchor="middle"
        fill="var(--faint)">Stimmung (1–5)</text>
    </svg>
    <div style="width:170px">
      <div class="faint" style="font-size:10px;margin-bottom:6px">Natürliche Häufigkeit</div>
      <svg width="155" height="150" viewBox="0 0 155 150">{freq}</svg>
      <div class="muted" style="font-size:10.5px;margin-top:6px">
        An <b>62 von 100</b> Sport-Tagen lag die Stimmung über deinem Schnitt —
        ohne Sport an 44 von 100.</div>
    </div>
    <div style="flex:1;font-size:11.5px">
      <div class="gapnote" style="margin-top:0">
        Heute steht die Differenz nur als Satz („0,6 Punkte höher“) und als Balken in M05.
        Wie stark sich die beiden Gruppen <i>überlappen</i>, ist nirgends sichtbar —
        genau das trennt ein belastbares von einem zufälligen Muster.</div>
    </div>
  </div>
  <p class="caption">G2 · Vorschlag <b>Verteilungsvergleich + natürliche Häufigkeiten</b> —
    deckt Lücke L2 (Effekt ohne Streuung) und schließt an die v1c-Entscheidung
    „natürliche Häufigkeiten statt blosser Präsenz“ an.</p>
</div>"""


def g3():
    n = 60
    vals = [3.1 + RNG.uniform(-0.3, 0.3) for _ in range(28)] + \
           [3.9 + RNG.uniform(-0.3, 0.3) for _ in range(32)]
    w, h = 620, 180
    px, py, pw, ph = 36, 16, w - 56, h - 54
    line = polyline(vals, px, py, pw, ph, 1, 5)
    cp_x = px + (28 / (n - 1)) * pw
    grid = "".join(
        f'<line x1="{px}" y1="{py + ph * i / 4:.0f}" x2="{px + pw}" y2="{py + ph * i / 4:.0f}" '
        f'stroke="var(--border)" opacity="0.3"/>' for i in range(5)
    )
    seg1_y = py + ph - ((3.1 - 1) / 4) * ph
    seg2_y = py + ph - ((3.9 - 1) / 4) * ph
    return 760, f"""
<div class="card">
  <span class="chip sm" style="border-color:var(--warn);color:var(--warn)">Vorschlag</span>
  <h2 style="margin-top:6px">Changepoint auf der Zeitachse</h2>
  <p class="sub">Der Backend-Insight-Typ <code>changepoint</code> existiert seit M10.1 —
    sichtbar ist er nur als Satz im Feed, nie auf der Achse.</p>
  <svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="margin-top:8px">
    {grid}
    <rect x="{cp_x - 3:.0f}" y="{py - 4}" width="6" height="{ph + 8}" fill="rgba(251,191,36,.18)"/>
    <line x1="{cp_x:.0f}" y1="{py - 8}" x2="{cp_x:.0f}" y2="{py + ph + 4}" stroke="var(--warn)"
      stroke-width="1.8" stroke-dasharray="5 3"/>
    <line x1="{px}" y1="{seg1_y:.0f}" x2="{cp_x:.0f}" y2="{seg1_y:.0f}" stroke="var(--muted)"
      stroke-width="1.5" stroke-dasharray="3 3"/>
    <line x1="{cp_x:.0f}" y1="{seg2_y:.0f}" x2="{px + pw}" y2="{seg2_y:.0f}" stroke="var(--muted)"
      stroke-width="1.5" stroke-dasharray="3 3"/>
    <polyline points="{line}" fill="none" stroke="var(--mood)" stroke-width="2"/>
    <text x="{cp_x + 8:.0f}" y="{py + 4}" font-size="10.5" fill="var(--warn)">
      Niveauwechsel · 14.07.</text>
    <text x="{px + 6}" y="{seg1_y - 6:.0f}" font-size="10" fill="var(--faint)" class="mono">
      Ø 3,1 · 28 Tage</text>
    <text x="{cp_x + 8:.0f}" y="{seg2_y - 6:.0f}" font-size="10" fill="var(--faint)" class="mono">
      Ø 3,9 · 32 Tage</text>
    <text x="{px}" y="{h - 8}" font-size="9" fill="var(--faint)">vor 60 Tagen</text>
    <text x="{px + pw}" y="{h - 8}" font-size="9" text-anchor="end" fill="var(--faint)">heute</text>
  </svg>
  <div class="gapnote">Die Marker-Infrastruktur ist vorhanden (EventMarkerLayer kennt
    <code>phase_transition</code>), nur speist niemand Changepoints ein.
    Erweiterung statt Neubau.</div>
  <p class="caption">G3 · Vorschlag <b>Changepoint-Annotation</b> — deckt Lücke L4
    (Backend-Insight ohne visuelle Entsprechung).</p>
</div>"""


FOREST = [
    ("Sport → Stimmung", 0.62, 0.41, 0.83, 34),
    ("Wenig Schlaf → Energie", -0.54, -0.72, -0.36, 41),
    ("Homeoffice → Stress", -0.41, -0.68, -0.14, 52),
    ("Kopfschmerz → Stimmung", -0.38, -0.79, 0.03, 23),
    ("Kaffee > 3 → Stress", 0.33, -0.05, 0.71, 18),
]


def g4():
    w = 560
    px, pw = 230, w - 260
    rows = ""
    y = 20

    def sx(v):
        return px + ((v + 1) / 2) * pw

    for label, est, lo, hi, n in FOREST:
        crosses = lo < 0 < hi
        col = "var(--faint)" if crosses else (
            "var(--energy)" if est > 0 else "var(--stress)")
        rows += (
            f'<text x="{px - 12}" y="{y + 4}" font-size="11" text-anchor="end" '
            f'fill="{"var(--muted)" if crosses else "var(--text)"}">{label}</text>'
            f'<line x1="{sx(lo):.1f}" y1="{y}" x2="{sx(hi):.1f}" y2="{y}" stroke="{col}" '
            f'stroke-width="2"/>'
            f'<line x1="{sx(lo):.1f}" y1="{y - 4}" x2="{sx(lo):.1f}" y2="{y + 4}" '
            f'stroke="{col}" stroke-width="2"/>'
            f'<line x1="{sx(hi):.1f}" y1="{y - 4}" x2="{sx(hi):.1f}" y2="{y + 4}" '
            f'stroke="{col}" stroke-width="2"/>'
            f'<circle cx="{sx(est):.1f}" cy="{y}" r="4.5" fill="{col}"/>'
            f'<text x="{w - 6}" y="{y + 4}" font-size="9.5" text-anchor="end" '
            f'fill="var(--faint)" class="mono">n={n}</text>'
        )
        y += 34
    zero = (
        f'<line x1="{sx(0):.1f}" y1="6" x2="{sx(0):.1f}" y2="{y - 20}" stroke="var(--border)" '
        f'stroke-width="1.5"/>'
        f'<text x="{sx(0):.1f}" y="{y + 2}" font-size="9" text-anchor="middle" '
        f'fill="var(--faint)">kein Effekt</text>'
    )
    ticks = "".join(
        f'<text x="{sx(v):.1f}" y="{y + 2}" font-size="9" text-anchor="middle" '
        f'fill="var(--faint)">{str(v).replace(".", ",")}</text>'
        for v in (-1, -0.5, 0.5, 1)
    )
    return 760, f"""
<div class="card">
  <span class="chip sm" style="border-color:var(--warn);color:var(--warn)">Vorschlag</span>
  <h2 style="margin-top:6px">Effektstärke mit Unsicherheitsintervall</h2>
  <p class="sub">Ersetzt bzw. ergänzt den Effekt-Balken der Korrelations-Matrix (M05):
    gleiche Zeile, aber mit Intervall statt Punktwert.</p>
  <svg width="{w}" height="{y + 14}" viewBox="0 0 {w} {y + 14}" style="margin-top:8px">
    {zero}{rows}{ticks}
  </svg>
  <div class="gapnote">Zeilen, deren Intervall die Null kreuzt, werden grau — das ist
    dieselbe Information, die heute hinter „4 schwächere Zusammenhänge anzeigen“
    versteckt ist, nur ehrlich skaliert.</div>
  <p class="caption">G4 · Vorschlag <b>Forest-Plot</b> — deckt Lücke L3
    (Konfidenz als 5-Punkte-Skala sagt nichts über die Breite des Effekts).</p>
</div>"""


MOCKS = {"m13_home": m13, "m14_gewohnheiten": m14, "m15_reife_abdeckung": m15,
         "g1_streudiagramm": g1, "g2_verteilungsvergleich": g2,
         "g3_changepoint": g3, "g4_forest_plot": g4}
