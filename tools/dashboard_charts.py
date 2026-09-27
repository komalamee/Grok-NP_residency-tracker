"""SVG chart and component builders for the HTML dashboard; the PDF export reuses several of them through
render_pdf.static_svg(), which turns the CSS classes here into presentation attributes.

v3 (26 Sep 2026) mirrors the Nomad Pro iOS app (its theme and dashboard components):
KpiProgressCard rings (track #EAE3D8, round caps), CountryDoughnutChart (stroke 26, butt caps, total + "days" in the
centre, legend rows "55d 32%"), MonthlyStackedChart (rounded #EDE7DE bar tracks, total above), LocationTimelineChart
(one row per stay: full country name, dates, day count, pill track with the coloured bar).

Colour carries category, never a verdict. UK = app coral (theme.chartColours['United Kingdom']); other countries use the
app chart colours where they do not collide with the reserved amber. Proximity uses one scale everywhere:
more than 20 days of room = calm (teal), 6-20 = amber, 0-5 or over = deep ochre. No green/red status colours.
Hover text lives in data-tip attributes (dashboard.js); SVG <title> is the no-JS fallback.
"""
from __future__ import annotations

import json
import math
from collections import Counter, OrderedDict
from datetime import date, timedelta

import srt_engine as E
from render_common import esc

# App theme tokens (from the Nomad Pro app theme)
PRIMARY = "#1A9B8C"       # colours.primary
PRIMARY_DARK = "#117C71"  # 3D button edge (DashboardScreen checkinActionButton)
CORAL = "#E8725A"         # colours.secondary; chartColours['United Kingdom']
AMBER = "#E5A535"         # colours.tertiary: here ONLY logging gaps and approaching a figure
OCHRE = "#A8620A"         # deeper step of the same amber scale for 0-5 days of room / over (not a red)
INFO = "#5BBFCF"          # colours.info
VIOLET = "#9B7ED8"        # chartColours['South Korea'] -> UK work days
INK = "#2D2D2D"           # textPrimary
INK_2 = "#6B6B6B"         # textSecondary
MUTED = "#9E9E9E"         # textMuted
BORDER = "#E8E2D9"
TRACK = "#EAE3D8"         # KpiProgressCard ring track
BAR_TRACK = "#EDE7DE"     # MonthlyStackedChart barTrack
PILL_TRACK = "#ECE5DC"    # LocationTimelineChart track
DONUT_TRACK = "#ECE6DD"
GAP_FILL = "#FFF1D6"
TEAL = PRIMARY            # alias used by the renderer
PLUM = VIOLET
INK_DARK = INK
GRID = "#EFEAE3"

# App chartColours where usable; Thailand/UAE are amber/gold in the app, re-mapped because amber is reserved here.
APP_COUNTRY = {"GB": CORAL, "SG": "#1A9B8C", "CY": "#5BBFCF", "PT": "#3EAF6E", "KR": "#9B7ED8", "FR": "#5B8FC9",
               "TH": "#EC6B9D", "AE": "#C9B28A", "CH": "#7A6FD0"}
PALETTE = ["#4F7CAC", "#8FB8DE", "#C7A4E8", "#B5835A", "#6FA88A", "#D98FB7", "#7FA7C9", "#B98AA0", "#5E8CA8", "#A08BC0",
           "#A3A86B", "#4F9D8F", "#C49A6C", "#8A9BB0", "#B9B2A6"]


def band(room):
    """(key, colour, label) on the engine's proximity scale."""
    if room is None:
        return "calm", PRIMARY, ""
    if room < 0:
        return "deep", OCHRE, "over the line"
    if room <= 5:
        return "deep", OCHRE, "at the line"
    if room <= 20:
        return "warn", AMBER, "getting close"
    return "calm", PRIMARY, "comfortable room"


class Colours:
    """Stable country -> colour map for one dashboard."""

    def __init__(self, log: E.DayLog):
        c = Counter(r["midnight_country"] for r in log.days.values() if r.get("midnight_country") and r.get("confidence") != "planned")
        for p in log.planned:
            c[p["country"]] += 0
        self.map = {"UNLOGGED": GAP_FILL}
        i = 0
        for code, _ in c.most_common():
            if code in APP_COUNTRY:
                self.map[code] = APP_COUNTRY[code]
        for code, _ in c.most_common():
            if code in self.map:
                continue
            self.map[code] = PALETTE[i % len(PALETTE)]
            i += 1

    def __call__(self, code):
        if code not in self.map:
            self.map[code] = PALETTE[len(self.map) % len(PALETTE)]
        return self.map[code]


def cn(code):
    return "Not logged" if code in (None, "UNLOGGED") else E.cname(code)


