# Nomad Pro – UK Residency Tracker (Grok Bot engine)

The engine behind the **Nomad Pro – UK Residency Tracker** Grok Bot template: the Python tools, schemas, templates, fictional example data and a local mirror of HMRC's Statutory Residence Test (SRT) guidance that the bot uses on each user's own Linux box.

A Grok Bot marketplace template can only carry prose (standing instructions, skills, routines). Everything that has to run lives here. On first use, each user's bot downloads this repo into `~/nomad-pro-engine` and runs the tools from there; the user's own records stay in a separate data folder (`~/nomad-pro-data/` by default) and never leave their box.

## What it is, and what it is not

Nomad Pro is a **record-keeping** tool. It keeps a dated day-by-day log of where someone was at midnight, whether they worked in the UK for more than 3 hours, and where the supporting records sit; it counts those days against the figures HMRC publishes for the SRT and against visa and stay limits abroad; and it produces a dashboard, a "Travel and day log" PDF/CSV and a records pack.

* It is **not tax, legal, immigration, financial or accounting advice**, and it does not decide or predict anyone's residence status or tax position. For that, take your records to a qualified adviser.
* It is **not affiliated with, endorsed by or approved by HM Revenue & Customs** (or GOV.UK). HMRC guidance in `hmrc/` is reproduced under the Open Government Licence; see [HMRC-NOTICE.md](HMRC-NOTICE.md).
* Everything in `example/` and `schema/example-*.json` is **fictional**. No real person's data is in this repo.

*Educational information, not tax advice. UK residence can turn on detailed facts and current law. If your position is close to a threshold or commercially significant, use current HMRC guidance and take advice from a qualified professional.*

## How the bot installs and updates it

The template's `engine-setup` skill tells the bot to run, on first use:

    curl -fsSL https://raw.githubusercontent.com/komalamee/Grok-NP_residency-tracker/main/install.sh -o /tmp/nomad-pro-install.sh
    bash /tmp/nomad-pro-install.sh

`install.sh` (no sudo, can be run any number of times):

1. installs into **`~/nomad-pro-engine`** (override with `NOMAD_PRO_ENGINE_DIR`);
2. updates an existing git checkout with `git pull --ff-only` (it refuses if tracked files in the engine folder were edited), or clones `https://github.com/komalamee/Grok-NP_residency-tracker.git` (branch `main`), or, if git is missing or fails, downloads `https://github.com/komalamee/Grok-NP_residency-tracker/archive/refs/heads/main.tar.gz` with curl;
3. installs `tools/requirements.txt` with `pip install --user` if anything is missing (PDF export needs WeasyPrint, whose system libraries may not be installable without sudo; the rest works without it);
4. runs the test suite and prints the installed version.

Once a week the bot runs `bash ~/nomad-pro-engine/install.sh --check`, which compares the installed `VERSION` with the published one (exit 0 = up to date, 10 = update available), and updates if needed.

Other overrides, mainly for testing: `NOMAD_PRO_REPO_URL`, `NOMAD_PRO_TARBALL_URL`, `NOMAD_PRO_VERSION_URL` (local paths and `file://` URLs work), `NOMAD_PRO_SOURCE_DIR` (copy from a local folder), `NOMAD_PRO_NO_GIT=1`, `NOMAD_PRO_SKIP_PIP=1`, `NOMAD_PRO_SKIP_TESTS=1`.

## What's in it

