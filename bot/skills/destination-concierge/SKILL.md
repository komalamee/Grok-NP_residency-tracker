---
name: destination-concierge
description: "Nomad Pro destination concierge: use only when a Nomad Pro user asks an open \"where should I go next?\" or \"where could I spend the winter?\" question; never during setup."
---
# "Where should I go next?" concierge

Offered when the user asks or a plan is still open ("not sure where yet"); never in onboarding, never pushed unprompted more than once a month. Engine `~/nomad-pro-engine` (`engine-setup` if missing).

1. **Preferences** (first time; later confirm or update), two short messages, "don't care" allowed. Save to `profile/destination-preferences.json` (schema `~/nomad-pro-engine/schema/destination-preferences.schema.json`) with history on change: monthly budget (rent included?), rent ceiling and type; weights 0–3 for cost of living, food cost, public transport, taxi cost, English widely spoken, LGBTQIA+ safety, crime safety; languages, climate, time-zone band, internet, stay length, must-haves, places to avoid; whether to include community threads (always labelled anecdotal).
2. **Hard filters from the log first:** `plan --trip CC:FIRST_NIGHT:LAST_NIGHT` per candidate (`trip-planning`); rules via `travel-rules-watch` if missing or older than 7 days. Check UK nights against their band (room, proximity, RFIG20520) and next year's 90-day tie (RFIG20570); Schengen days across the stay, latest end date within 90, earliest drop-off; Cyprus on its own 90/180 until accession takes effect; GOV.UK stay limits and entry rules. A candidate that doesn't fit is shown as "doesn't fit these dates" with the count and any range that would fit, never silently dropped.
3. **Research live; source and date for every figure:** GOV.UK foreign travel advice (entry, "Safety and security", local laws); Numbeo or similar (labelled crowd-sourced) and local listings; transit operators; EF English Proficiency Index; ILGA World or Equaldex; Reddit quoted briefly and marked **anecdotal**. No source, no figure.
4. **Answer:** one table (Place | Fits your dates? | Stay limit / entry | Schengen after stay | UK line | Rent 1-bed centre | Taxi 5 km | English | LGBTQIA+ (GOV.UK) | Crime (GOV.UK)), ranked by their weights (shown), then two lines per place, counts first ("Lisbon 1 Feb–31 Mar would take your Schengen count to 88 of 90 on 31 Mar (at the line); earliest drop-off 14 Apr."). Never say where to go or that a place suits their tax position; offer to model one (`trip-planning`) or add it to `planned_trips`.
End with one disclaimer line: L8, or `Source: [HMRC ref] · not tax or immigration advice` if a UK figure is stated.
