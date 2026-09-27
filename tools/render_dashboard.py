#!/usr/bin/env python3
"""Render the verdict-free single-file HTML dashboard from a day log.

  python3 render_dashboard.py DAYLOG.json OUT.html [--as-of YYYY-MM-DD] [--rules RULES.json] [--kb HMRC_MIRROR (default: <engine>/hmrc)]

Without --rules the country rules come from the user's own copy ($NOMAD_PRO_DATA/country-rules.json, else
~/nomad-pro-data/country-rules.json), else the engine's shipped schema/country-rules.json.

v3 layout (26 Sep 2026) mirrors the Nomad Pro iOS app dashboard (its dashboard screen
and components): location card, tax-year selector and a 3D teal status button, "Key metrics" KPI
progress cards, AlertCards, country doughnut, monthly bar tracks, location timeline rows, section headings outside
white cards on the warm #FAF7F2 background. Colour carries category, never an outcome (UK = app coral, Schengen =
teal, work = violet). One proximity scale everywhere: more than 20 days of room calm, 6-20 amber, 0-5 or over deep
ochre (dashboard_charts.band). Amber is otherwise only used for logging gaps.
L6 footer on every view, L8 on Schengen / stay-limit views. No surface states a residence outcome; the only
pointer wording is the engine's approved "Your log points to ..." line with its L4 source line.
Fully offline: CSS, JS, logo and the fallback font (Inter; Apple devices use SF like the app) are inlined from assets/.
"""
from __future__ import annotations

import argparse
import base64
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import srt_engine as E
from render_common import esc, last_logged, evidence_html, evidence_entries, file_prefix
import dashboard_charts as C

ASSETS = Path(__file__).resolve().parent / "assets"
SEP = " \u00b7 "
ARROW = " \u2192 "

TABS = [("overview", "Dashboard", "grid"), ("uk", "UK days", "moon"), ("schengen", "Schengen", "flag"),
        ("travel", "Travel", "map-pin"), ("work", "Work days", "briefcase"), ("ties", "Ties", "home"),
        ("daylog", "Day log", "calendar"), ("records", "Records", "file-text")]