# ------------------------------------------------------------------ KPI ring (KpiProgressCard: 48px, r17, stroke 6)
def ring(value, total, colour, size=56, stroke=7, tip=""):
    r = (size - stroke) / 2 - 1
    c = 2 * math.pi * r
    frac = 0 if not total else max(0.0, min(1.0, value / total))
    return (f"<svg class='ring' viewBox='0 0 {size} {size}' width='{size}' height='{size}' role='img' aria-label='{esc(tip or value)}'"
            + (f" data-tip='{esc(tip)}'" if tip else "") + ">"
            f"<circle cx='{size/2}' cy='{size/2}' r='{r:.1f}' fill='none' stroke='{TRACK}' stroke-width='{stroke}'/>"
            f"<circle cx='{size/2}' cy='{size/2}' r='{r:.1f}' fill='none' stroke='{colour}' stroke-width='{stroke}' stroke-linecap='round'"
            f" stroke-dasharray='{c * frac:.1f} {c:.1f}' transform='rotate(-90 {size/2} {size/2})'/></svg>")


def meter(value, total, colour, marks=(), attn=False):
    mx = max([total, value] + [m for m, _ in marks]) or 1
    pct = min(100, 100 * value / mx)
    ticks = "".join(f"<i class='tick' style='left:{100 * m / mx:.1f}%' data-tip='{esc(t)}'><b>{m}</b></i>" for m, t in marks)
    return f"<div class='meter{' attn' if attn else ''}'><span style='width:{pct:.1f}%;background:{colour}'></span>{ticks}</div>"


# ------------------------------------------------------------------ donut (CountryDoughnutChart)
def donut(items, colours, size=196, radius=66, stroke=26, centre="", centre_sub="days"):
    total = sum(v for _, v in items) or 1
    c = 2 * math.pi * radius
    out = [f"<svg class='donut' viewBox='0 0 {size} {size}' width='{size}' height='{size}' role='img' aria-label='Days by country'>",
           f"<circle cx='{size/2}' cy='{size/2}' r='{radius}' fill='none' stroke='{DONUT_TRACK}' stroke-width='{stroke}'/>"]
    off = 0.0
    for code, v in items:
        arc = c * v / total
        tip = f"{cn(code)}: {v} day{'s' if v != 1 else ''} ({100 * v / total:.0f}%)"
        col = AMBER if code == "UNLOGGED" else colours(code)
        out.append(f"<circle cx='{size/2}' cy='{size/2}' r='{radius}' fill='none' stroke='{col}' stroke-width='{stroke}' stroke-linecap='butt'"
                   f" stroke-dasharray='{arc:.2f} {c - arc:.2f}' stroke-dashoffset='{-off:.2f}' transform='rotate(-90 {size/2} {size/2})'"
                   f"{' opacity=.55' if code == 'UNLOGGED' else ''} data-tip='{esc(tip)}'><title>{esc(tip)}</title></circle>")
        off += arc
    out.append(f"<text x='50%' y='{size/2 - 2}' text-anchor='middle' class='rb' font-size='28'>{esc(centre)}</text>"
               f"<text x='50%' y='{size/2 + 20}' text-anchor='middle' class='rs' font-size='13'>{esc(centre_sub)}</text></svg>")
    return "".join(out)


def legend(items, colours, total=None, limit=8):
    rows = []
    for code, v in items[:limit]:
        pct = f"<em>{round(100 * v / total)}%</em>" if total else ""
        sw = f"background:{colours(code)}" if code != "UNLOGGED" else f"background:{GAP_FILL};box-shadow:inset 0 0 0 2px {AMBER}"
        rows.append(f"<li><i style='{sw}'></i><span>{esc(cn(code))}</span><b>{v}d</b>{pct}</li>")
    rest = items[limit:]
    if rest:
        rows.append(f"<li><i style='background:#D4CFC7'></i><span>Other ({len(rest)})</span><b>{sum(v for _, v in rest)}d</b>"
                    f"{f'<em>{round(100 * sum(v for _, v in rest) / total)}%</em>' if total else ''}</li>")
    return f"<ul class='legend'>{''.join(rows)}</ul>"


# ------------------------------------------------------------------ monthly bars (MonthlyStackedChart)
def monthly_stacked(log, start, end, colours, full_end=None):
    months = OrderedDict()
    d = date(start.year, start.month, 1)
    last = full_end or end
    while d <= last:
        months[(d.year, d.month)] = Counter()
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    for day in E.daterange(start, end):
        r = log.row(day)
        months[(day.year, day.month)][r["midnight_country"] if r else "UNLOGGED"] += 1
    cols = []
    for (yr, mo), counts in months.items():
        total = sum(counts.values())
        order = sorted(counts.items(), key=lambda kv: (kv[0] != "GB", kv[0] == "UNLOGGED", -kv[1]))
        segs = "".join(
            f"<span style='flex:{v};background:{GAP_FILL if c == 'UNLOGGED' else colours(c)}{f';box-shadow:inset 0 0 0 2px {AMBER}' if c == 'UNLOGGED' else ''}'"
            f" data-tip='{esc(f'{E.MONTHS[mo - 1]} {yr} · {cn(c)}: {v}d')}'></span>" for c, v in reversed(order))
        cols.append(f"<div class='mcol'><b>{total or ''}</b><div class='mtrack'><div class='mfill' style='height:{100 * total / 31:.1f}%'>{segs}</div></div>"
                    f"<small>{E.MONTHS[mo - 1]}</small></div>")
    return f"<div class='mbars'>{''.join(cols)}</div>"


