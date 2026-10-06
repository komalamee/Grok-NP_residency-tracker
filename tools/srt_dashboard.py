#!/usr/bin/env python3
"""The tabbed SRT Residency dashboard: Overview, UK Days, Schengen, Full Timeline, Work Days, SRT Status,
Documentation, plus a tax-year switch. Called by render_dashboard.py (the default design from engine 0.1.5).

  python3 render_dashboard.py DAYLOG.json OUT.html [--as-of YYYY-MM-DD] [--data-root DIR] [--source "Source: ..."]
  python3 render_dashboard.py DAYLOG.json --import-notes nomad-pro-notes-YYYY-MM-DD.json

Built only from the user's own day log (days, profile, user_notes) and documents/index.json. Rules it keeps:
* Counts and records labels only. No residence outcome, no test-outcome labels, no limit, headroom or days-remaining figure
  worked out from the ties table. HMRC day bands (16/46/91/121/183) appear as reference only; ties are a count;
  UK work days are a count with HMRC's 31 as reference.
* "Your own limit" is blank unless the user sets it (saved in the browser, imported into profile.user_limit).
* Notes are 2-4 short index bullets per row (stay city, which records exist, flights). Never addresses, IDs,
  amounts or what was bought. Each row also has a "Your note" box saved in the browser and exported as JSON.
* A place the user marks private shows as "<city> (family home)" (or the label they chose), everywhere.
* Documentation links only to documents with a working http(s) link; everything else is plain text saying where
  the record lives.
The page shell (CSS, markup, app script) is assets/srt_dashboard.html; Chart.js and its date adapter (MIT) are
inlined from assets/vendor/ so the file works offline.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import urllib.request
from pathlib import Path

import srt_engine as E

ASSETS = Path(__file__).resolve().parent / "assets"
TEMPLATE = ASSETS / "srt_dashboard.html"
VENDOR = [ASSETS / "vendor" / "chart.umd-4.5.1.min.js", ASSETS / "vendor" / "chartjs-adapter-date-fns-3.0.0.bundle.min.js"]
NOTES_FORMAT = "nomad-pro-dashboard-notes"
PRIVATE_LABEL = "family home"

# Official guidance (GOV.UK). Shown as links only when the link opens at build time (or when checks are switched off).
GUIDANCE = [
    {"type": "gov", "title": "HMRC RDR3: Statutory Residence Test (SRT)", "desc": "HMRC's guidance on the SRT, with the day bands and ties shown on the SRT tab.",
     "link": "https://www.gov.uk/government/publications/rdr3-statutory-residence-test-srt", "linkText": "Open on GOV.UK"},
    {"type": "gov", "title": "HMRC Residence, Domicile and Remittance Basis Manual", "desc": "The RFIG pages the day log cites (midnight rule, ties).",
     "link": "https://www.gov.uk/hmrc-internal-manuals/residence-domicile-and-remittance-basis", "linkText": "Open on GOV.UK"},
]
EVIDENCE_WORDS = {"booking": "booking confirmation", "card": "card statement", "calendar": "calendar", "ticket": "travel ticket",
                  "photo": "photo", "maps_timeline": "location history", "email": "email", "screenshot": "screenshot",
                  "document": "document", "other": "other record"}
SOURCE_ICON = {"calendar": "calendar", "card": "bank", "bank": "bank", "booking_site": "airbnb", "ticket": "flight", "email": "tool",
               "maps_timeline": "tool", "photo": "tool", "other": "tool"}
WORK_TYPES = {"employed": "Employed", "self_employed": "Self-employed", "contractor": "Contractor", "none": "Not working"}

STREET = re.compile(r"\b(street|st\.|road|rd\.?|lane|ln\.?|avenue|ave\.?|boulevard|blvd|place|close|drive|way|terrace|crescent|"
                    r"soi|jalan|calle|rua|rue|via|strasse|straße|ul\.)\b|\d", re.I)
POSTCODE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]?(\s*\d[A-Z]{2})?\b")
DWELLING = re.compile(r"\b(house|home|flat|apartment|apt|room|studio|condo|villa|hostel|hotel|airbnb|parents'?|family|friend'?s?|"
                      r"mum'?s?|dad'?s?|sister'?s?|brother'?s?|partner'?s?)\b", re.I)
FLIGHT = re.compile(r"\b([A-Z]{2}|[A-Z]\d|\d[A-Z])\s?(\d{1,4})\b(?![\d/.-])")
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def fmt_long(d: dt.date) -> str:
    return f"{d.day} {d.strftime('%B')} {d.year}"


# --------------------------------------------------------------------------- private places (rule 9)
def private_rules(profile: dict) -> list[dict]:
    """Places the user marked private, as matchers -> display text ('Leeds (family home)').

    Two ways to mark one: accommodation_register[].private = true (with city, optional private_label), or
    profile.private_places = [{"match": "text or [texts]", "city": "Leeds", "label": "family home"}]."""
    rules = []
    addr_by_acc = {}
    for a in profile.get("uk_addresses", []) or []:
        if a.get("accommodation_id") and a.get("label"):
            addr_by_acc.setdefault(a["accommodation_id"], []).append(a["label"])
    for a in profile.get("accommodation_register", []) or []:
        if a.get("private") is True:
            city = a.get("city") or city_of(a.get("label", "")) or "UK"
            rules.append({"ids": {a.get("id")}, "match": [m for m in [a.get("label"), *addr_by_acc.get(a.get("id"), [])] if m],
                          "show": f"{city} ({a.get('private_label') or PRIVATE_LABEL})"})
    labelled = [(a.get("id"), a.get("label")) for a in profile.get("accommodation_register", []) or [] if a.get("label")]
    labelled += [(a.get("accommodation_id"), a.get("label")) for a in profile.get("uk_addresses", []) or [] if a.get("label")]
    for p in profile.get("private_places", []) or []:
        m = p.get("match")
        match = [m] if isinstance(m, str) else [x for x in (m or []) if isinstance(x, str) and x]
        if match and p.get("city"):
            # A register entry or address that contains the marked text is private as a whole (street, postcode and all).
            hits = [(i, lab) for i, lab in labelled if any(x.lower() in lab.lower() for x in match)]
            rules.append({"ids": set(p.get("accommodation_ids") or []) | {i for i, _ in hits if i},
                          "match": match + [lab for _, lab in hits],
                          "show": f"{p['city']} ({p.get('label') or PRIVATE_LABEL})"})
    # Everything else in the register is shown at city level only: never a street, number or postcode.
    taken = {m.lower() for r in rules for m in r["match"]}
    for a in profile.get("accommodation_register", []) or []:
        lab = a.get("label")
        if lab and lab.lower() not in taken:
            city = a.get("city") or city_of(lab) or "a recorded place"
            rules.append({"ids": {a.get("id")} if a.get("id") else set(), "match": [lab], "show": city})
            taken.add(lab.lower())
    for i, lab in labelled:
        if lab.lower() not in taken:
            rules.append({"ids": set(), "match": [lab], "show": city_of(lab) or "a recorded place"})
            taken.add(lab.lower())
    return rules


def mask(text: str, rules: list[dict]) -> str:
    """Replace every private place mentioned in free text with its display form."""
    out = text or ""
    for r in rules:
        for m in sorted(r["match"], key=len, reverse=True):
            out = re.sub(re.escape(m), r["show"], out, flags=re.I)
    return out


def city_of(place: str) -> str:
    """City-level place: drop street segments, postcodes, numbers and bracketed details; keep the last segment left."""
    p = re.sub(r"\([^)]*\)", "", place or "")
    p = p.split(" \u2014 ")[0].split(" - ")[0]
    segs = [POSTCODE.sub("", s).strip() for s in re.split(r"[,;/]", p)]
    keep = [s for s in segs if s and not STREET.search(s) and not DWELLING.search(s)]
    return (keep[-1] if keep else "").strip()


def place_for(day: dict, rules: list[dict]) -> str:
    acc = day.get("accommodation_id")
    for r in rules:
        if acc and acc in r["ids"]:
            return r["show"]
    for field in ("midnight_place", "accommodation_label"):
        raw = day.get(field) or ""
        for r in rules:
            if any(m.lower() in raw.lower() for m in r["match"]):
                return r["show"]
    return city_of(day.get("midnight_place") or "")


# --------------------------------------------------------------------------- notes (rules 7 and 8)
def _flights(day_list: list[dict]) -> list[str]:
    out = []
    for d in day_list:
        for ev in d.get("evidence", []) or []:
            text = f"{ev.get('label') or ''} {ev.get('pointer') or ''}"
            if ev.get("type") != "ticket" and not re.search(r"\bflights?\b", text, re.I):
                continue
            for f in FLIGHT.finditer(text):
                code = f.group(1) + f.group(2)
                if f.group(1) in ("GB", "UK") and len(f.group(2)) == 4:
                    continue
                tail = text[f.end():f.end() + 40]
                m = re.match(rf"\s*\(?(\d{{1,2}} {MONTH})\b", tail)
                label = f"{code} ({m.group(1)})" if m else code
                if not any(x.split(" ")[0] == code for x in out):
                    out.append(label)
    return out


def _records(day_list: list[dict]) -> list[str]:
    seen = []
    for d in day_list:
        for ev in d.get("evidence", []) or []:
            t = ev.get("type")
            if t == "attestation":
                continue
            word = "bank export" if ev.get("source") == "bank_export" else EVIDENCE_WORDS.get(t)
            if word and word not in seen:
                seen.append(word)
    return seen


def stay_bullets(day_list: list[dict], place: str) -> list[str]:
    out = [f"Stay: {place}"] if place else []
    recs = _records(day_list)
    if recs:
        out.append("Records: " + ", ".join(recs[:5]))
    fl = _flights(day_list)
    if fl:
        out.append("Flights on record: " + ", ".join(fl[:4]))
    conf = []
    checkins = sum(1 for d in day_list if d.get("logged_via") == "checkin")
    attested = sum(1 for d in day_list if d.get("confidence") == "attested")
    if checkins:
        conf.append(f"you confirmed {_plural(checkins, 'night')} at check-in")
    if attested:
        conf.append(f"your statement on record ({_plural(attested, 'day')})")
    if conf:
        s = "; ".join(conf)
        out.append(s[0].upper() + s[1:])
    inferred = sum(1 for d in day_list if d.get("confidence") == "inferred")
    if inferred:
        out.append(f"{_plural(inferred, 'day')} inferred (reasoned, not evidenced)")
    no_work = sum(1 for d in day_list if (d.get("uk_work") or {}).get("over_3h") == "no"
                  and (d.get("uk_work") or {}).get("source") in (None, "", "user_answer") and d.get("midnight_country") == E.UK)
    if no_work:
        out.append(f"Work: you said no UK work on {_plural(no_work, 'day')}")
    if len(out) < 2:
        out.append(f"Day log: {_plural(len(day_list), 'day')} logged")
    return out[:4]


def work_bullets(day: dict) -> list[str]:
    w = day.get("uk_work") or {}
    src = w.get("source") or ""
    out = []
    if src.startswith("rule:"):
        out.append(f"Counted under your agreed work-day rule ({src[5:]})")
    elif src == "user_answer":
        out.append("Your own answer")
    if w.get("work_travel"):
        out.append("Travel day recorded as work travel")
    if w.get("exception"):
        out.append("A calendar exception from your rule applied")
    if w.get("hours") is not None:
        out.append(f"Hours you gave: {w['hours']}")
    recs = _records([day])
    if recs:
        out.append("Records: " + ", ".join(recs[:4]))
    if day.get("confidence") == "inferred":
        out.append("Inferred (reasoned, not evidenced)")
    if len(out) < 2:
        out.append("Day log: " + {"confirmed": "confirmed", "attested": "your statement", "inferred": "inferred"}.get(day.get("confidence"), "logged"))
    return out[:4]


def note_key(kind: str, start: str, end: str) -> str:
    return f"{kind}:{start}..{end}"


def _user_note(notes: list[dict], kind: str, start: str, end: str, country: str) -> str:
    by_key = {n.get("key"): n for n in notes}
    n = by_key.get(note_key(kind, start, end))
    if not n and kind == "stay":   # stay dates moved since the note was written: same country and overlapping dates
        n = next((x for x in notes if x.get("kind") == "stay" and x.get("country") == country and x.get("text")
                  and (x.get("start") or "") <= end and (x.get("end") or "") >= start), None)
    return (n or {}).get("text") or ""


# --------------------------------------------------------------------------- rows
def _logged_days(log: E.DayLog, as_of: dt.date) -> list[dict]:
    out = []
    for d in sorted(log.days):
        r = log.row(d)
        if d <= as_of and r and r.get("confidence") != "planned":
            out.append(r)
    return out


def build_travel(log: E.DayLog, as_of: dt.date, rules: list[dict]) -> list[dict]:
    runs = []
    for r in _logged_days(log, as_of):
        place = place_for(r, rules)
        c = E.cname(r["midnight_country"])
        ty = r.get("tax_year") or E.tax_year_of(r["date"])
        p = runs[-1] if runs else None
        if p and p["country"] == c and p["ty"] == ty and p["place"] == place and \
                (E.parse_date(r["date"]) - E.parse_date(p["end"])).days == 1:
            p["end"] = r["date"]
            p["days"].append(r)
        else:
            runs.append({"country": c, "ty": ty, "place": place, "start": r["date"], "end": r["date"], "days": [r]})
    notes = log.data.get("user_notes", []) or []
    out = []
    for x in runs:
        bullets = stay_bullets(x["days"], x["place"])
        inferred = any(d.get("confidence") == "inferred" for d in x["days"])
        out.append({"country": x["country"], "start": x["start"], "end": x["end"], "purpose": "", "accom": x["place"],
                    "notes": ("[INFERRED] " if inferred else "") + "; ".join(bullets), "bullets": bullets,
                    "userNote": _user_note(notes, "stay", x["start"], x["end"], x["country"])})
    return out


def build_work(log: E.DayLog, as_of: dt.date, rules: list[dict]) -> list[dict]:
    notes = log.data.get("user_notes", []) or []
    out = []
    for r in _logged_days(log, as_of):
        w = r.get("uk_work") or {}
        uk_day = r["midnight_country"] == E.UK or E.UK in (r.get("countries_present") or [])
        if uk_day and w.get("over_3h") == "yes":
            place = place_for(r, rules) if r["midnight_country"] == E.UK else ""
            loc = f"{place}, UK" if place else "UK"
            uk = "yes"
        elif r.get("overseas_work_hours"):
            loc, uk = f"{place_for(r, rules) or ''}{', ' if place_for(r, rules) else ''}{E.cname(r['midnight_country'])}", "no"
        else:
            continue
        bullets = work_bullets(r)
        out.append({"date": r["date"], "location": loc, "hours": w.get("hours") if uk == "yes" else r.get("overseas_work_hours"),
                    "uk": uk, "notes": ("Inferred; " if r.get("confidence") == "inferred" else "") + "; ".join(bullets),
                    "bullets": bullets, "userNote": _user_note(notes, "work", r["date"], r["date"], "")})
    return out


# --------------------------------------------------------------------------- SRT inputs per tax year
def leaver_info(log: E.DayLog, ty: str) -> dict:
    prev = [E.prev_tax_year(ty, n) for n in (1, 2, 3)]
    ans = {p: E.uk_resident_recorded(log, p) for p in prev}
    yes = [p for p, a in ans.items() if a == "yes"]
    unknown = [p for p, a in ans.items() if a not in ("yes", "no")]
    if yes:
        at_least = "at least " if unknown else ""
        return {"leaverYear": 4 - len(yes), "classification": f"Leaver (resident in {at_least}{len(yes)} of preceding 3 years)",
                "sub": "HMRC leaver table (RDR3), from your recorded residence for " + ", ".join(prev[::-1])}
    if not unknown:
        return {"leaverYear": 4, "classification": "Not previously resident", "sub": "HMRC arriver table (RDR3), from your recorded residence for " + ", ".join(prev[::-1])}
    return {"leaverYear": 0, "classification": "Residence in earlier years not recorded",
            "sub": "Not recorded yet: " + ", ".join(unknown[::-1]) + ". The leaver table is shown until you record them."}


def _answer_text(v: str | None) -> str:
    return {"yes": "yes", "no": "no", "unsure": "unsure"}.get(v or "", "not answered")


def year_config(log: E.DayLog, ty: str, as_of: dt.date, rules: list[dict]) -> dict:
    cfg = log.year_config(ty)
    start, end = E.tax_year_bounds(ty)
    periods = [p for p in log.profile.get("work_periods", []) or []
               if (p.get("from") or "0000") <= end.isoformat() and (p.get("to") or "9999") >= start.isoformat()]
    claim = cfg.get("overseas_full_time_work_claimed") or next((p.get("overseas_full_time_claimed") for p in periods
                                                                if p.get("overseas_full_time_claimed") not in (None, "not_answered")), "not_answered")
    status = {"yes": "claimed", "unsure": "grey"}.get(claim, "not_claimed")
    types = [WORK_TYPES.get(p.get("type"), p.get("type") or "") for p in periods]
    t = E.evaluate_ties(log, ty, as_of)
    counted = set(t["counted"])
    key = {"family": "family", "accommodation": "accommodation", "work": "work", "ninetyDay": "ninety_day", "country": "country"}
    ties_notes = {}
    for js_k, k in key.items():
        v = t["ties"].get(k) or {}
        ties_notes[js_k] = mask(f"{v.get('status', 'Not answered')}. Your log: {v.get('log_shows', '')}. {v.get('ref', '')}".strip(), rules)
    home, ftuk = cfg.get("only_home_in_uk_answer"), cfg.get("full_time_uk_work_answer")
    note = cfg.get("dashboard_note")
    return {
        "employedOverseasFulltime": claim == "yes",
        "employer": " / ".join(x for x in types if x),
        "employmentStart": min((p.get("from") or "" for p in periods), default=""),
        "employmentEnd": max((p.get("to") or "" for p in periods), default="") if all(p.get("to") for p in periods) else "",
        "contractType": "Contractor" if any(p.get("type") == "contractor" for p in periods) else "",
        "autoOverseas": {"ftWorkStatus": status,
                         "ftWorkNotes": f"Your answer for {ty}: full-time work overseas claimed: {_answer_text(claim)}."},
        "autoResident": {"days183": False,
                         "homeOnly": home == "yes", "homeOnlyNotes": f"Your answer: {_answer_text(home)}." if home else "",
                         "ftUkWork": ftuk == "yes", "ftUkWorkNotes": f"Your answer: {_answer_text(ftuk)}." if ftuk else ""},
        "ties": {js_k: (k in counted) for js_k, k in key.items()},
        "tiesNotes": ties_notes,
        "yearNote": {"title": str(note.get("title", ""))[:120], "text": str(note.get("text", ""))[:600]} if isinstance(note, dict) and note.get("text") else None,
    }


def key_dates(profile: dict) -> list[dict]:
    left = profile.get("left_uk_on")
    if not left:
        return []
    y0 = int(E.tax_year_of(left)[:4])
    return [{"date": fmt_long(dt.date(y0 + 4, 4, 5)), "text": "End of the third tax year after the tax year you left the UK. "
             "If none of those years is a year of UK residence, HMRC's leaver table stops applying after this date and the "
             "46-day automatic overseas figure applies instead of 16 (RDR3)."},
            {"date": fmt_long(dt.date(y0 + 6, 4, 5)), "text": "Five full tax years after the year you left. If none of "
             "those years is a year of UK residence, HMRC's temporary non-residence rules would no longer apply to most income "
             "and gains realised during the absence (RDR3)."}]


# --------------------------------------------------------------------------- documentation (rule 6)
def link_ok(url: str, timeout: float = 8.0) -> bool:
    if not re.match(r"^https?://", url or ""):
        return False
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": "nomad-pro-engine link check"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= resp.status < 400:
                    return True
        except Exception:
            continue
    return False


def build_docs(log: E.DayLog, documents: list[dict], rules: list[dict], check_links: bool = True) -> list[dict]:
    prof = log.profile
    docs = [{"type": "tool", "title": "Nomad Pro day log", "desc": "The record this dashboard is built from (one row per date).",
             "where": "File on your assistant's computer: ~/nomad-pro-data/daylog.json"},
            {"type": "tool", "title": "Nomad Pro \u2013 Travel log (Google Sheet)", "desc": "Your day-by-day log: days, records, trips and outputs.",
             "where": "Google Drive \u2192 \u201cNomad Pro \u2013 Travel log\u201d (ask your assistant for the link)"}]
    for l in prof.get("links", []) or []:   # links the user gave (e.g. their Sheet or Drive folder)
        if l.get("url") and l.get("title"):
            docs.append({"type": l.get("type") or "tool", "title": mask(l["title"], rules), "desc": mask(l.get("desc", ""), rules),
                         "link": l["url"], "linkText": "Open"})
    for d in documents or []:
        item = {"type": "tool", "title": mask(d.get("title") or "Document", rules),
                "desc": ", ".join(x for x in [(d.get("type") or "").replace("_", " ").capitalize(), ", ".join(d.get("tax_years") or [])] if x)}
        if d.get("url"):
            item.update(link=d["url"], linkText="Open the document")
        elif d.get("file"):
            item["where"] = f"Stored in your Nomad Pro data folder: {d['file']}"
        elif d.get("pointer"):
            item["where"] = mask(d["pointer"], rules)
        docs.append(item)
    for s in prof.get("evidence_sources", []) or []:
        if s.get("label"):
            docs.append({"type": SOURCE_ICON.get(s.get("type"), "tool"), "title": mask(s["label"], rules),
                         "desc": f"Record source ({(s.get('type') or 'other').replace('_', ' ')}).",
                         "where": "In your own account or app (not copied into the dashboard)"})
    docs += [dict(g) for g in GUIDANCE]
    docs.append({"type": "tool", "title": "Schengen short-stay calculator", "desc": "European Commission calculator for the 90/180 rule.",
                 "where": "European Commission website (home-affairs.ec.europa.eu) \u2192 Schengen short-stay calculator"})
    for d in docs:   # rule 6: a link only when it is a real http(s) link that opens; otherwise plain text
        if "link" in d:
            if not re.match(r"^https?://", d["link"]) or (check_links and not link_ok(d["link"])):
                url = d.pop("link"); d.pop("linkText", None)
                d["where"] = d.get("where") or (f"Link could not be opened when this page was built: {url}" if re.match(r"^https?://", url) else url)
    return docs


# --------------------------------------------------------------------------- page
def _esc(s) -> str:
    return (str(s if s is not None else "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _json_for_script(obj) -> str:
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("</", "<\\/").replace("<!--", "<\\!--").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def build_data(log: E.DayLog, as_of: dt.date, documents: list | None = None, check_links: bool = True) -> dict:
    rules = private_rules(log.profile)
    years = log.tracked_years(as_of)
    cur = E.tax_year_of(as_of)
    if cur not in years and years:
        cur = years[-1]
    travel = build_travel(log, as_of, rules)
    work = build_work(log, as_of, rules)
    summaries = {ty: E.summarise_year(log, ty, as_of) for ty in years}
    ul = log.profile.get("user_limit")
    names = sorted({E.cname(c) for c in E.schengen_members_on(as_of)})
    return {
        "asOf": as_of.isoformat(), "lastUpdated": as_of.strftime("%d/%m/%Y"),
        "taxYears": [{"label": ty, "start": E.tax_year_bounds(ty)[0].isoformat(), "end": E.tax_year_bounds(ty)[1].isoformat()} for ty in years],
        "selectedTaxYear": cur, "travel": travel, "workDays": work,
        "docs": build_docs(log, documents or [], rules, check_links),
        "taxYearConfig": {ty: year_config(log, ty, as_of, rules) for ty in years},
        "leaverYears": {ty: leaver_info(log, ty) for ty in years},
        "yearOpen": {ty: as_of < E.tax_year_bounds(ty)[1] for ty in years},
        "workUnsure": {ty: summaries[ty]["uk_work_unsure"] for ty in years},
        "schengenCountries": names,
        "keyDates": key_dates(log.profile),
        "userLimit": {"value": ul["value"], "updated_at": ul.get("updated_at")} if isinstance(ul, dict) and isinstance(ul.get("value"), int) and not isinstance(ul.get("value"), bool) and 1 <= ul["value"] <= 366 else None,
        "_summaries": summaries,
    }


def coverage_html(data: dict) -> str:
    ty = data["selectedTaxYear"]
    s = data["_summaries"].get(ty)
    if not s:
        return '<div class="coverage-notice"><strong>No days logged yet.</strong></div>'
    as_of = E.parse_date(data["asOf"])
    return (f'<div class="coverage-notice">\n        <strong>Current to {_esc(fmt_long(as_of))}.</strong> {s["logged"]} of {s["days_in_year_to_date"]} days of {ty} so far are logged '
            f'({s["unlogged"]} not logged). {ty} so far = {s["uk_midnights"]} UK days / {s["uk_work_days_over_3h"]} UK work days.\n'
            '        <span class="flags">Rows marked [INFERRED] include a day whose location is reasoned rather than evidenced. '
            'Only your own days are counted. Built when you asked for it; ask your assistant to rebuild for newer days.</span>\n    </div>')


def render(log: E.DayLog, as_of: dt.date, documents: list | None = None, source_line: str = "", check_links: bool = True) -> str:
    data = build_data(log, as_of, documents, check_links)
    prof = log.profile
    name = (prof.get("display_name") or "").strip()
    initials = "".join(w[0] for w in re.findall(r"[A-Za-z]+", name)[:2]).upper() or "NP"
    sub = ["UK residence day log"] + ([name] if name else []) + \
          ([f"Left UK: {fmt_long(E.parse_date(prof['left_uk_on']))}"] if prof.get("left_uk_on") else [])
    page = TEMPLATE.read_text(encoding="utf-8")
    libs = "\n".join(f"    <script>\n{p.read_text(encoding='utf-8')}\n    </script>" for p in VENDOR)
    cov = coverage_html(data)
    data.pop("_summaries")
    subs = {"<!--@@NP_CHART_LIBS@@-->": libs, "@@NP_TITLE@@": "Nomad Pro \u2014 UK Residency Tracker", "@@NP_BRAND@@": _esc(initials),
            "@@NP_SUBTITLE@@": " &middot; ".join(_esc(x) for x in sub), "@@NP_COVERAGE@@": cov, "@@NP_L6@@": _esc(E.L6),
            "@@NP_L8@@": _esc(E.L8), "@@NP_SOURCE@@": f'<div class="np-source">{_esc(source_line)}</div>' if source_line else "",
            "/*@@NP_DATA@@*/{}": _json_for_script(data)}
    for k, v in subs.items():
        if k not in page:
            raise RuntimeError(f"dashboard template is missing {k}")
        page = page.replace(k, v)
    return page


# --------------------------------------------------------------------------- notes import (rule 8) and your own limit (rule 5)
def import_notes(path: str | Path, daylog: str | Path) -> dict:
    """Merge an "Export my notes" file into the day log: user_notes by key (newer edit wins); user_limit into
    profile.user_limit (a blank export clears it). Backs up the day log first."""
    src = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(src, dict) or src.get("format") != NOTES_FORMAT or not isinstance(src.get("notes"), list):
        raise SystemExit(f"Not a notes export from the dashboard (expected format '{NOTES_FORMAT}').")
    daylog = Path(daylog)
    log = json.loads(daylog.read_text(encoding="utf-8"))
    now = dt.datetime.now().astimezone()
    backup = daylog.with_name(f"daylog.backup-{now.strftime('%Y-%m-%d-%H%M%S')}-before-import-notes.json")
    shutil.copyfile(daylog, backup)
    cur = {n.get("key"): n for n in log.get("user_notes", []) or []}
    merged = 0
    for n in src["notes"]:
        if not isinstance(n, dict):
            continue
        kind, start, end = n.get("kind"), n.get("start"), n.get("end")
        if kind not in ("stay", "work") or not all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", x or "") for x in (start, end)):
            continue
        key = note_key(kind, start, end)
        old = cur.get(key)
        if old and old.get("updated_at") and n.get("updated_at") and old["updated_at"] > n["updated_at"]:
            continue
        cur[key] = {"key": key, "kind": kind, "start": start, "end": end, "country": str(n.get("country") or "")[:80],
                    "text": str(n.get("text") or "").strip()[:2000], "updated_at": n.get("updated_at"),
                    "imported_at": now.isoformat(timespec="seconds"), "source": "dashboard export"}
        merged += 1
    log["user_notes"] = sorted(cur.values(), key=lambda x: (x["start"], x["kind"]))
    limit = "unchanged"
    if "user_limit" in src:
        ul = src["user_limit"]
        prof = log.setdefault("profile", {})
        old = prof.get("user_limit") if isinstance(prof.get("user_limit"), dict) else {}
        newer_old = old.get("updated_at") and isinstance(ul, dict) and ul.get("updated_at") and old["updated_at"] > ul["updated_at"]
        v = ul.get("value") if isinstance(ul, dict) else None
        if not newer_old:
            if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 366:
                prof["user_limit"] = {"value": v, "unit": "UK days per tax year (set by you)", "updated_at": ul.get("updated_at"),
                                      "imported_at": now.isoformat(timespec="seconds"), "source": "dashboard export"}
                limit = f"set to {v}"
            elif isinstance(ul, dict) and v is None and "user_limit" in prof:
                del prof["user_limit"]
                limit = "cleared"
    daylog.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"notes_merged": merged, "user_limit": limit, "backup": str(backup)}
