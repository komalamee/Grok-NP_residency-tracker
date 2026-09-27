"""Shared helpers for the dashboard and the PDF: escaping, neutral colours, small SVG charts."""
from __future__ import annotations

import hashlib
import html
from collections import OrderedDict
from datetime import date, timedelta

import srt_engine as E

INK = "#1f2933"
MUTED = "#616e7c"
LINE = "#d9d5cc"
PAPER = "#f7f6f3"
NAVY = "#243b53"
AMBER = "#b7791f"      # attention only: logging gaps and approaching reference figures
UK_TONE = "#334e68"


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def colour(code: str) -> str:
    """Muted, stable colour per country (hash -> hue, low saturation). UK gets slate navy."""
    if code == "GB":
        return UK_TONE
    if code in (None, "UNLOGGED"):
        return "#e4e0d8"
    h = int(hashlib.md5(code.encode()).hexdigest()[:4], 16) % 360
    return f"hsl({h} 22% 58%)"


def hbar_svg(items: list[tuple[str, int]], width=520, bar_h=18, gap=6, label_w=150) -> str:
    if not items:
        return "<p class='muted'>No logged days.</p>"
    mx = max(v for _, v in items) or 1
    h = len(items) * (bar_h + gap)
    out = [f"<svg viewBox='0 0 {width} {h}' width='100%' style='max-width:{width}px' role='img' aria-label='Midnights by country'>"]
    for i, (code, v) in enumerate(items):
        y = i * (bar_h + gap)
        w = (width - label_w - 50) * v / mx
        out.append(f"<text x='0' y='{y + bar_h - 5}' font-size='12' fill='{INK}'>{esc(E.cname(code))}</text>"
                   f"<rect x='{label_w}' y='{y}' width='{w:.1f}' height='{bar_h}' rx='3' fill='{colour(code)}'/>"
                   f"<text x='{label_w + w + 6:.1f}' y='{y + bar_h - 5}' font-size='12' fill='{MUTED}'>{v}</text>")
    out.append("</svg>")
    return "".join(out)


def monthly_counts(log: E.DayLog, start: date, end: date) -> "OrderedDict[str, dict]":
    months: OrderedDict[str, dict] = OrderedDict()
    for d in E.daterange(start, end):
        key = f"{d.year}-{d.month:02d}"
        r = log.row(d)
        c = r["midnight_country"] if r else "UNLOGGED"
        months.setdefault(key, {})
        months[key][c] = months[key].get(c, 0) + 1
    return months


def monthly_svg(log: E.DayLog, start: date, end: date, width=720, height=150) -> str:
    months = monthly_counts(log, start, end)
    n = len(months) or 1
    bw = (width - 40) / n
    out = [f"<svg viewBox='0 0 {width} {height + 24}' width='100%' style='max-width:{width + 200}px' role='img' aria-label='Midnights per month by country'>"]
    for i, (m, counts) in enumerate(months.items()):
        x = 30 + i * bw
        y = height
        order = sorted(counts.items(), key=lambda kv: (kv[0] != "GB", kv[0] == "UNLOGGED", -kv[1]))
        for c, v in order:
            hgt = (height - 10) * v / 31
            y -= hgt
            title = f"{E.MONTHS[int(m[5:]) - 1]} {m[:4]}: {E.cname(c) if c != 'UNLOGGED' else 'not logged'} {v}"
            stroke = f" stroke='{AMBER}' stroke-dasharray='3 2'" if c == "UNLOGGED" else ""
            out.append(f"<rect x='{x + 2:.1f}' y='{y:.1f}' width='{bw - 4:.1f}' height='{hgt:.1f}' fill='{colour(c)}'"
                       f"{stroke}><title>{esc(title)}</title></rect>")
        out.append(f"<text x='{x + bw / 2:.1f}' y='{height + 16}' font-size='10' text-anchor='middle' fill='{MUTED}'>{E.MONTHS[int(m[5:]) - 1]}</text>")
    out.append(f"<line x1='28' y1='{height}' x2='{width}' y2='{height}' stroke='{LINE}'/></svg>")
    return "".join(out)