# ------------------------------------------------------------------ location timeline (LocationTimelineChart rows)
def timeline_rows(stays, start, end, colours, today=None, max_rows=None, planned=()):
    total = (end - start).days + 1
    fmt = lambda d: f"{d.day} {E.MONTHS[d.month - 1]}"
    marks = []
    d = date(start.year, start.month, 1)
    while d <= end:
        if d > start:
            marks.append(100 * (d - start).days / total)
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    grid = "".join(f"<i style='left:{m:.2f}%'></i>" for m in marks)
    today_mark = f"<u style='left:{100 * ((today - start).days + 0.5) / total:.2f}%'></u>" if today and start <= today <= end else ""
    rows = []
    items = [(s, False) for s in stays] + [(p, True) for p in planned]
    for s, is_plan in items:
        a, b = E.parse_date(s["from"]), E.parse_date(s["to"])
        a2, b2 = max(a, start), min(b, end)
        if a2 > b2:
            continue
        n = (b - a).days + 1
        c = s["country"]
        left = 100 * (a2 - start).days / total
        width = max(100 * ((b2 - a2).days + 1) / total, 1.2)
        place = s.get("place") or ""
        conf = s.get("confidence") or []
        tag = "booked" if is_plan else ("not logged" if c == "UNLOGGED" else ("attested" if "attested" in conf else "inferred" if "inferred" in conf else ""))
        tip = f"{cn(c)}{(' · ' + place) if place else ''} · {E.fmt_date(a)} – {E.fmt_date(b)} · {n}d{(' · ' + tag) if tag else ''}"
        if c == "UNLOGGED":
            bar = f"<span class='bar gap' style='left:{left:.2f}%;width:{width:.2f}%'></span>"
        else:
            bar = f"<span class='bar{' plan' if is_plan else ''}' style='left:{left:.2f}%;width:{width:.2f}%;background:{colours(c)};--c:{colours(c)}'></span>"
        sw = f"<i class='sw' style='background:{AMBER if c == 'UNLOGGED' else colours(c)}'></i>"
        rows.append(f"<div class='trow{' gaprow' if c == 'UNLOGGED' else ''}' data-tip='{esc(tip)}'><div class='thead'><div><b>{sw}{esc(cn(c))}</b>"
                    f"<small>{fmt(a)} to {fmt(b)} · {n}d{(' · ' + esc(place)) if place else ''}</small></div>{f'<em>{esc(tag)}</em>' if tag else ''}</div>"
                    f"<div class='track'>{grid}{bar}{today_mark}</div></div>")
    rows.reverse()  # newest first, like the app's latest-trip focus
    if max_rows and len(rows) > max_rows:
        rows = rows[:max_rows]
    axis = (f"<div class='taxis'><span>{E.fmt_date(start)}</span><span>{E.fmt_date(end)}</span></div>")
    return f"<div class='tl'><div class='tyear'>Year {E.tax_year_of(start)}</div>{axis}<div class='trows'>{''.join(rows)}</div></div>"


