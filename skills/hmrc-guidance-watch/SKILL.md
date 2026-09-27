---
name: hmrc-guidance-watch
description: Use on the weekly HMRC guidance routine, or when the user asks whether HMRC's Statutory Residence Test guidance has changed, or before citing a page that hasn't been checked this week.
---

# HMRC guidance watch

The knowledge base is a local mirror of HMRC's SRT guidance: the RFIG20000 chapter of the Residence and FIG Regime Manual plus RDR3 and its guidance note (143 gov.uk pages). Each page has frontmatter `section`, `url`, `hmrc_updated`.

The engine ships a baseline copy at `~/nomad-pro-engine/hmrc/`; the `engine-setup` skill copies it into the user data folder as `hmrc/` on first use. The weekly watch reads and writes **that copy** (run from `~/nomad-pro-data`), never the engine's, so engine updates stay clean. The tools fall back to the engine's mirror if `--kb` is not given.

## Weekly run

1. `python3 ~/nomad-pro-engine/tools/hmrc_watch.py --kb hmrc/ --report watch/hmrc-YYYY-MM-DD.json` (check mode, writes nothing to the mirror).
2. Read the report:
   * `unchanged`: nothing to do.
   * `date_only`: HMRC's last-updated date moved but the wording is identical. Update the mirror date (step 3); no user message needed unless a page the user relies on is involved.
   * `text_changed`: read the diff and the live page in full.
   * `fetch_error`: retry once next day; never assume a change.
3. If anything changed, run again with `--write`: the mirror is updated, the old version is kept under `hmrc/history/<page>/<old-date>.md`, and `hmrc/CHANGES.md` gets a dated entry. History is never deleted.
4. **Impact on the user's log.** For each text change, check whether it touches something the engine or the user's record depends on: day counting (RFIG20700 range), ties (RFIG20510–20580), automatic tests (RFIG20100–20380), Tables A/B (RFIG20520, RDR3), work (RFIG20740–20800), accommodation/home (RFIG22110–22180), exceptional circumstances (RFIG22220–22230), split year (RFIG21000+). If a threshold, band or definition changed, flag that `~/nomad-pro-engine/tools/srt_engine.py` needs updating and do not quote the old figure until it is.
5. **Notify** only if text changed (or a date moved on a page the user's last export cites): one message with the page, old and new HMRC dates, a two-line plain summary of what changed, quoted where possible, and the effect on their log as counts ("No effect on your counts" is a valid answer). Cite as "RFIG20550 (updated 3 Jul 2026)". End with L4.
6. **Quiet if nothing changed.** Log the run in the watch folder.

Never interpret a change as affecting the user's residence; describe what the text now says and what it does to the arithmetic.
