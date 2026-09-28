<!-- banned-list:start (working notes: they quote wording the bot itself never uses) -->
# Retest (round 3: routines on + quality pass), 28 Sep 2026

Round 3 re-runs (a)–(d) against the 28 Sep drafts and adds (e)–(k) for the new behaviour. Counts re-checked on the box with the installed engine v0.1.2 (`~/nomad-pro-engine`, b6d51be) against throwaway test logs in `/tmp` (nothing in `~/nomad-pro-data` was touched). Round 2 is kept in `prev-round/RETEST.v2b.md`.

## (a)–(d): round 2 scenarios, re-run

These are paper simulations that follow the v2b drafts literally. The counts were checked against the merged engine v0.1.2 (`main` @ b6d51be, PR #3) with a test log: user list "Lisbon to 20 Jun, London 21–25 Jun, Bangkok since", as of 27 Sep 2026, UK resident in the previous 3 years. Result: `stage_lines: []`, withheld because "the tax year is still running", running count 5 against 16 and 183, Schengen 77 of 90.

## (a) "hi"
**First reply (2 lines):**
> Hi, I'm Nomad Pro. I count your UK days against HMRC's residence figures (records, not tax advice).
> Where have you slept since 6 April? A rough list is fine: "Lisbon to 20 Jun, London 21–25 Jun, Bangkok since".

**Count reply** (after the list):
```
UK nights  ░░░░░░░░░░  5 / 183
Schengen   ▓▓▓▓▓▓▓▓▓░ 77 / 90
```
> Year ends 5 Apr 2027 · 0 days missing.
> Were you UK resident in any of the last 3 tax years? Then I can show the figure that applies to you.
> Source: RFIG20320 · not tax or immigration advice

**After "yes":**
```
UK nights  ▓▓▓░░░░░░░  5 / 16
```
> 10 UK days of room before 16. Your evening check-in is on: one quick question at 21:00 Bangkok time. Say "stop" or "change time" any time.
> Source: RFIG20120 · not tax advice

Result: **pass**. The intro is 2 lines, with a visual by the bot's 2nd message, no form, and connectors offered later. Round 3: the check-in is now switched on (stated, not asked), and the two weekly watches go on silently; they're named once in "How to use it".

## (b) "I left the UK in March, am I non-resident this tax year?"
> I can't say; a qualified adviser can. March 2026 falls in the 2025/26 tax year.
> Where have you slept since 6 April? A rough list is fine.

Then the bars above plus "No result line until the year ends and every day and tie is filled in."

Result: **pass**. There's no verdict (engine gate plus core rules §3), and the tax-year line from the March fix is now included. It's 2 lines, with the count after one answer.

## (c) "Log the last 3 months, quickly"
> Go ahead, a rough list is fine: "Lisbon until the 13th, then Madrid". (Records, not tax advice.)

After the list: bars + "Year ends 5 Apr 2027 · 83 days missing (6 Apr–27 Jun)." If it includes a UK day, one work question follows.

Result: **pass**. It honours the intent and gets to a visual count in 2 bot messages.

## (d) "Should I set up a Portuguese company?" / "Which crypto should I buy?"
> That's outside what I can help with; I keep your UK day records and travel limits. An adviser can help with company set-up.
> Want to see how many nights you've logged in Portugal this tax year?

(For crypto, drop the second line.)

Result: **pass**. It's short and in scope, with no advice.

## (e) Evening check-in, 28 Sep (Mon), user in Bangkok
> Still in Bangkok today?

User: "yes" → `Logged: Bangkok, 28 Sep.` (no bar: nothing changed band; no disclaimer: no figure). "skip" or silence → nothing logged, nothing more sent today.

Result: **pass**. One tap-style question, skippable, one message per run.

## (f) Sunday check-in with the weekly line (27 Sep 2026 is a Sunday)
```
UK ▓▓▓░░░░░░░ 5/16 · Schengen ▓▓▓▓▓▓▓▓▓░ 77/90 · 0 missing
```
> Still in Bangkok today?
> Source: RFIG20120 · not tax or immigration advice

Engine: `running_count` 5 vs 16 (RFIG20120), Schengen 77 of 90 on 27 Sep, 0 unlogged. Result: **pass**: one visual line, one question, one disclaimer line.

## (g) Catch-up after 3 missed days
> Missed 3 days (25–27 Sep). Bangkok all 3?

"yes" writes 3 `attested` rows; "Bangkok, then Hanoi since Saturday" is applied as given; "not sure" leaves them not logged. Result: **pass**: one tap, never a guessed gap (rows only after yes).

## (h) Heads-up: Schengen enters "getting close"
Test log B: Portugal 6 Apr–31 May, Thailand 1 Jun–13 Sep, Portugal since 14 Sep. Engine: 25 Sep 69/90 (comfortable room), 26 Sep 70/90 (getting close, room 20), earliest drop-off 3 Oct. The 26 Sep check-in reply:
```
Schengen   ▓▓▓▓▓▓▓▓░░ 70 / 90
```
> Logged: Lisbon, 26 Sep. Getting close: 20 days of room. Earliest drop-off: 3 Oct.
> Not tax or immigration advice — check your own position.

Sent once for this band (`profile.alerts_sent`); the 27 Sep reply (71/90, same band) is just "Logged: Lisbon, 27 Sep." Result: **pass**: counts and dates only, no suggestion.

## (i) "What if I spend 18–27 Dec in London?" (test log A)
Engine `plan --trip GB:2026-12-18:2026-12-27`: UK midnights 5 → 15 in 2026/27; ties-test 105 days of room before 120 (1 tie); 90-day tie for 2027/28: 15 of 90.
```
UK nights  now  ▓▓▓░░░░░░░  5 / 16
           plan ▓▓▓▓▓▓▓▓▓░ 15 / 16
```
> With this trip: 0 UK days of room before 16 (at the line). Next year's 90-day tie: 15 of 90.
> Source: RFIG20120 · not tax advice

Then: "Save this trip? I'll recheck it weekly." Result: **pass**: before/after visual, 2 lines, no advice. Re-run 28 Sep on engine v0.1.4 (052b59e): `years[0].uk_days_remaining_with_plan` = `{figure: 16, uk_days: 15, days_remaining: 0, days_over: 0, text: "0 UK days of room before 16: first automatic overseas test"}`; `schengen_days_remaining_with_plan.days_remaining` = 90. The bot now quotes these; the earlier "1 day" line was the bot's own 16 − 15 and was off by one against the engine's "fit below" convention.

## (j) "File this year's log for my accountant"
PDF + CSV to the user only, with one line: "Travel and day log – 2026/27 (to 28 Sep 2026): PDF to read, CSV one row per date. 5 UK midnights · 5 UK work days unsure · 0 days not logged." + `Source: RFIG20710 · not tax advice`, then the paste-ready cover note offer. The bot never sends it. Result: **pass on paper**; PDF rendering not re-run this round (WeasyPrint check unchanged from round 1).

## (k) Weekly watches, nothing changed
Wednesday HMRC watch: all pages `unchanged` or `date_only` → no message, run logged in `watch/`. Monday travel-rules watch, first run after install → baseline only, no message. Result: **pass**: silent unless something changes.

## Checks
- `banned_scan.py` (engine v0.1.2) on all 17 drafted skills and the listing, 28 Sep: 0 banned-phrase hits, 0 private-data hits.
- Test logs A and B pass `srt_engine.py validate`, including with the new optional fields (`profile.checkin.weekly_line_day`, `profile.alerts_sent`).
- Bar maths (10 blocks, rounded): 5/16 → 3, 15/16 → 9, 14/16 → 9, 70/90 → 8, 77/90 → 9, 41/121 → 3.
- Every routine mention now says on by default (check-in, HMRC watch, travel-rules watch) or offered later (backup, year-end, calendar review): getting-started, onboarding B/G, daily-checkin, both watches, records-backup, year-end-lockdown, core rules §1, listing, PACKAGING.md.

## Round 3b (engine v0.1.4), 28 Sep 2026
- Engine v0.1.4 (`main` @ 052b59e, PR #5): 115 tests pass. `banned_scan.py` v0.1.4 (now also flags verdict, determine, the answer and every "non-resident") over the 17 skills + listing: 0 banned-phrase hits, 0 private-data hits.
- (i) re-run with the engine's new fields: 0 UK days of room before 16 (see above).
