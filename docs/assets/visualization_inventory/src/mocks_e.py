"""Proposal mockups for the four-layer model (E1-E6) — analysis of #875/#892/#928/#930/#931."""

from lib import polyline, series


def dots(n: int, total: int = 5) -> str:
    out = []
    for i in range(total):
        col = "var(--primary)" if i < n else "var(--border)"
        out.append(
            f'<span style="width:7px;height:7px;border-radius:50%;background:{col};'
            'display:inline-block;margin-right:3px"></span>'
        )
    return "".join(out)


def bar(label: str, val: float, vmax: float, colour: str, sub: str = "") -> str:
    w = max(2, int(val / vmax * 210))
    return f"""
<div class="row" style="gap:8px;margin:5px 0">
  <span class="mono faint" style="font-size:10px;width:96px;text-align:right">{label}</span>
  <span style="width:210px;height:14px;background:var(--offset);border-radius:3px;display:inline-block">
    <span style="display:block;width:{w}px;height:14px;background:{colour};border-radius:3px"></span>
  </span>
  <span class="mono muted" style="font-size:10px">{sub}</span>
</div>"""


def dist(values, colour: str, x0: int, y0: int, w: int, h: int) -> str:
    """Small horizontal density strip (schematic distribution)."""
    n = len(values)
    step = w / n
    out = []
    for i, v in enumerate(values):
        bh = max(1.5, v * h)
        out.append(
            f'<rect x="{x0 + i * step:.1f}" y="{y0 + h - bh:.1f}" width="{step - 1.4:.1f}" '
            f'height="{bh:.1f}" rx="1.5" fill="{colour}" opacity="0.85"/>'
        )
    return "".join(out)


# --------------------------------------------------------------------------- E1

def e1_hub_slim():
    return 740, f"""
<div class="between" style="margin-bottom:10px">
  <div><h1 style="font-size:17px">Erkenntnisse</h1>
    <p class="sub">Analysezeitraum: letzte 90 Tage · 78 Einträge</p></div>
  <div class="row"><span class="pill prov">vorläufig</span>
    <span class="chip sm">Zeitraum ▾</span></div>
</div>

<div class="card" style="border-left:3px solid var(--primary)">
  <div class="between">
    <span class="chip sm" style="border-color:var(--primary);color:var(--primary)">Zusammenhang</span>
    <span class="row" style="gap:6px"><span class="pill prov">vorläufig</span>
      <span class="faint" style="font-size:11px">✕</span></span>
  </div>
  <p style="font-size:14px;line-height:1.45;margin:10px 0 4px">
    An Tagen mit <b>Sport</b> war deine <b>Stimmung</b> im Schnitt
    <b>0,6 Punkte höher</b> als an Tagen ohne.</p>
  <p class="muted" style="font-size:11.5px;margin:0 0 8px">
    Gut an <b>24 von 34</b> Sport-Tagen · gut an <b>29 von 56</b> Tagen ohne Sport
    <span class="faint">— beide Nenner, ein Zeitraum (90 Tage)</span></p>
  <div class="row" style="gap:10px;margin:6px 0 2px">
    <span>{dots(3)}</span>
    <span class="faint" style="font-size:11px">Konfidenz · basierend auf 90 Tagen</span>
  </div>
  <div class="row" style="gap:8px;margin-top:10px">
    <span class="chip on sm">Zusammenhang prüfen →</span>
    <span class="chip sm">Nicht relevant</span>
  </div>
  <p class="caption">Ebene 1 · <b>eine</b> Konfidenzsprache, <b>ein</b> Fenster,
    natürliche Häufigkeiten mit zwei Nennern (D3). Der CTA ist der einzige Weg nach Ebene 2.</p>
</div>

<div class="card">
  <p style="font-size:13.5px;line-height:1.45;margin:0 0 6px">
    <b>Homeoffice-Tage</b> gingen mit <b>weniger Stress</b> einher —
    an <b>19 von 41</b> Homeoffice-Tagen gegenüber <b>9 von 37</b> Bürotagen.</p>
  <div class="row" style="gap:10px"><span>{dots(2)}</span>
    <span class="faint" style="font-size:11px">Konfidenz · noch wenig Bürotage</span>
    <span class="chip sm">prüfen →</span></div>
</div>

<div class="card" style="background:var(--offset)">
  <div class="between">
    <span class="muted" style="font-size:11.5px">Weitere Werkzeuge</span>
    <span class="faint" style="font-size:10px">nicht mehr im Einstieg</span>
  </div>
  <div class="row" style="gap:6px;margin-top:8px;flex-wrap:wrap">
    <span class="chip sm">Tabelle aller Zusammenhänge →</span>
    <span class="chip sm">Zeitversatz-Übersicht →</span>
    <span class="chip sm">Tag-Kombinationen →</span>
    <span class="chip sm">Archiv (7) →</span>
    <span class="chip sm">Bericht erstellen →</span>
  </div>
  <p class="caption">D5 · statt acht Default-Sektionen: zwei Antworten plus Links.
    Vorsicht — ein Flip in <span class="mono">DEFAULT_INSIGHT_SECTIONS</span> erreicht
    Bestandsnutzer nicht (<span class="mono">merge()</span> behandelt Gespeichertes als maßgeblich).</p>
</div>"""


