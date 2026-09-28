---
name: year-end-lockdown
description: "Nomad Pro year-end: use when the Nomad Pro 7 April routine runs, when a Nomad Pro user asks to close or lock down a UK tax year, or wants to change a day in a locked year."
---
# Year-end lockdown

**On by default** (7 April, 10:00 their time, from the first count; never a duplicate), for the tax year that ended on 5 April. That year has no logged days: send nothing. Engine `~/nomad-pro-engine` (`engine-setup` if missing). Follow `nomad-pro-core-rules`.

1. **Rebuild from the Sheet** (`export-travel-day-log`), then **catch up** every unlogged day to 5 April (`daily-checkin-and-catchup`).
2. **Book the session.** One short message with that year's headline counts (`summary`): UK midnights, UK work days, Schengen days in the last 180 at 5 April, days not logged, days without a record pointer (L4 when a figure is stated). Ask when they'd like about 20 minutes to lock the year down. Calendar connected: offer 2–3 free slots in the next 7 days; create the event ("Nomad Pro: lock down YYYY/YY") only after they pick one and say yes. No reply in 7 days: remind once, then leave it.
3. **The session.**
   * Show the pre-filled year grouped into stays ("3–11 Oct: Lisbon, Portugal").
   * Ask only about open items: not logged, UK work `unsure`, conflicts, no record pointer. Days they can't place stay not logged.
   * Re-confirm that year's tie answers, one at a time with pages: family (RFIG20530), accommodation (RFIG20550, including the 16-night count at a close relative's), work (RFIG20560), 90-day (RFIG20570), country (RFIG20580). Their answer is kept; flag differences from the log, never overwrite.
   * Status documents to file (contract end, P85 acknowledgement, tenancy end) via `evidence-and-documents`.
   * Confirm the work-day rule versions that applied, with their dates.
4. **Lock.** Set Locked "Yes" on that year's `Days` rows, append a `Changes` row, and append `tax_years[YYYY/YY].locked = {locked_at, locked_via: "year-end review with user", open_items_remaining: [...], confirmed_wording}` in `daylog.json` (append-only; never delete). `validate`, `summary`. A stage line returned: quote its `text` verbatim with L4 (core rules §3); `result_withheld`: name the open items (days not logged, ties not answered) and give the count instead. Then make the final "Travel and day log – YYYY/YY" PDF and CSV with `export-travel-day-log` (Source footer for rows `D-<first year>-04-06`–`D-<second year>-04-05`, `Outputs` row), send them to the user only, and offer a Records pack (`records-pack`).

## After locking
Any change to a locked day, in chat or the Sheet, needs the user's reason in their words (a Sheet edit isn't taken until they give it). Append it to the day's `changes` (`via: user_correction`, `after_lock: true`, old and new values); the next export shows it. Offer a re-export. Never unlock silently: reopen only on the user's explicit request, as a dated note appended to `locked`.

One disclaimer line per message: L4 when a rule or figure is stated, otherwise L3.
