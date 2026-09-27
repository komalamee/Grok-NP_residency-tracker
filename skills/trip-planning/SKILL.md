---
name: trip-planning
description: Use when the user asks where they can go, wants to model or compare proposed trips, asks how many UK days or Schengen days they have left, or is planning a UK visit or next tax year.
---

# Trip planning (AI travel concierge)

The user describes plans in plain words ("Christmas in London, then skiing in Austria in January, maybe Bali in spring"). You turn them into proposed trips and show what each would do to the log. You present options as counts; the user decides.

## Steps

1. Turn the plan into trips: country, first night, last night (midnight rule). Ask only for what's missing ("Which night do you fly back?"). Mark each as `idea` unless booked.
2. Refresh rules for every destination (`travel-rules-watch`) if its row is older than 7 days or missing.
3. Run `~/nomad-pro-engine/tools/srt_engine.py plan daylog.json --trip CC:FROM:TO --trip CC:FROM:TO` for the plan (and for alternatives if the user gives them). `--trip` takes one trip and is repeated once per trip, never a space-separated list. Run it from the user data folder and leave `--rules` off: the tools read the user's own `country-rules.json` (`$NOMAD_PRO_DATA/country-rules.json`, else `~/nomad-pro-data/country-rules.json`) before the engine's shipped table, so the weekly travel-rules watch's updates are the ones counted.
4. Report, per tax year touched, as a compact table:
   * UK midnights now → with this plan, against the user's own band: room before the line for their recorded number of ties, with the proximity level (e.g. "53 → 70 UK midnights: 50 days of room before the 120-day line for 1 tie (comfortable room)").
   * **Next year's 90-day tie:** UK midnights this year vs the 90-day line (RFIG20570).
   * **Country tie:** UK midnights vs the country with the most midnights, if it applies (RFIG20580).
   * UK work days vs 40 (RFIG20560) if the plan includes UK work.
   * **Schengen:** days in the 180-day window on the last day of each Schengen trip, room, the earliest drop-off date; longest stay from an entry date if asked.
   * **Stay limits** for each other country (per entry or rolling; entries per year where GOV.UK sets one).
   * Days not logged that could change the picture.
5. Offer to save trips they like as `planned_trips` and to recheck weekly.

## "Where can I go?"

Show the room, not a recommendation: UK midnights room in the current band, Schengen room today and on chosen dates, the longest Schengen stay from a date, and which countries in the rules table have limits that fit the length they want. If they ask "what should I do", say you can't advise and restate the counts.

## Wording

* Allowed: counts, room, proximity levels, "this plan would add…", "on these dates the window would show…".
<!-- banned-list:start -->
* Not allowed: "you'll be fine", "you'll stay non-resident", "leave by…", "you should…".
<!-- banned-list:end -->
* End with L4 (with the page reference for the figures used) and L8 if any visa or Schengen count appears.
