#!/usr/bin/env python3
"""Nomad Pro - UK Residency Tracker: counting engine.

Record-keeping arithmetic only. Every figure this module produces is a count
from the user's own day log. Nothing here determines anyone's residence.

What it computes
  * UK tax years (6 April - 5 April) and the midnight rule (RFIG20710).
  * UK midnights, UK work days of more than 3 hours (RFIG20560), unlogged days.
  * Ties inputs vs the user's own recorded answers (RFIG20530/20550/20560/20570/20580).
  * RDR3 / RFIG20520 Table A / Table B bands using HMRC's own "more than" boundaries.
  * Distance ("room") to each HMRC figure and a proximity level:
    comfortable room / getting close / at the line / over the line.
  * The verdict gate: a stage line ("Your log points to ...") only for a tax year that has ended with every day
    logged, the previous 3 years' residence recorded and every applicable tie answered; otherwise what is still
    missing (gate, verdict_withheld) and a running count of the year so far (running_count).
  * The HMRC figures that apply to a year's recorded facts, with the room left before each and the nearest one
    still ahead (applicable_figures), which is what the dashboard and the export show progress against.
  * Schengen 90/180 rolling window (any part of a day counts) with the next
    drop-off date, and other country stay limits from country_rules.json.
  * Trip modelling (planned trips merged into a copy of the log).

Usage
  python3 srt_engine.py summary  DAYLOG.json [--as-of YYYY-MM-DD] [--rules RULES.json]
  python3 srt_engine.py plan     DAYLOG.json --trip CC:FIRST_NIGHT:LAST_NIGHT [--trip ...] [--rules RULES.json]
  python3 srt_engine.py validate DAYLOG.json

--trip is given once per trip. Without --rules the country rules come from the user's own copy
($NOMAD_PRO_DATA/country-rules.json, else ~/nomad-pro-data/country-rules.json) and only then from the
engine's shipped schema/country-rules.json, so the weekly travel-rules watch's updates are the ones counted.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from collections import Counter, OrderedDict
from datetime import date, datetime, timedelta
from pathlib import Path

UK = "GB"

# --------------------------------------------------------------------------
# HMRC references. Dates are HMRC's own "last updated" dates from the local
# knowledge-base mirror; load_hmrc_dates() refreshes them from a mirror folder.
# --------------------------------------------------------------------------
HMRC_PAGES = {
    "RDR3": {"title": "RDR3 guidance note for the Statutory Residence Test", "updated": "2026-06-11",
             "url": "https://www.gov.uk/government/publications/rdr3-statutory-residence-test-srt/guidance-note-for-statutory-residence-test-srt-rdr3",
             "file": "guidance-note-for-statutory-residence-test-srt-rdr3"},
    "RFIG20120": {"title": "First automatic overseas test", "updated": "2025-04-07"},
    "RFIG20130": {"title": "Second automatic overseas test", "updated": "2025-04-04"},
    "RFIG20140": {"title": "Third automatic overseas test", "updated": "2025-04-04"},
    "RFIG20320": {"title": "First automatic UK test", "updated": "2025-04-04"},
    "RFIG20330": {"title": "Second automatic UK test", "updated": "2025-04-04"},
    "RFIG20370": {"title": "Third automatic UK test", "updated": "2025-04-04"},
    "RFIG20520": {"title": "The number of ties", "updated": "2026-07-03"},
    "RFIG20530": {"title": "Definition of a family tie", "updated": "2026-03-10"},
    "RFIG20550": {"title": "Accommodation tie", "updated": "2025-04-04"},
    "RFIG20560": {"title": "Work tie", "updated": "2025-04-04"},
    "RFIG20570": {"title": "90-day tie", "updated": "2026-01-08"},
    "RFIG20580": {"title": "Country tie", "updated": "2025-04-04"},
    "RFIG20710": {"title": "Meaning of a day spent in the UK", "updated": "2025-04-04"},
    "RFIG20720": {"title": "The deeming rule", "updated": "2025-04-04"},
    "RFIG20730": {"title": "Transit days", "updated": "2025-04-04"},
    "RFIG20740": {"title": "Work for the purpose of the SRT", "updated": "2025-04-04"},
    "RFIG21000": {"title": "Split year treatment", "updated": "2025-04-04"},
    "RFIG22170": {"title": "Accommodation as a UK tie", "updated": "2025-04-04"},
    "RFIG22220": {"title": "Exceptional circumstances", "updated": "2025-04-04"},
}
for _k, _v in HMRC_PAGES.items():
    _v.setdefault("url", "https://www.gov.uk/hmrc-internal-manuals/residence-and-fig-regime-manual/" + _k.lower())
    _v.setdefault("file", _k.lower())

COUNTRY_NAMES = {
    "GB": "United Kingdom", "AE": "UAE", "AT": "Austria", "BA": "Bosnia and Herzegovina", "BE": "Belgium", "BG": "Bulgaria",
    "CH": "Switzerland", "CN": "China", "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany", "DK": "Denmark", "EE": "Estonia",
    "ES": "Spain", "FI": "Finland", "FR": "France", "GR": "Greece", "HR": "Croatia", "HU": "Hungary", "ID": "Indonesia",
    "IE": "Ireland", "IS": "Iceland", "IT": "Italy", "JP": "Japan", "KH": "Cambodia", "KR": "South Korea", "LA": "Laos",
    "LI": "Liechtenstein", "LK": "Sri Lanka", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "ME": "Montenegro",
    "MT": "Malta", "MX": "Mexico", "MY": "Malaysia", "NL": "Netherlands", "NO": "Norway", "PH": "Philippines", "PL": "Poland",
    "PT": "Portugal", "RO": "Romania", "SE": "Sweden", "SG": "Singapore", "SI": "Slovenia", "SK": "Slovakia", "TH": "Thailand",
    "TR": "Türkiye", "US": "United States", "VN": "Vietnam", "AU": "Australia", "GE": "Georgia", "AL": "Albania", "RS": "Serbia",
}


def cname(code: str | None) -> str:
    return COUNTRY_NAMES.get(code or "", code or "-")


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Approved legal strings (SYSTEM.md section 3). Verbatim - do not edit.
L4_TEMPLATE = "Not tax advice \u2014 always check your own position. Source: {ref}."
L6 = ("Educational information, not tax advice. UK residence can turn on detailed facts and current "
      "law. If your position is close to a threshold or commercially significant, use current HMRC "
      "guidance and take advice from a qualified professional.")
L8 = "Not tax or immigration advice \u2014 check your own position."


ENGINE_ROOT = Path(__file__).resolve().parent.parent
# The engine repo ships its own HMRC mirror at <engine>/hmrc (pages under hmrc/pages).
# NOMAD_PRO_KB overrides it (mirror root or its pages/ folder), e.g. a user's own copy in their data folder.
DEFAULT_KB_ROOT = ENGINE_ROOT / "hmrc"


def default_kb(explicit: str | Path | None = None) -> Path | None:
    """The mirror to use: --kb if given, else $NOMAD_PRO_KB, else the engine's own hmrc/ (None if absent)."""
    for cand in (explicit, os.environ.get("NOMAD_PRO_KB"), DEFAULT_KB_ROOT):
        if cand:
            p = Path(cand).expanduser()
            if p.exists():
                return p
    return None


def kb_pages_dir(kb: str | Path | None) -> Path | None:
    """Accept either the mirror root (contains pages/) or the pages folder itself."""
    if not kb:
        return None
    p = Path(kb).expanduser()
    return p / "pages" if (p / "pages").is_dir() else p


def load_hmrc_dates(kb_pages_dir_: str | Path | None) -> None:
    """Refresh HMRC_PAGES[*]['updated'] from a mirror's frontmatter (hmrc_updated).

    Accepts the mirror root or its pages/ folder. None leaves the built-in dates untouched; the CLIs call
    it with default_kb(a.kb) so they use the engine's own mirror unless told otherwise."""
    if not kb_pages_dir_:
        return
    d = kb_pages_dir(kb_pages_dir_)
    for key, meta in HMRC_PAGES.items():
        f = d / (meta["file"] + ".md")
        if f.exists():
            m = re.search(r"^hmrc_updated:\s*(\S+)", f.read_text(encoding="utf-8"), re.M)
            if m:
                meta["updated"] = m.group(1)


def fmt_date(d: date | str) -> str:
    if isinstance(d, str):
        d = parse_date(d)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def cite(ref: str) -> str:
    """'RFIG20570 (updated 8 Jan 2026)'."""
    meta = HMRC_PAGES.get(ref)
    if not meta:
        return ref
    label = "RDR3" if ref == "RDR3" else ref
    return f"{label} (updated {fmt_date(meta['updated'])})"


def l4(ref: str) -> str:
    return L4_TEMPLATE.format(ref=cite(ref))


# --------------------------------------------------------------------------
# Dates and tax years
# --------------------------------------------------------------------------
def parse_date(s: str | date) -> date:
    if isinstance(s, date):
        return s
    return datetime.strptime(s[:10], "%Y-%m-%d").date()


def tax_year_of(d: date | str) -> str:
    d = parse_date(d)
    start = d.year if (d.month, d.day) >= (4, 6) else d.year - 1
    return f"{start}/{str(start + 1)[-2:]}"


def tax_year_bounds(ty: str) -> tuple[date, date]:
    start = int(ty[:4])
    return date(start, 4, 6), date(start + 1, 4, 5)


