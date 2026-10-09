---
name: daily-checkin-and-catchup
description: "Nomad Pro check-in: use when the Nomad Pro check-in routine (on by default) or calendar review routine runs, when a Nomad Pro user tells you where they slept or worked, catches up missed days (\"check my week\"), asks where they stand this week, or changes, pauses or stops the check-in or calendar-review rhythm."
---
# Daily check-in, catch-up, weekly line, heads-ups and calendar review

Data: `~/nomad-pro-data/daylog.json`, rebuilt from the travel log Sheet before every run and written to the Sheet first (`export-travel-day-log`); engine `~/nomad-pro-engine` (`engine-setup` if missing). Follow `nomad-pro-core-rules`.

**Work-day rule.** Set `uk_work` with `srt_engine.apply_work_rule(log, row, calendar_titles)` (rule in force that day, `source: rule:<id>`, plus `exception: {keyword, event}` when a calendar title matches an exception keyword). Ask about work only for exceptions: "ask" items, travel days, calendar hints the rule doesn't cover. The user's answer always wins (`source: user_answer`). No rule: calendar presence never makes a work day; ask, and unanswered UK days stay `unsure` (`source: not_asked`). A changed pattern: read it back, confirm, save a new version from their date (old one closes the day before); re-tag earlier days only if they say so (`applies_to_earlier_days_agreed: true`, a `changes` entry per day with their words).

## Check-in (on from the first count: one tap-style question)
Daily at their check-in time (default 21:00) in the timezone they're in. Rebuild from the Sheet first (valid edits go in; the next message carries one line on what was taken or couldn't be used). Skip silently if there's no day log yet, today is already logged, or check-ins are paused (`profile.checkin.paused_until`).

**The question: one line, one-word answer.** Predict tonight from a booked trip or today's calendar event, else the last logged night: "Still in Bangkok today?" / "Calendar says Porto today. Right?" / no entry yet: "Where are you tonight?" Nothing else in that message (no bar, no disclaimer). "yes", "same" or a thumbs-up is yes; a place name is a move.

**After the reply.** Write the row to `Days` first (both countries in `countries_present` on a travel day; `attested` with the date, or `confirmed` if they send a record; `logged_via: checkin`; plain labels), rebuild, `validate`, `summary`, rewrite `Summary`. Reply in one line: "Logged: Bangkok, 28 Sep." Add a bar only for a heads-up or on the weekly day.
* **UK day:** one follow-up only if the rule doesn't settle it: "Work over 3 hours today? yes / no / not sure" (never defaulted; hours only if given). If the rule settles it, say what it set ("Weekday in London: work day under your rule").
* **Record pointer:** only on a travel day or a new UK place ("Booking in Gmail? yes / no / skip"); if Gmail is connected, offer the matching email as a link. Screenshots: `evidence-and-documents`.
* A calendar title naming the place: pre-fill and ask only to confirm.

**Quiet-friendly.** One message per run, never a reminder or chaser. "skip" or no reply: nothing logged, nothing more today; the day folds into the next check-in. "stop", "pause until 10 Oct", "change time to 19:00": update the existing routine (never another) and confirm in one line. No runs 22:00–08:00 their time unless they pick it. A place in a new timezone: offer once "You're on Lisbon time now. Move check-in to 21:00 there? yes / no".

**Rhythm.** After 3 unanswered check-ins in a row, offer once: "Switch to a weekly check-in, or only when I spot a move?" ("when I move": a check-in when a calendar event or message suggests travel, plus the Sunday line). Update the existing routine.

## Catch-up (folded into the check-in)
Unlogged days since the last entry go into the same question: "Missed 3 days (25–27 Sep). Bangkok all 3?" "yes" writes them all (`attested`); a range or list ("Lisbon until the 13th, then Madrid") is applied as given; "not sure" leaves them not logged. More than 7 days, or a trip in the gap: "Last entry 9 Oct. 6 days to fill: 10–15 Oct. A range is fine." Propose from calendar/email if connected. Apply the work-day rule to the range; ask only about exceptions, in one go. A proposal is a question: rows are written only after their yes. **Never guess a gap**, never fill one from a booking alone.

## Weekly "where you stand" (Sunday's check-in)
On Sundays (or `profile.checkin.weekly_line_day`) the question carries one bar line above it and one disclaimer line:
```
UK ▓▓▓░░░░░░░ 5/16 · Schengen ▓▓▓▓▓▓▓▓▓░ 77/90 · 0 missing
```
> Still in Bangkok today?
> Source: RFIG20120 · not tax or immigration advice

