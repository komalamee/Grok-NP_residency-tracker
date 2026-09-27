#!/usr/bin/env python3
"""Build a Records pack: one zip with everything a user's adviser (or HMRC, if the user chooses to send it) may ask to see.

  python3 records_pack.py DAYLOG.json --tax-years 2024/25 2025/26 --out-dir OUT/ [--data-root DIR] [--as-of YYYY-MM-DD] [--kb HMRC_MIRROR (default: <engine>/hmrc)]

Zip layout ("Records pack 2024-25 and 2025-26 (prepared 14 May 2026).zip"):
  00 Index.pdf                         cover index: contents, per-year counts, evidence coverage, documents, gaps
  01 Travel and day logs/              "Travel and day log YYYY-YY.pdf" + .csv per tax year
  02 Evidence index/                   Evidence index.pdf + .csv: every day -> its evidence (link, file or pointer)
  03 Status documents/                 Documents index.pdf + .csv
  evidence/                            evidence files referenced by the selected years (copied verbatim)
  documents/                           status documents covering the selected years (copied verbatim)
  manifest.json                        sha256 of every file in the pack

Record-keeping only. The pack collects the user's own records; it does not determine residence.
Links inside the PDFs to evidence/ and documents/ are relative, so they work once the zip is extracted.
Without --rules the country rules come from the user's own copy ($NOMAD_PRO_DATA/country-rules.json, else
~/nomad-pro-data/country-rules.json), else the engine's shipped schema/country-rules.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import date
from pathlib import Path

import srt_engine as E
import render_pdf as RP
from render_common import esc, evidence_entries, evidence_html

CSS_EXTRA = ".note{font-size:8pt;color:#616e7c}.miss{color:#7a5210}"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def year_label(ty: str) -> str:
    return ty.replace("/", "-")


def evidence_rows(log, ty, as_of):
    start, end = E.tax_year_bounds(ty)
    for d in E.daterange(start, min(end, as_of)):
        r = log.days.get(d) or {}
        lr = log.row(d)
        ents = evidence_entries(r) or [None]
        for x in ents:
            yield {"date": d.isoformat(), "tax_year": ty, "midnight_country": (lr or {}).get("midnight_country") or "",
                   "country": E.cname(lr["midnight_country"]) if lr else "Not logged", "place": r.get("midnight_place", ""),
                   "confidence": r.get("confidence", "unlogged"), "row": r,
                   "evidence_kind": x["kind"] if x else "none", "evidence_label": x["label"] if x else "",
                   "evidence_link_or_file": (x["href"] or "") if x else "", "pointer": (x["pointer"] if x else "")}


def build(daylog: str, years: list[str], out_dir: str, data_root: str | None = None, as_of: date | None = None) -> Path:
    as_of = as_of or date.today()
    log = E.DayLog.load(daylog)
    root = Path(data_root or Path(daylog).parent)
    years = sorted(years)
    label = " and ".join(year_label(y) for y in years) if len(years) <= 2 else f"{year_label(years[0])} to {year_label(years[-1])}"
    title = f"Records pack {label}"
    shown = "Records pack " + (" and ".join(years) if len(years) <= 2 else f"{years[0]} to {years[-1]}")
    zip_name = f"{title} (prepared {E.fmt_date(as_of)}).zip"
    tmp = Path(tempfile.mkdtemp(prefix="records-pack-"))
    pack = tmp / title
    (pack / "01 Travel and day logs").mkdir(parents=True)
    (pack / "02 Evidence index").mkdir()
    (pack / "03 Status documents").mkdir()
    from weasyprint import HTML

    # 1. Travel and day logs (PDF + CSV) per year; evidence links point to ../evidence/
    logs = []
    for ty in years:
        html, base = RP.build_html(log, ty, as_of, prefix="../")
        HTML(string=html, base_url=None).write_pdf(pack / "01 Travel and day logs" / f"{base}.pdf")
        start, end = E.tax_year_bounds(ty)
        with open(pack / "01 Travel and day logs" / f"{base}.csv", "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(RP.csv_rows(log, start, min(end, as_of)))
        logs.append((ty, base))

    # 2. Evidence files + evidence index
    missing, copied = [], set()
    all_rows = []
    for ty in years:
        for row in evidence_rows(log, ty, as_of):
            if row["evidence_kind"] == "file":
                src = root / row["evidence_link_or_file"]
                if src.exists():
                    if row["evidence_link_or_file"] not in copied:
                        dst = pack / row["evidence_link_or_file"]
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                        copied.add(row["evidence_link_or_file"])
                else:
                    missing.append(row["evidence_link_or_file"])
                    row["evidence_kind"] = "file (missing from data folder)"
            all_rows.append(row)
    cols = ["date", "tax_year", "midnight_country", "country", "place", "confidence", "evidence_kind", "evidence_label", "evidence_link_or_file", "pointer"]
    with open(pack / "02 Evidence index" / "Evidence index.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)
    cover_stats = {}
    for ty in years:
        rows = [r for r in all_rows if r["tax_year"] == ty]
        days = {}
        for r in rows:
            k = days.setdefault(r["date"], set())
            k.add(r["evidence_kind"].split(" ")[0])
        cover_stats[ty] = {"days": len(days),
                           "link": sum(1 for v in days.values() if "link" in v or "file" in v),
                           "pointer_only": sum(1 for v in days.values() if v <= {"pointer"} and v),
                           "none": sum(1 for v in days.values() if v == {"none"})}
    seen = set()
    irows = []
    for r in all_rows:
        if r["date"] in seen:
            continue
        seen.add(r["date"])
        irows.append(f"<tr><td>{esc(r['date'])}</td><td>{esc(r['country'])}</td><td>{esc(r['place'])}</td><td>{esc(r['confidence'])}</td><td class='ptr'>{evidence_html(r['row'], '../', 4) or 'none'}</td></tr>")
    ev_html = f"""<!doctype html><html><head><meta charset='utf-8'><style>{RP.CSS}{CSS_EXTRA}</style></head><body>