def prev_tax_year(ty: str, n: int = 1) -> str:
    start = int(ty[:4]) - n
    return f"{start}/{str(start + 1)[-2:]}"


def daterange(a: date, b: date):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


# --------------------------------------------------------------------------
# Log loading
# --------------------------------------------------------------------------
class DayLog:
    def __init__(self, data: dict):
        self.data = data
        self.profile = data.get("profile", {})
        self.days: dict[date, dict] = {}
        for row in data.get("days", []):
            self.days[parse_date(row["date"])] = row
        self.planned = data.get("planned_trips", [])

    @classmethod
    def load(cls, path: str | Path) -> "DayLog":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    # a day is "logged" if a row exists with a midnight country and confidence != unlogged
    def row(self, d: date) -> dict | None:
        r = self.days.get(d)
        if not r or r.get("confidence") == "unlogged" or not r.get("midnight_country"):
            return None
        return r

    def present(self, d: date) -> list[str]:
        r = self.row(d)
        if not r:
            return []
        cp = r.get("countries_present") or []
        mc = r.get("midnight_country")
        out = list(cp)
        if mc and mc not in out:
            out.append(mc)
        return out

    def first_date(self) -> date | None:
        return min(self.days) if self.days else None

    def year_config(self, ty: str) -> dict:
        return (self.profile.get("tax_years") or {}).get(ty, {})

    def prior_year(self, ty: str) -> dict:
        for p in self.profile.get("prior_years", []):
            if p.get("tax_year") == ty:
                return p
        return {}

    def tracked_years(self, as_of: date) -> list[str]:
        f = self.first_date() or as_of
        years, ty = [], tax_year_of(f)
        while tax_year_bounds(ty)[0] <= as_of:
            years.append(ty)
            ty = f"{int(ty[:4]) + 1}/{str(int(ty[:4]) + 2)[-2:]}"
        return years


# --------------------------------------------------------------------------
# HMRC tables (RFIG20520 / RDR3). Each band: (more_than, not_more_than, ties_needed)
# --------------------------------------------------------------------------
TABLE_A = [(15, 45, 4), (45, 90, 3), (90, 120, 2), (120, None, 1)]
TABLE_B = [(45, 90, 4), (90, 120, 3), (120, None, 2)]
TABLES = {"A": TABLE_A, "B": TABLE_B}


def band_for(table: str, days: int) -> dict | None:
    for lo, hi, need in TABLES[table]:
        if days > lo and (hi is None or days <= hi):
            label = f"more than {lo}" + (f" but not more than {hi}" if hi is not None else "")
            return {"more_than": lo, "not_more_than": hi, "ties_needed": need, "label": label}
    return None


def ties_needed(table: str, days: int) -> int | None:
    b = band_for(table, days)
    return b["ties_needed"] if b else None


def line_for_ties(table: str, ties: int) -> int | None:
    """Day count above which `ties` recorded ties meet the table ('more than N')."""
    for lo, hi, need in TABLES[table]:
        if ties >= need:
            return lo
    return None


PROXIMITY_DEFAULT = {"at_the_line": 5, "getting_close": 20}


def proximity(room: int, thresholds: dict | None = None) -> str:
    t = thresholds or PROXIMITY_DEFAULT
    if room < 0:
        return "over the line"
    if room <= t["at_the_line"]:
        return "at the line"
    if room <= t["getting_close"]:
        return "getting close"
    return "comfortable room"


# --------------------------------------------------------------------------
# Year summary
# --------------------------------------------------------------------------
def summarise_year(log: DayLog, ty: str, as_of: date) -> dict:
    start, end = tax_year_bounds(ty)
    to = min(end, as_of)
    s = OrderedDict(tax_year=ty, start=start.isoformat(), end=end.isoformat(), counted_to=to.isoformat(),
                    complete=as_of >= end)
    uk_midnights = 0
    work_yes, work_unsure = [], []
    unlogged, no_pointer, inferred, attested = [], [], [], []
    countries = Counter()
    acc_nights = Counter()
    qualifying = []  # in UK part of day, not at midnight (deeming rule input)
    transit, exceptional, child_days, conflicts, edited = [], [], [], [], []
    uk_dates = []
    days_total = 0
    for d in daterange(start, to):
        days_total += 1
        r = log.row(d)
        if not r:
            unlogged.append(d.isoformat())
            continue
        mc = r["midnight_country"]
        countries[mc] += 1
        pres = log.present(d)
        if mc == UK:
            uk_midnights += 1
            uk_dates.append(d.isoformat())
            if r.get("accommodation_id"):
                acc_nights[r["accommodation_id"]] += 1
        elif UK in pres:
            qualifying.append(d.isoformat())
        w = (r.get("uk_work") or {}).get("over_3h")
        if UK in pres or mc == UK:
            if w == "yes":
                work_yes.append(d.isoformat())
            elif w == "unsure":
                work_unsure.append(d.isoformat())
        if not r.get("evidence"):
            no_pointer.append(d.isoformat())
        c = r.get("confidence")
        if c == "inferred":
            inferred.append(d.isoformat())
        elif c == "attested":
            attested.append(d.isoformat())
        if r.get("uk_transit_no_activity"):
            transit.append(d.isoformat())
        if (r.get("exceptional_circumstances") or {}).get("claimed"):
            exceptional.append(d.isoformat())
        if r.get("family_child_seen_in_uk"):
            child_days.append(d.isoformat())
        if r.get("conflict"):
            conflicts.append({"date": d.isoformat(), **r["conflict"]})
        if r.get("changes"):
            edited.append(d.isoformat())
    s.update(days_in_year_to_date=days_total, logged=days_total - len(unlogged), unlogged=len(unlogged),
             unlogged_dates=unlogged, uk_midnights=uk_midnights, uk_dates=uk_dates,
             uk_work_days_over_3h=len(work_yes), uk_work_dates=work_yes,
             uk_work_unsure=len(work_unsure), uk_work_unsure_dates=work_unsure,
             countries=OrderedDict(sorted(countries.items(), key=lambda kv: (-kv[1], kv[0]))),
             nights_by_accommodation=dict(acc_nights), no_pointer_dates=no_pointer,
             inferred_dates=inferred, attested_dates=attested, transit_flag_dates=transit,
             exceptional_circumstances_dates=exceptional, child_seen_in_uk_days=len(child_days),
             qualifying_days_not_midnight=qualifying, conflicts=conflicts, edited_dates=edited,
             schengen_days_any_part=sum(1 for d in daterange(start, to) if in_zone(log, d, "SCHENGEN")),
             schengen_midnights=sum(1 for d in daterange(start, to)
                                    if log.row(d) and log.row(d)["midnight_country"] in schengen_members_on(d)))
    return s


def uk_days_for_year(log: DayLog, ty: str, as_of: date) -> tuple[int | None, str]:
    """UK midnights for a tax year: from the log if fully logged, else profile prior_years."""
    start, end = tax_year_bounds(ty)
    first = log.first_date()
    if first and first <= start and as_of >= end:
        s = summarise_year(log, ty, as_of)
        if s["unlogged"] == 0:
            return s["uk_midnights"], "log"
        return s["uk_midnights"], f"log ({s['unlogged']} days not logged)"
    p = log.prior_year(ty)
    if p.get("uk_days") is not None:
        return int(p["uk_days"]), "your onboarding answer"
    if p.get("uk_days_over_90") in ("yes", "no"):
        return (91 if p["uk_days_over_90"] == "yes" else 0), "your onboarding answer (more than 90: " + p["uk_days_over_90"] + ")"
    return None, "not recorded"


def uk_resident_recorded(log: DayLog, ty: str) -> str:
    """The user's own recorded residence status for a year (never computed)."""
    cfg = log.year_config(ty)
    if cfg.get("uk_resident_recorded"):
        return cfg["uk_resident_recorded"]
    return log.prior_year(ty).get("uk_resident", "unsure")


def table_for(log: DayLog, ty: str) -> tuple[str | None, str]:
    prev = [prev_tax_year(ty, n) for n in (1, 2, 3)]
    answers = {p: uk_resident_recorded(log, p) for p in prev}
    if any(a == "yes" for a in answers.values()):
        return "A", f"You recorded UK residence in {', '.join(p for p, a in answers.items() if a == 'yes')}"
    if all(a == "no" for a in answers.values()):
        return "B", "You recorded 'not UK resident' for all of " + ", ".join(prev)
    return None, "Residence status not recorded for: " + ", ".join(p for p, a in answers.items() if a not in ("yes", "no"))


# --------------------------------------------------------------------------
# Ties
# --------------------------------------------------------------------------
def _status(user: str | None, log_shows: bool | None) -> str:
    u = user or "not_answered"
    if u in ("not_answered", "unsure", None):
        if log_shows is None:
            return "Not answered"
        return "Not answered - your log " + ("shows the tie's conditions" if log_shows else "does not show the tie's conditions")
    if log_shows is not None and (u == "yes") != log_shows:
        return "Your answer and your log differ \u2013 review"
    return "Recorded yes" if u == "yes" else "Recorded no"


