# Nomad Pro – UK Residency Tracker: the Grok Bot template (v2)

This folder is the source of truth for the **bot** side of Nomad Pro: the prose the Grok Bot template carries
(skills, routines, memories, plugins, listing copy) and the script that turns it into the arguments for
`create_bot_share_json`. The **engine** side — the Python that does the counting — is the rest of this repo and
is not changed by anything in here; each user's bot installs it from `main` into `~/nomad-pro-engine`.

* **Published:** v2, staged as template version 6 and published on **28 September 2026** —
  <https://x.ai/bot/A5PJWWubWq6RSITiu_tdG>
* **Retired:** the v1 listing at <https://x.ai/bot/QUBmv77N0RIAlXTUktubY> is being taken down.
* **What it packs:** 17 skills, 6 routines, 8 memories and 4 plugins (Gmail, Google Calendar, Google Drive,
  Google Sheets), with `gettingStarted` = `nomad-pro-getting-started`.

## Layout

| Path | What it is |
|---|---|
| `create_bot_share_json.args.json` | The arguments for the next staging (v2.2 draft: 91,470 bytes). Version 6 as published is this file at commit `606861e`. Generated; don't hand-edit |
| `build.py` | Builds those arguments from `skills/` and `TEMPLATE-PACKAGE.md` |
| `TEMPLATE-PACKAGE.md` | The package spec: keep line, description, skill list, memories, plugins, the routines (cron and job text, which `build.py` reads) and the travel-log Sheet |
| `PACKAGING.md` | Which skills ship and which are excluded, with reasons |
| `skills/<name>/SKILL.md` | The 17 skills as published (front matter `name` + `description`, then the body) |
| `listing/` | Marketplace listing copy (`LISTING.md`) and `profile.json` (name, title, description) |
| `samples/` | Fictional travel-log workbook and tab screenshots used in the listing, plus the scripts that make them (`samples/src/`) |
| `docs/` | Working notes: what changed on 28 Sep, v1 vs v2, the size trim, the retest transcripts |

## Regenerating the args

```
cd bot
python3 build.py        # needs PyYAML
```

`build.py` reads the 17 `skills/<name>/SKILL.md` files (front-matter `description` plus the body), the seven routine
job texts out of `TEMPLATE-PACKAGE.md`, and its own inline copies of the plugins, memories and profile, then
overwrites `create_bot_share_json.args.json`. It also prints the size and every match of its private-data pattern
(owner names, emails, Mac paths, long opaque strings) so a leak shows up before the args are staged.

The calendar review's routine slug is `calendar-review`, not `nomad-pro-calendar-review` as the other Nomad Pro
slugs would suggest: that is the slug the published v6 card was staged with, so the args in this folder are now
exactly what was staged. The other published slugs are `nomad-pro-check-in`, `weekly-travel-rules-watch`,
`weekly-hmrc-guidance-watch`, `year-end-lockdown` and `monthly-records-backup`; the v2.2 draft adds
`nomad-pro-booking-inbox-check`.

## Size limit

Staging rejected a 103,056-byte args payload as too large; 98.0 KB had gone through, so the cap sits somewhere
between **about 98 and 103 KB**. The published version 6 is well under it: **91,338 bytes** compact (91,890 on
disk at `indent=1`; `docs/TRIM-LOG.md` quotes 91,348, which counted the longer calendar-review slug). `docs/TRIM-LOG.md` records what was cut to get there and checks that no behaviour was lost.
Keep new prose inside that budget, and re-run `build.py` to see the byte count.

## Checks

```
python3 tools/banned_scan.py bot/skills     # 0 banned-phrase hits, 0 private-data hits
python3 tools/banned_scan.py bot/listing    # 0 and 0
python3 tools/banned_scan.py .              # whole repo, 0 and 0
python3 -m unittest discover -s tools/tests # 115 tests, OK
```

The published prose (skills, listing, args) is clean. The working notes in `docs/`, along with `PACKAGING.md` and
`TEMPLATE-PACKAGE.md`, quote the outcome and deciding words on the bot's own do-not-say list (`SYSTEM.md`
section 4), so each of them opens with a `banned-list` start comment that exempts it from the phrase check; the
private-data check still runs over them.

## Changelog

### v2.2 — draft, not staged or published

* **Daily booking inbox check** (new routine `nomad-pro-booking-inbox-check`, daily 08:05 in the owner's timezone,
  cron `5 8 * * *`). Packed **switched off**; `nomad-pro-getting-started` offers it once Gmail is connected, alongside
  the other routines, and switches it on only on a yes. That yes is a standing permission: it reads Gmail
  (read-only) for booking emails since the last run (60 days the first time), skips marketing and duplicates, and
  files each one as a `Records` row plus a `Changes` row, Sheet first, then rebuilds and validates. It never adds a
  day or sets a country; conflicts, and changes or cancellations of filed bookings, go to the owner. It messages only
  when it filed something (one line per booking) or needs an answer. Every record it adds can be undone.
