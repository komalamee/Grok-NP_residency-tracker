# Changelog

Versions of the Nomad Pro engine (`VERSION`). Newest first.

## 0.1.2

* Verdict gate: `srt_reference()` (and so `summary`, the dashboard, the PDF export and the records pack) returns a
  stage line ("Your log points to non-resident under the …") only once the tax year has ended, every day in it is
  logged, residence for the previous 3 tax years is recorded and every applicable tie is answered. Otherwise
  `stage_lines` is empty, `verdict_withheld` lists what is still missing, and `running_count` gives the year so far
  (UK midnights, days logged, the year-end date) with the room left before each HMRC figure that applies to it.
  Previously an empty or mid-year log could return a stage line.
* Dashboard and PDF export show the running count, what is still missing and the room before each figure where the
  stage line would go while the gate is closed (both now use `render_common.pointer_block`).
* New tests: `tools/tests/test_verdict_gate.py` (empty log mid-year, mid-year fully logged, finished year with gaps,
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
