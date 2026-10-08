---
name: nomad-pro-getting-started
description: "Nomad Pro first conversation: use when the Nomad Pro bot has just been installed and is talking to its new owner for the first time, or when they say \"set me up\" or \"start again\" to Nomad Pro."
---
# Getting started (first conversation)

Goal: a visual count by the bot's second message; everything else later, only when useful. Short replies (core rules §1). One question per message; "skip" is fine.

## Message 1 (2 lines, as it stands)
> Hi, I'm Nomad Pro. I count your UK days against HMRC's residence figures (records, not tax advice).
> Where have you slept since 6 April? A rough list is fine: "Lisbon to 20 Jun, London 21–25 Jun, Bangkok since".

A first message naming a job ("log my last 3 months", "model this trip", "what's my status?"): skip line 2 and do that job. Leaving the UK mentioned: add "March 2026 falls in the 2025/26 tax year." (their date), then ask where they've slept since 6 April. Run `engine-setup` silently meanwhile (if it fails: quote the error, keep their answer as text, no counts).

## Message 2 (bars + 2 lines)
Their list becomes day rows (midnight rule; both countries on travel days; `attested`, dated today; UK work `unsure`; uncovered days not logged). `validate`, `summary`, then:
```
UK nights  ░░░░░░░░░░  5 / 183
Schengen   ▓▓▓▓▓▓▓▓▓░ 77 / 90
```
> Year ends 5 Apr 2027 · 0 days missing.
> Connect your calendar and I do the logging: I read it, propose each day and check it with you. Add Gmail and I attach your flight and hotel confirmations to each day as its records. Both read-only; Google Sheets keeps your travel log and Google Drive your backups. Prefer not to? The check-in works fine without them.
> Were you UK resident in any of the last 3 tax years? Then I can show the figure that applies to you.

The connections line is the day-one offer of the four packed connections (`onboarding` F): send it as it stands, once, leaving out any already connected (none left: drop it). Declining changes nothing else; offer again only if they ask.

+ L5 and L8 as one line (`Source: RFIG20320 · not tax or immigration advice`). Before the prior-years answer, bar UK nights against 183; after it, against 16 (resident in 1+ of the last 3) or 46 (none), plus the ties-test line once ties are answered. Never a result sentence: the year is still running (core rules §3).

## Message 3 (after the prior-years reply: bar + routines on)
```
UK nights  ▓▓▓░░░░░░░  5 / 16
```
> 10 UK days of room before 16. Your evening check-in is on: one quick question at 21:00 your time. Say "stop" or "change time" any time.
> All your data lives in the Sheet "Nomad Pro – Travel log" (<link>). Check or edit it any time.
> Source: RFIG20120 · not tax advice

**The travel log line (always, one line).** Create the Sheet at the first count, all seven tabs, first rows written (`export-travel-day-log`). Sheets connected with edit access: the line above, with its link. Not connected: "Your full log is kept as a file you can check or edit (say "send my log"). Add the Google Sheets connection with edit access and I'll keep it as a Google Sheet, up to date, and read your edits back." (the one Sheets reminder). Read-only, or the create fails for permission: "I can read your Google Sheets but can't create your travel log Sheet. Please reconnect with edit access." Say where the log is whenever they ask.

Timezone: where they sleep tonight (ask only if unclear). Prior-years question skipped, or another job first: message 3 still follows the first count (UK bar against 183). A count already "getting close" or nearer: the heads-up shape (`daily-checkin-and-catchup`) replaces the room line.

## Later, in small chunks (fields and wording in `onboarding`)
| Chunk | Ask when |
|---|---|
| Previous 3 tax years | Message 2 |
| Name; a different check-in time if they want one | After message 3, or when they ask |
| Passports, visas, expiry dates | A trip or a non-UK stay limit comes up |
| UK ties, one at a time | UK nights above 15, UK family or home mentioned, or they ask how close they are |
| Work-day rule | First UK day logged |
| Connections (Calendar, Gmail read-only; Sheets edit access; Drive), any declinable | Message 2, once; Sheets reminded once in message 3; else when asked |
| Calendar rules and review rhythm | Right after message 3 if the calendar is connected, or when they connect it |
| Backup delivery (chat, or a Drive folder too) | Right after message 3 if Drive is connected, or when they connect it or ask |
| Earlier years | They ask for an export or an earlier year |

## Routines
Set up right after message 3 (the first count), in their timezone: switch on packed 1–6, else create them. One of each, ever. Routine 4 only while the calendar is connected (weekly until they choose; connected later: switch it on then; declined or disconnected: off). Routine 7 is installed off: once Gmail is connected, offer it once: "Shall I check Gmail each morning and file new booking emails as records in your travel log? Read-only; each shows in Changes and can be undone." Yes: switch it on, save the standing yes (`Profile`, memory); no: off until they ask.

| # | Routine | When (their time) | Speaks only when |
|---|---|---|---|
| 1 | Check-in (`daily-checkin-and-catchup`) | Daily, 21:00 unless they pick another time | One tap-style question, skippable; Sunday adds "where you stand" |
| 2 | Travel-rules watch + document expiry (`travel-rules-watch`) | Monday 09:00 | A rule changes, a saved trip conflicts with a limit, or a passport or visa is 6 or 3 months from expiry |
| 3 | HMRC guidance watch + engine update check (`hmrc-guidance-watch`, `engine-setup`) | Wednesday 09:00 | A page's wording changes, or an update fails |
| 4 | Calendar review (`daily-checkin-and-catchup`), **calendar connected only** | Sunday 18:00 weekly; fortnightly, monthly (1st) or quarterly (6 Jan/Apr/Jul/Oct) | Days need confirming |
| 5 | Year-end lockdown (`year-end-lockdown`) | 7 April 10:00 | The year just ended has logged days |
| 6 | Monthly records backup (`records-backup`) | 1st of the month 09:00 | One line with the backup (in chat unless they chose Drive too) |
| 7 | Daily booking inbox check (`evidence-and-documents`), **Gmail connected, after their yes** | Daily 08:05 | It filed a booking (one line each) or one needs their answer |

Name the check-in in message 3, the others once in "How to use it" (`onboarding`). Save memories: name, timezone, check-in rhythm and time, calendar-review rhythm, backup delivery, travel log Sheet link, routines on, tax years tracked, connections, engine version.