def evaluate_ties(log: DayLog, ty: str, as_of: date, summary: dict | None = None) -> dict:
    s = summary or summarise_year(log, ty, as_of)
    cfg = log.year_config(ty)
    answers = cfg.get("tie_answers", {})
    out = OrderedDict()

    # Family (RFIG20530)
    fam = cfg.get("family") or log.profile.get("family") or {}
    partner = fam.get("partner_uk_resident")
    kids = fam.get("children_under_18_uk") or []
    kid_resident = [k for k in kids if k.get("uk_resident") == "yes"]
    fam_log = None
    shows = []
    if partner in ("yes", "no"):
        fam_log = partner == "yes"
        shows.append(f"UK-resident spouse/civil/cohabiting partner: {partner}")
    if kids:
        shows.append(f"days you recorded seeing a UK-resident under-18 child in the UK: {s['child_seen_in_uk_days']} (tie needs 61 or more)")
        if kid_resident and s["child_seen_in_uk_days"] >= 61:
            fam_log = True
    elif partner in ("yes", "no"):
        shows.append("no under-18 children recorded")
    out["family"] = {"ref": "RFIG20530", "user_answer": answers.get("family", "not_answered"),
                     "log_shows": "; ".join(shows) or "no family details recorded", "log_indicates": fam_log}

    # Accommodation (RFIG20550): per place, available 91+ continuous days AND nights >= 1 (16 if close relative)
    avail = cfg.get("accommodation_available_91_days", {})
    places = []
    acc_log = None
    for a in log.profile.get("accommodation_register", []):
        if a.get("country") != UK:
            continue
        nights = s["nights_by_accommodation"].get(a["id"], 0)
        need = 16 if a.get("relationship") == "close_relative" else 1
        av = avail.get(a["id"], "not_answered")
        met = None
        if av == "yes":
            met = nights >= need
        elif av == "no":
            met = False
        if met:
            acc_log = True
        elif met is False and acc_log is None:
            acc_log = False
        places.append({"id": a["id"], "label": a.get("label", a["id"]), "relationship": a.get("relationship"),
                       "nights": nights, "nights_needed": need, "available_91_days_answer": av, "conditions_met": met})
    out["accommodation"] = {"ref": "RFIG20550", "user_answer": answers.get("accommodation", "not_answered"),
                            "log_shows": "; ".join(f"{p['label']}: {p['nights']} nights (figure used: {p['nights_needed']}+), available 91+ days: {p['available_91_days_answer'].replace('_', ' ')}"
                                                  for p in places if p["nights"] or p["available_91_days_answer"] != "not_answered") or "no UK accommodation recorded",
                            "log_indicates": acc_log, "places": places}

    # Work (RFIG20560): more than 3 hours on at least 40 days
    wd = s["uk_work_days_over_3h"]
    out["work"] = {"ref": "RFIG20560", "user_answer": answers.get("work", "not_answered"),
                   "log_shows": f"UK work days (>3 hours) logged: {wd}" + (f"; unsure: {s['uk_work_unsure']}" if s["uk_work_unsure"] else "") + " (figure used: 40)",
                   "log_indicates": wd >= 40, "room": 39 - wd, "proximity": proximity(39 - wd)}

    # 90-day (RFIG20570): more than 90 days in either of the previous 2 tax years
    looks = []
    nd_log = False
    unknown = []
    for n in (1, 2):
        p = prev_tax_year(ty, n)
        v, src = uk_days_for_year(log, p, as_of)
        looks.append({"tax_year": p, "uk_days": v, "source": src})
        if v is None:
            unknown.append(p)
        elif v > 90:
            nd_log = True
    if unknown and not nd_log:
        nd_log = None
    out["ninety_day"] = {"ref": "RFIG20570", "user_answer": answers.get("ninety_day", "not_answered"),
                         "log_shows": "; ".join(f"{l['tax_year']}: {l['uk_days'] if l['uk_days'] is not None else 'not recorded'} ({l['source']})" for l in looks) + " (figure used: more than 90)",
                         "log_indicates": nd_log, "looks_back": looks, "missing_years": unknown}

    # Country (RFIG20580): applies only if UK resident in 1+ of previous 3 years; UK wins ties
    table, _ = table_for(log, ty)
    other = [(c, n) for c, n in s["countries"].items() if c != UK]
    top_other = other[0] if other else (None, 0)
    ukn = s["uk_midnights"]
    applies = table == "A"
    ct_log = (ukn >= top_other[1] and ukn > 0) if applies else False
    out["country"] = {"ref": "RFIG20580", "user_answer": answers.get("country", "not_answered"),
                      "applies": applies,
                      "log_shows": (f"Most midnights: {cname(top_other[0])} {top_other[1]}, UK {ukn}" + ("" if s["complete"] else " (year to date)")) if applies else "Country tie applies only if you were UK resident in 1+ of the previous 3 tax years (Table A); not applicable on your recorded answers",
                      "log_indicates": ct_log, "top_other_country": top_other[0], "top_other_midnights": top_other[1],
                      "gap": top_other[1] - ukn}

    for k, v in out.items():
        v["status"] = _status(v["user_answer"], v["log_indicates"])
        v["cite"] = cite(v["ref"])
    # Tie count: user's own answer where given, else the log's indication; unknowns listed separately.
    counted, unknown_ties = [], []
    for k, v in out.items():
        if k == "country" and not v["applies"]:
            continue
        ans = v["user_answer"]
        if ans == "yes":
            counted.append(k)
        elif ans == "no":
            continue
        elif v["log_indicates"] is True:
            counted.append(k)
        elif v["log_indicates"] is None:
            unknown_ties.append(k)
    differ = [k for k, v in out.items() if v["status"].startswith("Your answer and your log differ")]
    return {"ties": out, "recorded_count": len(counted), "counted": counted, "unknown": unknown_ties, "differ": differ}


# --------------------------------------------------------------------------
# Verdict gate and running count
# --------------------------------------------------------------------------
# A stage line ("Your log points to non-resident under the <test>") is a statement about a whole tax year, so it
# is withheld until the year can be counted in full: the year has ended, every day in it is logged, residence for
# the previous 3 tax years is recorded and every applicable tie is answered. Until then the tools return what is
# still missing and a running count of the year so far, which decides nothing.
TIE_LABELS = {"ninety_day": "90-day"}   # the rest are already the words the product uses


def gate_items(s: dict, t: dict, table: str | None) -> list[dict]:
    """One item per gate condition: `done`, a short `label` for a checklist and the `detail` sentence."""
    n = s["unlogged"]
    unanswered = [k for k, v in t["ties"].items()
                  if not (k == "country" and not v.get("applies")) and v.get("user_answer") not in ("yes", "no")]
    return [
        {"key": "year_ended", "done": s["complete"],
         "label": "Tax year ended" if s["complete"] else f"Tax year ends {fmt_date(s['end'])}",
         "detail": f"the tax year is still running (it ends on {fmt_date(s['end'])})"},
        {"key": "days_logged", "done": not n,
         "label": "Every day logged" if not n else f"{n} day{'s' if n != 1 else ''} to log",
         "detail": f"{n} day{'s are' if n != 1 else ' is'} not logged"},
        {"key": "prior_years", "done": table is not None,
         "label": "Previous 3 years recorded" if table else "Previous 3 years to record",
         "detail": "residence for the previous 3 tax years is not recorded"},
        {"key": "ties_answered", "done": not unanswered,
         "label": "Ties answered" if not unanswered else f"{len(unanswered)} tie{'s' if len(unanswered) != 1 else ''} to answer",
         "detail": "ties not answered: " + ", ".join(TIE_LABELS.get(k, k) for k in unanswered)},
    ]


def verdict_gate(s: dict, t: dict, table: str | None) -> list[str]:
    """Reasons a stage line must NOT be returned. Empty list = every condition met."""
    return [i["detail"] for i in gate_items(s, t, table) if not i["done"]]


def applicable_figures(s: dict, table: str | None, ties_block: dict, overseas_claim: str = "not_answered") -> list[dict]:
    """The HMRC figures that apply to this year's recorded facts, each with the room left before it.

    `room` follows the convention used everywhere else in the engine: the number of days that can still be added
    before the figure is reached. `next` marks the nearest UK-day figure still ahead, which is the one the
    dashboard and the export put their progress bar against."""
    days = s["uk_midnights"]
    figs = []
    if table in ("A", None):
        figs.append({"figure": 16, "counted": days, "unit": "UK days", "test": "first automatic overseas test",
                     "text": "fewer than 16 UK days: first automatic overseas test"
                             + ("" if table == "A" else " (applies if you were UK resident in 1 or more of the previous 3 tax years)"),
                     "ref": "RFIG20120"})
    if table in ("B", None):
        figs.append({"figure": 46, "counted": days, "unit": "UK days", "test": "second automatic overseas test",
                     "text": "fewer than 46 UK days: second automatic overseas test"
                             + ("" if table == "B" else " (applies if you were not UK resident in any of the previous 3 tax years)"),
                     "ref": "RFIG20130"})
    if overseas_claim == "yes":
        figs.append({"figure": 91, "counted": days, "unit": "UK days", "test": "third automatic overseas test",
                     "text": "fewer than 91 UK days: third automatic overseas test (on your own recorded full-time overseas work answer)",
                     "ref": "RFIG20140"})
        figs.append({"figure": 31, "counted": s["uk_work_days_over_3h"], "unit": "UK work days",
                     "test": "third automatic overseas test",
                     "text": "fewer than 31 UK work days of more than 3 hours: third automatic overseas test",
                     "ref": "RFIG20140"})
    line = ties_block.get("line")
    if line is not None and line != 182:
        n = ties_block.get("recorded_ties", 0)
        ties = f"{n} recorded tie{'s' if n != 1 else ''}"
        figs.append({"figure": line + 1, "counted": ties_block.get("uk_days_used", days), "unit": "UK days",
                     "test": f"ties-test line for {ties}",
                     "text": f"more than {line} UK days: RDR3 Table {ties_block.get('table')} pairs that with {ties}",
                     "ref": "RFIG20520"})
    figs.append({"figure": 183, "counted": days, "unit": "UK days", "test": "first automatic UK test",
                 "text": "183 UK days: first automatic UK test", "ref": "RFIG20320"})
    for f in figs:
        f["room"] = f["figure"] - 1 - f["counted"]
        f["room_text"] = (f"{f['room']} {f['unit']} of room before {f['figure']}: {f['test']}" if f["room"] >= 0
                          else f"{-f['room']} {f['unit']} past {f['figure']}: {f['test']}")
        f["cite"] = cite(f["ref"])
        f["next"] = False
    ahead = [f for f in figs if f["unit"] == "UK days" and f["room"] >= 0]
    if ahead:
        min(ahead, key=lambda f: f["room"])["next"] = True
    return figs


