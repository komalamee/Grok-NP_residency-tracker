---
name: travel-rules-watch
description: Use when the user mentions a trip or destination, when they are in a new country, on the weekly travel-rules routine, or when they ask about visa or stay limits (Schengen 90/180, Cyprus, Thailand and others).
---

# Travel rules watch

Keeps `country-rules.json` (the country-rules table) current for every country the user is in or has upcoming, and alerts when a rule changes or a plan would break a limit.

The table this skill updates is the **user's own copy** in their data folder (`~/nomad-pro-data/country-rules.json`, seeded from the engine by `engine-setup`), never the engine's shipped one. Every tool reads that copy by default: without `--rules` they use `$NOMAD_PRO_DATA/country-rules.json`, else `~/nomad-pro-data/country-rules.json`, else the shipped table. So run the tools from the user data folder and leave `--rules` off, and the counts will use what this watch last wrote.

## Each row

`zone`, `name`, `passport`, `rule` (`rolling` / `per_entry` / `visa_per_entry`), `limit_days`, `window_days`, `counting` (any part of a day), `max_entries_per_calendar_year` if GOV.UK gives one, `effective_from` + `previous` for a rule that just changed, `source_url` (the GOV.UK foreign travel advice **Entry requirements** page for the user's passport), `source_updated` (GOV.UK's public_updated_at), `last_verified` (the date you read it), `finding` (a short quote or summary), `corroborating` (destination government, EU Commission), `legal: L8`. See `~/nomad-pro-engine/schema/country-rules.md` for the verified starter table.

## When a trip is mentioned (immediately)

1. Add or update the trip in `planned_trips` (country, first night, last night, status, pointer).
2. If the country has no row, or its row was last verified more than 7 days ago, run `~/nomad-pro-engine/tools/travel_rules_check.py --daylog daylog.json --country <gov.uk slug>` from the user data folder and read the Visa requirements text. Write or update the row in the user's own `country-rules.json` with the source and today's date. Never fill a row from memory.
3. Run `srt_engine.py plan` for the trip and report: stay-limit count on the last day (departure day included), Schengen days in the window, and entry count where GOV.UK sets one. Counts and proximity levels only.

## Weekly routine

Run `travel_rules_check.py` for all rows plus every upcoming and current country. For each zone with a changed Visa requirements section, read the new text, update the row (keep the old version under `previous` with its dates), and add a `rule_watch_log` entry. Then run the plan for all upcoming trips. **Quiet if nothing changed and no plan conflicts.** Otherwise send one message: what changed (quote + link + date checked) and which trips it touches, as counts.

## Counting rules

* **Schengen 90/180:** rolling window of 180 days ending on each day; any part of a day in a Schengen country counts, including entry and exit days. Members come from the SCHENGEN row (29 countries; Bulgaria and Romania since 1 Jan 2025). Report used, room, the earliest date a day drops off, and the longest stay from a given entry date.
* **Cyprus:** its own 90/180 count until a Schengen accession decision takes effect. When it does, set CY's `from` date in the SCHENGEN members and the engine switches automatically. Check the European Commission Schengen page and GOV.UK Cyprus page weekly.
* **Thailand:** read the current exemption length from GOV.UK and the Thai Ministry of Foreign Affairs (Department of Consular Affairs) each week; the engine applies `previous` to entries before `effective_from`. Report entries in the calendar year where GOV.UK gives a usual limit.
* Other countries: whatever GOV.UK states for the user's passport (per entry or rolling). If unclear, say so and link the page.

## Alerts (wording)

* "Rule change, Thailand (GOV.UK, updated 18 Sep 2026, checked 26 Sep 2026): visa-exempt stays are now up to 30 days. Your booked stay 3–20 Nov would reach day 18 of 30 on departure."
* "This booking would add 12 Schengen days: 71 of 90 in the 180 days to 2 Nov (getting close)."
* "Thailand entries this calendar year with this plan: 4. GOV.UK says visa-exempt entry is normally limited to two per calendar year. Which entry type are you using?"

Every message touching visas, Schengen or immigration ends with **L8**: Not tax or immigration advice — check your own position. Never suggest a route, date or visa to get round a limit; show the counts and link the official source.
