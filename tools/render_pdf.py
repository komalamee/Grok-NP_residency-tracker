#!/usr/bin/env python3
"""Render the "Travel and day log" export for one tax year: PDF (WeasyPrint) + CSV.

  python3 render_pdf.py DAYLOG.json --tax-year 2025/26 --out-dir OUT/ [--as-of YYYY-MM-DD] [--kb HMRC_MIRROR (default: <engine>/hmrc)] [--html-only]

v3 styling matches the HTML dashboard (see CSS note below).
Produces "Travel and day log YYYY-YY.pdf" (or "... (to D Mon YYYY).pdf" for a year in progress) and the matching CSV.
Without --rules the country rules come from the user's own copy ($NOMAD_PRO_DATA/country-rules.json, else
~/nomad-pro-data/country-rules.json), else the engine's shipped schema/country-rules.json.
Requires: pip install weasyprint
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

import srt_engine as E
from render_common import esc, evidence_html, evidence_text

import base64
import re
from datetime import timedelta

import dashboard_charts as C

ASSETS = Path(__file__).resolve().parent / "assets"
SEP = " \u00b7 "

# v3 (26 Sep 2026): same visual language as the v3 HTML dashboard and the iOS app theme: warm #FAF7F2 page,
# white 12px-radius cards with a 1.5px bottom border, teal #1A9B8C / coral #E8725A / violet work colour, amber only
# for attention, one proximity scale (teal > 20 days of room, amber 6-20, ochre 0-5), the dashboard's country colours,
# Inter (embedded) and Feather icons. A single flowing print document: no tabs, buttons or scripts. Charts are static SVG
# with presentation attributes (WeasyPrint does not apply page CSS inside SVG).
CSS = """
@page{size:A4;margin:16mm 14mm 22mm 14mm;background:#FAF7F2;
 @top-left{content:string(doctitle);font:600 7.5pt 'Inter NP',Helvetica,sans-serif;color:#9E9E9E}
 @top-right{content:"Page " counter(page) " of " counter(pages);font:600 7.5pt 'Inter NP',Helvetica,sans-serif;color:#9E9E9E}
 @bottom-center{content:"Educational information, not tax advice. UK residence can turn on detailed facts and current law. If your position is close to a threshold or commercially significant, use current HMRC guidance and take advice from a qualified professional.";font:6.6pt/1.35 'Inter NP',Helvetica,sans-serif;color:#6B6B6B;width:100%}}
@page:first{@top-left{content:none}@top-right{content:none}}
body{margin:0;font:8.8pt/1.45 'Inter NP',Helvetica,Arial,sans-serif;color:#2D2D2D}
h1{string-set:doctitle content();font-size:23pt;font-weight:800;letter-spacing:-.5pt;margin:1mm 0 1mm;color:#2D2D2D}
h2{font-size:14pt;font-weight:700;letter-spacing:-.3pt;margin:6mm 0 2.5mm;break-after:avoid;color:#2D2D2D}
h2 .n{display:inline-block;background:#1A9B8C;color:#fff;border-radius:3mm;font-size:9pt;font-weight:800;padding:.4mm 2.2mm;margin-right:2mm;vertical-align:2pt}
h2 .sub,h3 .sub{font-size:8.5pt;font-weight:500;color:#6B6B6B;margin-left:2mm}
h3{font-size:11pt;font-weight:700;margin:0 0 2mm;color:#2D2D2D;break-after:avoid}
.top{margin-bottom:4mm}.top img{width:14mm;height:14mm;border-radius:4mm;border:1px solid #E8E2D9}
.k{font-size:7pt;font-weight:800;letter-spacing:.8pt;text-transform:uppercase;color:#1A9B8C}
.meta{font-size:8.5pt;color:#6B6B6B}
.card{background:#fff;border:1px solid #E8E2D9;border-bottom:1.5px solid #E0D8CC;border-radius:3mm;padding:3.5mm 4mm;margin:0 0 3.5mm;break-inside:avoid}
.card.flow{break-inside:auto}
.card.teal{background:#F0FBF8;border-color:#C9ECE7}.card.amber{background:#FFF7E8;border-color:#F4DFB4}
table.lay{border-collapse:separate;border-spacing:3.5mm 0;table-layout:fixed;width:189mm;margin:0 -3.5mm 3.5mm}
td.card{vertical-align:top;margin:0}
table.split{width:100%;border-collapse:collapse;table-layout:fixed}td.sp{border:0;padding:0;vertical-align:middle}
table.tiles{width:100%;border-collapse:separate;border-spacing:2mm 0;table-layout:fixed}
.kpi{padding:3mm 3.5mm 3.5mm}

.kpi .lab{font-size:7.5pt;font-weight:700;color:#9E9E9E}
.kpi .val{font-weight:700;letter-spacing:-.5pt;margin-top:1mm;line-height:1.1}.kpi .val small{font-size:10.5pt}

.kpi .det{font-size:7.4pt;line-height:1.4;color:#6B6B6B;margin-top:2mm;overflow-wrap:anywhere}
.kpi .dot{width:11mm;height:11mm;border-radius:6mm;text-align:center;padding-top:2.6mm;box-sizing:border-box;margin-left:auto}.kpi .dot svg,.tie .ico svg{margin:0 auto}
table{width:100%;border-collapse:collapse;font-size:8pt}
th{background:#F4EEE5;color:#9E9E9E;text-align:left;font-weight:700;font-size:6.9pt;text-transform:uppercase;letter-spacing:.2pt;padding:1.6mm 1.6mm}
td{padding:1.4mm 2mm;border-bottom:1px solid #EFEAE3;vertical-align:top;overflow-wrap:anywhere}
table.fx{table-layout:fixed}td a{overflow-wrap:anywhere}tr{break-inside:avoid}
thead{display:table-header-group}
table.days td,table.days th{font-size:7pt;padding:.8mm 1.6mm}table.days td:first-child{white-space:nowrap;overflow-wrap:normal}
tr.gap td{background:#FFF7E8}td.n{text-align:right;font-weight:700}
.legend td{border:0;padding:.6mm 1mm;font-size:7.8pt}.legend td.v{white-space:nowrap;text-align:right;font-weight:700;color:#6B6B6B}
.sw{display:inline-block;width:2.6mm;height:2.6mm;border-radius:1.3mm;margin-right:1.6mm;vertical-align:-.2mm}
.ptr{color:#6B6B6B}.muted{color:#9E9E9E}.small{font-size:7.8pt}
.chip{display:inline-block;white-space:nowrap;border:1px solid #E8E2D9;border-radius:3mm;padding:.2mm 2.2mm;font-size:7.3pt;font-weight:700;background:#F4EEE5;color:#6B6B6B}
.quote{border-left:1.2mm solid #7A6FD0;background:#F5F3FD;padding:2.4mm 3.2mm;margin:1mm 0 2.5mm;font-size:9pt;line-height:1.45;overflow-wrap:anywhere}
table.kv th{text-transform:none;letter-spacing:0;font-size:8pt;vertical-align:top}
.chip.attn{border-color:#F3DDAF;background:#FFF7E8;color:#8A5A00}.chip.teal{border-color:#C7E7E0;background:#F0FBF8;color:#1A9B8C}.chip.deep{border-color:#EBC48F;background:#FBEBD5;color:#A8620A}
.pointer{background:#F0FBF8;border:1px solid #C9ECE7;border-radius:3mm;padding:2.5mm 3.5mm;margin:2mm 0}.pointer .d{font-size:7.5pt;color:#6B6B6B;margin-top:.8mm}
.legal{background:#fff;border:1px solid #E8E2D9;border-left:3px solid #1A9B8C;padding:3mm 4mm;border-radius:2mm;font-size:8.4pt;font-weight:600}
.quick .big{font-size:30pt;font-weight:800;letter-spacing:-1pt;line-height:1}.quick .big small{font-size:9.5pt;font-weight:700;color:#2D2D2D;letter-spacing:0}
.quick .room{font-size:12pt;font-weight:800;margin:1.5mm 0}.quick .drop{font-size:8.3pt;color:#6B6B6B;margin-top:1.5mm}
.bandkey div{font-size:7.4pt;color:#6B6B6B;margin-top:.8mm}.bandkey i{display:inline-block;width:5mm;height:2.4mm;border-radius:1mm;margin-right:1.5mm;vertical-align:-.2mm}
td.tie{vertical-align:top;text-align:center;border:1px solid #E8E2D9;border-bottom-width:1.5px;border-radius:3mm;background:#fff;padding:3mm 1.5mm}
.tie .ico{width:10mm;height:10mm;border-radius:5mm;margin:0 auto 1.5mm;background:#F4EEE5;padding-top:2.3mm;box-sizing:border-box}
.tie .nm{font-weight:700;font-size:8.6pt;overflow-wrap:anywhere}.tie .st{font-size:6.8pt;font-weight:800;text-transform:uppercase;letter-spacing:.5pt;color:#9E9E9E;margin-top:.6mm}.tie .rf{font-size:6.6pt;color:#9E9E9E;margin-top:.8mm}
.tie.on{background:#F0FBF8;border-color:#C9ECE7}.tie.on .ico{background:#1A9B8C}.tie.on .st{color:#1A9B8C}
.tie.na{border-style:dashed}.tie.rev{background:#FFF7E8;border-color:#F4DFB4}.tie.rev .ico{background:#E5A535}.tie.rev .st{color:#8A5A00}
.key span{font-size:7.4pt;color:#6B6B6B;margin-right:3mm;white-space:nowrap}
.toc{margin:0;padding-left:5mm;columns:2;font-size:8.3pt}.toc li{margin:.4mm 0}
.pb{break-before:page}svg{display:block}
a{color:#1A9B8C;text-decoration:underline}
ul{margin:1mm 0;padding-left:5mm}
"""


def _font_face() -> str:
    f = ASSETS / "Inter-latin-var.woff2"
    if not f.exists():
        return ""
    return ("@font-face{font-family:'Inter NP';font-weight:100 900;"
            f"src:url(data:font/woff2;base64,{base64.b64encode(f.read_bytes()).decode()}) format('woff2')}}")


def _logo() -> str:
    f = ASSETS / "nomadpro-logo-96.png"
    return f"<img src='data:image/png;base64,{base64.b64encode(f.read_bytes()).decode()}' alt='Nomad Pro'>" if f.exists() else ""


_SVG_CLASSES = [
    ("class='ax bandlab'", "font-size='11' font-weight='700'"),
    ("class='ax b'", f"font-size='11' font-weight='700' fill='{C.INK}'"),
    ("class='ax sm'", f"font-size='9' font-weight='600' fill='{C.MUTED}'"),
    ("class='ax'", f"font-size='11' font-weight='600' fill='{C.MUTED}'"),
    ("class='pilltxt'", "font-size='10' font-weight='800' fill='#fff'"),
    ("class='rb'", f"font-weight='700' fill='{C.INK}'"),
    ("class='rs'", f"font-weight='600' fill='{C.INK_2}'"),
]


def static_svg(svg: str, width_mm: float | None = None) -> str:
    """Dashboard SVG -> print SVG: CSS classes become presentation attributes, interactive attributes are dropped."""
    for a, b in _SVG_CLASSES:
        svg = svg.replace(a, b)
    svg = re.sub(r" data-(tip|x0|x1|w|fmt|l|v)='[^']*'", "", svg)
    svg = svg.replace("<svg ", "<svg font-family=\"'Inter NP', Helvetica, sans-serif\" ", 1)
    if width_mm:
        head, rest = svg.split(">", 1)
        head = re.sub(r" (width|height)='[^']*'", "", head) + f" style='width:{width_mm}mm;height:auto'"
        svg = head + ">" + rest
    return svg


def icon(name, colour, size=18):
    return C.icon(name, size).replace("currentColor", colour)


def fit(text, sizes=((7, 18), (9, 15), (13, 12.5), (99, 11))):
    """Auto-fit: font size in pt from the character count, so values never spill out of their card."""
    n = len(str(text))
    return next(sz for lim, sz in sizes if n <= lim)


def kpi(label, num, unit, det, visual, colour, word=False):
    u = f"<small style='font-size:.6em'> {esc(unit)}</small>" if unit else ""
    size = fit(f"{num}{(' ' + unit) if unit else ''}", ((6, 18), (8, 15.5), (11, 13), (16, 12), (99, 10.5))) if not word else fit(num, ((9, 13), (16, 12), (99, 10.5)))
    return (f"<td class='card kpi'><table class='split'><tr><td class='sp' style='vertical-align:top'><div class='lab'>{esc(label)}</div>"
            f"<div class='val' style='color:{colour};font-size:{size}pt'>{esc(num)}{u}</div></td><td class='sp' style='width:14mm;vertical-align:top;text-align:right'>{visual}</td></tr></table>"
            f"<div class='det'>{det}</div></td>")


def lay(*cells, widths=None):
    """A row of cards as a fixed table (WeasyPrint's flex layout mis-sizes card heights). cells: '<td ...>' strings."""
    cols = "".join(f"<col style='width:{w}%'>" for w in widths) if widths else ""
    # WeasyPrint adds border-spacing outside the table width: 182mm body + 2 x 3.5mm bleed, minus the spacings.
    return f"<table class='lay' style='width:{189 - (len(cells) + 1) * 3.5:.1f}mm'>{cols}<tr>{''.join(cells)}</tr></table>"


def split(*parts, widths):
    return "<table class='split'><tr>" + "".join(f"<td class='sp' style='width:{w}%'><div style='{'margin-right:3mm' if i < len(parts) - 1 else ''}'>{p}</div></td>" for i, (p, w) in enumerate(zip(parts, widths))) + "</tr></table>"


def evidence_cell(row, prefix="", maxn=3):
    """PDF evidence cell: short link text (never a raw path), long labels trimmed, links wrap anywhere."""
    from render_common import evidence_entries
    ents = evidence_entries(row)
    parts = []
    for x in ents[:maxn]:
        lab = x["label"] or ""
        if x["href"]:
            href = x["href"] if x["kind"] == "link" else prefix + x["href"]
            if "/" in lab or lab == x["href"] or lab.startswith("http"):
                lab = ("File: " + x["href"].split("/")[-1]) if x["kind"] == "file" else ("Email" if "mail.google" in x["href"] else "Link")
            short = lab if len(lab) <= 64 else lab[:60].rsplit(" ", 1)[0] + " …"
            parts.append(f"<a href='{esc(href)}'>{esc(short)}</a>")
        else:
            parts.append(esc(lab if len(lab) <= 110 else lab[:106].rsplit(" ", 1)[0] + " …"))
    if len(ents) > maxn:
        parts.append(f"+{len(ents) - maxn} more")
    return "; ".join(parts)


def dot(name, colour, tint):
    return f"<div class='dot' style='background:{tint}'>{icon(name, colour, 20)}</div>"


def bars_svg(months, cap=31, width=400, height=190, total_label=True):
    """months: [(label, [(value, colour, is_gap)])]. The app's MonthlyStackedChart: rounded #EDE7DE tracks, total above."""
    n = max(len(months), 1)
    slot = (width - 10) / n
    bw = min(26, slot * 0.62)
    top, base = 22, height - 20
    out = [f"<svg viewBox='0 0 {width} {height}' width='100%' role='img' aria-label='Days by month'>"]
    for i, (lab, segs) in enumerate(months):
        x = 5 + slot * i + (slot - bw) / 2
        out.append(f"<rect x='{x:.1f}' y='{top}' width='{bw:.1f}' height='{base - top}' rx='5' fill='{C.BAR_TRACK}'/>")
        y = base
        tot = 0
        for v, colr, gap in segs:
            if not v:
                continue
            h = (base - top) * v / cap
            y -= h
            tot += v
            extra = f" stroke='{C.AMBER}' stroke-width='1.5'" if gap else ""
            out.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bw:.1f}' height='{h:.1f}' fill='{colr}'{extra}/>")
        if tot and total_label:
            out.append(f"<text x='{x + bw / 2:.1f}' y='{top - 7}' text-anchor='middle' font-size='10' font-weight='700' fill='{C.MUTED}'>{tot}</text>")
        out.append(f"<text x='{x + bw / 2:.1f}' y='{height - 5}' text-anchor='middle' font-size='10' font-weight='700' fill='{C.INK_2}'>{esc(lab)}</text>")
    out.append("</svg>")
    return static_svg("".join(out))


def stay_row_svg(st, start, end, col, today=None, planned=False, width=700):
    """One timeline row: full country name + dates on the left, the app's pill track with the coloured bar on the right."""
    total = (end - start).days + 1
    a, b = E.parse_date(st["from"]), E.parse_date(st["to"])
    a2, b2 = max(a, start), min(b, end)
    n = (b - a).days + 1
    c = st["country"]
    tx0, tx1, ty, th = 300, width - 4, 9, 12
    px = lambda d: tx0 + (tx1 - tx0) * (d - start).days / total
    name = C.cn(c)
    colr = C.AMBER if c == "UNLOGGED" else col(c)
    conf = st.get("confidence") or []
    tag = "booked" if planned else ("not logged" if c == "UNLOGGED" else ("owner statement" if "attested" in conf else "inferred" if "inferred" in conf else ""))
    place = st.get("place") or ""
    if len(place) > 44:
        place = place[:42].rsplit(" ", 1)[0].rstrip(",;") + " …"
    sub = f"{a.day} {E.MONTHS[a.month - 1]} to {b.day} {E.MONTHS[b.month - 1]} {b.year}{SEP}{n}d" + (f"{SEP}{tag}" if tag else "")
    out = [f"<svg viewBox='0 0 {width} 34' width='100%' role='img' aria-label='{esc(name)} {esc(sub)}'>",
           f"<circle cx='5' cy='10' r='4.5' fill='{colr}'/>",
           f"<text x='15' y='14' font-size='12.5' font-weight='700' fill='{'#8A5A00' if c == 'UNLOGGED' else C.INK}'>{esc(name)}</text>",
           f"<text x='15' y='29' font-size='9.5' font-weight='500' fill='{C.INK_2}'>{esc(sub)}</text>",
           f"<rect x='{tx0}' y='{ty}' width='{tx1 - tx0}' height='{th}' rx='6' fill='{C.PILL_TRACK}'/>"]
    d = date(start.year, start.month, 1)
    while d <= end:
        if d > start:
            out.append(f"<line x1='{px(d):.1f}' x2='{px(d):.1f}' y1='{ty}' y2='{ty + th}' stroke='#000' stroke-opacity='.08'/>")
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    if a2 <= b2:
        x, w = px(a2), max(px(b2 + timedelta(days=1)) - px(a2), 4)
        if c == "UNLOGGED":
            out.append(f"<rect x='{x:.1f}' y='{ty}' width='{w:.1f}' height='{th}' rx='6' fill='{C.GAP_FILL}' stroke='{C.AMBER}' stroke-width='1.5' stroke-dasharray='3 2'/>")
        else:
            out.append(f"<rect x='{x:.1f}' y='{ty}' width='{w:.1f}' height='{th}' rx='6' fill='{colr}'{' fill-opacity=\'.45\' stroke=\'' + colr + '\' stroke-dasharray=\'3 2\'' if planned else ''}/>")
    if today and start <= today <= end:
        out.append(f"<line x1='{px(today):.1f}' x2='{px(today):.1f}' y1='{ty - 3}' y2='{ty + th + 3}' stroke='{C.INK}' stroke-width='2'/>")
    if place:
        out.append(f"<text x='{tx1}' y='31' text-anchor='end' font-size='8.5' fill='{C.MUTED}'>{esc(place)}</text>")
    out.append("</svg>")
    return static_svg("".join(out))


def quick_read(used, room, drop, window_end):
    key, colr, label = C.band(room)
    chip = {"calm": "teal", "warn": "attn", "deep": "deep"}[key]
    room_txt = f"{room} days of room" if room >= 0 else f"{-room} days over 90"
    return (f"<div class='quick'><div class='k' style='color:#6B6B6B'>Current status</div><div class='big' style='color:{colr}'>{used} <small>days in the last 180</small></div>"
            f"<div class='room' style='color:{colr}'>{room_txt}</div><span class='chip {chip}'>{esc(label)}</span>"
            f"<div class='drop'>Next drop-off: <b style='color:#2D2D2D'>{esc(drop)}</b><br>window to {esc(E.fmt_date(window_end))}</div>"
            f"<div class='bandkey' style='margin-top:2mm'><div><i style='background:{C.PRIMARY}'></i>more than 20 days of room</div>"
            f"<div><i style='background:{C.AMBER}'></i>6-20 days of room</div><div><i style='background:{C.OCHRE}'></i>0-5 days of room</div></div></div>")


def csv_rows(log: E.DayLog, start: date, to: date):
    yield ["date", "tax_year", "midnight_country", "country_name", "midnight_place", "uk_midnight", "countries_present",
           "uk_work_over_3h", "uk_work_hours", "uk_work_note", "accommodation", "confidence", "evidence",
           "conflict", "changes"]
    for d in E.daterange(start, to):
        r = log.days.get(d) or {}
        lr = log.row(d)
        yield [d.isoformat(), E.tax_year_of(d), (lr or {}).get("midnight_country") or "", E.cname(lr["midnight_country"]) if lr else "NOT LOGGED",
               r.get("midnight_place", ""), "yes" if lr and lr["midnight_country"] == "GB" else "no",
               "|".join(log.present(d)), (r.get("uk_work") or {}).get("over_3h", ""), (r.get("uk_work") or {}).get("hours") or "",
               (r.get("uk_work") or {}).get("note", ""), r.get("accommodation_label") or r.get("accommodation_id") or "",
               r.get("confidence", "unlogged"), evidence_text(r),
               (r.get("conflict") or {}).get("detail", ""), " | ".join(f"{c.get('at')}: {c.get('field')} {c.get('from')}->{c.get('to')} ({c.get('reason')})" for c in r.get("changes", []))]


CHOICE_LABEL = {"work": "work day", "no_work": "non-work day", "ask": "ask each time", "as_weekday": "treated like a weekday"}
MEANS_LABEL = {"no_work": "non-work day", "under_3h": "3 hours or less of UK work (not counted)", "work": "work day", "ask": "ask"}
SOURCE_LABEL = [("rule", "Set by the rule (default)"), ("rule_exception", "Set by the rule (calendar exception)"),
                ("user_answer", "Your answer"), ("not_asked", "Not asked yet / unsure"), ("unrecorded", "Older entries with no source recorded")]


def _periods(ps) -> str:
    return "; ".join(f"{E.fmt_date(p['from'])} to {E.fmt_date(p['to']) if p.get('to') else 'open'}" + (f" ({p['label']})" if p.get("label") else "") for p in ps or []) or "none recorded"


def work_rule_cards(log, ty: str, start: date, to: date) -> str:
    """Cards quoting the work-day rule(s) in force for the year, with counts by source and disagreements."""
    rules = E.rules_in_force(log, start, to)
    rep = E.work_rule_report(log, ty, to)
    out = []
    if not rules:
        out.append("<div class='card amber'><h3>No work-day rule agreed</h3><p class='small'>Every UK work entry in this year comes from your own answers; UK days without an answer stay 'unsure'.</p></div>")
    for r in rules:
        hol = CHOICE_LABEL.get(r.get("public_holidays", "ask"), r.get("public_holidays"))
        region = (r.get("public_holiday_region") or "").replace("-", " ").title().replace("And", "and")
        conf = set(r.get("to_confirm") or [])
        tc = lambda k: " <span class='chip attn'>to confirm</span>" if k in conf else ""
        exr = "".join(f"<tr><td>{esc(x.get('keyword'))}{(' <span class=muted>(also: ' + esc(', '.join(x.get('aliases') or [])) + ')</span>') if x.get('aliases') else ''}</td><td>{esc(x.get('meaning') or MEANS_LABEL.get(x.get('means'), x.get('means')))}</td></tr>" for x in r.get("exceptions") or [])
        out.append(f"""<div class='card'><h3>Rule {esc(r.get('id'))}{SEP}in force {esc(E.fmt_date(r['effective_from']))} to {esc(E.fmt_date(r['effective_to']) if r.get('effective_to') else 'today (open)')}</h3>
<div class='quote'>\u201c{esc(r.get('wording_shown'))}\u201d</div>
<table class='fx kv'><col style='width:30%'><col style='width:70%'>
<tr><th>Agreed</th><td>{esc(E.fmt_date(r.get('agreed_at')))}, {esc(r.get('agreed_via'))}{(', by ' + esc(r.get('agreed_by'))) if r.get('agreed_by') else ''}. {'Applied to days before that date with your agreement.' if r.get('applies_to_earlier_days_agreed') else 'Applies from that date only.'}</td></tr>
<tr><th>Your own answers</th><td><b>Always take priority over this rule.</b> Any day you answered yourself keeps your answer.</td></tr>
{''.join(f"<tr><th>Confirmed</th><td>{esc(E.fmt_date(c.get('at')))}, {esc(c.get('via'))}: {esc(c.get('what'))}</td></tr>" for c in r.get('confirmations') or [])}
<tr><th>Job periods</th><td>{esc(_periods(r.get('job_periods')))}</td></tr>
<tr><th>No-job periods</th><td>{esc(_periods(r.get('no_job_periods')))} \u2014 every day a non-work day</td></tr>
<tr><th>Weekdays in the UK</th><td>{esc(CHOICE_LABEL.get(r.get('weekdays'), r.get('weekdays')))}{tc('weekdays')}</td></tr>
<tr><th>Weekends</th><td>{esc(CHOICE_LABEL.get(r.get('weekends'), r.get('weekends')))}{tc('weekends')}</td></tr>
<tr><th>Public holidays</th><td>{esc(hol)}{(' (' + esc(region) + ')') if region else ''}{tc('public_holidays')}</td></tr>
<tr><th>Travel days (into or out of the UK)</th><td>{esc(CHOICE_LABEL.get(r.get('travel_days', 'ask')))}{tc('travel_days')}</td></tr>
<tr><th>Travelling for work</th><td>{esc({'ask': 'ask each time', 'work': 'work day', 'travel_day': 'follows the travel-day setting'}.get(r.get('work_travel') or 'ask'))}{'' if r.get('work_travel') else ' (not set: asked each time)'}{(' \u00b7 calendar words: ' + esc(', '.join(r.get('work_travel_keywords')))) if r.get('work_travel_keywords') else ''}{tc('work_travel')}</td></tr>
<tr><th>More than 3 hours</th><td>{esc(r.get('over_3h_basis') or 'Your answer each day.')}</td></tr></table>
{('<table class="fx"><col style="width:38%"><col style="width:62%"><thead><tr><th>Calendar exception</th><th>What it means</th></tr></thead>' + exr + '</table>') if exr else ''}
{('<p class="small muted">' + esc(r.get('notes')) + '</p>') if r.get('notes') else ''}</div>""")
    counts = rep["counts"]
    crow = "".join(f"<tr><td>{esc(lbl)}</td><td class='n'>{counts.get(k, 0)}</td></tr>" for k, lbl in SOURCE_LABEL if counts.get(k) or k in ("rule", "rule_exception", "user_answer"))
    dis = "".join(f"<tr><td>{E.fmt_date(x['date'])}</td><td>{esc(x['log'])}</td><td>{esc(x['rule'])} ({esc(x['basis'])})</td><td class='ptr'>{esc(x['note'])}</td></tr>" for x in rep["disagree"])
    ans = rep["answered_differently"]
    out.append(f"""<div class='card'><h3>How each UK day's work entry was set in {esc(ty)}</h3>
<table class='fx'><col style='width:75%'><col style='width:25%'><thead><tr><th>Source</th><th class='n'>UK days</th></tr></thead>{crow}</table>
<p class='small muted'>Counted over days with any part in the UK, to {esc(E.fmt_date(to))}. Your own answers always take precedence over the rule{(': ' + str(len(ans)) + ' day(s) differ from the rule because you answered (' + esc(E.ranges([x['date'] for x in ans])) + ')') if ans else ''}.</p></div>
<div class='card flow {'amber' if dis else ''}'><h3>Days where the log and the rule differ</h3>
<table class='fx'><col style='width:16%'><col style='width:10%'><col style='width:26%'><col style='width:48%'><thead><tr><th>Date</th><th>Log</th><th>Rule gives</th><th>Note</th></tr></thead>{dis or '<tr><td colspan=4>None</td></tr>'}</table></div>""")
    return "".join(out)


def build_html(log: E.DayLog, ty: str, as_of: date, prefix: str = "") -> tuple[str, str]:
    """prefix: path from the PDF's folder to the user's data folder, so evidence/ file links stay relative."""
    ref = E.srt_reference(log, ty, as_of)
    s, t, tt = ref["summary"], ref["ties"], ref["ties_test"]
    start, end = E.tax_year_bounds(ty)
    to = min(end, as_of)
    complete = as_of >= end
    period = f"6 April {start.year} to 5 April {end.year}" + ("" if complete else f" (recorded to {E.fmt_date(to)}, year in progress)")
    title = f"Travel and day log \u2013 {ty}"
    stays = E.stays(log, start, to)
    qs = E.open_questions(log, ty, as_of)
    name = log.profile.get("display_name", "")
    col = C.Colours(log)
    items = list(s["countries"].items())
    unl = s["unlogged"]
    total_days = sum(v for _, v in items) + unl

    # ---------------------------------------------------------------- key metrics (as the dashboard)
    uk = s["uk_midnights"]
    line = tt.get("line") if tt.get("line") is not None else 182
    room = tt.get("room", 182 - uk)
    ub = C.band(room)
    uk_col = C.CORAL if ub[0] == "calm" else ub[1]
    ties_label = f"{tt['recorded_ties']} tie{'s' if tt['recorded_ties'] != 1 else ''} recorded" if tt.get("table") else "RDR3 table not set"
    sch = E.rolling_status(log, to)
    sb = C.band(sch["room"])
    drop = E.fmt_date(sch["earliest_drop_off"]) if sch["earliest_drop_off"] else "none"
    wd = s["uk_work_days_over_3h"]
    wb = C.band(40 - wd)
    w_col = C.VIOLET if wb[0] == "calm" else wb[1]
    unsure = f" <span class='chip attn'>{s['uk_work_unsure']} unsure</span>" if s["uk_work_unsure"] else ""
    ring = lambda v, tot, c: static_svg(C.ring(v, tot, c, size=50, stroke=7))
    k1 = kpi("UK days", uk, f"/ {line}", f"<b>{max(room, 0) if room >= 0 else -room}</b> {'days of room before' if room >= 0 else 'over'} {line}", ring(uk, line, uk_col), uk_col)
    k2 = kpi("Schengen", sch["used"], "/ 90", f"<b>{sch['room']}</b> days of room{SEP}drop-off {esc(drop)}", ring(sch["used"], 90, sb[1]), sb[1])
    k3 = kpi("UK work days", wd, "/ 40", f"<b>{max(40 - wd, 0)}</b> days of room before 40{unsure}", ring(wd, 40, w_col), w_col)
    if unl:
        k4 = kpi("Logging", f"{unl} day{'s' if unl != 1 else ''} missing", "", f"{esc(E.ranges(s['unlogged_dates']))}; never filled by estimate", dot("alert-circle", "#B07A12", "#FFF7E8"), "#8A5A00", word=True)
    else:
        k4 = kpi("Logging", "All days logged", "", f"every day to {E.fmt_date(to)}", dot("check-circle", C.PRIMARY, "#F0FBF8"), C.PRIMARY, word=True)

    donut = static_svg(C.donut(items + ([("UNLOGGED", unl)] if unl else []), col, size=180, radius=60, stroke=24, centre=str(total_days), centre_sub="days"), 36)
    leg_items = items[:8]
    rest = items[8:]
    legend = "".join(f"<tr><td><span class='sw' style='background:{col(c)}'></span>{esc(E.cname(c))}</td><td class='v'>{v}d</td><td class='v'>{round(100 * v / max(total_days, 1))}%</td></tr>" for c, v in leg_items)
    if rest:
        legend += f"<tr><td><span class='sw' style='background:#D4CFC7'></span>Other ({len(rest)})</td><td class='v'>{sum(v for _, v in rest)}d</td><td class='v'>{round(100 * sum(v for _, v in rest) / max(total_days, 1))}%</td></tr>"
    if unl:
        legend += f"<tr><td><span class='sw' style='background:{C.GAP_FILL};border:1.5px solid {C.AMBER}'></span>Not logged</td><td class='v'>{unl}d</td><td class='v'>{round(100 * unl / max(total_days, 1))}%</td></tr>"

    months = []
    d = date(start.year, start.month, 1)
    while d <= end:
        cnt = {}
        for day in E.daterange(max(d, start), min(date(d.year + (d.month == 12), d.month % 12 + 1, 1) - timedelta(days=1), to)):
            r = log.row(day)
            k = r["midnight_country"] if r else "UNLOGGED"
            cnt[k] = cnt.get(k, 0) + 1
        order = sorted(cnt.items(), key=lambda kv: (kv[0] != "GB", kv[0] == "UNLOGGED", -kv[1]))
        months.append((E.MONTHS[d.month - 1], [(v, C.GAP_FILL if c == "UNLOGGED" else col(c), c == "UNLOGGED") for c, v in order]))
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    mkey = "".join(f"<span><span class='sw' style='background:{col(c)}'></span>{esc(E.cname(c))}</span>" for c, _ in items[:7])

    cover = f"""<div class='top'>{split(_logo(), f"<div class='k'>Nomad Pro{SEP}UK Residency Tracker</div><h1>{esc(title)}</h1><div class='meta'>{esc(name) + SEP if name else ''}{esc(period)}{SEP}generated {esc(E.fmt_date(as_of))}</div>", widths=(10, 90))}</div>
<h3>Key metrics <span class='sub'>{esc(ty)}{SEP}to {esc(E.fmt_date(to))}</span></h3>
{lay(k1, k2, k3, k4, widths=(25, 25, 25, 25))}
{lay(f"""<td class='card'><h3>Days by country</h3><div class='small muted' style='margin:-1.5mm 0 1.5mm'>counted by where you were at midnight</div>
<table class='split'><tr><td class='sp' style='width:40mm'>{donut}</td><td class='sp'><div style='margin-left:2mm'><table class='legend fx'><col><col style='width:11mm'><col style='width:10mm'>{legend}</table></div></td></tr></table>{(f"<p class='small muted' style='margin:1mm 0 0'>Other: {esc(', '.join(f'{E.cname(c)} {v}d' for c, v in rest))}</p>") if rest else ''}</td>""",
f"<td class='card'><h3>Days by month</h3><div class='small muted' style='margin:-1.5mm 0 1.5mm'>UK at the base of each bar</div>{bars_svg(months)}<div class='key'>{mkey}</div></td>", widths=(56, 44))}
<div class='card'><h3>Contents</h3><ol class='toc'><li>Location timeline</li><li>Schengen, rolling 180 days</li><li>Ties and reference figures</li><li>Summary counts</li><li>Stays</li><li>UK days</li><li>UK work days (more than 3 hours)</li><li>Work-day rule</li><li>Ties as recorded</li><li>Day-by-day log with evidence</li><li>Gaps, open questions and changes</li><li>Counting method</li></ol>
<p class='small muted' style='margin:2mm 0 0'>A record of the days, places and work you logged and where the supporting records sit. It does not determine residence. Counts are arithmetic on your own entries.</p></div>
<div class='legal'>{esc(E.L6)}</div>"""

    # ---------------------------------------------------------------- 1. timeline, 2. Schengen, 3. ties
    today = as_of if not complete else None
    tl_rows = "".join(stay_row_svg(x, start, end, col, today=today) for x in reversed(stays))
    planned = [p for p in log.planned if p.get("status") in ("idea", "booked") and p["to"] >= as_of.isoformat() and p["from"] <= end.isoformat()] if not complete else []
    pl_rows = "".join(stay_row_svg({"from": p["from"], "to": p["to"], "country": p["country"], "place": p.get("place")}, start, end, col, today=today, planned=True) for p in sorted(planned, key=lambda p: p["from"], reverse=True))
    timeline = f"""<h2 class='pb'><span class='n'>1</span>Location timeline<span class='sub'>{len(stays)} stays{SEP}newest first{SEP}{esc(E.fmt_date(start))} to {esc(E.fmt_date(end))}</span></h2>
<div class='card flow'>{(f"<div class='k' style='color:#9E9E9E;margin-bottom:1mm'>Booked, not yet travelled</div>{pl_rows}<div class='k' style='color:#9E9E9E;margin:2mm 0 1mm'>Logged</div>" if pl_rows else '')}{tl_rows or "<p class='muted'>No stays logged.</p>"}</div>"""

    series = E.schengen_series(log, start, to)
    sch_chart = static_svg(C.area(series, 90, C.PRIMARY, width=640, height=260, ymax=100, fmt="{v}", aria="Schengen days in the rolling 180-day window", bands=True, static=True))
    peak = max((v for _, v in series), default=0)
    schengen = f"""<h2><span class='n'>2</span>Schengen, rolling 180 days<span class='sub'>{esc(E.fmt_date(start))} to {esc(E.fmt_date(to))}</span></h2>
<div class='card'>{split(f"""{sch_chart}
<div class='key' style='margin-top:1mm'><span><span class='sw' style='background:{C.PRIMARY}'></span>more than 20 days of room</span><span><span class='sw' style='background:{C.AMBER}'></span>6-20</span><span><span class='sw' style='background:{C.OCHRE}'></span>0-5</span><span>dashed line: 90-day limit</span></div>""", quick_read(sch['used'], sch['room'], drop, to), widths=(66, 34))}
<p class='small muted' style='margin:2mm 0 0'>Highest count in this period: {peak} of 90. Any part of a day in a Schengen country counts, including entry and exit days; Cyprus is counted separately. {esc(E.L8)}</p></div>"""

    icons = {"family": "users", "accommodation": "home", "work": "briefcase", "ninety_day": "calendar", "country": "flag"}
    names = {"family": "Family", "accommodation": "Accommodation", "work": "Work", "ninety_day": "90-day", "country": "Country"}
    tiles = []
    for k, v in t["ties"].items():
        st = v["status"]
        if k == "country" and not v.get("applies"):
            cls, word = "na", "Not applicable"
        elif st == "Recorded yes":
            cls, word = "on", "On"
        elif st == "Recorded no":
            cls, word = "off", "Off"
        elif "differ" in st:
            cls, word = "rev", "Review"
        else:
            cls, word = "na", "Not answered"
        tiles.append(f"<td class='tie {cls}'><div class='ico'>{icon(icons[k], '#fff' if cls in ('on', 'rev') else C.INK_2, 20)}</div><div class='nm'>{names[k]}</div><div class='st'>{word}</div><div class='rf'>{esc(v['ref'])}</div></td>")
    ptrs = "".join(f"<div class='pointer'><b>{esc(l['text'])}</b><div class='d'>{esc(l['disclaimer'])}</div></div>" for l in ref["stage_lines"])
    prox = tt.get("proximity", "")
    pc = {"getting close": "attn", "at the line": "deep", "over the line": "deep"}.get(prox, "teal")
    fig = "".join(f"<tr><td>{f['figure']}</td><td>{esc(E.cite(f['ref']))}</td><td class='n'>{f['distance'] if f['distance'] > 0 else 'reached'}</td></tr>" for f in ref["figures"])
    ties_ref = f"""<h2><span class='n'>3</span>Ties and reference figures</h2>
<div class='card'><h3>Your UK ties <span class='sub'>as you recorded them{SEP}{t['recorded_count']} recorded</span></h3><table class='tiles'><tr>{''.join(tiles)}</tr></table>
<div class='key' style='margin-top:2mm'><span>On = recorded yes</span><span>Off = recorded no</span><span>Dashed = not answered / not applicable</span><span>Amber = your answer and the log differ</span></div></div>
<div class='card'><h3>UK days against RDR3 day figures <span class='sub'>{uk} UK days{SEP}your line {line}</span></h3>{static_svg(C.figure_line(uk, ref['figures'], tt.get('line'), colour=uk_col))}
<p style='margin:1mm 0'>{esc(tt.get('band_text', ''))} <b>{esc(tt.get('room_text', ''))}</b> <span class='chip {pc}'>{esc(prox)}</span></p>
<p class='small muted' style='margin:0'>{esc(tt.get('table_reason', ''))}. Table and boundaries as published in {esc(E.cite('RFIG20520'))} and {esc(E.cite('RDR3'))}.</p>{ptrs}
<table class='fx' style='margin-top:2mm'><col style='width:18%'><col style='width:60%'><col style='width:22%'><thead><tr><th>Figure</th><th>HMRC page</th><th>Days to go</th></tr></thead>{fig}</table>
<ul class='small'>{''.join(f'<li>{esc(n)}</li>' for n in ref['notes'])}<li>{esc(ref['ninety_day_next_year']['text'])} ({esc(ref['ninety_day_next_year']['cite'])}).</li></ul></div>"""

    # ---------------------------------------------------------------- 4. summary counts
    summary = f"""<h2 class='pb'><span class='n'>4</span>Summary counts</h2><div class='card'>
<table class='fx'><col style='width:42%'><col style='width:16%'><col style='width:42%'><thead><tr><th>Count</th><th>{esc(ty)}</th><th>Basis</th></tr></thead>
<tr><td>Days in the year {'' if complete else 'to date'}</td><td class='n'>{s['days_in_year_to_date']}</td><td>{E.fmt_date(start)} \u2013 {E.fmt_date(to)}</td></tr>
<tr><td>Days logged</td><td class='n'>{s['logged']}</td><td>{unl} not logged; gaps are never filled by estimate</td></tr>
<tr><td>UK midnights</td><td class='n'>{s['uk_midnights']}</td><td>{esc(E.cite('RFIG20710'))}</td></tr>
<tr><td>UK work days, more than 3 hours</td><td class='n'>{s['uk_work_days_over_3h']}</td><td>{esc(E.cite('RFIG20560'))}; {s['uk_work_unsure']} unsure</td></tr>
<tr><td>Days in the UK without a UK midnight</td><td class='n'>{len(s['qualifying_days_not_midnight'])}</td><td>recorded for {esc(E.cite('RFIG20720'))}</td></tr>
<tr><td>Schengen days (any part of a day) / midnights</td><td class='n'>{s['schengen_days_any_part']} / {s['schengen_midnights']}</td><td>immigration count, not an HMRC figure</td></tr>
<tr><td>Days confirmed / inferred / owner statement</td><td class='n'>{s['logged'] - len(s['inferred_dates']) - len(s['attested_dates'])} / {len(s['inferred_dates'])} / {len(s['attested_dates'])}</td><td>confidence per day</td></tr></table></div>"""

    srows = "".join(f"<tr{' class=gap' if x['country'] == 'UNLOGGED' else ''}><td>{E.fmt_date(x['from'])}</td><td>{E.fmt_date(x['to'])}</td><td class='n'>{x['nights']}</td><td><span class='sw' style='background:{C.AMBER if x['country'] == 'UNLOGGED' else col(x['country'])}'></span>{esc(C.cn(x['country']))}</td><td>{esc(', '.join(x['confidence']))}</td><td class='ptr'>{esc('; '.join(x['pointers'])[:240])}</td></tr>" for x in stays)
    stays_html = f"<h2><span class='n'>5</span>Stays<span class='sub'>consecutive nights in one place, first and last night (midnight rule)</span></h2><div class='card flow'><table class='fx'><col style='width:12%'><col style='width:12%'><col style='width:9%'><col style='width:16%'><col style='width:14%'><col style='width:37%'><thead><tr><th>First night</th><th>Last night</th><th>Nights</th><th>Country</th><th>Confidence</th><th>Record pointers</th></tr></thead>{srows}</table></div>"

    ukrows = []
    for dd in s["uk_dates"]:
        r = log.days[E.parse_date(dd)]
        w = r.get("uk_work") or {}
        ukrows.append(f"<tr><td>{E.fmt_date(dd)}</td><td>{esc(r.get('accommodation_label') or r.get('accommodation_id') or '')}</td><td>{esc(w.get('over_3h'))}</td><td>{esc(r.get('confidence'))}</td><td class='ptr'>{evidence_cell(r, prefix, 3)}</td></tr>")
    q = s["qualifying_days_not_midnight"]
    uk_html = f"""<h2 class='pb'><span class='n'>6</span>UK days<span class='sub'>{s['uk_midnights']} midnights</span></h2><div class='card flow'><table class='days fx'><col style='width:15%'><col style='width:24%'><col style='width:10%'><col style='width:13%'><col style='width:38%'><thead><tr><th>Date</th><th>Accommodation</th><th>Work >3h</th><th>Confidence</th><th>Evidence</th></tr></thead>{''.join(ukrows) or '<tr><td colspan=5>None</td></tr>'}</table>
<p class='small muted'>In the UK for part of the day without a UK midnight: {esc(E.ranges(q)) or 'none'}.</p></div>"""

    wm = []
    d = date(start.year, start.month, 1)
    while d <= end:
        km = f"{d.year}-{d.month:02d}"
        wm.append((E.MONTHS[d.month - 1], [(sum(1 for x in s['uk_work_dates'] if x.startswith(km)), C.VIOLET, False),
                                            (sum(1 for x in s['uk_work_unsure_dates'] if x.startswith(km)), C.GAP_FILL, True)]))
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    cap = max([sum(v for v, _, _ in sg) for _, sg in wm] + [5])
    wrows = []
    for dd in sorted(s["uk_work_dates"] + s["uk_work_unsure_dates"]):
        w = log.days[E.parse_date(dd)].get("uk_work") or {}
        wrows.append(f"<tr><td>{E.fmt_date(dd)}</td><td>{esc(w.get('over_3h'))}</td><td>{esc(w.get('hours') or '-')}</td><td class='ptr'>{esc(w.get('note'))}</td></tr>")
    work_html = f"""<h2><span class='n'>7</span>UK work days (more than 3 hours)<span class='sub'>{wd} logged{SEP}{s['uk_work_unsure']} unsure</span></h2>
<div class='card'>{split(f"""{bars_svg(wm, cap=cap, height=150)}<div class='key'><span><span class='sw' style='background:{C.VIOLET}'></span>more than 3 hours</span><span><span class='sw' style='background:{C.GAP_FILL};border:1.5px solid {C.AMBER}'></span>unsure</span></div>""", f"<div class='quick'><div class='big' style='color:{w_col}'>{wd} <small>of 40</small></div><div class='drop'>Figures HMRC uses: 31 ({esc(E.cite('RFIG20140'))}) and 40 ({esc(E.cite('RFIG20560'))}).</div></div>", widths=(62, 38))}</div>
<div class='card flow'><table class='days fx'><col style='width:16%'><col style='width:16%'><col style='width:10%'><col style='width:58%'><thead><tr><th>Date</th><th>More than 3 hours</th><th>Hours</th><th>Note</th></tr></thead>{''.join(wrows) or '<tr><td colspan=4>None logged</td></tr>'}</table>
<p class='small muted'>Hours appear only where given; nothing is defaulted. {esc(E.cite('RFIG20740'))} describes what counts as work.</p></div>"""

    rule_html = f"""<h2 class='pb'><span class='n'>8</span>Work-day rule<span class='sub'>how UK work days were set, as agreed with you; kept for any HMRC enquiry</span></h2>
<p class='small muted'>Your own answer for a day always takes priority over the rule. Each UK work entry records its source: your own answer, or the work-day rule you agreed (with the calendar keyword when an exception applied). A UK day that no rule covers and you have not answered stays 'unsure'. Changes to the rule are versioned with dates and never rewrite earlier days without asking you.</p>
{work_rule_cards(log, ty, start, to)}"""

    cfg = log.year_config(ty)
    trows = "".join(f"<tr><td>{esc(names.get(k, k))}</td><td>{esc(v['user_answer'].replace('_', ' '))}</td><td>{esc(v['log_shows'])}</td><td>{esc(v['cite'])}</td><td><span class='chip{' attn' if 'differ' in v['status'] or 'Not answered' in v['status'] else ''}' style='white-space:normal'>{esc(v['status'])}</span></td></tr>" for k, v in t["ties"].items())
    extra = "".join(f"<li>{esc(k)}: {esc(v)}</li>" for k, v in (cfg.get("notes") or {}).items())
    ties_html = f"""<h2 class='pb'><span class='n'>9</span>Ties as recorded<span class='sub'>your answers (last reviewed {esc(cfg.get('tie_answers_reviewed_at', '-'))}) next to what the log shows; nothing is overwritten</span></h2>
<div class='card'><table class='fx'><col style='width:15%'><col style='width:11%'><col style='width:35%'><col style='width:19%'><col style='width:20%'><thead><tr><th>Tie</th><th>Your answer</th><th>What the log shows</th><th>HMRC page</th><th>Status</th></tr></thead>{trows}</table><ul class='small'>{extra}</ul></div>
<div class='card'><h3>Other recorded answers</h3><table class='fx'><col style='width:38%'><col style='width:37%'><col style='width:25%'>
<tr><td>Full-time overseas work (your claim)</td><td>{esc(cfg.get('overseas_full_time_work_claimed', 'not answered').replace('_', ' '))}</td><td>{esc(E.cite('RFIG20140'))}</td></tr>
<tr><td>Only home in the UK (your answer)</td><td>{esc(cfg.get('only_home_in_uk_answer', 'not answered').replace('_', ' '))}</td><td>{esc(E.cite('RFIG20330'))}</td></tr>
<tr><td>Full-time work in the UK (your answer)</td><td>{esc(cfg.get('full_time_uk_work_answer', 'not answered').replace('_', ' '))}</td><td>{esc(E.cite('RFIG20370'))}</td></tr>
<tr><td>Residence recorded for the previous 3 tax years</td><td>{esc(', '.join(f"{E.prev_tax_year(ty, n)}: {E.uk_resident_recorded(log, E.prev_tax_year(ty, n))}" for n in (1, 2, 3)))}</td><td>{esc(E.cite('RFIG20520'))}</td></tr>
</table></div>"""

    drows = []
    for dd in E.daterange(start, to):
        r = log.days.get(dd) or {}
        lr = log.row(dd)
        c = lr["midnight_country"] if lr else None
        sw = f"<span class='sw' style='background:{col(c) if c else C.AMBER}'></span>"
        drows.append(f"<tr{'' if lr else ' class=gap'}><td>{dd.strftime('%a')} {E.fmt_date(dd)}</td><td>{sw}{esc(E.cname(c) if lr else 'Not logged')}</td><td>{esc(', '.join(E.cname(x) for x in log.present(dd)) if lr and len(log.present(dd)) > 1 else '')}</td><td>{esc((r.get('uk_work') or {}).get('over_3h') if (r.get('uk_work') or {}).get('over_3h') not in (None, 'n/a') else '')}</td><td>{esc(r.get('confidence', 'unlogged'))}</td><td class='ptr'>{evidence_cell(r, prefix, 3)}</td></tr>")
    days_html = f"""<h2 class='pb'><span class='n'>10</span>Day-by-day log with evidence<span class='sub'>one row per date</span></h2>
<p class='small muted'>'Also present' lists every country on days with more than one (used for Schengen and stay limits). Evidence shows a clickable link where one is filed (an email, or a stored file in evidence/) and otherwise a pointer saying where the record sits.</p>
<div class='card flow'><table class='days fx'><col style='width:16%'><col style='width:15%'><col style='width:15%'><col style='width:8%'><col style='width:12%'><col style='width:34%'><thead><tr><th>Date</th><th>Midnight</th><th>Also present</th><th>UK work</th><th>Confidence</th><th>Evidence</th></tr></thead>{''.join(drows)}</table></div>"""

    changes = [(dd, c) for dd in s["edited_dates"] for c in log.days[E.parse_date(dd)].get("changes", [])]
    conf = "".join(f"<tr><td>{E.fmt_date(c['date'])}</td><td>{esc(c.get('detail'))}</td><td>{esc(c.get('resolution'))} ({esc(c.get('resolved_by'))}, {esc(c.get('resolved_at'))})</td></tr>" for c in s["conflicts"])
    ch = "".join(f"<tr><td>{E.fmt_date(dd)}</td><td>{esc(c.get('field'))}: {esc(c.get('from'))} \u2192 {esc(c.get('to'))}</td><td>{esc(c.get('reason'))} ({esc(c.get('at'))})</td></tr>" for dd, c in changes)
    oq = "".join(f"<li>{esc(x)}</li>" for x in qs) + "".join(f"<li>{esc(x['text'])}</li>" for x in log.data.get("open_questions", []) if x.get("status") == "open" and ((ty in x["tax_years"]) if x.get("tax_years") else start.isoformat() <= x.get("raised_at", "")[:10] <= E.tax_year_bounds(ty)[1].isoformat()))
    gaps_html = f"""<h2 class='pb'><span class='n'>11</span>Gaps, open questions and changes</h2>
<div class='card'><table class='fx'><col style='width:30%'><col style='width:70%'><tr><th>Not yet logged</th><td>{esc(E.ranges(s['unlogged_dates'])) or 'none'}</td></tr><tr><th>Marked inferred</th><td>{esc(E.ranges(s['inferred_dates'])) or 'none'}</td></tr>
<tr><th>Owner statement (attested)</th><td>{esc(E.ranges(s['attested_dates'])) or 'none'}</td></tr><tr><th>No record pointer</th><td>{esc(E.ranges(s['no_pointer_dates'])) or 'none'}</td></tr></table></div>
<div class='card {'amber' if oq else ''}'><h3>Questions HMRC could ask about this year</h3><ul class='small'>{oq or '<li>None recorded.</li>'}</ul></div>
<div class='card flow'><h3>Conflicting records and how they were resolved</h3><table class='fx'><col style='width:15%'><col style='width:45%'><col style='width:40%'><thead><tr><th>Date</th><th>Conflict</th><th>Resolution</th></tr></thead>{conf or '<tr><td colspan=3>None</td></tr>'}</table></div>
<div class='card flow'><h3>Change log (edits after the day)</h3><table class='fx'><col style='width:15%'><col style='width:40%'><col style='width:45%'><thead><tr><th>Date</th><th>Change</th><th>Reason</th></tr></thead>{ch or '<tr><td colspan=3>None</td></tr>'}</table></div>"""

    method = f"""<h2><span class='n'>12</span>Counting method</h2><div class='card'><ul>
<li><b>Tax year:</b> 6 April to 5 April.</li>
<li><b>UK days:</b> a day counts as a UK day if you were in the UK at midnight (the midnight rule), {esc(E.cite('RFIG20710'))}.</li>
<li><b>UK work days:</b> days with more than 3 hours of work in the UK, {esc(E.cite('RFIG20560'))}, set from your answer or from the work-day rule you agreed (section 8); 'unsure' days are listed, not counted. Calendar entries alone never make a work day.</li>
<li><b>Ties:</b> your own recorded answers, shown next to what the log shows, with RDR3 Table A or B chosen from the residence status you recorded for the previous 3 tax years. Day bands use HMRC's own 'more than' wording, {esc(E.cite('RFIG20520'))}.</li>
<li><b>Proximity levels</b> are distance to an HMRC figure only: comfortable room (more than 20 days, teal), getting close (6\u201320, amber), at the line (0\u20135, ochre), over the line (ochre).</li>
<li><b>Recorded but not calculated</b> unless your data supports every condition: the deeming rule ({esc(E.cite('RFIG20720'))}), transit days ({esc(E.cite('RFIG20730'))}), exceptional circumstances ({esc(E.cite('RFIG22220'))}) and split-year treatment ({esc(E.cite('RFIG21000'))}).</li>
<li><b>Schengen and other stay limits</b> count any part of a day, including entry and exit days. {esc(E.L8)}</li>
<li><b>Confidence:</b> confirmed (a record points to it), inferred (a record at one end, the other end soft), owner statement (your attestation, dated). Unlogged days are never filled by estimate.</li>
<li><b>Colours</b> show the country or the category only (UK coral, work violet, Schengen teal); amber marks gaps and figures that are getting close.</li>
<li><b>Sources:</b> HMRC guidance mirrored from gov.uk; page dates are HMRC's own last-updated dates.</li></ul></div>
<div class='legal'>{esc(E.L6)}</div><p class='small muted'>Nomad Pro is not affiliated with HM Revenue &amp; Customs.</p>"""

    html = (f"<!doctype html><html lang='en-GB'><head><meta charset='utf-8'><title>{esc(title)}</title><style>{_font_face()}{CSS}</style></head><body>"
            f"{cover}{timeline}{schengen}{ties_ref}{summary}{stays_html}{uk_html}{work_html}{rule_html}{ties_html}{days_html}{gaps_html}{method}</body></html>")
    base = f"Travel and day log {ty.replace('/', '-')}" + ("" if complete else f" (to {E.fmt_date(to)})")
    return html, base


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("daylog")
    ap.add_argument("--tax-year", required=True)
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--as-of", default=date.today().isoformat())
    ap.add_argument("--rules", help=E.RULES_HELP)
    ap.add_argument("--kb", help="HMRC mirror (root or pages/ dir); default: $NOMAD_PRO_KB, else <engine>/hmrc")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--data-root", help="user data folder holding evidence/ (default: the day log's folder)")
    a = ap.parse_args(argv)
    E.load_hmrc_dates(E.default_kb(a.kb))
    E.load_rules(E.default_rules_path(a.rules))
    log = E.DayLog.load(a.daylog)
    as_of = E.parse_date(a.as_of)
    out = Path(a.out_dir)
    from render_common import file_prefix
    html, base = build_html(log, a.tax_year, as_of, file_prefix(a.data_root or str(Path(a.daylog).parent), out))
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{base}.html").write_text(html, encoding="utf-8")
    start, end = E.tax_year_bounds(a.tax_year)
    with open(out / f"{base}.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(csv_rows(log, start, min(end, as_of)))
    if not a.html_only:
        from weasyprint import HTML
        HTML(string=html, base_url=None).write_pdf(out / f"{base}.pdf")  # base_url=None keeps evidence links relative
        (out / f"{base}.html").unlink()
    print(out / f"{base}.pdf")


if __name__ == "__main__":
    main()