# ------------------------------------------------------------------ Schengen / rolling area with proximity bands
def area(series, line, colour, width=900, height=280, label_line="90", planned_from=None, today=None, fmt="{v} days", ymax=None,
         x_end=None, aria="Rolling count", bands=False, static=False):
    """series: [(iso_date, value)]. bands=True shades the chart and colours the line by room to `line`
    (>20 calm, 6-20 amber, 0-5 deep ochre). Booked-trip days are hatched neutral grey with a dashed line.
    static=True (PDF): the line is drawn as solid per-segment strokes in the band colour instead of a gradient stroke."""
    if not series:
        return ""
    d0 = E.parse_date(series[0][0])
    dN = E.parse_date(x_end) if x_end else E.parse_date(series[-1][0])
    span = max((dN - d0).days, 1)
    left, right, top, bottom = 40, 16, 16, 30
    mx = ymax or max(line * 1.08, max(v for _, v in series) * 1.1, 10)
    px = lambda d: left + (width - left - right) * (E.parse_date(d) - d0).days / span
    py = lambda v: top + (height - top - bottom) * (1 - min(v, mx) / mx)
    uid = f"a{abs(hash((series[0][0], series[-1][0], line, len(series)))) % 10**6}"
    out = [f"<svg viewBox='0 0 {width} {height}' width='100%' class='chart hov' role='img' aria-label='{esc(aria)}' "
           f"data-x0='{left}' data-x1='{px(series[-1][0]):.1f}' data-w='{width}' data-fmt='{esc(fmt)}' "
           f"data-l='{esc(json.dumps([E.fmt_date(d) for d, _ in series]))}' data-v='{json.dumps([v for _, v in series])}'>",
           f"<defs><pattern id='{uid}h' width='8' height='8' patternUnits='userSpaceOnUse' patternTransform='rotate(45)'>"
           f"<rect width='8' height='8' fill='#F4EEE5'/><line x1='0' y1='0' x2='0' y2='8' stroke='#D4CFC7' stroke-width='3'/></pattern>"]
    yw, yd = py(line - 20), py(line - 5)
    if bands:
        out.append(f"<linearGradient id='{uid}g' gradientUnits='userSpaceOnUse' x1='0' y1='{py(0):.1f}' x2='0' y2='{py(line):.1f}'>"
                   f"<stop offset='0' stop-color='{PRIMARY}'/><stop offset='{(line - 21) / line:.3f}' stop-color='{PRIMARY}'/>"
                   f"<stop offset='{(line - 19) / line:.3f}' stop-color='{AMBER}'/><stop offset='{(line - 6) / line:.3f}' stop-color='{AMBER}'/>"
                   f"<stop offset='{(line - 4) / line:.3f}' stop-color='{OCHRE}'/><stop offset='1' stop-color='{OCHRE}'/></linearGradient>")
    out.append("</defs>")
    if bands:
        out.append(f"<rect x='{left}' y='{py(mx):.1f}' width='{width - left - right}' height='{yd - py(mx):.1f}' fill='{OCHRE}' opacity='.10'/>"
                   f"<rect x='{left}' y='{yd:.1f}' width='{width - left - right}' height='{yw - yd:.1f}' fill='{AMBER}' opacity='.12'/>"
                   f"<rect x='{left}' y='{yw:.1f}' width='{width - left - right}' height='{py(0) - yw:.1f}' fill='{PRIMARY}' opacity='.05'/>"
                   f"<text x='{left + 8}' y='{(yw + py(0)) / 2 + 4:.1f}' class='ax bandlab' style='fill:{PRIMARY}'>comfortable room (more than 20 left)</text>"
                   f"<text x='{left + 8}' y='{(yd + yw) / 2 + 4:.1f}' class='ax bandlab' style='fill:#8A5A00'>getting close (6-20 left)</text>"
                   f"<text x='{left + 8}' y='{py(line) - 5:.1f}' class='ax bandlab' style='fill:{OCHRE}'>at the line (0-5 left)</text>")
    step = 30 if mx <= 130 else 50
    g = 0
    while g <= mx:
        out.append(f"<line x1='{left}' x2='{width - right}' y1='{py(g):.1f}' y2='{py(g):.1f}' stroke='{GRID}'/>"
                   f"<text x='{left - 8}' y='{py(g) + 4:.1f}' text-anchor='end' class='ax'>{g}</text>")
        g += step
    split = len(series)
    if planned_from:
        split = next((i for i, (d, _) in enumerate(series) if d >= planned_from), len(series))
        xp = px(series[min(split, len(series) - 1)][0])
        out.append(f"<rect x='{xp:.1f}' y='{top}' width='{px(series[-1][0]) - xp:.1f}' height='{py(0) - top:.1f}' fill='url(#{uid}h)' opacity='.8'/>"
                   f"<text x='{width - right - 4:.1f}' y='{py(mx * 0.45):.1f}' text-anchor='end' class='ax b'>booked</text>")
    stroke = f"url(#{uid}g)" if bands else colour
    def path(pts):
        return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    pts = [(px(d), py(v)) for d, v in series]
    actual, plan = pts[:max(split, 1)], pts[max(split - 1, 0):]
    base = py(0)
    out.append(f"<path d='{path(pts)} L{pts[-1][0]:.1f} {base:.1f} L{pts[0][0]:.1f} {base:.1f} Z' fill='{stroke}' opacity='.20'/>")
    if static and bands:
        vals = [v for _, v in series]
        for i in range(len(pts) - 1):
            colr = band(line - max(vals[i], vals[i + 1]))[1]
            dash = " opacity='.5'" if planned_from and i >= split - 1 else ""
            out.append(f"<line x1='{pts[i][0]:.1f}' y1='{pts[i][1]:.1f}' x2='{pts[i + 1][0]:.1f}' y2='{pts[i + 1][1]:.1f}' stroke='{colr}' stroke-width='3' stroke-linecap='round'{dash}/>")
    else:
        out.append(f"<path d='{path(actual)}' fill='none' stroke='{stroke}' stroke-width='3' stroke-linejoin='round' stroke-linecap='round'/>")
        if planned_from and len(plan) > 1:
            out.append(f"<path d='{path(plan)}' fill='none' stroke='{stroke}' stroke-width='3' stroke-dasharray='6 5' stroke-linecap='round'/>")
    out.append(f"<line x1='{left}' x2='{width - right}' y1='{py(line):.1f}' y2='{py(line):.1f}' stroke='{INK}' stroke-width='1.5' stroke-dasharray='6 5'/>"
               f"<rect x='{width - right - 22 - 8 * len(label_line)}' y='{py(line) - 9:.1f}' width='{16 + 8 * len(label_line)}' height='18' rx='9' fill='{INK}'/>"
               f"<text x='{width - right - 14 - 4 * len(label_line)}' y='{py(line) + 4:.1f}' text-anchor='middle' class='pilltxt'>{esc(label_line)}</text>")
    d = date(d0.year, d0.month, 1)
    k = 0
    every = 1 if (dN - d0).days <= 400 else 2
    while d <= dN:
        if d >= d0 and k % every == 0 and px(d.isoformat()) < width - right - 12:
            out.append(f"<text x='{px(d.isoformat()):.1f}' y='{height - 10}' text-anchor='middle' class='ax'>{E.MONTHS[d.month - 1]}{(' ' + str(d.year)[2:]) if d.month == 1 else ''}</text>")
        k += 1
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    if today:
        xt = px(today)
        tv = dict(series).get(today, series[-1][1])
        dot = band(line - tv)[1] if bands else colour
        out.append(f"<line x1='{xt:.1f}' x2='{xt:.1f}' y1='{top}' y2='{base:.1f}' stroke='{INK_2}' stroke-width='1'/>"
                   f"<text x='{xt:.1f}' y='{top - 3}' text-anchor='middle' class='ax b'>today</text>"
                   f"<circle cx='{xt:.1f}' cy='{py(tv):.1f}' r='6' fill='#fff' stroke='{dot}' stroke-width='3.5'/>")
    else:
        lv = series[-1][1]
        out.append(f"<circle cx='{pts[-1][0]:.1f}' cy='{pts[-1][1]:.1f}' r='5' fill='#fff' stroke='{band(line - lv)[1] if bands else colour}' stroke-width='3'/>")
    out.append(f"<line class='guide' x1='0' x2='0' y1='{top}' y2='{base:.1f}' stroke='{INK}' stroke-width='1' opacity='0'/><circle class='gdot' r='0'/>")
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ RDR3 number line
def figure_line(days, figures, line=None, width=640, height=104, colour=CORAL):
    mx = 200
    left, right = 18, 18
    px = lambda v: left + (width - left - right) * min(v, mx) / mx
    y = 50
    out = [f"<svg viewBox='0 0 {width} {height}' width='100%' class='chart' role='img' aria-label='UK days against RDR3 figures'>",
           f"<rect x='{left}' y='{y - 7}' width='{width - left - right}' height='14' rx='7' fill='{PILL_TRACK}'/>",
           f"<rect x='{left}' y='{y - 7}' width='{max(px(days) - left, 0):.1f}' height='14' rx='7' fill='{colour}'/>"]
    merged = False
    for f in figures:
        x = px(f["figure"])
        mine = line is not None and f["figure"] == line + 1
        merged = merged or mine
        tip = f"{f['figure']} days · {E.cite(f['ref'])}" + (f" · your line is {line} days" if mine else "")
        out.append(f"<g data-tip='{esc(tip)}'><line x1='{x:.1f}' x2='{x:.1f}' y1='{y - (22 if mine else 14)}' y2='{y + 14}' stroke='{INK if mine else INK_2}' stroke-width='{3 if mine else 2}'/>"
                   f"<text x='{x:.1f}' y='{y + 32}' text-anchor='middle' class='ax b'>{f['figure']}</text>"
                   f"<text x='{x:.1f}' y='{y + 47}' text-anchor='middle' class='ax sm'>{esc(f['ref'])}</text>"
                   + (f"<rect x='{x - 34:.1f}' y='{y - 42}' width='68' height='18' rx='9' fill='{INK}'/><text x='{x:.1f}' y='{y - 29}' text-anchor='middle' class='pilltxt'>your line</text>" if mine else "")
                   + f"<rect x='{x - 16:.1f}' y='{y - 16}' width='32' height='66' fill='transparent'/></g>")
    if line is not None and not merged:
        x = px(line)
        out.append(f"<line x1='{x:.1f}' x2='{x:.1f}' y1='{y - 22}' y2='{y + 10}' stroke='{INK}' stroke-width='2' stroke-dasharray='4 3'/>"
                   f"<rect x='{x - 40:.1f}' y='{y - 42}' width='80' height='18' rx='9' fill='{INK}'/><text x='{x:.1f}' y='{y - 29}' text-anchor='middle' class='pilltxt'>your line {line}</text>")
    xd = px(days)
    out.append(f"<circle cx='{xd:.1f}' cy='{y}' r='13' fill='{colour}' stroke='#fff' stroke-width='3'/>"
               f"<text x='{xd:.1f}' y='{y + 4}' text-anchor='middle' class='pilltxt'>{days if days < 100 else ''}</text></svg>")
    return "".join(out)


