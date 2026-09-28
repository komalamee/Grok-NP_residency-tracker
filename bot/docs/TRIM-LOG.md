<!-- banned-list:start (working notes: they quote wording the bot itself never uses) -->
# Trim log: Nomad Pro v2 args, 2026-09-28

Why: staging rejected the 103,056-byte args ("too large, host limit exceeded"). 98.0 KB had staged fine. Target: 92,000 bytes or less.
Result: **91,348 bytes** (the `build.py` measure, which gave the 103,056 figure; saved 11,708). Compact JSON: 91,129. File on disk (indent=1): 91,900.
Only wording was trimmed. Skill descriptions (they drive triggering), the 8 memories, profile and gettingStarted are unchanged.
Backups: `backups/2026-09-28-v2-pre-trim/` (drafts) and `backups/2026-09-28-v2-pre-trim-live/` (live workflows).

## Per skill (bytes of SKILL.md)
| Skill | Before | After | Saved | What was cut |
|---|---|---|---|---|
| export-travel-day-log | 16,050 | 12,606 | 3,444 | Tabs: column lists and label mappings compressed; Drive-only fallback reduced to connector steps; PDF contents now point to `dashboard`; year-end, write and outputs paragraphs de-duplicated |
| daily-checkin-and-catchup | 10,761 | 9,148 | 1,613 | Rhythm moved under check-in; disclaimer now points to core rules §6; calendar-review and rhythm-change wording tightened; work-day rule text shortened (full rule stays in `onboarding` E) |
| onboarding | 8,956 | 7,725 | 1,231 | Intro, A–I and "How to use it" condensed; F's Calendar/Gmail quote now points to getting-started message 2 (Sheets edit-access line kept) |
| nomad-pro-getting-started | 7,256 | 6,234 | 1,022 | Connections note, travel-log line, trigger and routines tables condensed; duplicate "all six on" paragraph merged into the routines intro; message-2 offer text unchanged |
| nomad-pro-core-rules | 9,783 | 9,163 | 620 | §1 routines line, §8 Sheet paragraph and §9 condensed; one lead-in in §3 shortened; §2 wording, the §3 quoted line, §6 disclaimers and §7 banned list unchanged |
| trip-planning | 4,878 | 4,307 | 571 | Command paths shortened; "UK visit spotted" line tightened |
| year-end-lockdown | 3,542 | 3,057 | 485 | Stage-line wording now points to core rules §3 |
| srt-explainer | 5,953 | 5,600 | 353 | Checked answers and the "not mentioned" step tightened |
| records-backup | 2,880 | 2,575 | 305 | Delivery and Drive wording tightened |
| evidence-and-documents | 3,852 | 3,582 | 270 | Records tab points to `export-travel-day-log`; save and bank-export line tightened |
| engine-setup | 3,401 | 3,134 | 267 | Steps tightened |
| dashboard | 2,320 | 2,058 | 262 | "What it shows" list shortened; stage line points to core rules §3 |
| hmrc-guidance-watch | 2,546 | 2,320 | 226 | Steps tightened |
| travel-rules-watch | 3,949 | 3,727 | 222 | Steps tightened |
| records-pack | 2,761 | 2,636 | 125 | Minor wording |
| destination-concierge | 2,674 | 2,594 | 80 | Step 2 points to `trip-planning` for the plan command |
| leaving-uk-checklist | 2,529 | 2,493 | 36 | Steps 1–2 tightened |
| **Total** | **94,091** | **82,959** | **11,132** | |

Other args sections: routines 4,444 → 4,088 (job texts tightened; all 6 kept, schedules unchanged); plugin descriptions 709 → 586 (all 4 kept); memory 1,920 → 1,920 (unchanged, 8 items).

