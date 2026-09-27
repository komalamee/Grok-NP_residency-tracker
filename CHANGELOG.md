# Changelog

Versions of the Nomad Pro engine (`VERSION`). Newest first.

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