| Path | What it is |
|---|---|
| install.sh | Installs or updates the engine at `~/nomad-pro-engine` (see below) |
| VERSION | Engine version (semantic versioning) |
| CHANGELOG.md | What changed in each engine version |
| hmrc/ | Mirror of HMRC's SRT guidance: 143 gov.uk pages (RFIG20000 chapter + RDR3), with catalogue, manifest, change log and `refresh.py` crawler. See HMRC-NOTICE.md |
| SYSTEM.md | Standing instructions, persona, guardrails, L1–L8 verbatim, data folder layout |
| skills/*/SKILL.md | engine-setup (first-use install and weekly update check), onboarding, daily-checkin-and-catchup (incl. end-of-week calendar review), evidence-and-documents, travel-rules-watch, hmrc-guidance-watch, trip-planning, export-travel-day-log, records-pack, dashboard, srt-explainer, leaving-uk-checklist, destination-concierge (on request only, never in onboarding) |
| schema/daylog.schema.json | Day-log JSON Schema (2020-12): days, evidence (link / file / pointer), change log, weekly reviews, versioned `profile.work_day_rules` (the work-day rule agreed with the user) and each work entry's `source` (`user_answer` or `rule:<id>`, plus the calendar exception that applied) |
| schema/documents-index.schema.json | Status documents index (type, tax years covered, file or link, date added) |
| schema/destination-preferences.schema.json | Destination concierge preferences profile |
| schema/example-*.json | Fictional examples |
| schema/country-rules.json / .md | Verified country-rules table with sources and dates |
| example/ | Fictional per-user data folder: daylog.json, evidence/, documents/ (+ index.json), profile/ |
| templates/leaving-uk-checklist.md | Leaving-the-UK checklist, every GOV.UK link verified (date recorded) |
| templates/arriving-uk-checklist.md | Arriving / returning variant |
| tools/srt_engine.py | Counts: tax years, midnight rule, UK work days >3h, ties, Table A/B bands, proximity, Schengen 90/180, country limits, trip planning, validation; work-day rule (`apply_work_rule`, `work_rule_report`, `srt_engine.py work-rules`); verdict gate (`verdict_gate`, `gate_items`, `running_count`): a stage line only for a tax year that has ended with every day logged, prior-year residence recorded and every tie answered, otherwise the year so far and what is missing; the HMRC figures that apply to the year with the room left before each (`applicable_figures`) |
| tools/render_dashboard.py (+ dashboard_charts.py, assets/) | Self-contained tabbed HTML dashboard (works offline), Evidence column, Reference card at a glance (progress bar, day strip, checklist, detail folded away) |
| tools/render_pdf.py | "Travel and day log" PDF + CSV per tax year: a single flowing document, no tab UI, Evidence column, the same Reference block as the dashboard |
| tools/records_pack.py | Records pack zip for one or more tax years: cover index, logs, evidence index, status documents, evidence files, manifest with SHA-256 |
| tools/travel_rules_check.py | GOV.UK entry-requirements watch + plan alerts |
| tools/hmrc_watch.py | Weekly HMRC knowledge-base comparison with live gov.uk |
| tools/banned_scan.py | Banned-phrase and private-data scan |
| tools/pdf_layout_check.py, tools/dashboard_layout_check.py | Layout checks: no text overflowing its box in the PDF (WeasyPrint boxes) or the dashboard (1360 and 390 px, Playwright) |
| tools/tests/ | Unit tests incl. HMRC boundary cases, evidence column, PDF has no tab UI, records pack |
| routines.md | The four routines to create per user (4 = end-of-week calendar review, only if the calendar is connected) |
| LISTING.md | Marketplace listing copy |


## Run and test

    pip install --user -r tools/requirements.txt
    python3 -m unittest discover -s tools/tests
    python3 tools/banned_scan.py . [--private-terms FILE]

Try the tools on the fictional data (the HMRC mirror is found automatically at `hmrc/`; give `--kb` or set `NOMAD_PRO_KB` to use another copy):

    python3 tools/srt_engine.py summary example/daylog.json --as-of 2026-07-31
    python3 tools/render_dashboard.py example/daylog.json /tmp/dashboard.html --as-of 2026-07-31 --data-root example
    python3 tools/render_pdf.py example/daylog.json --tax-year 2025/26 --out-dir /tmp/np-out --as-of 2026-07-31 --data-root example
    python3 tools/records_pack.py example/daylog.json --tax-years 2025/26 --out-dir /tmp/np-out --data-root example --as-of 2026-07-31
    python3 tools/srt_engine.py work-rules example/daylog.json --as-of 2026-07-31

On a user's box the bot runs the same tools from the user data folder, e.g. `cd ~/nomad-pro-data && python3 ~/nomad-pro-engine/tools/srt_engine.py summary daylog.json --kb hmrc`, where `hmrc/` is the user's own copy of the mirror (updated weekly by `tools/hmrc_watch.py`).

Country rules work the same way without needing a flag: given no `--rules`, the tools read `$NOMAD_PRO_DATA/country-rules.json`, else `~/nomad-pro-data/country-rules.json`, else this repo's `schema/country-rules.json`. The user's copy is the one `tools/travel_rules_check.py` keeps current, so it wins. A `--rules` path that doesn't exist loads no rules rather than falling back to a different table.

`banned_scan.py` checks prose for wording the template never uses (outcome words and residence verdicts) and for private-data leaks. It only has generic leak markers built in; keep any personal terms in a file **outside** the repo and give it with `--private-terms`. HMRC's own verbatim pages under `hmrc/` are exempt from the wording check (they are still scanned for private data).

## Work-day rule


At onboarding the bot agrees a work-day rule with the user in plain words (for example: "Weekends are non-work days; while employed every weekday in the UK is a work day unless my calendar says sick / holiday / less than 3 hours"), reads it back, and saves it in `profile.work_day_rules` with the date, how it was agreed and the exact wording confirmed. Check-ins, catch-ups and the weekly review then set UK work from that rule (`source: rule:v1`) and ask only about exceptions; the user's own answer always wins (`source: user_answer`). Calendar presence alone never makes a work day: with no rule, unanswered UK days stay `unsure`. Rule changes are new versions from their own date; earlier days are never rewritten without asking. `validate` errors only on work with no answer and no applicable rule; the PDF (section 8), records pack index and dashboard show the rule, the counts by source and any days where the log and the rule differ.

## Licence

Code and original text: MIT, see [LICENSE](LICENSE). HMRC guidance under `hmrc/pages/` (and the page titles, dates and URLs in `hmrc/catalogue.md` and `hmrc/manifest.json`) is Crown copyright, used under the Open Government Licence v3.0, see [HMRC-NOTICE.md](HMRC-NOTICE.md). The Inter font in `tools/assets/` is under the SIL Open Font Licence (`tools/assets/Inter-OFL.txt`).