<h1 style='font-size:18pt'>Evidence index</h1><p class='small muted'>{esc(shown)} \u00b7 one row per date \u00b7 links open the email or the file in evidence/ (extract the zip first). Pointers say where a record sits when no link or file is filed.</p>
<table class='days'><tr><th>Date</th><th>Midnight</th><th>Place</th><th>Confidence</th><th>Evidence</th></tr>{''.join(irows)}</table>
<div class='legal'>{esc(E.L6)}</div></body></html>"""
    HTML(string=ev_html, base_url=None).write_pdf(pack / "02 Evidence index" / "Evidence index.pdf")

    # 3. Status documents covering the selected years
    idx = root / "documents" / "index.json"
    docs = json.loads(idx.read_text(encoding="utf-8"))["documents"] if idx.exists() else []
    docs = [d for d in docs if set(d.get("tax_years", [])) & set(years) and d.get("status") != "superseded"]
    for d in docs:
        if d.get("file"):
            src = root / d["file"]
            if src.exists():
                dst = pack / d["file"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            else:
                d["_missing"] = True
    dcols = ["id", "type", "title", "tax_years", "document_date", "effective_from", "effective_to", "status", "file", "url", "pointer", "date_added", "notes"]
    with open(pack / "03 Status documents" / "Documents index.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(dcols)
        for d in docs:
            w.writerow(["|".join(d.get(c, [])) if c == "tax_years" else (d.get(c) or "") for c in dcols])

    def doc_cell(d, pre):
        if d.get("file"):
            return f"<a href='{esc(pre + d['file'])}'>{esc(d['file'].split('/')[-1])}</a>" + (" <span class='miss'>(file missing)</span>" if d.get("_missing") else "")
        if d.get("url"):
            return f"<a href='{esc(d['url'])}'>link</a>"
        return esc(d.get("pointer") or "requested, not yet provided")
    drows = lambda pre: "".join(f"<tr><td>{esc(d.get('title'))}</td><td>{esc(d.get('type', '').replace('_', ' '))}</td><td>{esc(', '.join(d.get('tax_years', [])))}</td><td class='ptr'>{doc_cell(d, pre)}</td><td>{esc(d.get('status', '').replace('_', ' '))}</td><td>{esc(d.get('notes', ''))}</td></tr>" for d in docs)
    dhead = "<tr><th>Document</th><th>Type</th><th>Tax years</th><th>File, link or pointer</th><th>Status</th><th>Notes</th></tr>"
    doc_html = f"""<!doctype html><html><head><meta charset='utf-8'><style>{RP.CSS}{CSS_EXTRA}</style></head><body>