# --------------------------------------------------------------------------- E2

def e2_signal_detail():
    with_vals = [0.10, 0.22, 0.45, 0.78, 1.00, 0.72, 0.38, 0.14]
    without_vals = [0.34, 0.62, 0.95, 0.80, 0.48, 0.22, 0.10, 0.05]
    line_a = [round(3.0 + 0.10 * i + (0.12 if i % 3 else -0.1), 2) for i in range(21)] + [
        round(4.15 + 0.30 * (1 - abs(i - 6) / 9) + (0.1 if i % 2 else -0.08), 2) for i in range(39)
    ]
    return 740, f"""
<div class="between" style="margin-bottom:10px">
  <div class="row" style="gap:8px"><span class="faint" style="font-size:12px">←</span>
    <div><h1 style="font-size:16px">Sport → Stimmung</h1>
      <p class="sub">Eine Hypothese · Fenster: letzte 90 Tage · 78 Einträge</p></div></div>
  <span class="pill prov">vorläufig</span>
</div>

<div class="card">
  <p style="font-size:14px;line-height:1.45;margin:0 0 4px">
    An Tagen mit <b>Sport</b> war deine <b>Stimmung</b> im Schnitt
    <b>0,6 Punkte höher</b> als an Tagen ohne.</p>
  <p class="faint" style="font-size:11px;margin:0">
    Ein Zusammenhang in deinen Einträgen — keine Ursache.</p>
</div>

<div class="card">
  <h2>Mit und ohne Sport</h2>
  <p class="sub">Wie sich die Tage verteilen — nicht nur der Mittelwert</p>
  <svg width="700" height="150" role="img">
    <text x="0" y="14" class="tick" style="font-size:10px">mit Sport · 34 Tage</text>
    {dist(with_vals, "var(--primary)", 0, 20, 320, 44)}
    <line x1="0" y1="64" x2="320" y2="64" class="axis"/>
    <text x="0" y="94" class="tick" style="font-size:10px">ohne Sport · 56 Tage</text>
    {dist(without_vals, "var(--muted)", 0, 100, 320, 44)}
    <line x1="0" y1="144" x2="320" y2="144" class="axis"/>
    <text x="0" y="78" class="tick">1</text><text x="310" y="78" class="tick">5</text>
    <line x1="360" y1="10" x2="360" y2="146" class="axis"/>
    <text x="380" y="26" style="font-size:11.5px;fill:var(--text)">Überlappung: gering</text>
    <text x="380" y="46" style="font-size:11px;fill:var(--muted)">Gut an 24 von 34 Sport-Tagen</text>
    <text x="380" y="64" style="font-size:11px;fill:var(--muted)">Gut an 29 von 56 Tagen ohne</text>
    <text x="380" y="90" style="font-size:11px;fill:var(--faint)">Verschiebung: +0,6 Punkte</text>
    <text x="380" y="108" style="font-size:11px;fill:var(--faint)">Konfidenz: 3 von 5</text>
    <text x="380" y="134" style="font-size:10.5px;fill:var(--faint)">Lift 1,4 ⓘ (Power-Ansicht)</text>
  </svg>
  <p class="caption">G2 · Lücke L2 — der häufigste Insight-Typ
    (<span class="mono">pointbiserial</span>) wird erstmals prüfbar. Zwei Nenner statt einer Zahl.</p>
</div>

<div class="card">
  <div class="between"><h2>Verlauf um die Sport-Tage</h2>
    <span class="chip sm">Ausgerichtete Ereignisse öffnen →</span></div>
  <svg width="700" height="96" role="img">
    <line x1="30" y1="86" x2="690" y2="86" class="axis"/>
    <line x1="250" y1="12" x2="250" y2="86" stroke="var(--marker)" stroke-dasharray="3 3"/>
    <text x="254" y="22" class="tick">T0</text>
    <polyline points="{polyline(line_a, 30, 12, 660, 66)}" fill="none"
      stroke="var(--mood)" stroke-width="1.8"/>
    <text x="30" y="20" class="tick">5</text><text x="30" y="84" class="tick">1</text>
  </svg>
  <div class="row" style="gap:6px;margin-top:4px">
    <span class="chip sm">Punktwolke anzeigen ▾</span>
    <span class="chip sm">In Trends anpinnen →</span>
    <span class="chip sm">Für Bericht merken</span>
  </div>
  <p class="caption">Ebene 2 (D1) · Satz → mit/ohne (G2) → Verlauf/ESM → Scatter (G1) hinter
    Disclosure. Ein Fenster, eine Konfidenzsprache, ein Weg zurück.</p>
</div>"""


