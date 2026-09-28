---
name: records-backup
description: "Nomad Pro backup: use when the Nomad Pro monthly backup routine runs, or a Nomad Pro user asks to back up or restore their day log and records."
---
# Records backup

**On by default** (1st of the month, 09:00 their time, from the first count; never a duplicate): a copy of everything in `~/nomad-pro-data`, so records survive a lost box or a bad edit. Delivery in chat unless they chose a Drive folder too (Drive is offered on day one; delivery agreed in `onboarding` G). No day log yet: send nothing. On request, any time. Engine `~/nomad-pro-engine` (`engine-setup` if missing). Follow `nomad-pro-core-rules`.

## Make the backup
1. Rebuild `daylog.json` from the Sheet (`export-travel-day-log`) and export its seven tabs (`.xlsx`, or the CSVs without Sheets) into `sheet/`, so the backup holds the source. Run `srt_engine.py validate daylog.json`; problems: still back up and note them (never fix silently).
2. Zip `daylog.json`, `evidence/`, `documents/`, `profile/`, `checklists/`, `country-rules.json`, `exports/` and `sheet/` plus the travel log CSVs (`hmrc/` optional: it can be re-seeded from the engine and the HMRC watch) as **"Nomad Pro backup YYYY-MM-DD.zip"**, with `MANIFEST.json` inside: each file's path, size and SHA-256, plus the date made, the engine version, the travel log Sheet link and the Row ID range covered.
3. Save it in `~/nomad-pro-backups/` (outside the data folder). Keep the last 3 there; delete only older "Nomad Pro backup …zip" files in that folder, never anything else.
4. Deliver as agreed at onboarding (`profile.backup`): in chat (default); and/or upload to the Google Drive folder they named (default "Nomad Pro"), only while Google Drive is connected and they agreed. Never share the file or change its sharing.
Add an `Outputs` row (type "Backup", date range, rows used, where it was saved) before delivering.
5. One line, no more: "Nomad Pro backup 2026-10-01.zip (4.2 MB): 548 days logged, last entry 30 Sep 2026." Add the validate note or any failed step (zip, upload) plainly.

Asked for a backup at any other time: same steps, same file name with today's date.

## Restore
1. Run `engine-setup` so `~/nomad-pro-engine` is in place.
2. Unzip into `~/nomad-pro-data` (if it already holds records, unzip to a new folder first and ask before replacing anything; keep the old folder).
3. Check every file against `MANIFEST.json` (SHA-256); list any mismatch or missing file.
4. Run `srt_engine.py validate daylog.json` and `summary`, and tell the user the days logged and last entry date.