<h1 style='font-size:18pt'>Status documents</h1><p class='small muted'>{esc(shown)} \u00b7 documents you filed that record your circumstances in these tax years.</p>
<table class='fx'><col style='width:24%'><col style='width:13%'><col style='width:11%'><col style='width:20%'><col style='width:10%'><col style='width:22%'>{dhead}{drows('../') or '<tr><td colspan=6>None filed.</td></tr>'}</table><div class='legal'>{esc(E.L6)}</div></body></html>"""
    HTML(string=doc_html, base_url=None).write_pdf(pack / "03 Status documents" / "Documents index.pdf")

    # 0. Cover index
    yrows = []
    for ty in years:
        ref = E.srt_reference(log, ty, as_of)
        s = ref["summary"]
        c = cover_stats[ty]
        start, end = E.tax_year_bounds(ty)
        yrows.append(f"<tr><td><b>{esc(ty)}</b>{'' if as_of >= end else ' (to ' + esc(E.fmt_date(as_of)) + ')'}</td><td>{s['uk_midnights']}</td><td>{s['uk_work_days_over_3h']} (+{s['uk_work_unsure']} unsure)</td><td>{s['logged']} / {s['unlogged']}</td><td>{c['link']}</td><td>{c['pointer_only']}</td><td>{c['none']}</td></tr>")
    rrows, rules_seen = [], {}
    for ty in years:
        st, en = E.tax_year_bounds(ty)
        to_ = min(en, as_of)
        rep = E.work_rule_report(log, ty, to_)
        c = rep["counts"]
        for r in E.rules_in_force(log, st, to_):
            rules_seen[r.get("id")] = r
        rrows.append(f"<tr><td><b>{esc(ty)}</b></td><td>{esc(', '.join(r.get('id') for r in E.rules_in_force(log, st, to_)) or 'none')}</td><td>{c.get('rule', 0)}</td><td>{c.get('rule_exception', 0)}</td><td>{c.get('user_answer', 0)}</td><td>{c.get('not_asked', 0) + c.get('unrecorded', 0)}</td><td>{len(rep['disagree'])}</td></tr>")
    rq = "".join(f"<p class='small'><b>Rule {esc(r.get('id'))}</b>, in force {esc(E.fmt_date(r['effective_from']))} to {esc(E.fmt_date(r['effective_to']) if r.get('effective_to') else 'open')}; agreed {esc(E.fmt_date(r.get('agreed_at')))}, {esc(r.get('agreed_via'))}:</p><div class='quote'>\u201c{esc(r.get('wording_shown'))}\u201d</div>" for r in rules_seen.values())
    rule_html = f"""<h3>Work-day rule</h3><p class='small'>How UK work days were set: from the user's answer, or from the work-day rule they agreed (full rule, exceptions and any days that differ in section 8 of each Travel and day log).</p>{rq or "<p class='small'>No work-day rule agreed; work entries are the user's own answers.</p>"}