# --------------------------------------------------------------------------- E3

def e3_nicht_ergebnis():
    a = [0.28, 0.55, 0.86, 1.00, 0.74, 0.40, 0.16, 0.07]
    b = [0.30, 0.58, 0.88, 0.96, 0.70, 0.44, 0.18, 0.08]
    return 740, f"""
<div class="between" style="margin-bottom:10px">
  <div class="row" style="gap:8px"><span class="faint" style="font-size:12px">←</span>
    <div><h1 style="font-size:16px">Kaffee → Schlafqualität</h1>
      <p class="sub">Eine Hypothese · Fenster: letzte 90 Tage</p></div></div>
  <span class="chip sm" style="border-color:var(--ok);color:var(--ok)">kein Muster</span>
</div>

<div class="card" style="border-left:3px solid var(--ok)">
  <p style="font-size:14px;line-height:1.45;margin:0 0 4px">
    <b>Kaffee-Tage</b> unterscheiden sich in deinen Daten <b>nicht</b> von den anderen Tagen.</p>
  <p class="muted" style="font-size:11.5px;margin:0">
    Gut geschlafen an <b>21 von 47</b> Kaffee-Tagen · an <b>20 von 43</b> Tagen ohne.
    Das ist praktisch derselbe Anteil.</p>
</div>

<div class="card">
  <h2>Mit und ohne Kaffee</h2>
  <svg width="700" height="150" role="img">
    <text x="0" y="14" class="tick" style="font-size:10px">mit Kaffee · 47 Tage</text>
    {dist(a, "var(--primary)", 0, 20, 320, 44)}
    <line x1="0" y1="64" x2="320" y2="64" class="axis"/>
    <text x="0" y="94" class="tick" style="font-size:10px">ohne Kaffee · 43 Tage</text>
    {dist(b, "var(--muted)", 0, 100, 320, 44)}
    <line x1="0" y1="144" x2="320" y2="144" class="axis"/>
    <line x1="360" y1="10" x2="360" y2="146" class="axis"/>
    <text x="380" y="26" style="font-size:11.5px;fill:var(--ok)">Überlappung: fast vollständig</text>
    <text x="380" y="48" style="font-size:11px;fill:var(--muted)">Verschiebung: 0,05 Punkte</text>
    <text x="380" y="66" style="font-size:11px;fill:var(--muted)">Konfidenz: nicht aussagekräftig</text>
    <text x="380" y="94" style="font-size:11px;fill:var(--faint)">Für dich heißt das: du kannst diese</text>
    <text x="380" y="110" style="font-size:11px;fill:var(--faint)">Vermutung vorläufig zur Seite legen.</text>
  </svg>
  <div class="row" style="gap:6px;margin-top:2px">
    <span class="chip sm">Andere Vermutung prüfen →</span>
    <span class="chip sm">In 30 Tagen erneut ansehen</span>
  </div>
  <p class="caption">D2 · Nicht-Ergebnis als eigenes, gleichwertiges Resultat.
    Kostet fast nichts, weil überlappende Verteilungen <b>die</b> Antwort sind (deckt L9).</p>
</div>

<div class="gapnote">Berührt <b>§1.6</b>: „Time-to-First-Insight &lt; 14 Tage" wird als Metrik
  unbrauchbar, wenn ein Nicht-Ergebnis ein gültiges Ergebnis ist — die Kennzahl muss zu
  <b>Time-to-First-Answer</b> umdefiniert werden, sonst belohnt sie weiter den Zufallsbefund.</div>"""