* `evidence-and-documents`: on-demand Gmail matches still ask first; the routine works under the standing yes, and
  "undo" removes a record with a `Changes` row. Smaller edits in `nomad-pro-getting-started` (offer and routine 7),
  `nomad-pro-core-rules` (seven routines; day rows still only on the user's yes), `onboarding` ("How to use it"),
  `export-travel-day-log` (`Profile` row) and memory 5 ("a day row").
* **Making room.** The routine's detailed steps live in the engine, `reference/booking-inbox-check.md` (engine
  0.1.6), and the `srt-explainer` checked answers moved, unchanged, to `reference/srt-checked-answers.md`; the
  skill keeps the topic list and falls back to searching the HMRC pages. `docs/TRIM-LOG.md` has the detail.
* Args 91,988 → 91,470 bytes (rule: 92,000). main's v2.1 args were 91,988 bytes by `build.py`'s measure, not the
  91,911 this file said. Needs engine 0.1.6 on `main` and a restage to reach new installs.

### v2.1 — draft, not staged or published

* **"Check my setup".** New `onboarding` section J (and its trigger in the `onboarding` description): one line each for the engine, travel log Sheet, Calendar, Gmail, Drive, routines and last backup, counts and links only, with what a failure stops and the fix. Also run once right after a connection is added.
* **Dropped-connection heads-up.** `nomad-pro-core-rules` §9: when Calendar or Gmail worked and now fails, one line once in the next check-in (what it stops, and 'Reconnect it, then say "check my setup".'), no repeat until it works again, so routines don't go quiet unnoticed.
* Args 91,338 → 91,911 bytes (rule: 92,000). Needs a restage from the bot that owns the listing to reach new installs.

### v2 — published 28 September 2026 (template version 6)

* **Counts first.** A new owner gets a visual count by the bot's second message instead of a 25–35 question
  onboarding; the rest of setup arrives in chunks, when it's needed.
* **The same 17 skill names as v1, with rewritten bodies**, and descriptions that now start "Nomad Pro <job>:" and
  scope their triggers to a Nomad Pro user or routine, so they can't pull in other bots on a shared box. Four of
  them (`nomad-pro-core-rules`, `nomad-pro-getting-started`, `records-backup`, `year-end-lockdown`) have no copy in
  the repo's older root `skills/` folder.
* **Result gate.** No residence conclusion before a tax year can be counted in full; the stage line is quoted from
  the engine (v0.1.4) rather than composed by the bot, and the outcome and deciding words it used to allow have
  gone on the do-not-say list.
* **One-tap check-in**, a Sunday "where you stand" line, heads-ups once per band as a figure gets close, one-tap
  catch-up for missed days, and trip "what if" answered from the engine's `days_remaining`.
* **Six routines packed** (v1's set, three slugs renamed): daily check-in, Monday travel-rules watch, Wednesday HMRC
  guidance watch, calendar review while the calendar is connected, 7 April year-end lockdown, monthly records
  backup. Packed routines run silently until the first count; the watches stay quiet unless something changed.
* **The travel log Sheet is the single source.** One Google Sheet, "Nomad Pro – Travel log", with tabs Summary,
  Days, Records, Trips, Profile, Changes and Outputs; `daylog.json` is rebuilt from it before every count and every
  output names the rows it came from. CSVs on the box when Sheets isn't connected.
* **Four plugins packed** so they're offered on day one and can each be declined: Gmail and Google Calendar
  (read-only), Google Drive (backups and records), Google Sheets (the travel log, needs edit access). v1's skills
  used Calendar, Gmail and Drive too, but whether its template packed them was never recorded.
* **8 memories** kept from v1's twelve; four were dropped as out of date or not job facts, and the engine-repo one
  no longer names the owner (`docs/V1-V2-COMPARISON.md` has the item-by-item reasons).
* **Args trimmed** from 103,056 to 91,338 bytes after staging refused the larger payload; wording only.

### v1 — <https://x.ai/bot/QUBmv77N0RIAlXTUktubY> (retired)

The same 17 skill names with their original bodies and generic descriptions, the six routines, 12 memories, no
`plugins` field in the recorded recipe, and a long question-and-answer setup before the first count. No copy of the
v1 share call survives, so what it actually packed beyond the skills is unverified; `docs/V1-V2-COMPARISON.md`
compares the two line by line and says which v1 details are inferred.

## Notes on what's here

* The bundle's superseded working copies were left out: the pre-trim skill bodies, the `prev-round/` drafts
  (including a pre-0.1.4 copy of the skills), `skills.diff` (a live-vs-draft diff against files that aren't in this
  repo) and `engine/`, whose result-gate patch landed in the engine as v0.1.2 long ago. Everything published is
  here.
* `TEMPLATE-PACKAGE.md` no longer prints the owner's agent id; the rest of the notes are unedited, so they still
  mention the owner's own box paths and backup folders as context.
* Everything under `samples/` is fictional example data, generated by `samples/src/build_sample.py`.
* The repo root still carries the v1-era bot material (`skills/`, `routines.md`, `LISTING.md`, `SYSTEM.md`). This
  folder supersedes it for anything the published bot does.