<table><tr><th>Tax year</th><th>Rule(s)</th><th>Set by rule</th><th>Rule exception (calendar keyword)</th><th>User's answer</th><th>Not asked / no source</th><th>Differ from rule</th></tr>{''.join(rrows)}</table>"""
    oq = [q["text"] for q in log.data.get("open_questions", []) if q.get("status") == "open" and (not q.get("tax_years") or set(q["tax_years"]) & set(years))]
    contents = "".join(f"<li><b>01 Travel and day logs/</b>{esc(b)}.pdf and .csv</li>" for _, b in logs)
    cover = f"""<!doctype html><html lang='en-GB'><head><meta charset='utf-8'><title>{esc(shown)}</title><style>{RP.CSS}{CSS_EXTRA}</style></head><body>
<div class='cover' style='height:auto'><div class='band'><h1>{esc(shown)}</h1><div class='sub'>{esc(log.profile.get('display_name', ''))} \u00b7 prepared {esc(E.fmt_date(as_of))} \u00b7 Nomad Pro \u00b7 UK Residency Tracker</div></div></div>
<p>This pack collects the travel and work records kept in Nomad Pro for the tax years below, with the evidence each day points to and the status documents on file. It is a record of what was logged, not a determination of residence.</p>
<h3>Contents</h3><ol class='toc'>{contents}<li><b>02 Evidence index/</b>Evidence index.pdf and .csv (each day and its evidence)</li>
<li><b>03 Status documents/</b>Documents index.pdf and .csv</li><li><b>evidence/</b> {len(copied)} evidence file(s) referenced by these years</li>
<li><b>documents/</b> {sum(1 for d in docs if d.get('file') and not d.get('_missing'))} status document file(s)</li><li><b>manifest.json</b> SHA-256 of every file</li></ol>
<h3>Counts per tax year</h3><table><tr><th>Tax year</th><th>UK midnights</th><th>UK work days (>3h)</th><th>Logged / not logged</th><th>Days with a link or file</th><th>Pointer only</th><th>No evidence</th></tr>{''.join(yrows)}</table>
<p class='note'>UK midnights: {esc(E.cite('RFIG20710'))}. UK work days of more than 3 hours: {esc(E.cite('RFIG20560'))}. Full counting method in section 12 of each Travel and day log.</p>
{rule_html}<h3>Status documents</h3><table class='fx'><col style='width:24%'><col style='width:13%'><col style='width:11%'><col style='width:20%'><col style='width:10%'><col style='width:22%'>{dhead}{drows('') or '<tr><td colspan=6>None filed.</td></tr>'}</table>
<h3>Open items in the records</h3><ul class='small'>{''.join(f'<li>{esc(q)}</li>' for q in oq) or '<li>None recorded.</li>'}{''.join(f'<li class=miss>Evidence file listed but not in the data folder: {esc(m)}</li>' for m in sorted(set(missing)))}</ul>
<div class='legal'>{esc(E.L6)}</div><p class='note'>Nomad Pro is not affiliated with HM Revenue &amp; Customs.</p></body></html>"""
    HTML(string=cover, base_url=None).write_pdf(pack / "00 Index.pdf")

    manifest = {"title": title, "prepared": as_of.isoformat(), "tax_years": years,
                "files": {str(p.relative_to(pack)): sha(p) for p in sorted(pack.rglob("*")) if p.is_file()}}
    (pack / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    zp = out / zip_name
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pack.rglob("*")):
            if p.is_file():
                z.write(p, Path(title) / p.relative_to(pack))
    shutil.rmtree(tmp)
    return zp


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("daylog")
    ap.add_argument("--tax-years", nargs="+", required=True)
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--data-root")
    ap.add_argument("--as-of", default=date.today().isoformat())
    ap.add_argument("--rules", help=E.RULES_HELP)
    ap.add_argument("--kb", help="HMRC mirror (root or pages/ dir); default: $NOMAD_PRO_KB, else <engine>/hmrc")
    a = ap.parse_args(argv)
    E.load_hmrc_dates(E.default_kb(a.kb))
    E.load_rules(E.default_rules_path(a.rules))
    print(build(a.daylog, a.tax_years, a.out_dir, a.data_root, E.parse_date(a.as_of)))


if __name__ == "__main__":
    main()