# --------------------------------------------------------------------------- E4

def e4_compare_range():
    mood = series(56, 3.7, 0.6, 13, 0.0, 0.2)
    energy = series(56, 3.2, 0.7, 9, 1.1, 0.22)
    rows = [("Sport", 3, 0), ("Homeoffice", 7, 1), ("Deadline", 9, 4)]
    row_html = ""
    for i, (name, every, off) in enumerate(rows):
        cells = ""
        for j in range(56):
            on = (j + off) % every in (0, 1) if every < 8 else (j + off) % every == 0
            col = "var(--hm4)" if on else "var(--offset)"
            cells += (f'<rect x="{60 + j * 11.2:.1f}" y="{6 + i * 20}" width="9.6" height="13" '
                      f'rx="2" fill="{col}"/>')
        row_html += (f'<text x="0" y="{17 + i * 20}" class="tick" style="font-size:10px">'
                     f'{name}</text>{cells}')
    return 740, f"""
<div class="between" style="margin-bottom:8px">
  <div><h1 style="font-size:17px">Trends · Vergleichen</h1>
    <p class="sub">Labor — hier darf Dichte sein, weil du sie wählst</p></div>
  <span class="chip sm">Einstellungen ▾</span>
</div>

<div class="card">
  <div class="between" style="margin-bottom:8px">
    <div class="row" style="gap:5px">
      <span class="chip sm">Woche</span><span class="chip sm">Monat</span>
      <span class="chip on sm">Quartal</span><span class="chip sm">Jahr</span>
    </div>
    <span class="chip sm" style="border-color:var(--warn);color:var(--warn)">
      Fenster: 01.07.–18.09.2026 · 90 Tage</span>
  </div>
  <svg width="700" height="128" role="img">
    <line x1="30" y1="110" x2="690" y2="110" class="axis"/>
    <polyline points="{polyline(mood, 60, 8, 630, 96)}" fill="none" stroke="var(--mood)"
      stroke-width="1.8"/>
    <polyline points="{polyline(energy, 60, 8, 630, 96)}" fill="none" stroke="var(--energy)"
      stroke-width="1.8"/>
    <text x="30" y="16" class="tick">5</text><text x="30" y="108" class="tick">1</text>
  </svg>
  <svg width="700" height="70" role="img">{row_html}</svg>
  <div class="row" style="gap:10px;margin-top:6px">
    <span class="legend"><span class="sw" style="background:var(--mood)"></span>Stimmung</span>
    <span class="legend"><span class="sw" style="background:var(--energy)"></span>Energie</span>
    <span class="legend"><span class="sw" style="background:var(--hm4)"></span>Tag war aktiv</span>
  </div>
  <div class="hr"></div>
  <div class="between">
    <span class="muted" style="font-size:11.5px">Sport &amp; Homeoffice angepinnt —
      beides aktiv an <b>11 von 34</b> Sport-Tagen · <b>11 von 41</b> Homeoffice-Tagen</span>
    <span class="chip on sm">Diese Frage prüfen →</span>
  </div>
  <p class="caption">O5/W6 · Der Zeitraum-Regler ist auf <b>Vergleichen</b> wieder da
    (<span class="mono">showRangeControl={{activeTab !== 'compare'}}</span> entfällt) und das
    Fenster steht sichtbar am Chart. Der CTA verbindet Ebene 3 → Ebene 2 (ESM/Signal).</p>
</div>

<div class="gapnote">Solange Home <b>28 Tage</b> und Vergleichen <b>365 Tage</b> meinen, können zwei
  Pfeile auf einem Screen in entgegengesetzte Richtungen zeigen — das ist der teuerste
  Vertrauensbruch im ganzen Inventar und hängt zusätzlich an #867.</div>"""


