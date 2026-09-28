---
name: hmrc-guidance-watch
description: "Nomad Pro HMRC watch: use when the Nomad Pro HMRC guidance routine runs, when a Nomad Pro user asks whether HMRC's Statutory Residence Test guidance has changed, or before citing an SRT page not checked this week."
---
# HMRC guidance watch

**On by default:** Wednesday 09:00 their time, from the first count, with the engine update check (`engine-setup`). Silent unless HMRC's wording changes. "stop the HMRC watch": run it only on request.

The knowledge base mirrors HMRC's SRT guidance (RFIG20000 chapter plus RDR3 and its note: 143 gov.uk pages; frontmatter `section`, `url`, `hmrc_updated`). The engine baseline `~/nomad-pro-engine/hmrc/` is copied to `~/nomad-pro-data/hmrc/` by `engine-setup`; the watch reads and writes **the user's copy** only.

1. From `~/nomad-pro-data`: `python3 ~/nomad-pro-engine/tools/hmrc_watch.py --kb hmrc/ --report watch/hmrc-YYYY-MM-DD.json` (check mode, writes nothing).
2. Read the report: `unchanged` → nothing; `date_only` → wording identical, update the date quietly; `text_changed` → read the diff and the live page in full; `fetch_error` → retry next run, never assume a change.
3. If anything changed, rerun with `--write`: the mirror updates, the old version goes to `hmrc/history/<page>/<old-date>.md`, `hmrc/CHANGES.md` gets a dated entry. History is never deleted.
4. **Impact:** check whether a text change touches day counting (RFIG20700 range), ties (RFIG20510–20580), automatic tests (RFIG20100–20380), Tables A/B (RFIG20520, RDR3), work (RFIG20740–20800), accommodation/home (RFIG22110–22180), exceptional circumstances (RFIG22220–22230) or split year (RFIG21000+). If a threshold, band or definition changed, note that the engine needs an update and don't quote the old figure until it has one.
5. **Notify** only on a text change, 3 lines at most: the page and new HMRC date ("RFIG20550 (updated 3 Jul 2026)"); a one-line plain summary, quoted where possible; the effect on their counts ("No effect on your counts." is valid). End with L4. Date-only changes stay quiet.
6. **Quiet if nothing changed**, on the first run and on any `fetch_error`; never "no changes this week". Log the run in `watch/`.

Never interpret a change as affecting the user's residence; describe the text and the arithmetic.
