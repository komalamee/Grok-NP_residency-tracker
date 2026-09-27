#!/usr/bin/env python3
"""Travel rules watch: re-read GOV.UK entry requirements for each zone in country-rules.json (and any new
country), report changes since the last check, and flag planned trips that would break a limit.

  python3 travel_rules_check.py --rules country-rules.json [--daylog DAYLOG.json] [--country thailand ...]
                                [--state rules-watch-state.json] [--report OUT.json] [--as-of YYYY-MM-DD]

Change detection: the GOV.UK 'Entry requirements' part is reduced to its 'Visa requirements' section and hashed;
public_updated_at and change_description are recorded. A changed hash = "review this row" (the bot then reads
the new text and updates limit/counting/source/last_verified). Official corroboration (Thai MFA, EU Commission)
is a manual step recorded in the row's 'corroborating' list.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import srt_engine as E

API = "https://www.gov.uk/api/content/foreign-travel-advice/"
UA = "nomad-pro-travel-rules-watch/1.0"
SLUGS = {"SCHENGEN": "italy", "CY": "cyprus", "TH": "thailand", "LA": "laos", "AE": "united-arab-emirates", "MY": "malaysia",
         "ME": "montenegro", "JP": "japan", "VN": "vietnam", "ID": "indonesia", "PH": "philippines", "KH": "cambodia",
         "SG": "singapore", "KR": "south-korea", "CN": "china", "GE": "georgia", "AL": "albania", "RS": "serbia",
         "BA": "bosnia-and-herzegovina", "TR": "turkey", "MX": "mexico", "US": "usa", "AU": "australia", "LK": "sri-lanka",
         "IN": "india", "PT": "portugal", "ES": "spain", "FR": "france", "IT": "italy", "GR": "greece", "HR": "croatia"}


def visa_section(slug: str) -> dict:
    req = urllib.request.Request(API + slug, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    text = ""
    for p in d.get("details", {}).get("parts", []):
        if p.get("slug") == "entry-requirements":
            t = html.unescape(re.sub(r"<[^>]+>", " ", p["body"]))
            t = re.sub(r"\s+", " ", t)
            i = t.find("Visa requirements")
            j = min([k for k in (t.find("Vaccine requirements", i), t.find("Vaccination requirements", i)) if k > 0] or [len(t)])
            text = t[i:j].strip() if i >= 0 else t
    return {"slug": slug, "url": f"https://www.gov.uk/foreign-travel-advice/{slug}/entry-requirements",
            "public_updated_at": d.get("public_updated_at"), "change_description": (d.get("details") or {}).get("change_description"),
            "visa_text": text, "hash": hashlib.sha256(text.encode()).hexdigest()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", required=True)
    ap.add_argument("--daylog")
    ap.add_argument("--country", action="append", default=[], help="extra GOV.UK slug(s) to read, e.g. vietnam")
    ap.add_argument("--state")
    ap.add_argument("--report")
    ap.add_argument("--as-of", default=date.today().isoformat())
    a = ap.parse_args(argv)
    doc = json.loads(Path(a.rules).read_text(encoding="utf-8"))
    rules = doc["rules"]
    E.set_rules(rules)
    state = json.loads(Path(a.state).read_text()) if a.state and Path(a.state).exists() else {}
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    targets = {r["zone"]: SLUGS.get(r["zone"]) or r["source_url"].split("/foreign-travel-advice/")[1].split("/")[0] for r in rules}
    log = E.DayLog.load(a.daylog) if a.daylog else None
    as_of = E.parse_date(a.as_of)
    if log:  # every country the user is in or has upcoming
        for p in log.planned:
            if p.get("status") in ("idea", "booked") and p["country"] not in targets and p["country"] != "GB":
                targets[p["country"]] = SLUGS.get(p["country"])
        cur = log.row(as_of)
        if cur and cur["midnight_country"] not in targets and cur["midnight_country"] != "GB":
            targets[cur["midnight_country"]] = SLUGS.get(cur["midnight_country"])
    for slug in a.country:
        targets[slug.upper()] = slug
    findings = []
    for zone, slug in targets.items():
        if not slug:
            findings.append({"zone": zone, "status": "no_rule_row", "finding": "No GOV.UK slug known; add a row after reading the entry requirements page."})
            continue
        try:
            v = visa_section(slug)
        except Exception as e:
            findings.append({"zone": zone, "status": "fetch_error", "error": str(e)})
            continue
        prev = state.get(zone)
        row = next((r for r in rules if r["zone"] == zone), None)
        status = "new_baseline" if not prev else ("changed" if prev["hash"] != v["hash"] else "unchanged")
        if not row:
            status = "no_rule_row"
        findings.append({"zone": zone, "status": status, "source_url": v["url"], "gov_uk_updated": v["public_updated_at"],
                         "change_description": v["change_description"], "visa_text_excerpt": v["visa_text"][:600],
                         "row_last_verified": row.get("last_verified") if row else None})
        state[zone] = {"hash": v["hash"], "checked_at": now, "public_updated_at": v["public_updated_at"]}
    plan_alerts = []
    if log and log.planned:
        trips = [p for p in log.planned if p.get("status") in ("idea", "booked") and p["to"] >= as_of.isoformat()]
        if trips:
            res = E.plan(log, trips, as_of, rules)
            for st in res["limits_at_trip_end"]:
                over_days = st.get("room") is not None and st["room"] < 0
                over_entries = bool(st.get("entries_this_year")) and len(st["entries_this_year"]) > st.get("max_entries", 99)
                if over_days or over_entries or (st.get("room") is not None and st["room"] <= 5):
                    level = ("over the day limit" if over_days else
                             f"{len(st['entries_this_year'])} entries this calendar year; GOV.UK's usual figure is {st['max_entries']}" if over_entries
                             else st.get("proximity"))
                    plan_alerts.append({"trip": st["trip"], "text": st.get("text"), "room": st.get("room"),
                                        "entries_this_year": st.get("entries_this_year"), "max_entries": st.get("max_entries"),
                                        "level": level})
    out = {"checked_at": now, "findings": findings, "plan_alerts": plan_alerts, "legal": E.L8}
    if a.state:
        Path(a.state).write_text(json.dumps(state, indent=1))
    if a.report:
        Path(a.report).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    changed = [f for f in findings if f["status"] in ("changed", "no_rule_row", "fetch_error")]
    print(f"Travel rules watch {now[:10]}: {len(findings)} zones read; needs review: {len(changed)}; plan alerts: {len(plan_alerts)}")
    for f in changed:
        print(f"  {f['zone']}: {f['status']} {f.get('gov_uk_updated') or f.get('error') or ''}")
    for p in plan_alerts:
        print(f"  PLAN {p['trip']}: {p['level']} - {p['text']} entries={p.get('entries_this_year')}")
    return 1 if changed or plan_alerts else 0


if __name__ == "__main__":
    sys.exit(main())