## Behaviour-preservation check (every item verified present after the trim)
| Behaviour / rule | Where it lives now |
|---|---|
| Sheet "Nomad Pro – Travel log" is the single source; `daylog.json` rebuilt from it before runs | export-travel-day-log (Travel log Sheet; Read the Sheet steps 1–7); core rules §8 |
| Write to the Sheet first, then rebuild and `summary`; a failed write is kept and retried | export-travel-day-log "Write to the Sheet"; core rules §8; check-in |
| Invalid rows flagged, never guessed | export-travel-day-log (plain labels, read steps); core rules §8; evidence-and-documents |
| Profile edits read back before use; the old value stays until confirmed | export-travel-day-log step 6 |
| Locked year: their reason first, `after_lock` append | export-travel-day-log step 7; year-end-lockdown; core rules §8 |
| Deleted cell or row is never a deletion; conflicts kept both ways, then ask | export-travel-day-log step 7 |
| `Outputs` row plus "Source: Nomad Pro – Travel log, rows …" footer on every output | export-travel-day-log "Outputs trace to rows"; core rules §8; dashboard, records-pack, records-backup, year-end-lockdown |
| Chat counts traceable to Row IDs | export-travel-day-log |
| Sheets edit-access line | onboarding F ("I need edit access…") |
| Read-only or failed create: reconnect message | getting-started travel-log line; onboarding F |
| CSV fallback and exactly one Sheets reminder | getting-started travel-log line ("the one Sheets reminder"); getting-started chunk table |
| Drive-only fallback (xlsx, refresh at most daily, older versions moved, never deleted) | export-travel-day-log "Drive-only fallback" |
| Never a second Sheet; never share it | export-travel-day-log (Google Sheets bullet) |
| Message-2 Calendar/Gmail/Sheets/Drive offer, once, declinable | getting-started message 2 (text unchanged) + note; onboarding F |
| Calendar review only while the calendar is connected; rhythms and cron | getting-started routines table; daily-checkin (calendar review, rhythm change); onboarding F; routine 4 |
| Six routines, schedules, one of each ever | getting-started "Routines"; args routines (6) |
| Restored v1 routine steps: check-in suggests days from calendar/email; calendar review reads Gmail; year-end offers 2–3 calendar slots | args routines 1, 4, 5 (phrases verified present) |
| Quiet watches (never "no changes") | core rules §1; travel-rules-watch; hmrc-guidance-watch |
| One-tap check-in, skip, stop or change time, no night runs | daily-checkin-and-catchup (Quiet-friendly) |
| Catch-up ("Missed 3 days…"); **never guess a gap**; proposal = question | daily-checkin-and-catchup |
| Heads-up bands (getting close / at the line / over), once per figure, band and year | daily-checkin-and-catchup; core rules §4 |
| Work-day rule: theirs, never a default; read back; re-tag only with OK | onboarding E; daily-checkin (work-day rule) |
| Result gate (`result_withheld`, stage line L4 only from engine) | core rules §3 (unchanged apart from one lead-in); dashboard; year-end-lockdown; export PDF line |
| Figures only from the engine; never estimate | core rules §4; engine-setup; trip-planning |
| Red line: records, never advice | core rules §2 (unchanged) |
| Disclaimers L1–L8 verbatim | core rules §6 (byte-identical to pre-trim) |
| Banned words | core rules §7 (byte-identical to pre-trim) |
| Cover note never sent by the bot | export-travel-day-log "For my accountant"; core rules §9 |
| Leaving-UK: re-verify links; no must-do advice; no forms submitted | leaving-uk-checklist |
| 8 memories (v1-parity) | args memory (unchanged, 8) |
| 4 plugins, string `pluginId`s (45893410 Gmail, 45893411 Calendar, 45893413 Drive, 45893414 Sheets) | args plugins (descriptions shortened, each still says read-only, private or edit access) |
| gettingStarted = nomad-pro-getting-started, among the 17 skills | args |

## Checks
* `banned_scan.py` on the 17 skills plus listing: 0 banned hits, 0 private-data hits. Same on the args JSON: 0 and 0. Two hits that trimming introduced ("tests failed", "pass 90") were reworded back to the pre-trim wording.
* Live copy: live SKILL.md files backed up to `backups/2026-09-28-v2-pre-trim-live/` (17), then the 17 drafts copied to `/home/box/agent-data/workflows/<name>/SKILL.md` (not `original`). cmp: 17/17 identical.
