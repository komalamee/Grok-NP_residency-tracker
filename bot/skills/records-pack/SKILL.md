---
name: records-pack
description: "Nomad Pro Records pack: use when a Nomad Pro user wants all their day logs, evidence and status documents for one or more UK tax years in one zip, e.g. for an HMRC enquiry or their accountant."
---
# Records pack

One request, one zip of the user's own records; it records days, it doesn't decide anyone's residence. Engine `~/nomad-pro-engine` (`engine-setup` if missing).

<!-- banned-list:start -->
Call it a **Records pack** ("Records pack 2024-25 and 2025-26 (prepared 14 May 2026).zip"). Never "audit-ready", "audit pack", "evidence pack", "HMRC-proof", "compliant" or anything implying an outcome. If the user says "audit pack", build the Records pack and use that name.
<!-- banned-list:end -->

1. Confirm the tax years (6 April–5 April); a year in progress is included "to date".
2. Rebuild `daylog.json` from the travel log Sheet (`export-travel-day-log`), then `srt_engine.py validate daylog.json`. List unlogged days, conflicts and `unsure` UK work days in those years in one message and offer to resolve them first, or build with them listed as gaps. Never fill a gap to tidy the pack.
3. Check `documents/index.json` for those years; say once if a mentioned document is only `requested` or `pointer_only`.
4. Build: `python3 ~/nomad-pro-engine/tools/records_pack.py daylog.json --tax-years 2024/25 2025/26 --out-dir exports/ --data-root . --kb hmrc/pages --as-of <today>`.
5. Trace it to the Sheet: `Source.txt` in the zip ("Source: Nomad Pro – Travel log, rows <first>–<last>, generated <date>", plus the `Records` IDs) and an `Outputs` row (type "Records pack"). The pack PDFs can't take the footer yet (mention only if asked); `Source.txt` and the dates (Row ID = `D-` + date) trace every page. Send the zip to the user only. Summarise in four lines: file name and years; per-year UK midnights and UK work days; days with link or file vs pointer only vs none, and documents included; open items. End with one disclaimer line: L4 citing RFIG20710 and RFIG20560 (or L6 instead if describing contents at length).

Contents: `00 Index.pdf` (cover index with counts, evidence coverage, documents, open items, Work-day rule section, L6) · `01 Travel and day logs/` (PDF + CSV per year) · `02 Evidence index/` · `03 Status documents/` · `evidence/`, `documents/` (verbatim copies) · `manifest.json` (SHA-256 of every file). Links are relative, so they work once extracted.

Never send the pack to anyone but the user unless they explicitly ask for that specific send, naming the recipient; then confirm recipient and message first. Never comment on what HMRC will think of it.
