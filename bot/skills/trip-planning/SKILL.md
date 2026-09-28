---
name: trip-planning
description: "Nomad Pro trip planning: use when a Nomad Pro user asks \"what if\" about a trip before booking, wants to model or compare trips against their UK day count or Schengen/stay limits, asks how many UK or Schengen days they have left, or is planning a UK visit."
---
# Trip planning

Turn plain-words plans into trips and show what each does to the log, as counts; the user decides. Engine `~/nomad-pro-engine` (`engine-setup` if missing); data `~/nomad-pro-data`, rebuilt from the Sheet.

1. Turn the plan into trips: country, first night, last night (midnight rule); ask only for what's missing. Mark `idea` unless booked.
2. Refresh rules for each destination with `travel-rules-watch` if the row is missing or older than 7 days.
3. `python3 ~/nomad-pro-engine/tools/srt_engine.py plan daylog.json --trip CC:FIRST_NIGHT:LAST_NIGHT` (one `--trip` per trip; alternatives run separately; engine v0.1.4+).
   **Never do the arithmetic; read the engine's numbers.** UK: `years[].uk_days_remaining_with_plan` (`figure`, `test`, `uk_days`, `days_remaining`, `days_over`, `ref`). Schengen: `schengen_days_remaining_with_plan` (`on`, `used`, `limit`, `days_remaining`, `days_over`, `earliest_drop_off`); other stay limits: `days_remaining` / `days_over` on each `limits_at_trip_end` row. `days_remaining` counts days that still fit **below** the figure (15 UK days against "fewer than 16" is 0, not 1); quote it, never recompute. Missing or `null`: run `engine-setup`; still missing, bars without a room line.
4. **"What if" reply: before/after bars, then at most 2 lines** (core rules §1), for the figures that move most: UK (`uk_days` / `figure`), Schengen (`used` / `limit`) if the plan has a Schengen stay. "What if I spend 18–27 Dec in London?":
   ```
   UK nights  now  ▓▓▓░░░░░░░  5 / 16
              plan ▓▓▓▓▓▓▓▓▓░ 15 / 16
   ```
   > With this trip: 0 UK days of room before 16 (at the line). Next year's 90-day tie: 15 of 90.
   > Source: RFIG20120 · not tax advice

   More only if it applies or they ask: ties-test room and band ("105 days of room before the 120-day line for 1 tie"); country tie (RFIG20580); UK work days vs 40 if UK work is planned (RFIG20560); Schengen at its fullest (`used` of `limit` on `on`, `days_remaining`, earliest drop-off); other stay limits; unlogged days that could change the picture. Two plans: one bar pair each, same figure.
5. One question: "Save this trip? I'll recheck it weekly." Yes: a `Trips` row (columns in `export-travel-day-log`; Status "Idea (what if)" or "Booked", Result when saved from the engine) plus a `Changes` row, rebuilt into `planned_trips` (`id` = Trip ID). They can edit or cancel it in the Sheet (read at the next rebuild); the weekly travel-rules watch and check-in heads-up cover it. Not saved: nothing is kept.

"Where can I go?": show the room, not a recommendation (UK room in the current band, Schengen room today and on chosen dates, longest Schengen stay from a date, countries whose limits fit the length). Asked "what should I do": say you can't advise and restate the counts.

<!-- banned-list:start -->
Allowed: counts, room, proximity levels, "this plan would add…". Not allowed: "you'll be fine", any residence status or outcome, "leave by…", "you should…".
<!-- banned-list:end -->
## UK visit spotted
A calendar event, a Gmail booking (if connected) or a message shows an upcoming UK trip not in `planned_trips`: confirm the dates, add it (`idea` or `booked`), run `plan --trip GB:FIRST_NIGHT:LAST_NIGHT`, and send one line: UK midnights this tax year now → after, `days_remaining` before its figure (or the ties-test room) with proximity band, and whether this tax year would go over 90 UK days (next year's 90-day tie, RFIG20570); UK work days vs 40 (RFIG20560) if work is planned. E.g. "UK 18–27 Dec (booked): 41 → 51 UK midnights in 2026/27: 69 days of room before the 120-day line for 1 tie (comfortable room); 51 of the 90 days for next year's 90-day tie." L5. Once per trip (record `uk_check_sent: {at, from, to}` on the trip); send again only if the dates change.

End with one disclaimer line: L5 (page for the figures used), or `Source: [HMRC ref] · not tax or immigration advice` if any visa or Schengen count appears.