def timeline_svg(stays: list[dict], start: date, end: date, width=720, height=34) -> str:
    total = (end - start).days + 1
    out = [f"<svg viewBox='0 0 {width} {height + 14}' width='100%' role='img' aria-label='Timeline of stays'>"]
    for s in stays:
        a = (E.parse_date(s["from"]) - start).days
        w = s["nights"]
        x = width * a / total
        ww = max(width * w / total, 0.8)
        c = s["country"]
        label = f"{E.cname(c) if c != 'UNLOGGED' else 'Not logged'}: {E.fmt_date(s['from'])} \u2013 {E.fmt_date(s['to'])} ({w})"
        stroke = f" stroke='{AMBER}'" if c == "UNLOGGED" else ""
        out.append(f"<rect x='{x:.2f}' y='0' width='{ww:.2f}' height='{height}' fill='{colour(c)}'"
                   f"{stroke}><title>{esc(label)}</title></rect>")
    out.append(f"<text x='0' y='{height + 12}' font-size='10' fill='{MUTED}'>{E.fmt_date(start)}</text>"
               f"<text x='{width}' y='{height + 12}' font-size='10' text-anchor='end' fill='{MUTED}'>{E.fmt_date(end)}</text></svg>")
    return "".join(out)


def schengen_svg(series: list[tuple[str, int]], planned_from: str | None = None, width=720, height=170) -> str:
    if not series:
        return ""
    n = len(series)
    mx = max(95, max(v for _, v in series) + 5)
    def px(i): return 30 + (width - 40) * i / max(n - 1, 1)
    def py(v): return height - (height - 10) * v / mx
    pts = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, (_, v) in enumerate(series))
    out = [f"<svg viewBox='0 0 {width} {height + 20}' width='100%' role='img' aria-label='Schengen days in the rolling 180-day window'>",
           f"<line x1='30' y1='{py(90):.1f}' x2='{width - 10}' y2='{py(90):.1f}' stroke='{MUTED}' stroke-dasharray='4 3'/>",
           f"<text x='26' y='{py(90) + 4:.1f}' font-size='10' text-anchor='end' fill='{MUTED}'>90</text>",
           f"<polyline points='{pts}' fill='none' stroke='{NAVY}' stroke-width='1.6'/>"]
    if planned_from:
        idx = next((i for i, (d, _) in enumerate(series) if d >= planned_from), None)
        if idx is not None:
            out.append(f"<rect x='{px(idx):.1f}' y='0' width='{width - 10 - px(idx):.1f}' height='{height}' fill='{NAVY}' opacity='0.05'/>"
                       f"<text x='{px(idx) + 4:.1f}' y='{height - 6}' font-size='10' fill='{MUTED}'>planned</text>")
    out.append(f"<text x='30' y='{height + 14}' font-size='10' fill='{MUTED}'>{E.fmt_date(series[0][0])}</text>"
               f"<text x='{width - 10}' y='{height + 14}' font-size='10' text-anchor='end' fill='{MUTED}'>{E.fmt_date(series[-1][0])}</text></svg>")
    return "".join(out)


def last_logged(log: E.DayLog, as_of: date) -> date | None:
    d = as_of
    first = log.first_date()
    while first and d >= first:
        if log.row(d):
            return d
        d -= timedelta(days=1)
    return None


# ---------------------------------------------------------------- evidence (links or pointers)
def evidence_entries(row: dict | None) -> list[dict]:
    """One dict per evidence item: label, href (email/web link or file path relative to the data folder), kind."""
    out = []
    for e in (row or {}).get("evidence", []):
        label = e.get("label") or e.get("pointer") or e.get("type") or "record"
        if e.get("url"):
            out.append({"label": label, "href": e["url"], "kind": "link", "pointer": e.get("pointer", "")})
        elif e.get("file"):
            out.append({"label": label, "href": e["file"], "kind": "file", "pointer": e.get("pointer", "")})
        else:
            out.append({"label": label, "href": None, "kind": "pointer", "pointer": e.get("pointer", "")})
    return out


def file_prefix(data_root, out_dir) -> str:
    """Prefix that turns a data-folder-relative evidence path into a link that works from out_dir."""
    import os
    if not data_root or not out_dir:
        return ""
    rel = os.path.relpath(os.path.abspath(data_root), os.path.abspath(out_dir))
    return "" if rel == "." else rel.replace(os.sep, "/") + "/"


def evidence_html(row: dict | None, prefix: str = "", maxn: int = 4) -> str:
    """Evidence cell: clickable link for emails/files, plain text for pointers."""
    parts = []
    for x in evidence_entries(row)[:maxn]:
        if x["href"]:
            href = x["href"] if x["kind"] == "link" else prefix + x["href"]
            parts.append(f"<a href='{esc(href)}'>{esc(x['label'][:70])}</a>")
        else:
            parts.append(esc(x["label"][:110]))
    extra = len(evidence_entries(row)) - maxn
    if extra > 0:
        parts.append(f"+{extra} more")
    return "; ".join(parts)


def evidence_text(row: dict | None) -> str:
    """CSV form: 'label <link>' or pointer text, separated by ' | '."""
    return " | ".join(f"{x['label']} <{x['href']}>" if x["href"] else x["label"] for x in evidence_entries(row))