# --------------------------------------------------------------------------- E5

def e5_belastung_overlay():
    stress = series(28, 3.4, 0.7, 9, 0.3, 0.2)
    energy = series(28, 2.9, 0.6, 11, 2.0, 0.2)
    return 740, f"""
<div class="between" style="margin-bottom:8px">
  <div><h1 style="font-size:17px">Belastung &amp; Erholung</h1>
    <p class="sub">Optionaler Bereich · in Einstellungen aktiviert</p></div>
  <span class="chip sm">aktiv · abschaltbar</span>
</div>

<div class="card" style="border-left:3px solid var(--warn)">
  <div class="between">
    <h2>Belastungsmuster der letzten 14 Tage</h2>
    <span class="pill early">Hinweis, keine Bewertung</span>
  </div>
  <p style="font-size:13.5px;line-height:1.45;margin:8px 0 2px">
    In den letzten zwei Wochen lagen <b>höherer Stress</b>, <b>niedrigere Energie</b> und
    <b>Erschöpfung</b> häufiger zusammen als in den vier Wochen davor.</p>
  <p class="muted" style="font-size:11.5px;margin:0 0 8px">
    Erschöpfung an <b>7 von 14</b> Tagen · davor an <b>4 von 28</b> Tagen.
    Erholungstage (Wochenende, Urlaub, Nap): <b>3 von 14</b> · davor <b>9 von 28</b>.</p>
  <svg width="700" height="82" role="img">
    <line x1="30" y1="68" x2="690" y2="68" class="axis"/>
    <polyline points="{polyline(stress, 40, 8, 640, 58)}" fill="none" stroke="var(--stress)"
      stroke-width="1.8"/>
    <polyline points="{polyline(energy, 40, 8, 640, 58)}" fill="none" stroke="var(--energy)"
      stroke-width="1.8" stroke-dasharray="3 2"/>
    <text x="30" y="16" class="tick">5</text><text x="30" y="66" class="tick">1</text>
  </svg>
  <div class="row" style="gap:10px">
    <span class="legend"><span class="sw" style="background:var(--stress)"></span>Stress</span>
    <span class="legend"><span class="sw" style="background:var(--energy)"></span>Energie</span>
    <span class="faint" style="font-size:10px">28 Tage · heuristisch zusammengefasst</span>
  </div>
  <div class="hr"></div>
  <div class="row" style="gap:6px">
    <span class="chip on sm">Arbeitsintensität prüfen →</span>
    <span class="chip sm">Schlaf → Folgetag prüfen →</span>
  </div>
  <p style="font-size:10.5px;color:var(--faint);line-height:1.5;margin:10px 0 0">
    Dies ist keine medizinische Einschätzung und keine Diagnose. CorrelCore zeigt Muster in
    deinen eigenen Einträgen. Wenn dich deine Belastung anhaltend beeinträchtigt, sprich mit
    einer Ärztin oder Therapeutin. Diese Daten liegen ausschließlich bei dir —
    <b>niemals bei einem Arbeitgeber</b>.</p>
  <p class="caption">#875 Option 1 + benannter Composite, opt-in, keine neuen Pflichtfelder.
    Landeplatz ist <b>Ebene 1</b> mit CTA in Ebene 2 — nicht eine neunte
    <span class="mono">/insights</span>-Sektion.</p>
</div>

<div class="gapnote">Der Composite braucht ein Erholungssignal, das nicht arbeitsförmig ist —
  <span class="mono">work_context</span> kennt nur
  <span class="mono">homeoffice|office|vacation|sick|weekend|travel</span> und hat keinen Wert für
  Elternzeit, Studium, Rente oder Arbeitslosigkeit. Genau die Leitsituation aus #875 (AU-Phase im
  Wiedereinstieg) fällt sonst aus dem Anker.</div>"""