def running_count(s: dict, table: str | None, ties_block: dict, overseas_claim: str = "not_answered") -> dict:
    """The year so far against the HMRC figures that apply to it, and the year-end date. Never a verdict."""
    days = s["uk_midnights"]
    figs = applicable_figures(s, table, ties_block, overseas_claim)
    text = (f"Your log so far: {days} UK midnight{'s' if days != 1 else ''} from {fmt_date(s['start'])} to {fmt_date(s['counted_to'])} "
            f"({s['logged']} of {s['days_in_year_to_date']} days logged). "
            f"The tax year {'ended' if s['complete'] else 'ends'} on {fmt_date(s['end'])}.")
    return {"uk_midnights": days, "counted_to": s["counted_to"], "year_ends": s["end"], "logged": s["logged"],
            "days_in_year_to_date": s["days_in_year_to_date"], "figures": figs,
            "next_figure": next((f for f in figs if f["next"]), None), "text": text}


# --------------------------------------------------------------------------
# SRT reference view (stage order, no verdicts)
# --------------------------------------------------------------------------
def srt_reference(log: DayLog, ty: str, as_of: date, thresholds: dict | None = None) -> dict:
    s = summarise_year(log, ty, as_of)
    t = evaluate_ties(log, ty, as_of, s)
    cfg = log.year_config(ty)
    table, table_reason = table_for(log, ty)
    days = s["uk_midnights"]
    lines = []   # approved-phrasing statements
    notes = []
    figures = []

    # Deeming rule (RFIG20720): recorded, applied only when the log supports every condition.
    deemed = 0
    q = len(s["qualifying_days_not_midnight"])
    if table == "A" and t["recorded_count"] >= 3 and q > 30:
        deemed = q - 30
        notes.append(f"Deeming rule conditions appear in your log: {q} days in the UK without a UK midnight. "
                     f"RFIG20720 adds the {deemed} days above 30 to the count used for the ties test. {cite('RFIG20720')}")
    elif q:
        notes.append(f"{q} days in the UK without a UK midnight are recorded. The deeming rule is not applied: "
                     f"its conditions (Table A, 3+ ties, more than 30 such days) are not all shown in your log. {cite('RFIG20720')}")
    ties_days = days + deemed
    if s["transit_flag_dates"]:
        notes.append(f"{len(s['transit_flag_dates'])} UK days are flagged as transit (RFIG20730). They are included in the count; the transit exception is recorded, not applied.")
    if s["exceptional_circumstances_dates"]:
        notes.append(f"{len(s['exceptional_circumstances_dates'])} UK days carry an exceptional-circumstances note (RFIG22220). They are included in the count; nothing is deducted.")
    if cfg.get("split_year_claimed") in ("yes", "unsure"):
        notes.append(f"You recorded a possible split year ({cfg['split_year_claimed']}). Split-year treatment is recorded, not calculated. {cite('RFIG21000')}")
    if s["unlogged"]:
        notes.append(f"{s['unlogged']} days in {ty} are not logged yet. Every count for the year may change once they are.")

    # Reference figures strip (RDR3): 16, 46, 91, 121, 183
    for fig, ref in ((16, "RFIG20120"), (46, "RFIG20130"), (91, "RFIG20140"), (121, "RFIG20520"), (183, "RFIG20320")):
        figures.append({"figure": fig, "distance": fig - days, "ref": ref})

    auto_uk = []
    if days >= 183:
        auto_uk.append("first")
        lines.append(f"Your UK midnights ({days}) are at or above 183, the figure used in the first automatic UK test. "
                     f"Take your records to a qualified adviser. {l4('RFIG20320')}")
    home = cfg.get("only_home_in_uk_answer", "not_answered")
    ftuk = cfg.get("full_time_uk_work_answer", "not_answered")
    if home != "no":
        auto_uk.append("second (recorded answer: " + home + ")")
    if ftuk != "no":
        auto_uk.append("third (recorded answer: " + ftuk + ")")

    pointer = None
    # Automatic overseas tests
    if table == "A" and days < 16:
        pointer = "first automatic overseas test"
        ref = "RFIG20120"
    elif table == "B" and days < 46:
        pointer = "second automatic overseas test"
        ref = "RFIG20130"
    else:
        ref = None
    ft = cfg.get("overseas_full_time_work_claimed", "not_answered")
    third_ok = days < 91 and s["uk_work_days_over_3h"] < 31
    third = {"uk_days": days, "uk_days_room": 90 - days, "uk_work_days": s["uk_work_days_over_3h"],
             "work_room": 30 - s["uk_work_days_over_3h"], "full_time_claim": ft,
             "day_figures_within": third_ok}
    if pointer is None and ft == "yes" and third_ok and not auto_uk:
        pointer = "third automatic overseas test"
        ref = "RFIG20140"
    stage_lines = []
    if pointer:
        stage_lines.append({"test": pointer, "ref": ref,
                            "text": f"Your log points to non-resident under the {pointer}."
                                    + (" (Day and work-day figures from your log; the full-time overseas work condition is your own recorded answer and is not calculated.)" if ref == "RFIG20140" else ""),
                            "disclaimer": l4(ref)})

    # Ties test (always shown as reference, even when an automatic test is also indicated)
    ties_block = {"table": table, "table_reason": table_reason, "uk_days_used": ties_days,
                  "recorded_ties": t["recorded_count"], "counted": t["counted"], "unknown": t["unknown"]}
    if table:
        band = band_for(table, ties_days)
        need = band["ties_needed"] if band else None
        line = line_for_ties(table, t["recorded_count"])
        ties_block.update(band=band, ties_needed=need, line=line)
        if line is not None:
            room = line - ties_days
            ties_block.update(room=room, proximity=proximity(room, thresholds))
            ties_block["room_text"] = (f"{room} days of room before the {line}-day line for {t['recorded_count']} tie{'s' if t['recorded_count'] != 1 else ''}"
                                       if room >= 0 else f"{-room} days over the {line}-day line for {t['recorded_count']} tie{'s' if t['recorded_count'] != 1 else ''}")
        else:
            room = 182 - days
            ties_block.update(room=room, proximity=proximity(room, thresholds), line=182)
            ties_block["room_text"] = (f"No day count in Table {table} is paired with {t['recorded_count']} recorded ties; "
                                       f"{room} days of room before 183, the first automatic UK test figure")
        if need is None:
            ties_block["band_text"] = (f"{ties_days} UK days is below Table {table}'s first band "
                                       f"({'more than 15' if table == 'A' else 'more than 45'} days).")
        else:
            ties_block["band_text"] = f"RDR3 Table {table} pairs {band['label']} days with at least {need} ties; your log records {t['recorded_count']}."
        insufficient = need is None or t["recorded_count"] + len(t["unknown"]) < need
        if not auto_uk and insufficient:
            stage_lines.append({"test": "sufficient ties test", "ref": "RFIG20520",
                                "text": "Your log points to non-resident under the sufficient ties test.",
                                "disclaimer": l4("RFIG20520")})
        elif not auto_uk and t["unknown"] and t["recorded_count"] < (need or 0):
            notes.append("Unanswered ties (" + ", ".join(t["unknown"]) + ") could change the ties test reference. Answer them to complete the record.")
        elif not auto_uk:
            notes.append(f"Recorded ties ({t['recorded_count']}) are at or above the number Table {table} pairs with {band['label']} UK days. "
                         f"Take your records to a qualified adviser. {l4('RFIG20520')}")
    else:
        notes.append("Table A or B can't be chosen until you record your residence status for the previous 3 tax years.")
    if auto_uk and days < 183:
        notes.append("Automatic UK tests 2 and 3 rely on your own answers; not recorded as 'no': " + ", ".join(auto_uk) + ". No pointer is shown until they are.")

    # The verdict gate: no stage line for a year that cannot yet be counted in full, whatever the pointer above says.
    gate = gate_items(s, t, table)
    withheld = [i["detail"] for i in gate if not i["done"]]
    applicable = applicable_figures(s, table, ties_block, ft)
    running = None
    if withheld:
        stage_lines = []
        running = running_count(s, table, ties_block, ft)

    # Next year's 90-day tie
    next_ty = f"{int(ty[:4]) + 1}/{str(int(ty[:4]) + 2)[-2:]}"
    ninety_next = {"for_tax_year": next_ty, "uk_days": days, "room": 90 - days, "proximity": proximity(90 - days, thresholds),
                   "text": (f"{90 - days} days of room before the 90-day line for a 90-day tie in {next_ty}" if days <= 90
                            else f"{days - 90} days over the 90-day line: {ty} would count towards a 90-day tie in {next_ty} and the year after"),
                   "cite": cite("RFIG20570")}
    return {"tax_year": ty, "summary": s, "ties": t, "ties_test": ties_block, "third_automatic_overseas": third,
            "automatic_uk_open": auto_uk, "stage_lines": stage_lines, "verdict_withheld": withheld,
            "gate": gate, "applicable_figures": applicable, "running_count": running, "notes": notes,
            "figures": figures, "ninety_day_next_year": ninety_next, "work_tie": t["ties"]["work"], "l6": L6}