def _asset(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def _font_css() -> str:
    f = ASSETS / "Inter-latin-var.woff2"
    if not f.exists():
        return ""
    b64 = base64.b64encode(f.read_bytes()).decode()
    return ("@font-face{font-family:'Inter NP';font-style:normal;font-weight:400 800;font-display:swap;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")


def _logo() -> str:
    f = ASSETS / "nomadpro-logo-96.png"
    return f"data:image/png;base64,{base64.b64encode(f.read_bytes()).decode()}" if f.exists() else ""


def sec(title, body, sub="", card="", cls="", head=""):
    """SectionHeading (outside) + SurfaceCard, as in the app."""
    sub_html = f"<span class='sub'>{sub}</span>" if sub else ""
    inner = f"<div class='card {card}'>{body}</div>" if body is not None else ""
    return f"<section class='sec {cls}'><div class='sh'><h2>{title}</h2>{sub_html}{head}</div>{inner}</section>"


def ordinal(d):
    n = d.day
    suf = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{d.strftime('%A')}, {n}{suf} {d.strftime('%B')}"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def info(tip):
    return f"<span class='info' data-tip='{esc(tip)}'>{C.icon('info', 16)}</span>"


def kpi(label, num, unit, foot, visual, acc, tip, attn=False, word=False, go=None):
    """KpiProgressCard: muted label, big coloured value, ring on the right, one detail line."""
    unit_html = f"<small> {esc(unit)}</small>" if unit else ""
    goattr = f" data-go='{go}'" if go else ""
    return (f"<div class='card kpi' style='--c:{acc}'{goattr}><div class='row'><div class='copy'><div class='lab'>{esc(label)} {info(tip)}</div>"
            f"<div class='val{' word' if word else ''}'>{esc(num)}{unit_html}</div></div>{visual}</div><div class='det'>{foot}</div></div>")


def dot(icon_name, colour, tint):
    return f"<div class='dot' style='background:{tint};color:{colour}'>{C.icon(icon_name, 22)}</div>"


def quick_read(used, room, drop, window_end):
    """Big quick-read figure next to the Schengen chart, coloured by the proximity band."""
    key, colour, label = C.band(room)
    chip = {"calm": "teal", "warn": "attn", "deep": "deep"}[key]
    room_txt = f"{room} days of room" if room >= 0 else f"{-room} days over 90"
    return (f"<div class='quick' style='--bc:{colour}'><div class='k'>Current status</div>"
            f"<div class='big'>{used} <small>days in the last 180</small></div><div class='room'>{room_txt}</div>"
            f"<span class='chip {chip}'>{esc(label)}</span>"
            f"<div class='drop'>Next drop-off: <b>{esc(drop)}</b><br><span class='small muted'>window to {esc(E.fmt_date(window_end))}</span></div>"
            f"<div class='bandkey'><span><i style='background:{C.PRIMARY}'></i>more than 20 days of room</span>"
            f"<span><i style='background:{C.AMBER}'></i>6-20 days of room</span><span><i style='background:{C.OCHRE}'></i>0-5 days of room</span></div></div>")


# ---------------------------------------------------------------- attention items: short line + full text in tooltip
def attention(ref: dict) -> list[tuple[str, str, bool]]:
    s, t, tt = ref["summary"], ref["ties"], ref["ties_test"]
    out = []
    if s["unlogged"]:
        out.append((f"{plural(s['unlogged'], 'day')} not logged", f"{s['unlogged']} days in {s['tax_year']} are not logged yet: {E.ranges(s['unlogged_dates'])}.", True))
    if s["no_pointer_dates"]:
        out.append((f"{plural(len(s['no_pointer_dates']), 'day')} without a record", f"{len(s['no_pointer_dates'])} logged days have no record pointer.", True))
    if tt.get("line") is not None and tt.get("room") is not None and tt["room"] <= 20:
        out.append((f"UK days {max(tt['room'], 0)} from {tt['line']}", f"Your UK midnights ({s['uk_midnights']}) are {max(tt['room'], 0)} away from {tt['line']}, a figure used in RDR3.", True))
    wt = ref["work_tie"]
    if wt["room"] <= 20:
        out.append((f"Work days {s['uk_work_days_over_3h']} of 40", f"UK work days logged: {s['uk_work_days_over_3h']}. RFIG20560 uses 40 days for the work tie.", True))
    ct = t["ties"]["country"]
    if ct.get("applies") and ct.get("top_other_country") and 0 <= ct["gap"] <= 20:
        out.append((f"UK nights {ct['gap']} behind {E.cname(ct['top_other_country'])}",
                    f"UK midnights ({s['uk_midnights']}) are within {ct['gap']} of your country with the most midnights ({E.cname(ct['top_other_country'])}, {ct['top_other_midnights']}). RFIG20580.", True))
    for y in t["ties"]["ninety_day"]["missing_years"]:
        out.append((f"UK days for {y} missing", f"Your 90-day-tie input depends on UK days in the two previous tax years; {y} isn't recorded.", True))
    if s["conflicts"]:
        unresolved = [c for c in s["conflicts"] if not c.get("resolution")]
        out.append((f"{plural(len(s['conflicts']), 'record')} disagree" + (" (resolved)" if not unresolved else ""),
                    " ".join(f"{E.fmt_date(c['date'])}: {c.get('detail', '')} Resolution: {c.get('resolution', 'none')}." for c in s["conflicts"]), bool(unresolved)))
    if s["uk_work_unsure"]:
        out.append((f"{plural(s['uk_work_unsure'], 'work day')} marked unsure", f"{s['uk_work_unsure']} UK days have work marked 'unsure': {E.ranges(s['uk_work_unsure_dates'])}.", True))
    if t["differ"]:
        out.append((f"{plural(len(t['differ']), 'tie answer')} to review", "Your answer and your log differ for: " + ", ".join(t["differ"]), True))
    return out


def attention_html(items):
    """AlertCard list: uppercase coloured title + one short body line."""
    if not items:
        return f"<div class='alerts'><div class='alert teal'><div class='at'>Nothing flagged {C.icon('check-circle', 18)}</div><p>Every item on this list is clear for this tax year.</p></div></div>"
    return "<div class='alerts'>" + "".join(
        f"<div class='alert {'amber' if a else 'info'}' data-tip='{esc(full)}'><div class='at'>{esc(short)} {C.icon('alert-circle' if a else 'info', 18)}</div><p>{esc(full if len(full) <= 150 else full[:140].rsplit(' ', 1)[0] + ' …')}</p></div>"
        for short, full, a in items) + "</div>"


# ---------------------------------------------------------------- per tax year views
def year_section(log, ty, as_of, planned, prefix, col):
    ref = E.srt_reference(log, ty, as_of)
    s, t, tt = ref["summary"], ref["ties"], ref["ties_test"]
    start, end = E.tax_year_bounds(ty)
    to = min(end, as_of)
    current = as_of <= end
    stays = E.stays(log, start, to)
    sch = E.rolling_status(log, to)
    items = list(s["countries"].items())
    unl = s["unlogged"]
    donut_items = items + ([("UNLOGGED", unl)] if unl else [])
    h = {}

    # ---- Key metrics (KpiProgressCard x4)
    uk = s["uk_midnights"]
    line = tt.get("line") if tt.get("line") is not None else 182
    room = tt.get("room", 182 - uk)
    uk_band = C.band(room)
    uk_col = C.CORAL if uk_band[0] == "calm" else uk_band[1]
    uk_near = room <= 20
    uk_foot = (f"<b>{room}</b> days of room before {line}" if room >= 0 else f"<b>{-room}</b> over {line}")
    ties_label = f"{plural(tt['recorded_ties'], 'tie')} recorded" if tt.get("table") else "table not set"
    uk_tip = (f"UK midnights in {ty}, counted to {E.fmt_date(to)} (midnight rule, {E.cite('RFIG20710')}). "
              f"Your line: {line} = RDR3 Table {tt.get('table') or '?'} day figure for {ties_label} ({E.cite('RFIG20520')}). Reference only.")
    k_uk = kpi("UK days", uk, f"/ {line}", uk_foot, C.ring(uk, line, uk_col, tip=uk_tip), uk_col, uk_tip, go="uk")
    drop = E.fmt_date(sch["earliest_drop_off"]) if sch["earliest_drop_off"] else "none"
    sch_band = C.band(sch["room"])
    sch_tip = f"Days in Schengen (any part of a day) in the 180 days to {E.fmt_date(to)}. The next day drops out of the window on {drop}. {E.L8}"
    k_sch = kpi("Schengen, last 180", sch["used"], "/ 90", f"<b>{sch['room']}</b> days of room{SEP}drop-off {esc(drop)}",
                C.ring(sch["used"], 90, sch_band[1], tip=sch_tip), sch_band[1], sch_tip, go="schengen")
    wd = s["uk_work_days_over_3h"]
    wroom = 40 - wd
    w_band = C.band(wroom)
    w_col = C.VIOLET if w_band[0] == "calm" else w_band[1]
    w_near = ref["work_tie"]["room"] <= 20
    unsure = f" <span class='chip attn'>{s['uk_work_unsure']} unsure</span>" if s["uk_work_unsure"] else ""
    w_tip = f"UK days with more than 3 hours of work. RFIG20560 uses 40 days for the work tie; RFIG20140 uses 31 for the third automatic overseas test."
    k_work = kpi("UK work days", wd, "/ 40", f"<b>{max(wroom, 0)}</b> days of room before 40{unsure}", C.ring(wd, 40, w_col, tip=w_tip), w_col, w_tip, go="work")
    if unl:
        log_tip = f"{unl} of {s['days_in_year_to_date']} days so far in {ty} have no entry: {E.ranges(s['unlogged_dates'])}. Gaps are never guessed."
        k_log = kpi("Logging", f"{plural(unl, 'day')} missing", "", f"Tap to catch up{SEP}to {E.fmt_date(to)}",
                    dot("alert-circle", "#B07A12", "#FFF7E8"), "#8A5A00", log_tip, word=True, go="daylog")
        status_btn = (f"<div class='btn3d warn' data-go='daylog' data-tip='{esc(log_tip)}'>{C.icon('alert-circle', 22)}<b>{plural(unl, 'day')} missing</b>"
                      f"<small>Tap to catch up</small></div>")
    else:
        log_tip = f"All {s['days_in_year_to_date']} days from {E.fmt_date(start)} to {E.fmt_date(to)} have an entry."
        k_log = kpi("Logging", "All days logged", "", f"Every day to {E.fmt_date(to)}", dot("check-circle", C.PRIMARY, "#F0FBF8"), C.PRIMARY,
                    log_tip, word=True, go="daylog")
        status_btn = (f"<div class='btn3d' data-go='daylog' data-tip='{esc(log_tip)}'>{C.icon('check-circle', 22)}<b>All days logged</b>"
                      f"<small>Recorded to {E.fmt_date(to)}</small></div>")
    h["status"] = status_btn
    hero = sec("Key metrics", f"<div class='grid k4'>{k_uk}{k_sch}{k_work}{k_log}</div>", sub=f"{ty}{SEP}to {E.fmt_date(to)}", card=None).replace("<div class='card None'>", "<div>")

    total_logged = sum(v for _, v in items)
    donut = (f"<div class='donut-wrap'>{C.donut(donut_items, col, centre=str(total_logged + unl), centre_sub='days')}"
             f"{C.legend(donut_items, col, total=total_logged + unl, limit=7)}</div>")
    key = "".join(f"<span><i style='background:{col(c)}'></i>{esc(E.cname(c))}</span>" for c, _ in items[:8])
    if unl:
        key += f"<span><i style='background:{C.GAP_FILL};box-shadow:inset 0 0 0 2px {C.AMBER}'></i>Not logged</span>"
    monthly = C.monthly_stacked(log, start, to, col, full_end=end if current else None)
    tl_end = end if current else to
    tl_short = C.timeline_rows(stays, start, to, col, today=as_of if current else None, max_rows=6)
    tl_full = C.timeline_rows(stays, start, tl_end, col, today=as_of if current else None,
                              planned=[p for p in planned if p["from"] <= end.isoformat()] if current else ())
    sch_series = E.schengen_series(log, to - timedelta(days=179), to)
    att = attention(ref)
    n_attn = sum(1 for _, _, a in att if a)
    dbc = sec("Days by country", donut, sub="counted by where you were at midnight")
    h["overview"] = f"""{hero}
<div class='g21'>{sec("Days by month", f"<div class='scroll'>{monthly}</div><div class='key'>{key}</div>", sub="UK at the base of each bar")}{dbc}</div>
<div class='g21'>{sec("Location timeline", tl_short, sub=f"latest {min(6, len(stays))} of {plural(len(stays), 'stay')}", head="<span class='pill' data-go='travel'>See all</span>")}
{sec("Alerts", attention_html(att), sub=plural(n_attn, 'item') + ' to check', card='muted' if att else '')}</div>
{sec("Schengen, last 180 days", f"<div class='g21'><div class='scroll'>{C.area(sch_series, 90, C.PRIMARY, width=640, height=250, ymax=100, fmt='{v} of 90 Schengen days', aria='Schengen days in the rolling 180-day window', bands=True)}</div>{quick_read(sch['used'], sch['room'], drop, to)}</div><p class='small muted'>{esc(E.L8)}</p>", sub=f"{sch['used']} of 90")}"""

    # ---- UK days
    cum, n = [], 0
    for d in E.daterange(start, to):
        r = log.row(d)
        n += 1 if (r and r["midnight_country"] == "GB") else 0
        cum.append((d.isoformat(), n))
    ptrs = "".join(f"<div class='pointer'><b>{esc(l['text'])}</b><div class='disc'>{esc(l['disclaimer'])}</div></div>" for l in ref["stage_lines"])
    notes = "".join(f"<li>{esc(x)}</li>" for x in ref["notes"])
    uk_stays = [x for x in stays if x["country"] == "GB"]
    rows = []
    for x in uk_stays:
        a, b = E.parse_date(x["from"]), E.parse_date(x["to"])
        wdn = sum(1 for d in s["uk_work_dates"] if x["from"] <= d <= x["to"])
        accs = sorted({(log.days[d].get("accommodation_label") or log.days[d].get("accommodation_id") or "-") for d in E.daterange(a, b)})
        rows.append(f"<tr><td>{E.fmt_date(a)}</td><td>{E.fmt_date(b)}</td><td class='n'>{x['nights']}</td><td class='n'>{wdn}</td><td>{esc(', '.join(accs))}</td><td class='ptr'>{esc('; '.join(x['pointers'])[:160])}</td></tr>")
    accn = "".join(f"<tr><td>{esc(p['label'])}</td><td>{esc((p['relationship'] or '').replace('_', ' '))}</td><td class='n'>{p['nights']}</td><td>{p['nights_needed']}+</td><td>{esc(p['available_91_days_answer'].replace('_', ' '))}</td></tr>" for p in t["ties"]["accommodation"]["places"])
    nd = ref["ninety_day_next_year"]
    mini = (f"<div class='stats'><div class='stat'><b>{uk}</b><span>UK days</span></div><div class='stat{' attn' if uk_near else ''}'><b>{max(room, 0)}</b><span>days of room before {line}</span></div>"
            f"<div class='stat'><b>{tt.get('recorded_ties', '-')}</b><span>ties recorded</span></div><div class='stat'><b>{esc(tt.get('table') or '-')}</b><span>RDR3 table</span></div>"
            f"<div class='stat'><b>{len(uk_stays)}</b><span>UK visits</span></div></div>")
    h["uk"] = f"""<div class='grid'><section class='card'><h2>UK days so far {info(uk_tip)}<span class='sub'>counted to {E.fmt_date(to)}</span></h2>{mini}
<div class='scroll' style='margin-top:10px'>{C.area(cum, line, C.CORAL, height=260, label_line=str(line), fmt='{v} UK days', x_end=end.isoformat() if current else None, ymax=max(line + 12, uk + 10), aria='Cumulative UK days this tax year', bands=True)}</div>
<div class='key'><span><i style='background:{C.PRIMARY}'></i>UK days, running total (colour shows room left)</span><span><i style='background:{C.INK};height:3px'></i>your line ({line}, {esc(ties_label)})</span></div></section></div>
<div class='grid g11'><section class='card'><h2>Reference</h2>{ptrs}<p class='small'>{esc(tt.get('band_text', ''))}</p><p class='small'>Next year: {esc(nd['text'])}.</p>
<details><summary>How this is counted</summary><ul class='small'>{notes}</ul><p class='small muted'>{esc(tt.get('table_reason', ''))}. Boundaries follow HMRC's wording ("more than 120"), {esc(E.cite('RFIG20520'))}; {esc(nd['cite'])}.</p></details></section>
<section class='card'><h2>RDR3 day figures <span class='sub'>tap a tick for the HMRC page</span></h2><div class='scroll'>{C.figure_line(uk, ref['figures'], tt.get('line'))}</div>
<p class='small muted'>A count from your entries. It does not determine residence.</p></section></div>
<section class='card mb'><h2>UK visits <span class='sub'>{plural(len(uk_stays), 'visit')}</span></h2><div class='tbl'><table><tr><th>First night</th><th>Last night</th><th>Nights</th><th>Work days</th><th>Stayed at</th><th>Evidence</th></tr>{''.join(rows) or "<tr><td colspan=6 class='muted'>No UK midnights logged.</td></tr>"}</table></div>
<details><summary>Nights per UK place (accommodation tie inputs, {esc(E.cite('RFIG20550'))})</summary><div class='tbl'><table><tr><th>Place</th><th>Relationship</th><th>Nights</th><th>Figure used</th><th>Available 91+ days (your answer)</th></tr>{accn}</table></div>
<p class='small muted'>Transit-flagged days: {len(s['transit_flag_dates'])} (recorded, {esc(E.cite('RFIG20730'))}; not applied). UK days without a UK midnight: {len(s['qualifying_days_not_midnight'])} ({esc(E.cite('RFIG20720'))}).</p></details></section>"""

    # ---- Travel (per year part)
    hb = "".join(f"<li><i style='background:{col(c)}'></i><span>{esc(E.cname(c))}</span><b>{v}d</b><em>{100 * v / max(total_logged, 1):.0f}%</em></li>" for c, v in items[:12])
    srows = "".join(f"<tr{' class=gap' if x['country'] == 'UNLOGGED' else ''}><td><i style='display:inline-block;width:10px;height:10px;border-radius:3px;background:{col(x['country']) if x['country'] != 'UNLOGGED' else C.AMBER};margin-right:8px'></i>{esc(C.cn(x['country']))}</td><td>{esc(x.get('place') or '')}</td><td>{E.fmt_date(x['from'])}</td><td>{E.fmt_date(x['to'])}</td><td class='n'>{x['nights']}</td></tr>"
                    for x in reversed(stays))
    h["travel"] = f"""<div class='g21'>{sec("Location timeline", tl_full, sub=f"{ty}{SEP}{plural(len(stays), 'stay')}, newest first")}
{sec("Days by country", donut, sub="counted by where you were at midnight")}</div>
<div class='grid'>
<section class='card'><h2>Stays <span class='sub'>{plural(len(stays), 'stay')}, newest first</span></h2><div class='tbl' style='max-height:360px;overflow:auto'><table><tr><th>Country</th><th>Place</th><th>First night</th><th>Last night</th><th>Nights</th></tr>{srows}</table></div></section></div>"""

    # ---- Work
    mon = []
    d = date(start.year, start.month, 1)
    lastm = end if current else to
    while d <= lastm:
        key_m = f"{d.year}-{d.month:02d}"
        mon.append((f"{E.MONTHS[d.month - 1]} {d.year}", sum(1 for x in s["uk_work_dates"] if x.startswith(key_m)), sum(1 for x in s["uk_work_unsure_dates"] if x.startswith(key_m))))
        d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    wrows = "".join(f"<tr><td>{E.fmt_date(x)}</td><td>{esc((log.days[E.parse_date(x)].get('uk_work') or {}).get('over_3h'))}</td><td>{esc((log.days[E.parse_date(x)].get('uk_work') or {}).get('hours') or '-')}</td><td class='ptr'>{esc((log.days[E.parse_date(x)].get('uk_work') or {}).get('note'))}</td></tr>" for x in sorted(s["uk_work_dates"] + s["uk_work_unsure_dates"], reverse=True))
    third = ref["third_automatic_overseas"]
    w_rules = E.rules_in_force(log, start, to)
    w_rep = E.work_rule_report(log, ty, to)
    w_c = w_rep["counts"]
    if w_rules:
        w_q = "".join(f"<blockquote class='rule'>\u201c{esc(r.get('wording_shown'))}\u201d</blockquote><p class='small muted'>Rule {esc(r.get('id'))}{SEP}in force {esc(E.fmt_date(r['effective_from']))} to {esc(E.fmt_date(r['effective_to']) if r.get('effective_to') else 'today')}{SEP}agreed {esc(E.fmt_date(r.get('agreed_at')))}, {esc(r.get('agreed_via'))}" + (f"{SEP}<span class='chip attn'>to confirm: {esc(', '.join(x.replace('_', ' ') for x in r.get('to_confirm')))}</span>" if r.get('to_confirm') else "") + "</p>" for r in w_rules)
        w_src = f"<p class='small'>UK days set by the rule <b>{w_c.get('rule', 0)}</b>{SEP}calendar exceptions <b>{w_c.get('rule_exception', 0)}</b>{SEP}your answers <b>{w_c.get('user_answer', 0)}</b>" + (f"{SEP}not asked <b>{w_c.get('not_asked', 0)}</b>" if w_c.get('not_asked') else "") + (f"{SEP}no source <b>{w_c.get('unrecorded', 0)}</b>" if w_c.get('unrecorded') else "") + "</p><p class='small muted'>Your own answer for a day always takes priority over the rule.</p>"
        w_dis = (f"<div class='alert attn-soft'><b>{plural(len(w_rep['disagree']), 'day')} differ from your rule:</b> " + esc(E.ranges([x['date'] for x in w_rep['disagree']])) + ". Keep the log as it is, or follow the rule?</div>") if w_rep["disagree"] else ""
        rule_card = f"<section class='card mb'><h2>Work-day rule <span class='sub'>how work days are set, as you agreed</span></h2>{w_q}{w_src}{w_dis}</section>"
    else:
        rule_card = "<section class='card mb'><h2>Work-day rule</h2><p class='small muted'>No rule agreed yet: every UK day is asked. Agree one in plain words (for example, weekends off, weekdays in the UK are work days unless your calendar says sick) and the check-in will only ask about exceptions.</p></section>"
    h["work"] = f"""<div class='grid k3'>
{kpi('UK work days', wd, '/ 40', f"<b>{max(wroom, 0)}</b> days of room before 40", C.ring(wd, 40, w_col, tip=w_tip), w_col, w_tip)}
{kpi('Marked unsure', s['uk_work_unsure'], '', 'answer these to complete the record' if s['uk_work_unsure'] else 'none to answer', dot('alert-circle', '#B07A12', '#FFF7E8') if s['uk_work_unsure'] else dot('check-circle', C.MUTED, '#F4EEE5'), '#8A5A00' if s['uk_work_unsure'] else C.INK_2, 'Days in the UK where you marked more than 3 hours of work as unsure. RFIG20740 explains what counts as work.', attn=bool(s['uk_work_unsure']))}
{kpi('Left before 31', max(third['work_room'] + 1, 0), 'days', f"31 = third automatic overseas test figure ({esc(E.cite('RFIG20140'))})", '', C.INK_2, 'Full-time overseas work is your own recorded answer: ' + third['full_time_claim'].replace('_', ' ') + '. Not calculated.')}
</div>
<div class='grid g21'><section class='card'><h2>Work days per month</h2><div class='scroll'>{C.columns([(l, v) for l, v, _ in mon], colour=C.VIOLET, unsure=[u for _, _, u in mon])}</div>
<div class='key'><span><i style='background:{C.VIOLET}'></i>more than 3 hours</span><span><i style='background:{C.GAP_FILL};box-shadow:inset 0 0 0 2px {C.AMBER}'></i>unsure</span></div></section>
<section class='card'><h2>Against HMRC figures</h2><div style='padding:0 6px'>{C.meter(wd, 40, w_col, [(31, '31 days: third automatic overseas test, ' + E.cite('RFIG20140')), (40, '40 days: work tie, ' + E.cite('RFIG20560'))], attn=w_near)}</div>
<p class='small'><b>{wd}</b> logged{SEP}31 and 40 are figures HMRC uses.</p><p class='small muted'>Hours are shown only when you gave a number; nothing is defaulted.</p></section></div>
{rule_card}<section class='card mb'><h2>Work day list <span class='sub'>{plural(len(s['uk_work_dates']) + len(s['uk_work_unsure_dates']), 'day')}</span></h2>
<details><summary>Show every work day</summary><div class='tbl'><table><tr><th>Date</th><th>More than 3 hours</th><th>Hours</th><th>Note</th></tr>{wrows or "<tr><td colspan=4 class='muted'>No UK work days logged.</td></tr>"}</table></div></details></section>"""

    # ---- Ties
    icons = {"family": "family", "accommodation": "home", "work": "work", "ninety_day": "calendar", "country": "flag"}
    names = {"family": "Family", "accommodation": "Accommodation", "work": "Work", "ninety_day": "90-day", "country": "Country"}
    chips = []
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
        tip = f"{names[k]} tie · {v['cite']}. Your answer: {v['user_answer'].replace('_', ' ')}. Your log shows: {v['log_shows']}. Status: {st}."
        chips.append(f"<div class='tie {cls}' data-tip='{esc(tip)}'><div class='ico'>{C.icon(icons[k], 22)}</div><div class='nm'>{names[k]}</div><div class='st'>{word}</div><div class='rf'>{esc(v['ref'])}</div></div>")
    trs = "".join(f"<tr><td>{names[k]}</td><td>{esc(v['user_answer'].replace('_', ' '))}</td><td>{esc(v['log_shows'])}</td><td>{esc(log.year_config(ty).get('tie_answers_reviewed_at', '-'))}</td><td>{esc(v['cite'])}</td><td><span class='chip{' attn' if 'differ' in v['status'] or 'Not answered' in v['status'] else ''}'>{esc(v['status'])}</span></td></tr>" for k, v in t["ties"].items())
    band_line = f"RDR3 Table {tt['table']} pairs {t['recorded_count']} recorded tie{'s' if t['recorded_count'] != 1 else ''} with {esc(tt.get('room_text', ''))}." if tt.get("table") else ""
    h["ties"] = f"""<section class='card mb'><h2>Your UK ties <span class='sub'>{ty}{SEP}tap a tie for detail</span></h2><div class='ties'>{''.join(chips)}</div>
<div class='key' style='margin-top:16px'><span><i style='background:{C.PRIMARY}'></i>On = recorded yes</span><span><i style='background:#fff;border:2px solid {C.BORDER}'></i>Off = recorded no</span><span><i style='background:#fff;border:2px dashed {C.BORDER}'></i>Not answered</span><span><i style='background:{C.AMBER}'></i>Your answer and log differ</span></div></section>
<div class='grid k3'><div class='card'><div class='stat' style='background:none;padding:0'><span>Ties recorded</span><b style='font-size:40px'>{t['recorded_count']}</b></div></div>
<div class='card'><div class='stat' style='background:none;padding:0'><span>RDR3 table</span><b style='font-size:40px'>{esc(tt.get('table') or '-')}</b></div><div class='small muted'>{esc(tt.get('table_reason', ''))}</div></div>
<div class='card'><div class='stat' style='background:none;padding:0'><span>Your day line</span><b style='font-size:40px'>{line}</b></div><div class='small muted'>{esc(tt.get('room_text', ''))}</div></div></div>
<section class='card mb'><h2>Answers and what your log shows</h2><p class='small'>{band_line} (reference only)</p>
<details><summary>Show the full table</summary><div class='tbl'><table><tr><th>Tie</th><th>Your answer</th><th>What your log shows</th><th>Last reviewed</th><th>HMRC page</th><th>Status</th></tr>{trs}</table></div>
<p class='small muted'>Your own answers are kept alongside what the log shows. If they differ, the row says so; nothing is overwritten.</p></details></section>"""

    # ---- Day log (health + calendar + table)
    def lst(dates):
        return esc(E.ranges(dates)) if dates else "<span class='muted'>none</span>"
    edits = [(r["date"], c) for r in (log.days[E.parse_date(x)] for x in s["edited_dates"]) for c in r.get("changes", [])]
    drows, n_link = [], 0
    for d in sorted(E.daterange(start, to), reverse=True):
        r = log.days.get(d) or {}
        lr = log.row(d)
        ents = evidence_entries(r)
        n_link += any(x["href"] for x in ents)
        w = (r.get("uk_work") or {}).get("over_3h")
        also = ", ".join(E.cname(c) for c in log.present(d)) if lr and len(log.present(d)) > 1 else ""
        drows.append(f"<tr{'' if lr else ' class=gap'}><td>{d.strftime('%a')} {E.fmt_date(d)}</td><td>{esc(E.cname(lr['midnight_country']) if lr else 'Not logged')}</td>"
                     f"<td>{esc(r.get('midnight_place', ''))}</td><td>{esc(also)}</td><td>{esc(w if w not in (None, 'n/a') else '')}</td>"
                     f"<td>{esc(r.get('confidence', 'unlogged'))}</td><td class='ptr'>{evidence_html(r, prefix, 4) or '<span class=muted>none</span>'}</td></tr>")
    qs = E.open_questions(log, ty, as_of)
    stats = (f"<div class='stats'><div class='stat'><b>{s['logged']}</b><span>days logged</span></div>"
             f"<div class='stat{' attn' if unl else ''}'><b>{unl}</b><span>not logged</span></div>"
             f"<div class='stat{' attn' if s['no_pointer_dates'] else ''}'><b>{len(s['no_pointer_dates'])}</b><span>no record</span></div>"
             f"<div class='stat'><b>{len(s['inferred_dates'])}</b><span>inferred</span></div><div class='stat'><b>{len(s['attested_dates'])}</b><span>own statement</span></div>"
             f"<div class='stat'><b>{n_link}</b><span>with a link</span></div></div>")
    h["daylog"] = f"""<section class='card mb'><h2>Every day of {ty} <span class='sub'>colour = country at midnight{SEP}dot = UK work</span></h2>{stats}<div class='scroll' style='margin-top:14px'>{C.calendar(log, start, end if current else to, col, today=as_of if current else None)}</div><div class='key'>{key}</div>
<details><summary>Log health detail</summary><div class='tbl'><table>
<tr><th>Not yet logged</th><td>{lst(s['unlogged_dates'])}</td></tr><tr><th>No record pointer</th><td>{lst(s['no_pointer_dates'])}</td></tr>
<tr><th>Marked inferred</th><td>{lst(s['inferred_dates'])}</td></tr><tr><th>Own statement</th><td>{lst(s['attested_dates'])}</td></tr>
<tr><th>Conflicts</th><td>{''.join(f"<div>{esc(E.fmt_date(c['date']))}: {esc(c.get('detail'))} <span class='ptr'>Resolution: {esc(c.get('resolution'))} ({esc(c.get('resolved_by'))}, {esc(c.get('resolved_at'))})</span></div>" for c in s['conflicts']) or "<span class='muted'>none</span>"}</td></tr>
<tr><th>Edits after the day</th><td>{''.join(f"<div>{esc(E.fmt_date(d))}: {esc(c.get('field'))} {esc(c.get('from'))}{ARROW}{esc(c.get('to'))} <span class='ptr'>{esc(c.get('reason'))}</span></div>" for d, c in edits) or "<span class='muted'>none</span>"}</td></tr></table></div>
<p class='small'><b>Questions HMRC could ask about this year</b></p><ul class='small'>{''.join(f'<li>{esc(q)}</li>' for q in qs) or '<li>None.</li>'}</ul>
<p class='small muted'>Catch up missed days in one go: tell the bot where you were and it fills every gap from your answers. Gaps are never guessed.</p></details></section>
<section class='card mb'><h2>Day log and records <span class='sub'>newest first</span></h2><input class='f' id='f-{ty.replace('/', '')}' placeholder='Filter (e.g. Lisbon, Aug)' oninput="filt(this)">
<div class='tbl' style='max-height:560px;overflow:auto'><table class='dl'><tr><th>Date</th><th>Midnight</th><th>Place</th><th>Also present</th><th>UK work >3h</th><th>Confidence</th><th>Evidence</th></tr>{''.join(drows)}</table></div></section>"""
    return ref, h


def render(log: E.DayLog, as_of: date, rules: list[dict], prefix: str = "", documents: list | None = None) -> str:
    years = log.tracked_years(as_of)
    cur = E.tax_year_of(as_of)
    if cur not in years and years:
        cur = years[-1]
    last = last_logged(log, as_of)
    planned = [p for p in log.planned if p.get("status") in ("idea", "booked") and p["to"] >= as_of.isoformat()]
    col = C.Colours(log)
    per_year = {ty: year_section(log, ty, as_of, planned, prefix, col) for ty in years}

    def year_views(key):
        return "".join(f"<div class='year{' on' if ty == cur else ''}' data-v='{ty}'>{per_year[ty][1][key]}</div>" for ty in years)

    # ---- Schengen & stay limits (as of today, with booked trips)
    sch = E.rolling_status(log, as_of)
    after = E.apply_trips(log, planned) if planned else log
    horizon = max([E.parse_date(p["to"]) + timedelta(days=1) for p in planned] + [as_of])
    series = E.schengen_series(after, as_of - timedelta(days=364), horizon)
    lim = E.country_limit_status(log, as_of, rules)
    lim_cards = []
    for x in lim:
        if x.get("zone") == "SCHENGEN":
            continue
        if x.get("used") is not None:
            v, sub, used, lim_n = f"{x['used']} / {x['limit']}", f"days in the rolling {180} days", x["used"], x["limit"]
        elif x.get("in_country"):
            v, sub, used, lim_n = f"Day {x['days_used']} / {x['limit']}", f"since entry {E.fmt_date(x['entry'])}{SEP}limit to {E.fmt_date(x['last_day_of_limit'])}", x["days_used"], x["limit"]
        else:
            v, sub, used, lim_n = f"{x['limit']} days", "per entry (not in country)", 0, x["limit"]
        extra = ""
        over_entries = x.get("entries_this_year") and len(x["entries_this_year"]) > x.get("max_entries", 99)
        if x.get("entries_this_year") is not None and (x.get("in_country") or x.get("entries_this_year")):
            n = len(x["entries_this_year"])
            extra = f"<div style='margin-top:6px'><span class='chip{' attn' if n > x['max_entries'] else ''}' data-tip='GOV.UK: normally {x['max_entries']} visa-exempt entries per calendar year'>{n} entries in {as_of.year}</span></div>"
        attn = (x.get("room") is not None and x["room"] <= 7) or over_entries
        bar = f"<div class='meter' style='margin:10px 0 4px;height:8px'><span style='width:{min(100, 100 * used / max(lim_n, 1)):.0f}%;background:{C.AMBER if attn else C.INK_2}'></span></div>" if used else ""
        lim_cards.append(f"<div class='limit{' attn' if attn else ''}'><div class='t'>{esc(x['name'])}</div><div class='v'>{esc(v)}</div>{bar}<div class='s'>{esc(sub)}</div>{extra}"
                         f"<div class='s' style='margin-top:6px'><a href='{esc(x['source_url'])}'>GOV.UK</a>{SEP}checked {esc(E.fmt_date(x['last_verified']))}</div></div>")
    proj = []
    res = E.plan(log, planned, as_of, rules) if planned else None
    if res:
        for st in res["limits_at_trip_end"]:
            proj.append(f"<li>{esc(st['trip'])}: if this trip goes ahead as booked, {esc(st.get('text') or '')}</li>")
    drop = E.fmt_date(sch["earliest_drop_off"]) if sch["earliest_drop_off"] else "none"
    stay = E.max_stay_from(log, as_of + timedelta(days=1))
    sch_tip = f"Any part of a day in a Schengen country counts, including entry and exit days. Window: {E.fmt_date(sch['window_start'])} to {E.fmt_date(as_of)}. {E.L8}"
    sch_band = C.band(sch["room"])
    booked_note = ""
    if planned:
        peak = max((v for d, v in series if d > as_of.isoformat()), default=sch["used"])
        booked_note = f"<p class='small'>With your booked trips the count peaks at <b>{peak}</b> of 90 ({90 - peak} days of room). Booked days are hatched grey; the dashed line is the projection.</p>"
    schengen_html = f"""<div class='grid k3 sec'>
{kpi('Schengen, last 180', sch['used'], '/ 90', f"<b>{sch['room']}</b> days of room to {E.fmt_date(as_of)}", C.ring(sch['used'], 90, sch_band[1], tip=sch_tip), sch_band[1], sch_tip)}
{kpi('Next drop-off', drop, '', "first counted day to leave the window", dot('calendar', C.PRIMARY, '#F0FBF8'), C.INK, 'The earliest date one of your counted Schengen days falls out of the rolling 180-day window.', word=True)}
{kpi('Longest stay', stay, 'days', 'if you entered tomorrow', dot('navigation', C.PRIMARY, '#F0FBF8'), C.INK, 'Longest continuous Schengen stay starting tomorrow before the 180-day window would go over 90 days, on your log as it stands.')}
</div>
{sec("Schengen days in the rolling 180-day window", f"""<div class='g21 sch'><div><div class='scroll'>{C.area(series, 90, C.PRIMARY, width=720, height=300, ymax=100, planned_from=as_of.isoformat() if planned else None, today=as_of.isoformat(), fmt='{v} of 90 Schengen days', aria='Schengen days in the rolling 180-day window', bands=True)}</div>
<div class='key'><span><i style='background:linear-gradient(90deg,{C.PRIMARY},{C.AMBER},{C.OCHRE})'></i>days in the window, coloured by room left</span><span><i style='background:repeating-linear-gradient(45deg,#F4EEE5 0 3px,#D4CFC7 3px 5px)'></i>booked trips</span><span><i style='background:{C.INK};height:3px'></i>90-day limit</span></div>
{booked_note}</div>{quick_read(sch['used'], sch['room'], drop, as_of)}</div>
<p class='small muted'>Cyprus is counted separately until its Schengen accession takes effect. {esc(sch['text'])}</p><p class='small'><b>{esc(E.L8)}</b></p>""", sub=f"last 12 months{' + booked trips' if planned else ''}")}
{sec("Other stay limits", f"<div class='trips'>{''.join(lim_cards)}</div>" + (f"<details><summary>If booked trips go ahead</summary><ul class='small'>{''.join(proj)}</ul></details>" if proj else '') + f"<p class='small'><b>{esc(E.L8)}</b></p>", sub="visa-free stays on your passport")}"""

    # ---- Travel (global part: booked trips, rules, watch)
    tcards = "".join(f"<div class='trip'><span class='sw' style='background:{col(p['country'])}'></span><div><b>{esc(E.cname(p['country']))}</b><span>{E.fmt_date(p['from'])} – {E.fmt_date(p['to'])}{SEP}{plural((E.parse_date(p['to']) - E.parse_date(p['from'])).days + 1, 'night')}</span><div style='margin-top:6px'><span class='chip teal'>{esc(p['status'])}</span>{(' <span class=ptr>' + esc(p.get('place')) + '</span>') if p.get('place') else ''}</div></div></div>" for p in planned)
    plan_years = "".join(f"<li>{esc(y['tax_year'])}: UK midnights {y['uk_midnights_before']}{ARROW}{y['uk_midnights_with_plan']} with these trips; {esc(y['ties_test_with_plan'].get('room_text') or '')}.</li>" for y in (res["years"] if res else []))
    watch = "".join(f"<tr><td>{esc(w.get('checked_at'))}</td><td>{esc(w.get('zone'))}</td><td>{esc(w.get('finding'))}</td><td>{'changed' if w.get('changed') else 'no change'}</td></tr>" for w in log.data.get("rule_watch_log", []))
    rules_rows = "".join(f"<tr><td>{esc(r['name'])}</td><td>{r['limit_days']} days {'in any ' + str(r['window_days']) if r['rule'] == 'rolling' else 'per entry'}</td><td>any part of a day</td><td><a href='{esc(r['source_url'])}'>GOV.UK</a> (updated {esc(r.get('source_updated'))})</td><td>{esc(r['last_verified'])}</td></tr>" for r in rules)
    oq = "".join(f"<li>{esc(q['text'])}</li>" for q in log.data.get("open_questions", []) if q.get("status") == "open")
    travel_global = f"""<section class='card mb'><h2>Coming up <span class='sub'>{plural(len(planned), 'booked trip')}</span></h2><div class='trips'>{tcards or "<p class='muted'>No upcoming trips recorded.</p>"}</div>
{f"<ul class='small' style='margin-top:14px'>{plan_years}</ul>" if plan_years else ''}
<details><summary>Country rules and rule watch</summary><div class='tbl'><table><tr><th>Zone</th><th>Limit</th><th>Counting</th><th>Source</th><th>Checked</th></tr>{rules_rows}</table></div>
<div class='tbl'><table><tr><th>Checked</th><th>Zone</th><th>Finding</th><th></th></tr>{watch or "<tr><td colspan=4 class='muted'>No findings recorded yet.</td></tr>"}</table></div><p class='small'>{esc(E.L8)}</p></details>
{f"<details><summary>Open questions</summary><ul class='small'>{oq}</ul></details>" if oq else ''}</section>"""

    # ---- Records
    srcs = "".join(f"<span class='chip teal'>{esc(e.get('label'))}</span> " for e in log.profile.get("evidence_sources", []))
    ptr_counts = Counter()
    for r in log.days.values():
        for e in r.get("evidence", []):
            if e.get("pointer"):
                ptr_counts[e["pointer"]] += 1
    idx = "".join(f"<tr><td class='ptr'>{esc(p)}</td><td class='n'>{n}</td></tr>" for p, n in ptr_counts.most_common(40))
    docs = documents or []

    def doc_link(x):
        if x.get("file"):
            return f"<a href='{esc(prefix + x['file'])}'>{esc(x['file'].split('/')[-1])}</a>"
        if x.get("url"):
            return f"<a href='{esc(x['url'])}'>link</a>"
        return esc(x.get("pointer") or "")
    drows = "".join(f"<tr><td>{esc(x.get('title'))}</td><td>{esc(x.get('type', '').replace('_', ' '))}</td><td>{esc(', '.join(x.get('tax_years', [])))}</td><td class='ptr'>{doc_link(x)}</td><td>{esc(x.get('status', '').replace('_', ' '))}</td><td>{esc(x.get('date_added'))}</td></tr>" for x in docs)
    n_days_ev = sum(1 for r in log.days.values() if r.get("evidence"))
    records_html = f"""<div class='grid k3'><div class='card'><div class='stat' style='background:none;padding:0'><span>Record sources</span><b style='font-size:40px'>{len(log.profile.get('evidence_sources', []))}</b></div></div>
<div class='card'><div class='stat' style='background:none;padding:0'><span>Days with a record</span><b style='font-size:40px'>{n_days_ev}</b></div></div>
<div class='card'><div class='stat' style='background:none;padding:0'><span>Status documents</span><b style='font-size:40px'>{len(docs)}</b></div></div></div>
<section class='card mb'><h2>Record sources</h2><div>{srcs or "<span class='muted'>None recorded.</span>"}</div>
<details><summary>Record pointer index (top 40)</summary><div class='tbl'><table><tr><th>Pointer</th><th>Days</th></tr>{idx}</table></div></details></section>
<section class='card mb'><h2>Status documents <span class='sub'>filing records it; it decides nothing</span></h2><div class='tbl'><table><tr><th>Document</th><th>Type</th><th>Tax years</th><th>File, link or pointer</th><th>Status</th><th>Added</th></tr>{drows or "<tr><td colspan=6 class='muted'>No documents filed yet.</td></tr>"}</table></div></section>
<section class='card mb'><h2>Export</h2><p>Ask the bot for <b>"Travel and day log"</b> for any tax year (PDF + CSV), or a <b>Records pack</b> (one zip: day log PDF and CSV per year, an index linking each day to its records, your files and status documents).</p>
<details><summary>What the export contains</summary><p class='small muted'>Your counts, stays, UK days, UK work days, ties as you recorded them with HMRC page references, record pointers per day, gaps and the counting method. Produced automatically after 5 April for the year just ended, and on request at any time.</p></details></section>"""

    views = {"overview": year_views("overview"), "uk": year_views("uk"), "schengen": schengen_html,
             "travel": year_views("travel") + travel_global, "work": year_views("work"), "ties": year_views("ties"),
             "daylog": year_views("daylog"), "records": records_html}
    body = "".join(f"<div class='view{' on' if k == 'overview' else ''}' data-v='{k}'>{views[k]}</div>" for k, _, _ in TABS)
    tyb = "".join(f"<button class='ty{' on' if ty == cur else ''}' data-v='{ty}'>{ty}</button>" for ty in years)
    tabs = "".join(f"<button class='tab{' on' if k == 'overview' else ''}' data-v='{k}' role='tab'>{C.icon(ic, 22)}{v}</button>" for k, v, ic in TABS)
    name = log.profile.get("display_name") or ""
    here = log.row(as_of)
    loc = ""
    if here:
        recent = E.stays(log, as_of - timedelta(days=400), as_of)
        st = recent[-1] if recent else None
        since = E.parse_date(st["from"]) if st else as_of
        place = here.get("midnight_place") or ""
        loc = (f"<div class='card teal loc'><div class='sh' style='margin:0'><span style='color:{C.PRIMARY}'>{C.icon('map-pin', 20)}</span>"
               f"<h2>{esc(E.cname(here['midnight_country']))}</h2></div><p>Day {(as_of - since).days + 1}{SEP}since {esc(E.fmt_date(since))}{(SEP + esc(place)) if place else ''}</p></div>")
    status = "".join(f"<div class='year{' on' if ty == cur else ''}' data-v='{ty}'>{per_year[ty][1]['status']}</div>" for ty in years)
    return f"""<!doctype html><html lang='en-GB'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>
<meta name='color-scheme' content='light'><meta name='theme-color' content='#FAF7F2'><title>Nomad Pro: UK Residency Tracker</title><style>{_font_css()}{_asset('dashboard.css')}</style></head><body>
<div class='orbs' aria-hidden='true'><i></i><i></i><i></i></div>
<header class='top'><img src='{_logo()}' alt='Nomad Pro'><div class='ttl'><div class='k'>Nomad Pro</div><h1>UK Residency Tracker</h1></div>
<div class='today'><div class='k'>Today</div><b>{esc(ordinal(as_of))}</b><div class='small muted rec'>{esc(name) + SEP if name else ''}recorded to {esc(E.fmt_date(last) if last else '-')}</div></div></header>
<div class='wrap' style='padding-bottom:0'><div class='hero'>{loc}<div class='card ysel'><div class='k'>Tax year</div><div class='years' role='tablist' aria-label='Tax year'>{tyb}</div></div>{status}</div></div>
<nav class='tabs'><div class='in' role='tablist'>{tabs}</div></nav>
<main class='wrap'>{body}</main>
<footer><div class='l6'>{esc(E.L6)}</div><div style='margin-top:6px'>Counts come from your own entries using the midnight rule ({esc(E.cite('RFIG20710'))}). Nomad Pro is not affiliated with HMRC.</div></footer>
<script>{_asset('dashboard.js')}</script></body></html>"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("daylog"); ap.add_argument("out")
    ap.add_argument("--as-of", default=date.today().isoformat())
    ap.add_argument("--rules", help=E.RULES_HELP)
    ap.add_argument("--kb", help="HMRC mirror (root or pages/ dir); default: $NOMAD_PRO_KB, else <engine>/hmrc")
    ap.add_argument("--data-root", help="user data folder holding evidence/ and documents/ (default: the day log's folder)")
    a = ap.parse_args(argv)
    E.load_hmrc_dates(E.default_kb(a.kb))
    rules = E.load_rules(E.default_rules_path(a.rules))
    log = E.DayLog.load(a.daylog)
    root = Path(a.data_root or Path(a.daylog).parent)
    idx = root / "documents" / "index.json"
    docs = json.loads(idx.read_text(encoding="utf-8"))["documents"] if idx.exists() else []
    prefix = file_prefix(str(root), str(Path(a.out).parent))
    Path(a.out).write_text(render(log, E.parse_date(a.as_of), rules, prefix, docs), encoding="utf-8")
    print(a.out)


if __name__ == "__main__":
    main()