# ------------------------------------------------------------------ work days per month (same track style as the monthly chart)
def columns(months, colour=VIOLET, unsure=None, cap=None):
    mx = cap or max([v + (unsure[i] if unsure else 0) for i, (_, v) in enumerate(months)] + [5])
    cols = []
    for i, (lab, v) in enumerate(months):
        u = unsure[i] if unsure else 0
        segs = (f"<span style='flex:{u};background:{GAP_FILL};box-shadow:inset 0 0 0 2px {AMBER}' data-tip='{esc(lab)}: {u} marked unsure'></span>" if u else "") + \
               (f"<span style='flex:{v};background:{colour}' data-tip='{esc(lab)}: {v} work day{'s' if v != 1 else ''}'></span>" if v else "")
        cols.append(f"<div class='mcol'><b>{(str(v) if v else '') + (f'+{u}?' if u else '')}</b><div class='mtrack'><div class='mfill' style='height:{100 * (v + u) / mx:.1f}%'>{segs}</div></div>"
                    f"<small>{esc(lab.split(' ')[0])}</small></div>")
    return f"<div class='mbars'>{''.join(cols)}</div>"


# ------------------------------------------------------------------ calendar (one cell per day)
def calendar(log, start, end, colours, cell=13, gap=3, today=None):
    first = start - timedelta(days=start.weekday())
    weeks = ((end - first).days // 7) + 1
    left, top = 30, 20
    width = left + weeks * (cell + gap)
    height = top + 7 * (cell + gap)
    out = [f"<svg viewBox='0 0 {width} {height}' width='100%' class='chart cal' style='min-width:{min(width, 760)}px' role='img' aria-label='Every day of the tax year, coloured by country at midnight'>"]
    for i, lab in ((0, "Mon"), (2, "Wed"), (4, "Fri")):
        out.append(f"<text x='0' y='{top + i * (cell + gap) + cell - 2}' class='ax sm'>{lab}</text>")
    seen = set()
    for dd in E.daterange(start, end):
        wk = (dd - first).days // 7
        x = left + wk * (cell + gap)
        y = top + dd.weekday() * (cell + gap)
        if (dd.year, dd.month) not in seen and dd.day <= 7 and x <= width - 24:
            seen.add((dd.year, dd.month))
            out.append(f"<text x='{x}' y='12' class='ax sm'>{E.MONTHS[dd.month - 1]}</text>")
        if today and dd > today:
            out.append(f"<rect x='{x}' y='{y}' width='{cell}' height='{cell}' rx='3' fill='none' stroke='{BORDER}'/>")
            continue
        r = log.row(dd)
        if r:
            c = r["midnight_country"]
            w = (r.get("uk_work") or {}).get("over_3h")
            tip = f"{dd.strftime('%a')} {E.fmt_date(dd)} · {cn(c)}{(' · ' + r['midnight_place']) if r.get('midnight_place') else ''}{' · UK work' if w == 'yes' else ''}{' · ' + r.get('confidence') if r.get('confidence') not in (None, 'confirmed') else ''}"
            out.append(f"<rect x='{x}' y='{y}' width='{cell}' height='{cell}' rx='3' fill='{colours(c)}' data-tip='{esc(tip)}'/>")
            if w == "yes":
                out.append(f"<circle cx='{x + cell / 2}' cy='{y + cell / 2}' r='2.4' fill='#fff' pointer-events='none'/>")
        else:
            out.append(f"<rect x='{x + 1}' y='{y + 1}' width='{cell - 2}' height='{cell - 2}' rx='3' fill='{GAP_FILL}' stroke='{AMBER}' stroke-width='1.5' data-tip='{esc(dd.strftime('%a') + ' ' + E.fmt_date(dd) + ' · not logged')}'/>")
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ Reference card: gauge, day strip, status block
STRIP_OTHER = "#C8C0B4"   # a logged day outside the UK: neutral, so UK days and gaps carry the eye
STRIP_TRACK = "#F1ECE4"   # days still to come


def gauge(days, figure, marks=(), width=660, height=58, colour=None, aria=""):
    """Progress bar: `days` UK midnights against `figure`, the nearest HMRC figure ahead.

    `marks` are other figures inside the scale, drawn as a tick and their number. No sentences: the labels
    around the bar live in the HTML, so the same bar serves the dashboard and the print export."""
    left = right = 8
    y, h = 12, 20
    scale = max(figure, days, 1)
    colour = colour or band(figure - 1 - days)[1]
    px = lambda v: left + (width - left - right) * min(v, scale) / scale
    out = [f"<svg viewBox='0 0 {width} {height}' width='100%' class='chart' role='img' "
           f"aria-label='{esc(aria or f'{days} UK midnights against the {figure}-day figure')}'>",
           f"<rect x='{left}' y='{y}' width='{width - left - right}' height='{h}' rx='{h / 2}' fill='{PILL_TRACK}'/>"]
    if px(days) > left:
        out.append(f"<rect x='{left}' y='{y}' width='{px(days) - left:.1f}' height='{h}' rx='{h / 2}' fill='{colour}'/>")
    for m, tip in marks:
        if not 0 < m < scale:
            continue
        out.append(f"<g data-tip='{esc(f'{m} days · {tip}')}'><line x1='{px(m):.1f}' x2='{px(m):.1f}' y1='{y - 4}' y2='{y + h + 4}' stroke='{INK_2}' stroke-width='2'/>"
                   f"<text x='{px(m):.1f}' y='{height - 3}' text-anchor='middle' class='ax b'>{m}</text></g>")
    out.append(f"<line x1='{px(figure):.1f}' x2='{px(figure):.1f}' y1='{y - 7}' y2='{y + h + 7}' stroke='{INK}' stroke-width='3'/>"
               f"<text x='{px(figure):.1f}' y='{height - 3}' text-anchor='end' class='ax b'>{figure}</text>"
               f"<circle cx='{px(days):.1f}' cy='{y + h / 2}' r='{h / 2 - 1}' fill='#fff' stroke='{colour}' stroke-width='4'/></svg>")
    return "".join(out)


def day_strip(log, start, end, today=None, width=660, height=24):
    """One thin cell per day of the tax year: UK midnight, logged elsewhere, not logged, or still to come."""
    n = (end - start).days + 1
    cw = (width - 2) / n
    y, h = 2, 16
    runs: list[list] = []
    for i, d in enumerate(E.daterange(start, end)):
        r = None if (today and d > today) else log.row(d)
        kind = "future" if (today and d > today) else ("gap" if not r else ("uk" if r["midnight_country"] == E.UK else "other"))
        if runs and runs[-1][0] == kind:
            runs[-1][2] = i
        else:
            runs.append([kind, i, i])
    fill = {"uk": CORAL, "other": STRIP_OTHER, "gap": AMBER}
    logged = sum(b - a + 1 for k, a, b in runs if k in ("uk", "other"))
    out = [f"<svg viewBox='0 0 {width} {height}' width='100%' class='chart' role='img' "
           f"aria-label='Every day from {esc(E.fmt_date(start))} to {esc(E.fmt_date(end))}: {logged} logged'>",
           f"<rect x='1' y='{y}' width='{width - 2}' height='{h}' rx='3' fill='{STRIP_TRACK}'/>"]
    for kind, a, b in runs:
        if kind == "future":
            continue
        out.append(f"<rect x='{1 + a * cw:.2f}' y='{y}' width='{max((b - a + 1) * cw, 0.8):.2f}' height='{h}' fill='{fill[kind]}'/>")
    d = date(start.year, start.month, 1)
    while d <= end:
        if d > start:
            x = 1 + (d - start).days * cw
            out.append(f"<line x1='{x:.2f}' x2='{x:.2f}' y1='{y}' y2='{y + h}' stroke='#fff' stroke-width='1' opacity='.65'/>")
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    if today and start <= today <= end:
        x = 1 + ((today - start).days + 1) * cw
        out.append(f"<line x1='{x:.2f}' x2='{x:.2f}' y1='{y - 2}' y2='{y + h + 2}' stroke='{INK}' stroke-width='2'/>")
    out.append("</svg>")
    return "".join(out)


def _sw(colour, outline=False):
    return (f"<i style='display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px;"
            f"background:{colour}{f';box-shadow:inset 0 0 0 1px {INK_2}' if outline else ''}'></i>")


def status_block(ref, log, *, svg=None, icon_fn=None, disc="disc", detail_wrap=None, detail_extra="", strip_width=660):
    """The Reference block: one visual read of the year, a short checklist, then the figure detail.

    The same markup serves the dashboard and the print export: `svg` adapts a dashboard SVG for print,
    `icon_fn(name, colour, size)` draws an icon, `disc` is the caller's small-print class and
    `detail_wrap(html)` wraps the detail (a <details> in the dashboard, a footnote in the export)."""
    svg = svg or (lambda x: x)
    icon_fn = icon_fn or (lambda name, colour, size: icon(name, size))
    s, tt, ty = ref["summary"], ref["ties_test"], ref["tax_year"]
    start, end = E.tax_year_bounds(ty)
    to = E.parse_date(s["counted_to"])
    days = s["uk_midnights"]
    figs = ref["applicable_figures"]
    uk_figs = [f for f in figs if f["unit"] == "UK days"]
    target = next((f for f in figs if f["next"]), None) or (uk_figs[-1] if uk_figs else None)
    room = target["room"] if target else None
    key, colr, _ = band(room)
    colr = CORAL if key == "calm" else colr   # UK days are coral until a figure is close, as in the KPI cards
    chip = {"calm": "teal", "warn": "attn", "deep": "deep"}[key]
    if room is None:
        left_chip = ""
    elif room < 0:
        left_chip = f"{-room} days past {target['figure']}"
    else:
        left_chip = f"{room} days {'below' if s['complete'] else 'left before'} {target['figure']}"
    of = f"of {target['figure']}" if target else ""
    head = (f"<div class='refhead'><div class='refnum'><b style='color:{colr}'>{days}</b>"
            f"<span><i>{of}</i><br>UK midnights to {esc(E.fmt_date(to))}</span></div>"
            + (f"<span class='chip {chip} big'>{esc(left_chip)}</span>" if left_chip else "") + "</div>")
    bar = svg(gauge(days, target["figure"], [(f["figure"], f["test"]) for f in uk_figs if f is not target], colour=colr)) if target else ""
    legend_key = (f"<div class='key'><span>{_sw(CORAL)}UK midnight</span><span>{_sw(STRIP_OTHER)}Elsewhere</span>"
                  + (f"<span>{_sw(AMBER)}Not logged</span>" if s["unlogged"] else "")
                  + (f"<span>{_sw(STRIP_TRACK, True)}To come</span>" if not s["complete"] else "")
                  + f"<span class='chip'>{s['logged']} of {s['days_in_year_to_date']} days logged</span>"
                  + (f"<span class='chip attn'>{s['unlogged']} to log</span>" if s["unlogged"] else "") + "</div>")
    strip = (f"<div class='refstrip'>{svg(day_strip(log, start, end, today=None if s['complete'] else to, width=strip_width))}"
             f"<div class='taxis'><span>{esc(E.fmt_date(start))}</span><span>{esc(E.fmt_date(end))}</span></div>{legend_key}</div>")
    if ref["stage_lines"]:
        status = "".join(f"<div class='pointer'><b>{esc(l['text'])}</b><div class='{disc}'>{esc(l['disclaimer'])}</div></div>"
                         for l in ref["stage_lines"])
    else:
        status = (f"<div class='refstat'><span class='chip attn'>No result for {esc(ty)} yet</span>"
                  f"<span class='{disc}'>Every box is ticked before a result is given.</span></div>")
    checks = "".join(f"<li class='{'ok' if i['done'] else 'todo'}'>"
                     f"{icon_fn('check-circle' if i['done'] else 'alert-circle', PRIMARY if i['done'] else '#B07A12', 15)}"
                     f"<span>{esc(i['label'])}</span></li>" for i in ref["gate"])
    nd = ref["ninety_day_next_year"]
    table_note = " ".join(x for x in (tt.get("band_text") or "", (tt.get("table_reason") or "") + ".") if x.strip(". "))
    detail = (f"<ul class='small'>" + "".join(f"<li>{esc(f['room_text'])} <span class='muted'>{esc(f['cite'])}</span></li>" for f in figs)
              + f"</ul><p class='small'>{esc(table_note)}</p>"
              + f"<p class='small'>Next year: {esc(nd['text'])}. <span class='muted'>{esc(nd['cite'])}</span></p>"
              + (f"<ul class='small'>" + "".join(f"<li>{esc(n)}</li>" for n in ref["notes"]) + "</ul>" if ref["notes"] else "")
              + detail_extra)
    return (f"<div class='ref'>{head}{bar}{strip}{status}<ul class='check'>{checks}</ul>"
            f"{detail_wrap(detail) if detail_wrap else detail}"
            f"<p class='{disc}'>A count from your entries. It does not determine residence.</p></div>")


# ------------------------------------------------------------------ icons: Feather set (the app uses @expo/vector-icons Feather)
_I = {
    "grid": "<rect x='3' y='3' width='7' height='7'/><rect x='14' y='3' width='7' height='7'/><rect x='14' y='14' width='7' height='7'/><rect x='3' y='14' width='7' height='7'/>",
    "users": "<path d='M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2'/><circle cx='9' cy='7' r='4'/><path d='M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75'/>",
    "home": "<path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/>",
    "briefcase": "<rect x='2' y='7' width='20' height='14' rx='2' ry='2'/><path d='M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16'/>",
    "calendar": "<rect x='3' y='4' width='18' height='18' rx='2' ry='2'/><line x1='16' y1='2' x2='16' y2='6'/><line x1='8' y1='2' x2='8' y2='6'/><line x1='3' y1='10' x2='21' y2='10'/>",
    "flag": "<path d='M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z'/><line x1='4' y1='22' x2='4' y2='15'/>",
    "check-circle": "<path d='M22 11.08V12a10 10 0 1 1-5.93-9.14'/><polyline points='22 4 12 14.01 9 11.01'/>",
    "check": "<polyline points='20 6 9 17 4 12'/>",
    "alert-circle": "<circle cx='12' cy='12' r='10'/><line x1='12' y1='8' x2='12' y2='12'/><line x1='12' y1='16' x2='12.01' y2='16'/>",
    "info": "<circle cx='12' cy='12' r='10'/><line x1='12' y1='16' x2='12' y2='12'/><line x1='12' y1='8' x2='12.01' y2='8'/>",
    "navigation": "<polygon points='3 11 22 2 13 21 11 13 3 11'/>",
    "file-text": "<path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><polyline points='14 2 14 8 20 8'/><line x1='16' y1='13' x2='8' y2='13'/><line x1='16' y1='17' x2='8' y2='17'/>",
    "moon": "<path d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/>",
    "globe": "<circle cx='12' cy='12' r='10'/><line x1='2' y1='12' x2='22' y2='12'/><path d='M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'/>",
    "map-pin": "<path d='M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z'/><circle cx='12' cy='10' r='3'/>",
    "bar-chart-2": "<line x1='18' y1='20' x2='18' y2='10'/><line x1='12' y1='20' x2='12' y2='4'/><line x1='6' y1='20' x2='6' y2='14'/>",
    "chevron-down": "<polyline points='6 9 12 15 18 9'/>",
    "chevron-right": "<polyline points='9 18 15 12 9 6'/>",
    "clock": "<circle cx='12' cy='12' r='10'/><polyline points='12 6 12 12 16 14'/>",
    "book-open": "<path d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/><path d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/>",
}
_ALIAS = {"family": "users", "work": "briefcase", "alert": "alert-circle", "check": "check-circle", "plane": "navigation", "doc": "file-text"}


def icon(name, size=20, cls="ic"):
    name = _ALIAS.get(name, name)
    return (f"<svg class='{cls}' viewBox='0 0 24 24' width='{size}' height='{size}' fill='none' stroke='currentColor' stroke-width='2' "
            f"stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'>{_I[name]}</svg>")