# --------------------------------------------------------------------------
# Schengen and stay limits
# --------------------------------------------------------------------------
SCHENGEN_DEFAULT = {"AT": None, "BE": None, "BG": "2025-01-01", "HR": "2023-01-01", "CZ": None, "DK": None, "EE": None,
                    "FI": None, "FR": None, "DE": None, "GR": None, "HU": None, "IS": None, "IT": None, "LV": None,
                    "LI": None, "LT": None, "LU": None, "MT": None, "NL": None, "NO": None, "PL": None, "PT": None,
                    "RO": "2025-01-01", "SK": None, "SI": None, "ES": None, "SE": None, "CH": None}
_SCHENGEN = dict(SCHENGEN_DEFAULT)
_RULES: list[dict] = []


def set_rules(rules: list[dict]) -> None:
    """Install country rules; the SCHENGEN row's members (with join dates) drive zone membership."""
    global _RULES, _SCHENGEN
    _RULES = rules
    for r in rules:
        if r.get("zone") == "SCHENGEN" and r.get("members"):
            _SCHENGEN = {m["code"]: m.get("from") for m in r["members"]}


# The engine ships a baseline country-rules table at <engine>/schema/country-rules.json. The user's own copy lives
# in their data folder and is the one the weekly travel-rules watch updates, so it wins unless --rules says otherwise.
SHIPPED_RULES_FILE = ENGINE_ROOT / "schema" / "country-rules.json"
USER_RULES_FILE = "~/nomad-pro-data/country-rules.json"
RULES_HELP = ("country-rules JSON; default: $NOMAD_PRO_DATA/country-rules.json, else ~/nomad-pro-data/country-rules.json, "
              "else <engine>/schema/country-rules.json")


def default_rules_path(explicit: str | Path | None = None) -> Path | None:
    """The country-rules file to use, in order: --rules if given (None if that path does not exist, so a wrong
    path never silently reads a different table), else $NOMAD_PRO_DATA/country-rules.json, else
    ~/nomad-pro-data/country-rules.json, else the engine's shipped schema/country-rules.json (None if absent)."""
    if explicit:
        p = Path(explicit).expanduser()
        return p if p.exists() else None
    data_dir = os.environ.get("NOMAD_PRO_DATA")
    cands = [Path(data_dir) / "country-rules.json"] if data_dir else []
    cands += [Path(USER_RULES_FILE), SHIPPED_RULES_FILE]
    for c in cands:
        p = Path(c).expanduser()
        if p.exists():
            return p
    return None


def load_rules(path: str | Path | None) -> list[dict]:
    if not path:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rules = data["rules"] if isinstance(data, dict) else data
    set_rules(rules)
    return rules


def schengen_members_on(d: date) -> set[str]:
    return {c for c, f in _SCHENGEN.items() if f is None or parse_date(f) <= d}


def in_zone(log: DayLog, d: date, zone: str) -> bool:
    pres = log.present(d)
    if zone == "SCHENGEN":
        m = schengen_members_on(d)
        return any(c in m for c in pres)
    return zone in pres


def rolling_status(log: DayLog, on: date, zone: str = "SCHENGEN", limit: int = 90, window: int = 180) -> dict:
    ws = on - timedelta(days=window - 1)
    used_days = [d for d in daterange(ws, on) if in_zone(log, d, zone)]
    unlogged = sum(1 for d in daterange(ws, on) if not log.row(d))
    used = len(used_days)
    nxt = (used_days[0] + timedelta(days=window)) if used_days else None
    return {"zone": zone, "on": on.isoformat(), "window_start": ws.isoformat(), "used": used, "limit": limit,
            "room": limit - used, "proximity": proximity(limit - used), "unlogged_in_window": unlogged,
            "earliest_drop_off": nxt.isoformat() if nxt else None,
            "text": f"{'Schengen' if zone == 'SCHENGEN' else cname(zone)}: {used} of {limit} days in the {window} days to {fmt_date(on)}."}


def max_stay_from(log: DayLog, entry: date, zone: str = "SCHENGEN", limit: int = 90, window: int = 180) -> int:
    """Longest continuous stay (any part of day) starting on `entry`, before a window would exceed `limit`."""
    tmp = DayLog(copy.deepcopy(log.data))
    n = 0
    d = entry
    code = next(iter(schengen_members_on(entry))) if zone == "SCHENGEN" else zone
    while n < 400:
        tmp.days[d] = {"date": d.isoformat(), "midnight_country": code, "countries_present": [code], "confidence": "planned"}
        if rolling_status(tmp, d, zone, limit, window)["used"] > limit:
            break
        n += 1
        d += timedelta(days=1)
    return n


def schengen_series(log: DayLog, start: date, end: date) -> list[tuple[str, int]]:
    return [(d.isoformat(), rolling_status(log, d)["used"]) for d in daterange(start, end)]


def current_stay(log: DayLog, code: str, on: date) -> tuple[date | None, int]:
    if code not in log.present(on):
        return None, 0
    d = on
    while code in log.present(d - timedelta(days=1)):
        d -= timedelta(days=1)
    return d, (on - d).days + 1


def entries_in_calendar_year(log: DayLog, code: str, year: int, until: date | None = None) -> list[str]:
    out = []
    end = min(date(year, 12, 31), until) if until else date(year, 12, 31)
    for d in daterange(date(year, 1, 1), end):
        if code in log.present(d) and code not in log.present(d - timedelta(days=1)):
            if log.row(d - timedelta(days=1)) or d == date(year, 1, 1):
                out.append(d.isoformat())
            else:
                out.append(d.isoformat() + " (previous day not logged)")
    return out


def rule_applicable(rule: dict, entry: date | None) -> dict:
    """Pick the rule version in force for an entry date (e.g. TH 60 days before 15 Sep 2026, 30 after)."""
    if entry and rule.get("previous") and rule.get("effective_from") and entry < parse_date(rule["effective_from"]):
        prev = dict(rule)
        prev.update(rule["previous"])
        return prev
    return rule


def country_limit_status(log: DayLog, on: date, rules: list[dict] | None = None) -> list[dict]:
    rules = rules if rules is not None else _RULES
    out = []
    for r in rules:
        z = r["zone"]
        if r.get("rule") == "rolling":
            if z != "SCHENGEN" and z in schengen_members_on(on):
                continue  # e.g. Cyprus once Schengen accession takes effect
            st = rolling_status(log, on, z, r["limit_days"], r.get("window_days", 180))
            st.update(rule_id=r["id"], name=r.get("name", z), source_url=r["source_url"], last_verified=r["last_verified"])
            out.append(st)
        elif r.get("rule") in ("per_entry", "visa_per_entry"):
            entry, n = current_stay(log, z, on)
            rr = rule_applicable(r, entry)
            item = {"rule_id": r["id"], "zone": z, "name": r.get("name", z), "on": on.isoformat(), "in_country": bool(entry),
                    "source_url": r["source_url"], "last_verified": r["last_verified"], "limit": rr["limit_days"]}
            if entry:
                last = entry + timedelta(days=rr["limit_days"] - 1)
                item.update(entry=entry.isoformat(), days_used=n, room=rr["limit_days"] - n,
                            proximity=proximity(rr["limit_days"] - n), last_day_of_limit=last.isoformat(),
                            text=f"{r.get('name', z)}: day {n} of {rr['limit_days']} since entry on {fmt_date(entry)} (limit counted to {fmt_date(last)}).")
            if r.get("max_entries_per_calendar_year"):
                ents = entries_in_calendar_year(log, z, on.year, on)
                item.update(entries_this_year=ents, max_entries=r["max_entries_per_calendar_year"])
            out.append(item)
    return out


