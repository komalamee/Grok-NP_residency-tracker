# Changelog

Versions of the Nomad Pro engine (`VERSION`). Newest first.

## 0.1.4

* Wording guardrails. Four more words and phrases join the do-not-say list in `SYSTEM.md` section 4 and are out
  of every user-facing string the engine and its renderers produce: a residence status (which had one sanctioned
  use left, in the year-end stage line), a ruling, a deciding verb, and a phrase that promises a single answer.
  Nothing about the counting changed: a stage line is still returned only for a tax year that can be counted
  in full.
  * The year-end stage line is now "Your log matches the &lt;test&gt; for this tax year." for the automatic overseas
    tests and "Your log does not match the sufficient ties test for this tax year." for the ties test (the two
    read in opposite directions, so one template could not state both honestly). Each stage line also carries a
    `matches` boolean.
  * The dashboard caption, the export cover note and the records pack cover now read "Educational, not tax advice.
    It records days; it doesn't decide your residence."
  * `srt_reference()["verdict_withheld"]` is now `result_withheld`, `verdict_gate()` is `result_gate()`, and <!-- banned-list:skip -->
    `tools/tests/test_verdict_gate.py` is `tools/tests/test_result_gate.py`. Nothing else about them changed. <!-- banned-list:skip -->
  * `SYSTEM.md` sections 3 and 4 and the `dashboard`, `records-pack`, `onboarding`, `trip-planning` and
    `destination-concierge` skills follow the same wording.
  * `banned_scan.py` now flags every one of them (the old approved-template exemption for a residence status
    is gone) and takes a `banned-list:skip` comment to exempt a single line. GOV.UK scheme and page titles
    quoted as titles (the non-resident landlord scheme, temporary non-residence) stay exempt, as does HMRC's <!-- banned-list:skip -->
    verbatim mirror.
  * New `tools/tests/test_output_wording.py` renders the CLI summary and plan output, the dashboard, the PDF
    export HTML and the CSV for a finished year and a mid-year log, and fails if any banned word appears.

* Trip what-if: `srt_engine.py plan` (and `plan()`) now state the room left outright instead of leaving the
  subtraction to the caller. All existing fields are unchanged; these are additions.
  * `years[].uk_days_remaining_with_plan`: the UK day figure that applies next with the trip included
    (`figure`, `test`), `uk_days`, `days_remaining` (UK days that still fit below the figure), `days_over`,
    `room`, `ref`, `cite`, `text`.
  * `schengen_days_remaining_with_plan`: the fullest point of the 90/180 rolling window with the trip included
    (`on`, `used`, `limit`, `window_days`, `days_remaining`, `days_over`, `room`, `proximity`,
    `earliest_drop_off`, `text`).
  * Every row in `limits_at_trip_end` that has a `room` also carries `days_remaining` and `days_over`.
  * New helpers `uk_days_remaining()` and `schengen_days_remaining()`; documented in the README
    ("Trip what-if") and in the `trip-planning` skill.

## 0.1.3

* Reference card, dashboard and export, redesigned around one visual: a progress bar of UK midnights against the
  nearest HMRC figure that applies, a strip of every day of the tax year (UK midnights, days elsewhere, gaps, days
  still to come), an "X days left before Y" chip and a four-box checklist of what is still to record. Short labels
  only; the figure explanations, the room before each figure, the HMRC page dates, the counting notes and the RDR3
  number line moved into "Figures and sources" (a collapsible block in the dashboard, a footnote in the export).
  The running-count sentence and the prose list of missing items are no longer shown to the reader; the engine
  still returns both. Disclaimer wording is unchanged and set small.
* The export's section 3 is now "Where your log stands, and your ties" and is built from the same component as the
  dashboard card (`dashboard_charts.status_block`, with `gauge` and `day_strip`), so the two read the same.
  `render_common.pointer_block` is gone.
* Engine: `srt_reference()` also returns `gate` (one item per gate condition, each with a short checklist label)
  and `applicable_figures` (the figures that apply to the year with the room left before each, and `next` on the
  nearest UK-day figure still ahead), for a year with a result as well as one without. `running_count` keeps its
  `figures` and gains `next_figure`.
* New tests: the checklist labels, the figure marked `next` (never a work-day figure), the gauge and the day strip,
  and the dashboard and export output either side of the result gate.

## 0.1.2

* Result gate: `srt_reference()` (and so `summary`, the dashboard, the PDF export and the records pack) returns a
  stage line naming the test a year's counts line up with only once the tax year has ended, every day in it is
  logged, residence for the previous 3 tax years is recorded and every applicable tie is answered. Otherwise
  `stage_lines` is empty, `result_withheld` (named `verdict_withheld` until 0.1.4) lists what is still missing, and <!-- banned-list:skip -->
  `running_count` gives the year so far (UK midnights, days logged, the year-end date) with the room left before
  each HMRC figure that applies to it.
  Previously an empty or mid-year log could return a stage line.
* Dashboard and PDF export show the running count, what is still missing and the room before each figure where the
  stage line would go while the gate is closed (both now use `render_common.pointer_block`).
* New tests: `tools/tests/test_result_gate.py` (empty log mid-year, mid-year fully logged, finished year with gaps,
  a single unlogged day, unanswered tie, prior years unrecorded, complete year still returns its line, which figures
  apply per table and per recorded claim, dashboard and PDF output, CLI summary).

## 0.1.1

* Country rules: without `--rules`, the tools (`srt_engine.py`, `render_pdf.py`, `render_dashboard.py`,
  `records_pack.py`, `travel_rules_check.py`) now read the user's own `country-rules.json`
  (`$NOMAD_PRO_DATA/country-rules.json`, else `~/nomad-pro-data/country-rules.json`) and fall back to the engine's
  shipped `schema/country-rules.json` only if neither exists. The weekly travel-rules watch updates the user's copy,
  so counts previously kept using the shipped table. A `--rules` path that does not exist now loads no rules instead
  of silently reading a different table, and `travel_rules_check.py --rules` is no longer required.
* Skills and `SYSTEM.md`: example commands say to run from the user data folder with `--rules` left off;
  `engine-setup` and `onboarding` state that the shipped table is copied into the data folder on first set-up if it
  isn't already there.
* `srt_engine.py plan` examples corrected: `--trip` is given once per trip, not as a space-separated list.
* `install.sh`: `--help` / `-h` prints the usage and exits 0 without installing anything; any unknown flag prints the
  usage on stderr and exits 2, also installing nothing.

## 0.1.0

* First release: counting engine, HTML dashboard, "Travel and day log" PDF + CSV, Records pack, HMRC guidance mirror
  and watch, travel-rules watch, work-day rule, schemas, skills and `install.sh`.