UK bar: nearest figure ahead in `running_count.figures` (183 until prior years are recorded). Schengen only if there in the last 180 days or a Schengen trip is saved (combined line then replaces L5). "missing" = days not logged this tax year. Detail only if asked (`srt-explainer`).

## Heads-up before a line (proactive, once per band)
After every write (check-in, catch-up, review, saved trip), check engine proximity (core rules §4) for UK figures and the ties-test line (`running_count.figures`, `ties_test`), next year's 90-day tie (`ninety_day_next_year`), UK work days vs 40 and 31, Schengen and any stay limit where they are or have a trip saved. Entering **getting close**, **at the line** or **over the line**: add a heads-up to that reply, room exactly as the engine gives it, once per figure, band and tax year (`profile.alerts_sent` `{figure, band, tax_year, at}`):
```
UK nights  ▓▓▓▓▓▓▓▓▓░ 14 / 16
```
> At the line: 1 UK day of room before 16 this tax year. Year ends 5 Apr 2027.
> Source: RFIG20120 · not tax advice

Schengen: bar, then "Getting close: 19 days of room. Earliest drop-off: 3 Oct." with L8. A saved trip moving a figure into a new band gets the same shape once, "with this trip" (`trip-planning`). Counts and dates only: never a suggestion ("leave by…") and no outcome words (core rules §7).

## Calendar review (calendar connected)
On whenever the calendar is connected (offered in `nomad-pro-getting-started` message 2; rules in `onboarding` F): Sunday 18:05 weekly by default, their timezone; fortnightly, monthly or quarterly if chosen (memory). Not connected when it runs: send nothing. The period: every night since the last review in `weekly_reviews` (first review: the last week/fortnight/month/quarter), plus earlier unlogged days.
1. **Due?** Off-rhythm runs stay quiet (fortnightly skips until 14 days since the last review; monthly/quarterly until a month/quarter has passed). Every day in the period already logged with a link or pointer: say nothing.
2. Rebuild from the Sheet. Read the calendar(s) in `profile.calendar_rules` for the period by those rules (events naming a place, flights, trains, hotel check-ins); match Gmail bookings if connected. An upcoming UK trip not in `planned_trips`: "UK visit spotted" in `trip-planning` after the review.
3. One message: "Here's what I think your [week/fortnight/month/quarter] was. Is this right?", one line per night (date, country and place, basis such as "event 'Porto, Portugal'" or "no calendar entry"); for a month or quarter, group consecutive nights ("3–11 Oct: Lisbon, Portugal"). Then the UK work each UK day gets under their rule and "Any exceptions (sick, less than 3 hours, holiday)?" (no rule: "Any UK work over 3 hours on the UK days?"; never propose a work answer).
4. Go back and forth until each line is confirmed or corrected.
5. Write confirmed days (`logged_via: weekly_review`) to the Sheet and rebuild; each correction to a logged day goes in `changes` (`via: weekly_review`, old and new values, their words); record the review in `weekly_reviews` with `period` `{from, to, rhythm}`; attach calendar/Gmail links with their OK. An event alone never becomes a day row.

**Changing the review rhythm** ("make my calendar review monthly"): update the existing routine in their timezone (never another): weekly `5 18 * * 0`; fortnightly the weekly schedule, skipping until 14 days have passed; monthly `5 18 1 * *`; quarterly `5 18 6 1,4,7,10 *`. Save in memory; confirm in one line ("Done: your calendar review is now monthly, on the 1st at 18:05."). Monthly or quarterly: mention once that more days come at once; the check-in still catches missing days.

## Flag, one at a time
UK weekday with work unanswered or `unsure`; a day without a record pointer; conflicting records (keep both in `conflict`, ask, log who resolved it); a new UK accommodation (relationship, 91-day availability, RFIG20550); a trip mentioned in passing (add to `planned_trips`, run `travel-rules-watch`); an upcoming UK trip not in `planned_trips` ("UK visit spotted" in `trip-planning`). Band changes go through the heads-up.

From 6 April, catch up last tax year to 5 April; the 7 April `year-end-lockdown` checks the year and makes its Travel and day log (only if that routine is off and no log exists, make it here with `export-travel-day-log`). Disclaimers: one line per message, as core rules §6 sets out.