# --------------------------------------------------------------------------
# Trip modelling
# --------------------------------------------------------------------------
def apply_trips(log: DayLog, trips: list[dict]) -> DayLog:
    """Return a copy of the log with planned trips as days. Trip = {country, from: first night, to: last night}."""
    data = copy.deepcopy(log.data)
    tmp = DayLog(data)
    for t in sorted(trips, key=lambda x: x["from"]):
        a, b = parse_date(t["from"]), parse_date(t["to"])
        before = tmp.row(a - timedelta(days=1))
        prev_c = before["midnight_country"] if before else None
        for d in daterange(a, b):
            pres = [t["country"]]
            if d == a and prev_c and prev_c != t["country"]:
                pres = [prev_c, t["country"]]
            tmp.days[d] = {"date": d.isoformat(), "tax_year": tax_year_of(d), "midnight_country": t["country"],
                           "countries_present": pres, "confidence": "planned", "evidence": [],
                           "uk_work": {"over_3h": t.get("uk_work_over_3h", "n/a")}}
        nxt = tmp.row(b + timedelta(days=1))
        if nxt and nxt["midnight_country"] != t["country"]:
            nxt = dict(nxt)
            cp = list(nxt.get("countries_present") or [nxt["midnight_country"]])
            if t["country"] not in cp:
                cp.insert(0, t["country"])
            nxt["countries_present"] = cp
            tmp.days[b + timedelta(days=1)] = nxt
    return tmp


def plan(log: DayLog, trips: list[dict], as_of: date, rules: list[dict] | None = None) -> dict:
    after = apply_trips(log, trips)
    end = max(parse_date(t["to"]) for t in trips) + timedelta(days=1)
    years = sorted({tax_year_of(parse_date(t["from"])) for t in trips} | {tax_year_of(parse_date(t["to"])) for t in trips})
    res = {"trips": trips, "years": [], "limits_at_trip_end": [], "l8": L8, "l6": L6}
    for ty in years:
        s_end = tax_year_bounds(ty)[1]
        before_ref = srt_reference(log, ty, s_end)
        after_ref = srt_reference(after, ty, s_end)
        res["years"].append({"tax_year": ty,
                             "uk_midnights_before": before_ref["summary"]["uk_midnights"],
                             "uk_midnights_with_plan": after_ref["summary"]["uk_midnights"],
                             "ties_test_with_plan": {k: after_ref["ties_test"].get(k) for k in ("table", "recorded_ties", "line", "room", "proximity", "room_text", "band_text")},
                             "ninety_day_next_year_with_plan": after_ref["ninety_day_next_year"],
                             "country_tie_with_plan": after_ref["ties"]["ties"]["country"]["log_shows"],
                             "work_days_with_plan": after_ref["summary"]["uk_work_days_over_3h"],
                             "days_not_logged_or_planned": after_ref["summary"]["unlogged"]})
    for t in trips:
        last = parse_date(t["to"])
        dep = last + timedelta(days=1)  # departure day: present for part of the day, so it counts
        dep_logged = after.row(dep) is not None
        tend = dep if dep_logged else last
        for st in country_limit_status(after, tend, rules):
            if not dep_logged and st.get("zone") in (t["country"], "SCHENGEN"):
                if st.get("used") is not None and (st["zone"] == t["country"] or t["country"] in schengen_members_on(dep)):
                    st["used"] += 1
                    st["room"] = st["limit"] - st["used"]
                    st["proximity"] = proximity(st["room"])
                    st["text"] = (f"{'Schengen' if st['zone'] == 'SCHENGEN' else cname(st['zone'])}: {st['used']} of {st['limit']} days "
                                  f"in the 180 days to {fmt_date(dep)} (departure day included).")
                elif st.get("days_used") is not None:
                    st["days_used"] += 1
                    st["room"] = st["limit"] - st["days_used"]
                    st["proximity"] = proximity(st["room"])
                    st["text"] = (f"{st['name']}: day {st['days_used']} of {st['limit']} since entry on {fmt_date(st['entry'])} "
                                  f"on departure day {fmt_date(dep)} (limit counted to {fmt_date(st['last_day_of_limit'])}).")
            z = st.get("zone")
            if z == t["country"] or (z == "SCHENGEN" and t["country"] in schengen_members_on(tend)):
                st["trip"] = f"{t['country']} {t['from']}\u2192{t['to']}"
                res["limits_at_trip_end"].append(st)
    return res


# --------------------------------------------------------------------------
# Stays (derived: consecutive same-country midnights) and open questions
# --------------------------------------------------------------------------
def stays(log: DayLog, start: date, end: date) -> list[dict]:
    out = []
    cur = None
    for d in daterange(start, end):
        r = log.row(d)
        key = (r["midnight_country"], r.get("midnight_place") or "") if r else ("UNLOGGED", "")
        if cur and cur["key"] == key and (parse_date(cur["to"]) + timedelta(days=1)) == d:
            cur["to"] = d.isoformat()
            cur["nights"] += 1
            if r:
                for e in r.get("evidence", []):
                    if e.get("pointer") and e["pointer"] not in cur["pointers"]:
                        cur["pointers"].append(e["pointer"])
                cur["confidence"].add(r.get("confidence"))
        else:
            cur = {"key": key, "country": key[0], "place": key[1], "from": d.isoformat(), "to": d.isoformat(), "nights": 1,
                   "pointers": [e["pointer"] for e in (r or {}).get("evidence", []) if e.get("pointer")],
                   "confidence": {r.get("confidence")} if r else {"unlogged"}}
            out.append(cur)
    for c in out:
        c["confidence"] = sorted(x for x in c["confidence"] if x)
        c.pop("key")
    return out


def open_questions(log: DayLog, ty: str, as_of: date) -> list[str]:
    ref = srt_reference(log, ty, as_of)
    s, t = ref["summary"], ref["ties"]
    qs = []
    if s["unlogged"]:
        qs.append(f"{s['unlogged']} days in {ty} are not logged yet ({_ranges(s['unlogged_dates'])}). Where were you?")
    if s["no_pointer_dates"]:
        qs.append(f"{len(s['no_pointer_dates'])} logged days have no record pointer. HMRC could ask what shows where you were.")
    if s["inferred_dates"]:
        qs.append(f"{len(s['inferred_dates'])} days are marked inferred ({_ranges(s['inferred_dates'])}). Can you add a pointer that shows those nights?")
    if s["attested_dates"]:
        qs.append(f"{len(s['attested_dates'])} days rest on your own statement ({_ranges(s['attested_dates'])}). Is there anything that shows them (booking, ticket, card spend)?")
    if s["uk_work_unsure"]:
        qs.append(f"{s['uk_work_unsure']} UK days have work marked 'unsure'. Did you work more than 3 hours on them? (Work takes its everyday meaning, RFIG20740; RFIG21930 lists reviewing and responding to emails as work activity to record.)")
    inf = work_inferred_dates(log, ty)
    if inf:
        qs.append(f"{len(inf)} UK work days in {ty} have no answer from you and no agreed work-day rule behind them ({_ranges(inf)}). Did you work more than 3 hours on each of them?")
    wr = work_rule_report(log, ty, as_of)
    if wr["disagree"]:
        dd = [x["date"] for x in wr["disagree"]]
        qs.append(f"{len(dd)} days in {ty} differ from your work-day rule ({_ranges(dd)}). Keep the log as it is, or follow the rule?")
    for k in t["differ"]:
        v = t["ties"][k]
        qs.append(f"{k.replace('_', '-')} tie: your answer ({v['user_answer']}) and your log ({v['log_shows']}) differ. {v['cite']}")
    nd = t["ties"]["ninety_day"]
    if nd["missing_years"]:
        qs.append(f"90-day tie: UK days not recorded for {', '.join(nd['missing_years'])} (your answer: {nd['user_answer'].replace('_', ' ')}). HMRC could ask for the count. {nd['cite']}")
    for k in t["unknown"]:
        v = t["ties"][k]
        if k != "ninety_day":
            qs.append(f"{k.replace('_', '-')} tie: not answered. {v['cite']}")
    for c in s["conflicts"]:
        qs.append(f"Records for {c['date']} point to two different places ({c.get('detail', '')}). Resolution recorded: {c.get('resolution', 'none')}.")
    return qs


def _ranges(dates: list[str]) -> str:
    if not dates:
        return ""
    ds = sorted(parse_date(x) for x in dates)
    out, a, b = [], ds[0], ds[0]
    for d in ds[1:]:
        if d == b + timedelta(days=1):
            b = d
        else:
            out.append((a, b))
            a = b = d
    out.append((a, b))
    return ", ".join(fmt_date(x) if x == y else f"{fmt_date(x)} \u2013 {fmt_date(y)}" for x, y in out)


ranges = _ranges


# --------------------------------------------------------------------------
# Work status provenance: the user's answer, or the work-day rule they agreed
# --------------------------------------------------------------------------
# Calendar, email, booking or card records place the user somewhere; on their own
# they never say whether the user worked. UK work (over_3h) is set either from the
# user's own answer (source "user_answer") or from a WORK-DAY RULE the user agreed
# in plain words and that is saved, versioned, in profile.work_day_rules (source
# "rule:<id>", plus the calendar event/keyword when an exception applied). A UK
# day that no rule covers, and that the user has not answered, stays "unsure".
_INFERRED_WORK = re.compile(r"calendar[- ]?(confirmed|presence|inferred|shows? (uk )?presence)|no exclusion event|"
                            r"inferred from (the )?(calendar|email|booking|presence)|presence implies work", re.I)
RULE_CHOICES = ("work", "no_work", "ask")
WORK_TRAVEL_CHOICES = ("ask", "work", "travel_day")   # travel day tagged as travelling for work
DEFAULT_WORK_TRAVEL_KEYWORDS = ("work trip", "business trip", "conference", "client meeting", "work event", "offsite")
EXCEPTION_MEANS = {"no_work": "no", "under_3h": "no", "work": "yes", "ask": "unsure"}
_CHOICE_VALUE = {"work": "yes", "no_work": "no", "ask": "unsure"}

