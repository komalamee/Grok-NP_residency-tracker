---
name: dashboard
description: "Nomad Pro dashboard: use only when a Nomad Pro user asks for their dashboard, charts or a picture of their UK and Schengen days for a tax year."
---
# Dashboard

Build it only when the user asks: never on a schedule or after an export. Engine `~/nomad-pro-engine` (`engine-setup` if missing). Rebuild `daylog.json` from the Sheet (`export-travel-day-log`), then from `~/nomad-pro-data`:
`python3 ~/nomad-pro-engine/tools/render_dashboard.py daylog.json dashboard.html --as-of <today> --data-root . --source "Source: Nomad Pro – Travel log, rows <first>–<last>, generated <date>"`
One offline HTML file: Overview, UK Days, Schengen, Full Timeline, Work Days, SRT Status, Documentation, tax-year switch. Don't restyle or add to it. Add an `Outputs` row (type "Dashboard"); send it to the user only, with an Overview screenshot and a one-line caption.

* Counts only. HMRC day bands (16/46/91/121/183) and work-day figures are reference; ties are a plain count. Never give a UK day limit, room or days left from the ties band, on the page or in chat.
* "Your own limit" stays blank unless the user sets it on the page.
* Notes are 2–4 index bullets per row (stay city, which records exist, flights); no addresses, IDs or purchases. The user's "Your note" boxes save in their browser. When they send their "Export my notes" file, run `render_dashboard.py daylog.json --import-notes <file>` (it also saves their own limit).
* A place the user marks private (`private: true` and `city` on its `accommodation_register` entry, or `profile.private_places`) shows as "<city> (family home)".
* Documentation links only to documents that open; anything else is plain text saying where it lives.
* Image for X: crop to the counts and charts, without the SRT and HMRC wording, or warn the user it carries that wording.

Not a substitute for the "Travel and day log" PDF.

<!-- banned-list:start -->
No surface states a residence status or uses outcome words (core rules §7); stage labels stay as the engine prints them.
<!-- banned-list:end -->
