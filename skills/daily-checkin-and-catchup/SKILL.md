---
name: daily-checkin-and-catchup
description: Use when running the scheduled check-in, when the user tells you where they were or what they did, or when they come back after going quiet and missed days need filling in one go. Also adapts the check-in rhythm.
---

# Daily check-in and catch-up

## The check-in (four questions, nothing more)

**Follow the agreed work-day rule.** Set `uk_work` with `srt_engine.apply_work_rule(log, row, calendar_titles)`: it applies the rule in force that day (`profile.work_day_rules`) and records `source: rule:<id>`, plus `exception: {keyword, event}` when a calendar title matches one of the rule's exception keywords. Ask about work only for exceptions: days the rule leaves as "ask", travel days, and days where the calendar hints at something the rule doesn't cover. The user's own answer always takes priority over the rule (`source: user_answer`). With no rule in force, calendar presence alone never makes a work day: ask, and leave unanswered UK days `unsure` (`source: not_asked`).

**Changing the rule.** If the user says their pattern has changed ("I'm freelancing from 1 March, weekends are sometimes work"), read the new rule back, confirm, and save it as a new version (`v2`, `effective_from` the date they give, `agreed_at` today, `wording_shown`), closing the old version the day before. Never re-tag earlier days under the new version unless they say so; if they do, set `applies_to_earlier_days_agreed: true` and log each changed day in `changes` with their words.

1. **Where were you today?** One location (city, country). Record it as tonight's `midnight_country` unless they say they'll move before midnight.
2. **Did you work?** Skip this if the agreed work-day rule already settles today and the calendar shows no exception; say what the rule set ("Weekday in London: work day under your rule") so they can correct it.
3. **If you were in the UK: was it more than 3 hours?** (yes / no / unsure). Hours only if they give a number. Never default hours.
4. **Where does the record sit?** A short record pointer: "Airbnb receipt in Gmail", "Revolut spend", "Google Maps timeline", "boarding card in Wallet". If Gmail is connected, offer the matching email as a link instead ("Attach the Booking.com email?"); if they send a screenshot, store it in `evidence/` (see `evidence-and-documents`).

If a calendar event title already names the place, pre-fill and ask only for confirmation: "Calendar says Porto, Portugal. Right? Work today?" Keep it to one short message; the user can answer in any wording ("Porto, no work, Booking.com email").

Write the row: `midnight_country`, `countries_present` (add both countries on a travel day), `uk_work`, `evidence` (pointer, and `url` or `file` when a link or stored file exists) with `added_at`, `confidence` (`confirmed` if a record exists, `attested` if it's their word alone, with the date), `logged_via: checkin`. Then run `srt_engine.py validate` and `summary`.

Reply in two or three lines: what was recorded, and only if something moved: e.g. "UK midnights 2026/27: 41. 79 days of room before the 120-day line for 1 tie (comfortable room)." + L4 with the page. Nothing to say? Just confirm the entry.

## Catch-up (the user went quiet)

Before asking today's questions, check the log for unlogged dates since the last entry. If there are any:

* Say how many and the range: "Last entry 9 Oct. 6 days to fill: 10–15 Oct."
* Pre-fill from calendar/email if connected, as a proposed list, and ask the user to confirm or correct in one reply. Otherwise ask as a single question: "Where were you each night from 10 to 15 Oct? A range is fine, e.g. 'Lisbon until the 13th, then Madrid'."
* Apply the work-day rule to the whole range and ask only about the exceptions in one go ("Your rule makes 6 of these UK days work days; your calendar shows 'sick' on Tue 4th. Anything else different?"). With no rule, ask for the range; UK days they don't answer stay `unsure`.
* Write every day; any day the user can't place stays not logged. **Never guess a gap** and never fill it from a booking alone without the user's confirmation.
* Then continue with today's check-in.

## End-of-week calendar review (if the calendar is connected)

Run by the weekly review routine (default Sunday 18:00 local) and whenever the user asks "check my week".

1. Read the calendar for the 7 days just ended (and any unlogged days before them). Use events whose title or location names a place, plus flights, trains and hotel check-ins. If Gmail is connected, match bookings to the same dates.
2. Build a **proposal**, one line per night: date, proposed midnight country and place, and the basis ("event 'Porto, Portugal'", "flight TP1335 LIS–OPO", "Booking.com email"). Mark days with nothing as "no calendar entry". Propose UK work only from the agreed work-day rule (say which rule and any calendar exception keyword it matched); with no rule, never propose a work answer, ask.
3. Send it as one message: "Here's what I think your week was. Is this right?" followed by the list, then the UK work each day gets under their work-day rule, and "Any exceptions (sick, less than 3 hours, holiday)?" (with no rule: "Any UK work over 3 hours on the UK days?")
4. Go back and forth until the user confirms or corrects each line. Accept corrections in any wording ("Wednesday I was still in Lisbon").
5. Write the confirmed days (`logged_via: weekly_review`, confidence `confirmed` where a record exists, else `attested`). For every correction to an already-logged day, append to `changes` with `via: weekly_review`, the old and new value and the user's words as the reason. Record the review itself in `weekly_reviews` (proposed days, status, corrections, confirmed_at).
6. Attach links for the evidence used (calendar event link, Gmail message link) with the user's OK.
7. Days the user can't place stay not logged. The calendar is a source of evidence, not a record of where they slept; an event alone never becomes a day row without confirmation.

## Rhythm

* Default daily at the user's chosen time in their timezone.
* If the user misses 3 check-ins in a row, or says so, offer weekly or "when I move". "When I move" = a check-in when a calendar event or message suggests travel, plus a weekly sweep.
* Update the check-in routine when the rhythm changes.

## Things to flag (auditor-style, one at a time)

* A UK weekday with work not answered, or `unsure`.
* A logged day without a record pointer.
* Two records pointing to different places: record both in `conflict`, ask which is right, log who resolved it.
* A new UK accommodation (ask the relationship and 91-day availability; RFIG20550).
* A trip mentioned in passing: add to `planned_trips` and run `travel-rules-watch` for it now.
* A count crossing into "getting close" or "at the line": state it once, as a count with the page reference. No advice.

L4 when a rule or figure is stated; L8 when Schengen or a visa limit is mentioned.
