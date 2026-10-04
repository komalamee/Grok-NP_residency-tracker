---
name: dashboard
description: Use only when the user asks for the dashboard, an overview, a picture of their year or charts of their UK and Schengen days. Never on a schedule, after onboarding or after an export.
---

# Dashboard

Build it only when the user asks. Rebuild `daylog.json` from the latest log first, then from the user data folder:

`python3 ~/nomad-pro-engine/tools/render_dashboard.py daylog.json dashboard.html --as-of <today> --data-root . --source "Source: Nomad Pro – Travel log, rows <first>–<last>, generated <date>"`

It writes one self-contained HTML file (CSS, scripts and charts inline; works offline). `--design classic` still renders the earlier layout; `--no-link-check` skips opening document links (they are then shown untested).

## The design (engine 0.1.5)

The tabbed SRT Residency dashboard, used as it is: **Overview**, **UK Days**, **Schengen**, **Full Timeline**, **Work Days**, **SRT Status**, **Documentation**, and a tax-year switch. Don't restyle it or add panels.

## Rules

1. Same tabs and design every time.
2. Rebuild from the latest day log only when the user asks. No daily rebuild or routine.
3. Neutral record labels. No surface states a residence outcome; the per-test marks and the pathway show only for a finished tax year. While the selected year is unfinished they are hidden and the figures show with "Year not finished; figures so far".
4. Counts only. HMRC's day bands (16, 46, 91, 121, 183) are shown as reference; ties are a plain count; work days are a count with HMRC's figures as reference. No UK day limit, room or days left is worked out from the ties band, on the page or in chat.
5. **Your own limit** is blank until the user sets it on the page. It is saved in their browser and goes into `profile.user_limit` when they import their notes.
6. **Documentation** links only to documents that open (each http(s) link is tested at build time). Anything else is plain text saying where it lives. No dead links.
7. Notes are 2–4 index bullets per row: stay city, which records exist, flights. No text blobs, purchase detail, addresses or internal IDs.
8. Each row has a **Your note** box saved in the browser. **Export my notes** downloads a JSON file; `render_dashboard.py daylog.json --import-notes <file>` merges it into the day log (the newer edit wins; a backup is written first).
9. A place the user marks private shows as "<city> (family home)": set `private: true`, `city` and optionally `private_label` on its `accommodation_register` entry, or add `profile.private_places: [{"match": "...", "city": "...", "label": "..."}]`. Other places show at city level only.

## Sharing

The dashboard goes to the user only. If they want an image to post on X, crop it to the neutral parts (counts and charts, no SRT or HMRC wording), or tell them the image carries that wording.

## Dashboard vs PDF

The "Travel and day log" PDF (`render_pdf.py`) is unchanged and is the document to send; the dashboard is not a substitute for it.
