<!-- banned-list:start (working notes: they quote wording the bot itself never uses) -->
# Skill packaging for the Nomad Pro template (draft v2)

The skills folder `/home/box/agent-data/workflows/` is shared by every agent on Koko's box. A template export must pick skills by name, so this is the exact list.

## Ship (17 skills). Set `gettingStarted` = `nomad-pro-getting-started`
| # | Skill | Role | Draft change |
|---|---|---|---|
| 1 | nomad-pro-core-rules | Standing rules, disclaimers, verdict gate | Rewritten (11.3 → 8.3 KB); 28 Sep (later): six routines, raw-file rule, Drive edit access |
| 2 | nomad-pro-getting-started | First conversation | Rewritten: hello + one question → 3-line count → chunks; 28 Sep (later): sets up the six v1 routines, travel log line |
| 3 | onboarding | Setup chunks (what to ask, where it's saved) | Rewritten (9.5 → 6.1 KB), British-only gate removed; 28 Sep (later): backup on by default, Drive edit-access line |
| 4 | engine-setup | Install and update the engine | Description tightened |
| 5 | daily-checkin-and-catchup | Check-in (on by default), catch-up, Sunday line, heads-ups, calendar review | Rewritten 28 Sep: one-tap check-in, weekly line, heads-ups; later: calendar review set-up line, Sheet read/refresh |
| 6 | trip-planning | "What if" trips against the counts | 28 Sep: before/after bar reply, save prompt |
| 7 | travel-rules-watch | GOV.UK entry rules, Schengen, document expiry | 28 Sep: on by default (Mon 09:00), silent unless changed |
| 8 | srt-explainer | Plain-English SRT from the HMRC mirror | Description + verdict wording |
| 9 | evidence-and-documents | Records and status documents | Description tightened; 28 Sep (later): Record column edits from the Sheet |
| 10 | dashboard | HTML dashboard | Description + verdict wording |
| 11 | export-travel-day-log | PDF/CSV per tax year; travel log Sheet (mirror, two-way edits) | Description + verdict wording; 28 Sep (later): travel log Sheet procedure |
| 12 | records-pack | Multi-year zip | Description tightened |
| 13 | records-backup | Monthly backup and restore | Description tightened; 28 Sep (later): on by default again (1st 09:00) |
| 14 | year-end-lockdown | 7 April close-out (the one normal place a result line can appear) | Description + verdict step; 28 Sep (later): on by default again (7 April 10:00) |
| 15 | hmrc-guidance-watch | Weekly HMRC mirror check | 28 Sep: on by default (Wed 09:00), silent unless wording changes |
| 16 | leaving-uk-checklist | Official leaving/returning pages | Description tightened |
| 17 | destination-concierge | "Where next?" on request only | Description tightened (could be cut for size; see open questions) |

Total prose: 82,632 bytes for the 17 SKILL.md files (71,559 before the 28 Sep v1-routines and travel-log-Sheet pass; 68 KB in v1).

## Exclude, and why
| Skill | Owner | Why exclude |
|---|---|---|
| getting-started | SEO & AEO Desk | Opens with "you find what people search and what they ask AI assistants…". Its trigger ("first conversation after setup, or whenever memory has no user prefs") would fire on a new Nomad Pro user and compete with `nomad-pro-getting-started`. |
| extra-recurring-checks | SEO & AEO Desk | "Three routines ship with you: the weekly ideas digest, the Monday search report…". Wrong product. Its trigger ("asks what else you can watch on a schedule") collides with Nomad Pro routine questions. |
| answer-engine-question-map, keyword-and-question-research, page-audit-and-refresh-plan, weekly-search-report, writer-content-brief | SEO & AEO Desk | Unrelated product. |
| crypto-contract-safety-gate, early-legs-crypto-research | Crypto desks | Unrelated, and crypto has no place near a residency-records product. |

## Also leave out
- **Memories:** all of Koko's own. The shared memory holds Mac paths and business facts. (The template packs 8 general Nomad Pro job and convention facts from the v1 template instead; see TEMPLATE-PACKAGE.md.)
- **Routines (updated again 28 Sep 2026, Koko: back to the v1 set):** six, set up after the first count in the new owner's timezone, never duplicated: (1) check-in daily at their chosen time, 21:00 by default; (2) travel-rules watch Monday 09:00; (3) HMRC guidance watch with the engine update check Wednesday 09:00; (4) calendar review only if the calendar is connected, Sunday 18:00 weekly by default (fortnightly, monthly or quarterly options); (5) year-end lockdown 7 April 10:00; (6) monthly records backup on the 1st at 09:00. 1–3, 5 and 6 are on by default; 4 only while the calendar is connected. If the template format can carry routines, pack all six with no Koko timezone (the calendar review stays off until the calendar is connected); `nomad-pro-getting-started` sets the timezone and switches them on after the first count (before that, packed routines run silently). If it can't, getting-started creates them at that point. Schedules and job text: TEMPLATE-PACKAGE.md.
- **Connectors (updated 28 Sep 2026, v1 parity):** four are packed and offered on day one, each can be declined: Gmail (45893410, read-only), Google Calendar (45893411, read-only), Google Drive (45893413) and Google Sheets (45893414, edit access). Sheets: the travel log Sheet "Nomad Pro – Travel log" is the single source of all the owner's data (tabs Summary, Days, Records, Trips, Profile, Changes, Outputs), created once and edited in place; `daylog.json` is rebuilt from it before every count; every output names its source rows. Without Sheets, the same tabs as CSVs on the box. Google Drive: backups, records and the "Nomad Pro" folder, plus the Sheet fallback when Sheets isn't connected. Google Calendar and Gmail: read-only, to propose days (calendar review, check-in, catch-up) and attach booking records.
- **Teammate directory / other agents:** not part of a template. Test in a clean agent with no other skills visible.

## Collision risk and tightened descriptions
The old descriptions started "use this when…" with generic triggers ("when the user says where they were", "something for an accountant", "a backup or copy of all their records", "mentions a trip or destination", "where do I stand"). On a box with several bots, those can pull other bots into Nomad Pro skills, or pull Nomad Pro into theirs. Every draft description now starts with "Nomad Pro <job>:" and scopes the trigger to "a Nomad Pro user" or a Nomad Pro routine. For example:
- `export-travel-day-log`: "Nomad Pro export: use when a Nomad Pro user asks for their Travel and day log (PDF or CSV) for a tax year, e.g. for their accountant, and at the 7 April year-end lockdown."
- `records-backup`: "Nomad Pro backup: use when the Nomad Pro monthly backup routine runs, or a Nomad Pro user asks to back up or restore their day log and records."
- `daily-checkin-and-catchup`: "Nomad Pro check-in: use when the Nomad Pro check-in routine runs, when a Nomad Pro user tells you where they slept or worked, catches up missed days (\"check my week\"), or changes the check-in or calendar-review rhythm."

All 17 are in `skills/<name>/SKILL.md`; `skills.diff` shows every change against the live copies.

Optional, not drafted: renaming generic slugs (`onboarding`, `dashboard`) to `nomad-pro-onboarding`, `nomad-pro-dashboard`. That needs every cross-reference updated, so it waits for Koko's call.
