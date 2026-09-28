---
name: destination-concierge
description: Use when the user asks "where should I go next?", "where could I spend the winter?", "suggest somewhere for 2 months" or similar open destination questions. Runs a light preferences questionnaire (saved to their profile), then shortlists destinations that fit both their preferences and their log (UK line, Schengen window, stay limits, entry rules), with sources researched at answer time. Not part of onboarding.
---

# "Where should I go next?" destination concierge

A headline benefit, offered when the user asks or when a plan conversation opens up ("not sure where yet"). **Never run it during onboarding** and never push it unprompted more than once a month.

## 1. Preferences (first time only; later just confirm or update)

Ask in two short messages, accepting "don't care" for anything. Save to `profile/destination-preferences.json` (schema `~/nomad-pro-engine/schema/destination-preferences.schema.json`), with a history entry when an answer changes.

1. Budget: monthly total (and whether rent is included), rent ceiling and type (room, studio, 1-bed, serviced).
2. What matters, each 0–3: cost of living, food cost, ease of public transport, taxi/ride-hail cost, English widely spoken, LGBTQIA+ safety (laws and local attitudes), crime safety.
3. Languages they speak, climate they like, time-zone band for work calls, internet needs, stay length (min/max days), must-haves and places to avoid.
4. Whether to include community threads (Reddit and similar) on local nuances, always labelled anecdotal.

## 2. Hard filters from the log (run the tools first)

For the requested window, run `~/nomad-pro-engine/tools/srt_engine.py plan` on each candidate (one `--trip CC:FIRST_NIGHT:LAST_NIGHT` per candidate, repeated) and read `country-rules.json` (refresh with the `travel-rules-watch` skill if the entry is older than 7 days or the country isn't in it). Run it from the user data folder and leave `--rules` off, so the tools read the user's own `country-rules.json` (`$NOMAD_PRO_DATA/country-rules.json`, else `~/nomad-pro-data/country-rules.json`) before the engine's shipped table:

* **UK line:** any UK nights in the plan against the user's tie band (room and proximity level, RFIG20520), and the 90-day tie for next year (RFIG20570).
* **Schengen:** days used in the rolling 180 at every date of the stay; the latest date a stay could end without going over 90; the earliest drop-off date.
* **Cyprus** on its own 90/180 until its Schengen accession takes effect.
* **Stay limits and entry rules** for each candidate from GOV.UK foreign travel advice (entry requirements): visa-exempt length, entries per year, onward-ticket rules.

A candidate that would break a limit on the user's dates is shown as "doesn't fit these dates" with the count, never silently dropped, and the date range that would fit if there is one.

## 3. Research at answer time (cite everything)

For each shortlisted place (3–5), research live and cite source + date for every figure:

| Topic | Preferred sources |
|---|---|
| Entry rules, local laws, LGBTQIA+ travel, crime and terrorism | GOV.UK foreign travel advice (entry requirements; "Safety and security"; local laws and customs) |
| Cost of living, rent, food, taxi cost | Numbeo or similar crowd-sourced indices (label as crowd-sourced, give the retrieval date), local listing sites for rent ranges |
| Transport ease | Official transit operators, ride-hail availability |
| English spoken | EF English Proficiency Index or similar (name it, year) |
| LGBTQIA+ | GOV.UK local laws section plus ILGA World or Equaldex (name and date) |
| Local nuances | Reddit threads (r/digitalnomad, city subs): quote briefly, link, mark **anecdotal** |

No source, no figure. If data is old or thin, say so.

## 4. What you send back

One short table, then two lines per place:

| Place | Fits your dates? | Stay limit / entry | Schengen after stay | UK line | Rent (1-bed, centre) | Taxi 5 km | English | LGBTQIA+ (GOV.UK) | Crime (GOV.UK) |

* Rank by the user's own weights, and show the weights used.
* Counts first: "Lisbon 1 Feb–31 Mar would take your Schengen count to 88 of 90 on 31 Mar (at the line); earliest drop-off 14 Apr." + L8.
* Never tell the user where to go or that a place is "best for your tax position". The user chooses; offer to model any of them in detail with the `trip-planning` skill or add one to `planned_trips`.

End with L8 (visa and stay limits always appear) and L4 if a UK figure is stated.
