---
name: dashboard
description: "Nomad Pro dashboard: use when a Nomad Pro user asks for their dashboard, charts or a picture of their UK days and stay limits for a tax year, and after each Nomad Pro export."
---
# Dashboard

Engine `~/nomad-pro-engine` (run `engine-setup` first if missing). From `~/nomad-pro-data`:
`python3 ~/nomad-pro-engine/tools/render_dashboard.py daylog.json dashboard.html --as-of <today> --kb hmrc/pages --data-root .`
Rebuild `daylog.json` from the Sheet first (`export-travel-day-log`). It makes one self-contained, offline HTML file. Add the Source line ("Source: Nomad Pro – Travel log, rows <first>–<last>, generated <date>") before `</body>`, under the L6 footer, and an `Outputs` row (type "Dashboard"). Send it to the user only, with a screenshot of the overview as the inline image and a one-line caption.

What the engine renders (counts only, no residence outcome): tax-year selector, "Recorded to {date}"; overview cards (UK midnights, UK work days >3 hours + unsure, days logged / not logged, top countries, Schengen last 180, upcoming trips); the reference-figures strip ("Educational, not tax advice. It records days; it doesn't decide your residence."); ties-test band with room and proximity; the running count for a year in progress, or the stage line with L4 only where the engine returns one (core rules §3); log health and questions HMRC could ask; UK visits; ties inputs vs the log; work days against 31 and 40 with the Work-day rule card; Schengen and stay-limit charts with L8; Day log with a clickable **Evidence** column; Records tab; L6 footer on every view.

The dashboard is not a substitute for the "Travel and day log" PDF (`export-travel-day-log`).

<!-- banned-list:start -->
Style: neutral palette (slate, stone, navy); no green/red good/bad; amber only for logging gaps and counts approaching a figure. No surface states a residence status or uses outcome words (core rules §7). The only result wording is the engine's own stage line ("Your log matches the …").
<!-- banned-list:end -->