# --------------------------------------------------------------------------- E6

def e6_bericht():
    rows = [
        ("Sport", "Stimmung", "+0,6 Punkte", "24/34 vs. 29/56", 3, "vorläufig"),
        ("Homeoffice", "Stress", "−0,5 Punkte", "19/41 vs. 9/37", 2, "früh"),
        ("Wenig Schlaf", "Energie (Folgetag)", "−0,7 Punkte", "12/19 vs. 14/71", 4, "belastbar"),
        ("Deadline", "Erschöpfung", "+0,4 Punkte", "8/12 vs. 11/78", 2, "früh"),
    ]
    body = ""
    for a, b, eff, freq, conf, phase in rows:
        cls = {"früh": "early", "vorläufig": "prov", "belastbar": "rob"}[phase]
        body += (f'<tr><td>{a}</td><td>{b}</td><td class="mono">{eff}</td>'
                 f'<td class="mono muted">{freq}</td><td>{dots(conf)}</td>'
                 f'<td><span class="pill {cls}">{phase}</span></td></tr>')
    return 740, f"""
<div class="between" style="margin-bottom:8px">
  <div><h1 style="font-size:17px">Bericht</h1>
    <p class="sub">Zum Mitnehmen ins Arztgespräch · 01.07.–18.09.2026</p></div>
  <div class="row" style="gap:5px">
    <span class="chip on sm">Als PDF</span><span class="chip sm">PNG</span>
    <span class="chip sm">CSV</span><span class="chip sm">JSON</span></div>
</div>

<div class="card">
  <div class="between">
    <h2>Zusammenhänge im Zeitraum</h2>
    <span class="chip sm">Zeilen abwählen</span>
  </div>
  <p class="sub">Dichte ist hier gewollt — ein Ausdruck soll eine Tabelle sein</p>
  <table class="grid" style="margin-top:10px">
    <tr><th>Faktor</th><th>wirkt auf</th><th>Unterschied</th><th>Häufigkeiten</th>
      <th>Konfidenz</th><th>Datenreife</th></tr>
    {body}
  </table>
  <div class="hr"></div>
  <div class="between">
    <span class="muted" style="font-size:11px">78 Einträge · Eintragsquote 87 % ·
      Schlafdaten an 61 von 90 Tagen</span>
    <span class="faint" style="font-size:10px">Keine Diagnose. Muster aus Selbstauskunft.</span>
  </div>
  <p class="caption">Ebene 4 · hier landet die heutige „Korrelations-Matrix" (M05) —
    als Bericht, nicht als Hub-Einstieg. Umbenannt, mit <b>einer</b> Konfidenzskala und beiden
    Nennern je Zeile.</p>
</div>

<div class="gapnote"><b>Diese Ebene existiert noch nicht als Fläche.</b> Verifiziert im Repo:
  <span class="mono">pdf</span> kommt weder in <span class="mono">apps/web/src</span> noch in
  <span class="mono">backend/app</span> vor; CSV/JSON/ZIP liegen in
  <span class="mono">/settings/data</span> (einer Datenschutz-Seite), PNG steckt <b>innerhalb</b>
  von <span class="mono">InsightMatrix.svelte:106</span>. „M05 → Ebene 4" verschiebt die Matrix
  also in einen Raum, den es nicht gibt — und ein „Default aus" für
  <span class="mono">correlation_matrix</span> entfernt nebenbei den einzigen PNG-Export.</div>"""


MOCKS = {
    "e1_hub_ebene1": e1_hub_slim,
    "e2_signal_detail": e2_signal_detail,
    "e3_nicht_ergebnis": e3_nicht_ergebnis,
    "e4_compare_zeitraum": e4_compare_range,
    "e5_belastung_overlay": e5_belastung_overlay,
    "e6_bericht_ebene4": e6_bericht,
}
