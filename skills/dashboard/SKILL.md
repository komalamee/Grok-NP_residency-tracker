---
name: dashboard
description: Use when the user asks for the dashboard, an overview, a picture of their year, charts, or "where do I stand" in counts; also after onboarding and after each export.
---

# Dashboard

`python3 ~/nomad-pro-engine/tools/render_dashboard.py daylog.json dashboard.html --as-of <today> --kb hmrc/pages` produces a single self-contained HTML file (no external scripts). Send it to the user; optionally send a screenshot.

## What it shows (verdict-free)

* Global: tax-year selector, "Recorded to {date}", generated time in the user's timezone.
* **Overview:** cards for UK midnights, UK work days (>3 hours) + unsure, days logged / not yet logged, top 3 countries by midnights, Schengen days in the 180 days to today, upcoming trips. A **reference figures strip** ("HMRC's RDR3 uses these day counts: 16, 46, 91, 121, 183. Your UK midnights so far: X.") with the distance to each, captioned "A count from your entries. It does not determine residence." Ties-test reference (Table A/B band, room text and proximity chip), approved stage lines with L4 where the engine returns them, a needs-attention list, midnights by country, midnights per month (not-logged days shown in amber outline), timeline.
* **Log health:** not logged, no record pointer, inferred, owner statements, conflicts, edits after the day, questions HMRC could ask.
* **UK days:** visits table (first/last UK night, midnights, UK work days, accommodation, pointers) and nights per UK accommodation.
* **Ties inputs:** your answer · what your log shows · last reviewed · HMRC page · status (Recorded yes / Recorded no / Not answered / Your answer and your log differ – review).
* **Work days:** log with hours (only if given) and notes; counters shown against 31 and 40 as figures HMRC uses; a short **Work-day rule** card quoting the rule the user agreed (version, dates, agreed date, parts still to confirm), how many UK days were set by the rule, by calendar exceptions and by their answers, and any days that differ from the rule.
* **Schengen & stay limits:** rolling-window chart against 90 with planned trips, earliest drop-off date, longest stay from tomorrow, a card per country rule with source and date checked, planned-trip projections. L8.
* **Upcoming trips & rule watch**, **Records** (sources and pointer index), **Export**.
* Footer on every view: L6.

## Evidence and documents

* **Day log** tab: one row per date with an **Evidence** column: clickable links to emails (Gmail) and to stored files in `evidence/`, otherwise the pointer text. Use `--data-root <user data folder>` so file links resolve from where the HTML is saved.
* **Records** tab: record sources, pointer index and the status documents index (`documents/index.json`) with file/link/pointer and status.

## Dashboard vs PDF

The dashboard is the interactive, tabbed HTML (self-contained: CSS, JS, fonts and charts inline, works offline). The "Travel and day log" PDF is a single flowing document with no tabs or buttons. Don't send the dashboard as a substitute for the PDF export.

## Style rules

Neutral palette (slate, stone, navy). No green/red good/bad colours. Amber only for logging gaps and counts approaching a figure. <!-- banned-list:start -->
No word on any surface says resident, non-resident (outside the approved stage sentence), safe, pass, fail, proof, compliant or anything similar.
<!-- banned-list:end -->
Run `~/nomad-pro-engine/tools/banned_scan.py` on template changes.