# England & Wales bank holidays (GOV.UK /bank-holidays). Extend yearly, or give
# a rule its own "public_holiday_dates" list.
BANK_HOLIDAYS = {"england-and-wales": {
    "2024-01-01", "2024-03-29", "2024-04-01", "2024-05-06", "2024-05-27", "2024-08-26", "2024-12-25", "2024-12-26",
    "2025-01-01", "2025-04-18", "2025-04-21", "2025-05-05", "2025-05-26", "2025-08-25", "2025-12-25", "2025-12-26",
    "2026-01-01", "2026-04-03", "2026-04-06", "2026-05-04", "2026-05-25", "2026-08-31", "2026-12-25", "2026-12-28",
    "2027-01-01", "2027-03-26", "2027-03-29", "2027-05-03", "2027-05-31", "2027-08-30", "2027-12-27", "2027-12-28",
}}


def _rows(data_or_log) -> list[dict]:
    return data_or_log.data.get("days", []) if isinstance(data_or_log, DayLog) else data_or_log.get("days", [])


def _profile(data_or_log) -> dict:
    d = data_or_log.data if isinstance(data_or_log, DayLog) else data_or_log
    return d.get("profile") or {}


def work_day_rules(data_or_log) -> list[dict]:
    return list(_profile(data_or_log).get("work_day_rules") or [])


def _in(d: str, a: str | None, b: str | None) -> bool:
    return (a is None or a <= d) and (b is None or d <= b)


def rule_for(data_or_log, d: date | str, rule_id: str | None = None) -> dict | None:
    """The agreed rule in force on d (or the named rule, if it covers d)."""
    ds = d.isoformat() if isinstance(d, date) else d
    for r in work_day_rules(data_or_log):
        if rule_id is not None and r.get("id") != rule_id:
            continue
        if _in(ds, r.get("effective_from"), r.get("effective_to")):
            return r
    return None


def _exception_for(rule: dict, text: str) -> dict | None:
    t = (text or "").lower()
    for ex in rule.get("exceptions") or []:
        for k in [ex.get("keyword", "")] + list(ex.get("aliases") or []):
            if k and k.lower() in t:
                return ex
    return None


def work_travel_keyword(rule: dict, text: str) -> str | None:
    t = (text or "").lower()
    for k in rule.get("work_travel_keywords") or DEFAULT_WORK_TRAVEL_KEYWORDS:
        if k and k.lower() in t:
            return k
    return None


def is_work_travel(rule: dict, row: dict, calendar_text: str = "") -> bool:
    """A travel day tagged as travelling for work: by the user's answer or a recorded tag
    (uk_work.work_travel), or by a work-travel keyword in the calendar text."""
    if (row.get("uk_work") or {}).get("work_travel"):
        return True
    return work_travel_keyword(rule, calendar_text) is not None


def rule_outcome(rule: dict, row: dict, calendar_text: str = "") -> tuple[str, str, dict | None]:
    """What the agreed rule gives for a day: (over_3h, basis, exception or None).

    over_3h is yes / no / unsure / n/a. Only the countries of the day and the date are
    used, plus the calendar text for exception keywords."""
    ds = row["date"]
    d = parse_date(ds)
    present = row.get("countries_present") or [row.get("midnight_country")]
    if row.get("midnight_country") != "GB" and "GB" not in present:
        return "n/a", "not in the UK", None
    # a travel day: flying (or otherwise travelling) into or out of the UK, so the UK and another country that day
    travel = any(c != "GB" for c in present) or row.get("midnight_country") != "GB"
    for p in rule.get("no_job_periods") or []:
        if _in(ds, p.get("from"), p.get("to")):
            return "no", "no job in this period", None
    jobs = rule.get("job_periods")
    if jobs is not None and not any(_in(ds, p.get("from"), p.get("to")) for p in jobs):
        return _CHOICE_VALUE.get(rule.get("outside_periods", "ask"), "unsure"), "outside the job periods in the rule", None
    ex = _exception_for(rule, calendar_text) if calendar_text else None
    if ex is not None:
        return EXCEPTION_MEANS.get(ex.get("means", "ask"), "unsure"), f"calendar exception '{ex.get('keyword')}'", ex
    if travel:
        if is_work_travel(rule, row, calendar_text):
            wt = rule.get("work_travel") or "ask"
            if wt == "work":
                return "yes", "travelling for work (counted as a work day under the rule)", None
            if wt == "travel_day":
                return _CHOICE_VALUE.get(rule.get("travel_days", "ask"), "unsure"), "travelling for work (follows the travel-day setting)", None
            return "unsure", "travelling for work (ask each time)", None
        return _CHOICE_VALUE.get(rule.get("travel_days", "ask"), "unsure"), "travel day into or out of the UK", None
    if d.weekday() >= 5:
        return _CHOICE_VALUE.get(rule.get("weekends", "ask"), "unsure"), "weekend", None
    hol = set(rule.get("public_holiday_dates") or []) | BANK_HOLIDAYS.get(rule.get("public_holiday_region", "england-and-wales"), set())
    if ds in hol and rule.get("public_holidays", "ask") != "as_weekday":
        return _CHOICE_VALUE.get(rule.get("public_holidays", "ask"), "unsure"), "public holiday", None
    return _CHOICE_VALUE.get(rule.get("weekdays", "ask"), "unsure"), "weekday", None


def apply_work_rule(data_or_log, row: dict, calendar_titles: list[str] | None = None) -> dict:
    """uk_work for a day from the agreed rule (used by check-in, catch-up, weekly review, import).

    Calendar titles are only matched against the rule's exception keywords. With no
    rule in force, a UK day is left 'unsure' (ask the user)."""
    rule = rule_for(data_or_log, row["date"])
    text = " | ".join(calendar_titles or [])
    if rule is None:
        return uk_work_unanswered(row.get("midnight_country"))
    val, basis, ex = rule_outcome(rule, row, text)
    out = {"over_3h": val, "hours": None, "note": f"Work-day rule {rule.get('id')}: {basis}",
           "source": f"rule:{rule.get('id')}" if val != "unsure" else "not_asked"}
    if ex is not None:
        hit = next((t for t in (calendar_titles or []) if _exception_for(rule, t)), text)
        out["exception"] = {"keyword": ex.get("keyword"), "event": hit}
    elif "travelling for work" in basis:
        tag = (row.get("uk_work") or {}).get("work_travel")
        if not tag:
            hit = next((t for t in (calendar_titles or []) if work_travel_keyword(rule, t)), text)
            tag = {"keyword": work_travel_keyword(rule, hit), "event": hit}
        out["work_travel"] = tag
    return out


def uk_work_unanswered(country: str | None, note: str = "") -> dict:
    """uk_work for a day proposed from records when no rule covers it: a question, never a work day."""
    if country == "GB":
        return {"over_3h": "unsure", "hours": None, "note": note or "Not asked yet: ask whether you worked more than 3 hours",
                "source": "not_asked"}
    return {"over_3h": "n/a", "hours": None, "note": note, "source": "not_asked"}


def uk_work_from_answer(answer: str, hours: float | None = None, note: str = "") -> dict:
    """uk_work from the user's own answer ('yes' / 'no' / 'unsure')."""
    if answer not in ("yes", "no", "unsure"):
        raise ValueError(f"uk_work answer must be yes/no/unsure, got {answer!r}")
    if hours is not None and answer == "yes" and hours <= 3:
        raise ValueError("over_3h yes but hours <= 3")
    return {"over_3h": answer, "hours": hours, "note": note, "source": "user_answer"}


def work_source_of(row: dict) -> str:
    """'user_answer', 'rule', 'rule_exception', 'not_asked' or 'unrecorded' (legacy entry with no source)."""
    w = row.get("uk_work") or {}
    src = w.get("source")
    if src == "user_answer":
        return "user_answer"
    if isinstance(src, str) and src.startswith("rule:"):
        return "rule_exception" if w.get("exception") else "rule"
    if src == "not_asked":
        return "not_asked"
    return "unrecorded"


def work_entry_problem(data_or_log, row: dict) -> str | None:
    """Validation error for a day's work entry, or None.

    Allowed: the user's answer; a rule-sourced value that matches the agreed rule
    in force (with its exception keyword where one applied); 'unsure'; 'n/a'.
    An error means work with no answer and no applicable rule, or a rule source
    that does not match the rule."""
    w = row.get("uk_work") or {}
    val, src = w.get("over_3h"), w.get("source")
    if src is not None and not (src in ("user_answer", "not_asked") or (isinstance(src, str) and src.startswith("rule:"))):
        return f"uk_work.source {src!r}: use 'user_answer' or 'rule:<id>'"
    if val not in ("yes", "no"):
        return None
    if src == "user_answer":
        return None
    if isinstance(src, str) and src.startswith("rule:"):
        rid = src.split(":", 1)[1]
        rule = rule_for(data_or_log, row["date"], rid)
        if rule is None:
            return f"uk_work source {src} but no agreed rule {rid!r} covers this date"
        ex = w.get("exception") or {}
        exp, basis, hit = rule_outcome(rule, row, (ex.get("keyword") or "") + " " + (ex.get("event") or ""))
        if ex and hit is None:
            return f"uk_work exception {ex.get('keyword')!r} is not one of rule {rid}'s exception keywords"
        if exp != val:
            return f"uk_work.over_3h {val!r} from {src}, but rule {rid} gives {exp!r} ({basis})"
        return None
    # not_asked, or a legacy entry with no source
    if rule_for(data_or_log, row["date"]) is not None:
        return None  # an agreed rule applies; any difference is listed by work_rule_report
    if src == "not_asked" or _INFERRED_WORK.search(w.get("note") or ""):
        return f"uk_work.over_3h {val!r} with no answer from the user and no agreed work-day rule; ask the user"
    return None


