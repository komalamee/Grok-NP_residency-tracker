---
name: export-travel-day-log
description: Use when the user asks for their records, a PDF, a CSV, an export, something to give an accountant or adviser, or automatically after 5 April for the tax year just ended.
---

# Export: "Travel and day log"

One export per tax year, named **"Travel and day log – YYYY/YY"** (files: `Travel and day log YYYY-YY.pdf` and `.csv`; a year in progress adds "(to D Mon YYYY)").

## Make it

1. Run a catch-up first if the year has unlogged days, and ask once whether they'd like to fill them before exporting. Gaps stay visible either way.
2. `python3 ~/nomad-pro-engine/tools/render_pdf.py daylog.json --tax-year YYYY/YY --out-dir exports/ --data-root . --as-of <today> --kb hmrc/pages` (links to `evidence/` files are written relative to the PDF, so they work while the PDF stays in `exports/` next to the data folder; for a portable bundle use the `records-pack` skill). Run it from the user data folder and leave `--rules` off, so the stay-limit figures come from the user's own `country-rules.json` (`$NOMAD_PRO_DATA/country-rules.json`, else `~/nomad-pro-data/country-rules.json`) rather than the engine's shipped table.
3. Check the PDF opened (page count > 1) and hand both files to the user in chat. Never email or share it unless the user asks for that specific send.

The PDF is a single flowing document: cover, numbered sections, page numbers, L6 in every footer. It has no tabs, buttons or interactive elements (those belong to the dashboard).

## What's inside (in this order)

Page 1 (key metrics: UK days, Schengen, UK work days, logging; days by country and by month; contents; L6) → 1 Location timeline → 2 Schengen, rolling 180 days (with quick read) → 3 Ties and reference figures (RDR3 figures, ties-test reference with room and proximity, approved stage lines with L4 where the engine returns them) → 4 Summary counts → 5 Stays → 6 UK days → 7 UK work days (>3 hours; unsure listed) → 8 **Work-day rule** (the rule(s) in force for the year quoted word for word as the user confirmed them, date and way agreed, job and no-job periods, weekday / weekend / public-holiday / travel-day handling, calendar exception keywords and their meaning, how 'more than 3 hours' is decided, anything still to confirm, how many UK days were set by the rule vs rule exceptions vs the user's answer, and every day where the log and the rule differ) → 9 Ties as recorded with HMRC page references and the other recorded answers → 10 Day-by-day log with an **Evidence** column (clickable link to the email or to the stored file in `evidence/`, otherwise the pointer text) → 11 Gaps, questions HMRC could ask, conflicts and resolutions, change log → 12 Counting method (midnight rule; deeming rule, transit, exceptional circumstances and split year recorded but not calculated unless the data supports them) → L6 on every page. Check layout with `~/nomad-pro-engine/tools/pdf_layout_check.py` before sending.

The CSV is the day rows flattened (one row per date).

## Automatic year-end export

The check-in routine checks on or after 6 April: if no export exists for the year just ended, run the catch-up for any gaps up to 5 April, then produce the export and tell the user in one message with the headline counts. Offer an updated export whenever late corrections come in.

## Wording

<!-- banned-list:start -->
Describe the export as "your travel and day log for YYYY/YY: the days, places and work you recorded and where the records sit". Never call it a residency or residence summary, an evidence pack, or anything that claims an outcome.
<!-- banned-list:end -->


For several years in one bundle with evidence files, status documents and an index, use the `records-pack` skill.
