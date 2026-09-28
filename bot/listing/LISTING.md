# Marketplace listing (draft v2d, 28 Sep 2026)

## Name
Nomad Pro - UK Residency Tracker

## Pitch
The boring UK residency admin, managed for you: a day-by-day travel and work log with records, measured against HMRC's Statutory Residence Test figures and visa stay limits, with a travel concierge for your next move as a bonus. Record-keeping, not advice; free for Grok users.

## What it does
- **Logs your nights.** Tell it roughly where you've been; it never guesses a gap.
- **One-tap check-in.** "Still in Lisbon today?" Skip any day; it catches up.
- **Your UK days at a glance.** Bars against HMRC's published figures, a Sunday one-liner, a heads-up near a figure.
- **"What if" before you book.** Your count now and with the trip.
- **Watches the rules.** HMRC guidance and GOV.UK entry rules, weekly; silent unless something changes.
- **All your data in one Sheet.** Days, records, trips, changes and every export in one Google Sheet, "Nomad Pro – Travel log". Edit it any time; every PDF names the rows it came from.
- **Files for your accountant.** PDF and CSV per tax year, plus a dashboard.

## On from day one
The check-in, both weekly watches, a monthly records backup and the 7 April year-end lockdown, plus a calendar review once your calendar is connected. Say "stop" or "change time" any time.

## Who it's for
Anyone abroad who watches their UK time. Mostly British nomads and expats; any passport works.

## What it connects to
Google Sheets (with edit access) for your full travel log, Google Calendar (read-only) to propose your days, Gmail (read-only) to attach booking confirmations as records, and Google Drive for your backups. All four are offered when you start; skip any and the check-in still works.

## Try saying
1. "I left the UK in March. Lisbon to June, then Bangkok."
2. "What if I spend three weeks in London at Christmas?"
3. "I missed a week: Porto, then Madrid since Tuesday."
4. "File this year's log for my accountant."

---
*Records and arithmetic, not tax or immigration advice. Not affiliated with HMRC.*

## Visual ideas for the listing (not part of the copy)
1. **Chat screenshot:** the 2-line hello, the user's rough list, then the reply with two progress bars (`UK nights ▓▓▓░░░░░░░ 5 / 16`, `Schengen ▓▓▓▓▓▓▓▓▓░ 77 / 90`). This shows the result in about 10 seconds.
2. **Dashboard overview:** the tax-year cards and the UK-nights chart in neutral slate and navy, with fictional example data from the engine's `example/` folder.
3. **Trip "what if":** two bars (now vs with a Christmas trip) under the prompt "What if I spend three weeks in London at Christmas?"
4. **One-tap check-in:** "Still in Bangkok today?" → "yes" → "Logged: Bangkok, 28 Sep."
