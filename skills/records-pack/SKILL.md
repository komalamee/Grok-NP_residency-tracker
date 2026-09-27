---
name: records-pack
description: Use when the user asks for everything in one bundle for one or more tax years, for example "HMRC is enquiring, build a pack for 2024/25 and 2025/26", "my accountant wants all my records", or "zip up my records". Produces a Records pack zip.
---

# Records pack

One request, one zip. The pack collects the user's own records; it does not determine residence and is never described as anything more than that.

## Name it neutrally

<!-- banned-list:start -->
Call it a **Records pack** ("Records pack 2024-25 and 2025-26 (prepared 14 May 2026).zip"). Never "audit-ready", "audit pack", "evidence pack", "HMRC-proof", "compliant" or anything that implies an outcome. If the user says "audit pack", build the Records pack and use that name in the reply.
<!-- banned-list:end -->

## Steps

1. Confirm the tax years (6 April to 5 April) and whether any year is still in progress (it's included "to date").
2. Run `~/nomad-pro-engine/tools/srt_engine.py validate daylog.json`. If there are unlogged days, conflicts or `unsure` UK work days in those years, list them in one message and offer to resolve them first ("7 days in 2024/25 aren't logged. Fill them now, or build the pack with them listed as gaps?"). Never fill a gap to tidy the pack.
3. Check the documents index for those years. If a status document the user mentioned is only `requested` or `pointer_only`, say so once ("The contract for 2025/26 is recorded as a pointer only. Add the file first?").
4. Build: `python3 ~/nomad-pro-engine/tools/records_pack.py daylog.json --tax-years 2024/25 2025/26 --out-dir exports/ --data-root . --kb hmrc/pages --as-of <today>`.
The cover index also carries a **Work-day rule** section: the rule(s) in force quoted as the user confirmed them, with the date agreed, and per year how many UK days were set by the rule, by calendar exceptions and by the user's answer, and how many differ from the rule (full detail in section 8 of each Travel and day log).

5. Send the zip to the user only. Summarise in four lines: file name, years, per-year UK midnights and UK work days, days with a link or file vs pointer only vs none, documents included, and open items. End with L4 citing RFIG20710 and RFIG20560, and L6 if you describe the contents at length.

## What the zip contains

| Path | Content |
|---|---|
| `00 Index.pdf` | Cover index: contents, counts per year, evidence coverage, status documents, open items, L6 |
| `01 Travel and day logs/` | "Travel and day log YYYY-YY" PDF + CSV per year (same as the `export-travel-day-log` skill) |
| `02 Evidence index/` | Evidence index PDF + CSV: every date, where the user was, confidence, and each evidence item (link, file or pointer) |
| `03 Status documents/` | Documents index PDF + CSV |
| `evidence/`, `documents/` | Copies of the files referenced by those years, verbatim |
| `manifest.json` | SHA-256 of every file |

Links inside the PDFs to `evidence/` and `documents/` are relative, so they work once the zip is extracted. Email links open in the user's own Gmail.

## Never

* Send the pack to anyone but the user, even if asked to "send it to HMRC" or to an adviser, unless the user explicitly asks for that specific send, naming the recipient. Then confirm the recipient and message first.
* Add commentary about what HMRC will think of it.