def work_inferred_dates(data_or_log, ty: str | None = None) -> list[str]:
    """Days whose yes/no work value has neither the user's answer nor an applicable rule behind it."""
    return sorted(r["date"] for r in _rows(data_or_log) if r.get("date") and (ty is None or tax_year_of(r["date"]) == ty)
                  and work_entry_problem(data_or_log, r) is not None and (r.get("uk_work") or {}).get("over_3h") in ("yes", "no"))


def work_rule_report(data_or_log, ty: str | None = None, as_of: date | None = None) -> dict:
    """Counts by source and the days where the log and the agreed rule disagree."""
    counts = Counter()
    disagree, answered_differently = [], []
    rules_used = set()
    for r in _rows(data_or_log):
        ds = r.get("date")
        if not ds or (ty and tax_year_of(ds) != ty) or (as_of and ds > as_of.isoformat()):
            continue
        w = r.get("uk_work") or {}
        val = w.get("over_3h")
        if val not in ("yes", "no", "unsure"):
            continue
        if "GB" not in (r.get("countries_present") or [r.get("midnight_country")]) and r.get("midnight_country") != "GB":
            continue  # not in the UK: no UK work either way
        src = work_source_of(r)
        counts[src] += 1
        rule = rule_for(data_or_log, ds)
        if rule is None:
            continue
        rules_used.add(rule.get("id"))
        ex = w.get("exception") or {}
        exp, basis, _ = rule_outcome(rule, r, (ex.get("keyword") or "") + " " + (ex.get("event") or ""))
        if exp == val or exp == "unsure":
            continue
        item = {"date": ds, "log": val, "rule": exp, "basis": basis, "source": src, "note": w.get("note", ""), "rule_id": rule.get("id")}
        if src == "user_answer":
            answered_differently.append(item)
        else:
            disagree.append(item)
    return {"counts": dict(counts), "disagree": disagree, "answered_differently": answered_differently,
            "rules": [r for r in work_day_rules(data_or_log) if r.get("id") in rules_used] if ty else work_day_rules(data_or_log)}


def rules_in_force(data_or_log, start: date, end: date) -> list[dict]:
    a, b = start.isoformat(), end.isoformat()
    return [r for r in work_day_rules(data_or_log)
            if (r.get("effective_from") is None or r["effective_from"] <= b) and (r.get("effective_to") is None or r["effective_to"] >= a)]


def validate_work_rules(data: dict) -> list[str]:
    errs = []
    rules = work_day_rules(data)
    ids = [r.get("id") for r in rules]
    if len(ids) != len(set(ids)):
        errs.append("work_day_rules: duplicate id")
    for r in rules:
        rid = r.get("id")
        for k in ("id", "effective_from", "weekdays", "weekends", "public_holidays", "travel_days", "agreed_at", "agreed_via",
                  "wording_shown", "user_answers_take_priority"):
            if not r.get(k):
                errs.append(f"work_day_rules[{rid}]: missing {k} (ask the user; no defaults are assumed)")
        if "exceptions" not in r:
            errs.append(f"work_day_rules[{rid}]: missing exceptions (ask the user which calendar keywords mark an exception; [] if none)")
        for k in ("weekdays", "weekends", "travel_days", "outside_periods"):
            if r.get(k) is not None and r[k] not in RULE_CHOICES:
                errs.append(f"work_day_rules[{rid}]: {k} {r[k]!r}")
        if r.get("work_travel") is not None and r["work_travel"] not in WORK_TRAVEL_CHOICES:
            errs.append(f"work_day_rules[{rid}]: work_travel {r['work_travel']!r}")
        if r.get("public_holidays") is not None and r["public_holidays"] not in RULE_CHOICES + ("as_weekday",):
            errs.append(f"work_day_rules[{rid}]: public_holidays {r['public_holidays']!r}")
        for ex in r.get("exceptions") or []:
            if ex.get("means") not in EXCEPTION_MEANS:
                errs.append(f"work_day_rules[{rid}]: exception {ex.get('keyword')!r} means {ex.get('means')!r}")
        if r.get("effective_from") and r.get("agreed_at") and r["effective_from"] < r["agreed_at"] and not r.get("applies_to_earlier_days_agreed"):
            errs.append(f"work_day_rules[{rid}]: starts before it was agreed ({r['effective_from']} < {r['agreed_at']}) "
                        "without the user's OK to apply it to earlier days")
    srt = sorted((r for r in rules if r.get("effective_from")), key=lambda r: r["effective_from"])
    for a, b in zip(srt, srt[1:]):
        if a.get("effective_to") is None or a["effective_to"] >= b["effective_from"]:
            errs.append(f"work_day_rules: {a.get('id')} and {b.get('id')} overlap; close {a.get('id')} the day before {b.get('id')} starts")
    return errs


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
REQUIRED_DAY = ("date", "midnight_country", "confidence")
CONF = {"confirmed", "inferred", "attested", "unlogged", "planned"}


def validate(data: dict) -> list[str]:
    errs = []
    seen = set()
    for i, r in enumerate(data.get("days", [])):
        for k in REQUIRED_DAY:
            if k not in r:
                errs.append(f"days[{i}] missing {k}")
        if r.get("date") in seen:
            errs.append(f"duplicate date {r.get('date')}")
        seen.add(r.get("date"))
        if r.get("confidence") not in CONF:
            errs.append(f"{r.get('date')}: confidence {r.get('confidence')!r}")
        if r.get("confidence") != "unlogged" and not r.get("midnight_country"):
            errs.append(f"{r.get('date')}: no midnight_country")
        if r.get("date") and r.get("tax_year") and tax_year_of(r["date"]) != r["tax_year"]:
            errs.append(f"{r['date']}: tax_year {r['tax_year']} should be {tax_year_of(r['date'])}")
        w = (r.get("uk_work") or {}).get("over_3h")
        if w not in (None, "yes", "no", "unsure", "n/a"):
            errs.append(f"{r.get('date')}: uk_work.over_3h {w!r}")
        if w == "yes" and (r.get("uk_work") or {}).get("hours") is not None and r["uk_work"]["hours"] <= 3:
            errs.append(f"{r.get('date')}: over_3h yes but hours <= 3")
        if r.get("date"):
            prob = work_entry_problem(data, r)
            if prob:
                errs.append(f"{r.get('date')}: {prob}")
    errs.extend(validate_work_rules(data))
    return errs


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def full_summary(log: DayLog, as_of: date, rules: list[dict] | None = None) -> dict:
    out = {"as_of": as_of.isoformat(), "years": {}, "l6": L6}
    for ty in log.tracked_years(as_of):
        ref = srt_reference(log, ty, as_of)
        ref["open_questions"] = open_questions(log, ty, as_of)
        out["years"][ty] = ref
    out["schengen"] = rolling_status(log, as_of)
    out["schengen"]["max_stay_if_entering_tomorrow"] = max_stay_from(log, as_of + timedelta(days=1))
    out["limits"] = country_limit_status(log, as_of, rules)
    out["l8"] = L8
    return out


def _default(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, set):
        return sorted(o)
    raise TypeError(type(o))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["summary", "plan", "validate", "work-rules"])
    ap.add_argument("daylog")
    ap.add_argument("--as-of", default=date.today().isoformat())
    ap.add_argument("--rules", help=RULES_HELP)
    ap.add_argument("--kb", help="HMRC mirror (root or pages/ dir) for citation dates; default: $NOMAD_PRO_KB, else <engine>/hmrc")
    ap.add_argument("--trip", action="append", default=[], help="CC:FIRST_NIGHT:LAST_NIGHT")
    a = ap.parse_args(argv)
    load_hmrc_dates(default_kb(a.kb))
    data = json.loads(Path(a.daylog).read_text(encoding="utf-8"))
    if a.cmd == "validate":
        errs = validate(data)
        print("\n".join(errs) if errs else "OK")
        return 1 if errs else 0
    log = DayLog(data)
    if a.cmd == "work-rules":
        as_of = parse_date(a.as_of)
        out = {"rules": work_day_rules(log), "years": {}}
        for ty in log.tracked_years(as_of):
            rep = work_rule_report(log, ty, as_of)
            out["years"][ty] = {"counts": rep["counts"], "disagree": rep["disagree"], "answered_differently": [x["date"] for x in rep["answered_differently"]]}
        print(json.dumps(out, indent=1, ensure_ascii=False, default=_default))
        return 0
    rules = load_rules(default_rules_path(a.rules))
    as_of = parse_date(a.as_of)
    if a.cmd == "summary":
        print(json.dumps(full_summary(log, as_of, rules), indent=1, default=_default))
    else:
        trips = []
        for t in a.trip:
            c, f, to = t.split(":")
            trips.append({"country": c, "from": f, "to": to})
        print(json.dumps(plan(log, trips, as_of, rules), indent=1, default=_default))
    return 0


if __name__ == "__main__":
    sys.exit(main())
