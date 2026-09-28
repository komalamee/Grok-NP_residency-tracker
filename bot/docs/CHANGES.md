<!-- banned-list:start (working notes: they quote wording the bot itself never uses) -->
# Nomad Pro – UK Residency Tracker: v2 drafts (for review only)

- Drafted 27 Sep 2026 (ICT) by Bot Studio. Koko approved drafting fixes 1–4 from the review, for review only.
- Nothing live was changed:
  - the live agent's files, the shared skills in `/home/box/agent-data/workflows/` and the profile are untouched;
  - nothing was pushed to GitHub, and no one was messaged.
- The engine work was done in a throwaway clone under `/tmp`.
- Positioning follows Koko's steer: lead with nomads and expats with a UK past, "Built for British nomads" as a secondary line, and no nationality gate.

## Folder
| Path | What |
|---|---|
| `CHANGES.md` | This summary |
| `engine/verdict-gate-0.1.2.patch` | `git diff` against the public engine `main` @ 8d710da (v0.1.1) |
| `engine/TEST-RESULTS.txt` | Patch applied to a clean clone: 78 tests OK, banned_scan clean |
| `skills/<name>/SKILL.md` | The 17 skills to ship: 3 rewritten, 14 with tightened descriptions (4 of those also carry verdict wording) |
| `skills/original/` | Copies of the live skills taken 27 Sep 2026, for comparison |
| `skills.diff` | Unified diff, live → draft, for every skill |
| `listing/profile.json` | New name/title/description |
| `listing/LISTING.md` | Marketplace listing draft |
| `PACKAGING.md` | Exact ship/exclude list, with reasons |
| `RETEST.md` | The four simulated first conversations re-run against the drafts |

## 1. Verdict fix
**Engine (v0.1.2 draft).**
- A new `verdict_gate()` in `srt_reference()` returns a stage line only if all of these hold:
  - the tax year has ended;
  - every day is logged;
  - prior-3-year residence is recorded;
  - every applicable tie is answered.
- Otherwise `stage_lines` is empty, `verdict_withheld` lists the reasons, and a new `running_count` gives, for example: "Your log so far: 5 UK midnights from 6 Apr 2026 to 27 Sep 2026 (175 of 175 days logged). The tax year ends on 5 Apr 2027." It also gives room against the figures that apply (16 and/or 46, the ties-test line, 183).
- The dashboard and PDF show that line instead of a stage line.
- New `tools/tests/test_verdict_gate.py` has 7 cases, among them: empty log mid-year, mid-year fully logged, finished year with gaps, unanswered tie, prior years unrecorded, a complete year that still returns its line, and the CLI `summary` on an empty log.
- The existing 71 tests are unchanged and still pass.

**Skills.**
- `nomad-pro-core-rules` §2 "Counts before verdicts":
  - "Default: the running count."
  - "The result sentence, only when all four hold: the tax year has ended (after 5 April), every day in it is logged, residence for the previous 3 tax years is recorded, and every applicable tie is answered."
  - "Never … build it yourself from counts."
  - When withheld: "A result line needs a finished year with every day logged and every tie answered; 2026/27 runs to 5 Apr 2027."
- Matching wording in `srt-explainer`, `dashboard`, `export-travel-day-log` and `year-end-lockdown`. Year-end is the one normal place a result line can appear; if items are still open, it names them and gives the count.
- Core rules shrank from 11.3 KB to 8.3 KB. The disclaimers stay word for word; the banned-words list and the rules on the record are condensed. §9 adds "do the named job first" and a one-line way to handle off-scope requests.

## 2. Fast first result
- `nomad-pro-getting-started` message 1: "Hello, I'm Nomad Pro. I keep a day-by-day log of where you sleep and any UK work, and count it against HMRC's published Statutory Residence Test figures and visa stay limits. I keep records and do arithmetic; I don't give tax or immigration advice. To start: where have you slept since 6 April? A rough list is fine…"
- Message 2 is three count lines (UK midnights with the year-end date; days not logged plus Schengen; the HMRC day figures), then one question: "were you UK resident in any of the last 3 tax years?"
- The remaining setup is a trigger table. For example: ties "when UK midnights go above 15"; work-day rule "the first time a UK day is logged"; calendar/Gmail "after the third check-in or a catch-up of more than 7 days" (optional, read-only); backups "once there are 30+ days logged".
- If the first message names a job, it does that job first.
- Routines: it offers only the evening check-in at first, and adds others when they become relevant.
- `onboarding` is rewritten as reference chunks A–I: what to ask and where it's saved, with no fixed order (9.5 → 6.1 KB). The data fields are unchanged, so existing users' logs stay compatible.
- The British-only gate is removed. Chunk C asks "which passport(s) they travel on", adding "for other passports say so and point them to their own government's travel advice" and "Any nationality is fine; never stop because someone isn't British." Core rules: "The SRT does not depend on nationality: help anyone, whatever passport they hold."

## 3. Listing
- **profile.json**
  - name: unchanged, "Nomad Pro – UK Residency Tracker".
  - title: "UK residency day log".
  - description: "Track your UK residency days, for nomads and expats who've lived in the UK. Logs where you sleep and any UK work, day by day, and counts it against HMRC's published Statutory Residence Test figures and the Schengen and stay limits on GOV.UK. Built for British nomads. Records and arithmetic, not tax advice. Not affiliated with HMRC."
- **LISTING.md** has: pitch "Track your UK residency days, for nomads and expats who've lived in the UK." with *Built for British nomads.* beneath it; what it does; who it's for ("any nationality"); optional connections (Calendar, Gmail, Drive); four example first messages; the not-advice and not-affiliated lines. It has no price, no "global visa" and no concierge-first framing.

## 4. Packaging
- Ship exactly 17 skills, with `gettingStarted` = `nomad-pro-getting-started`.
- Exclude the SEO desk's `getting-started` and `extra-recurring-checks` (generic triggers that would compete on a new user's first message), its other 5 skills, and both crypto skills. Pack no memories and no routines (or pack routines paused).
- Every description now reads "Nomad Pro <job>: use when a Nomad Pro user …". Details are in PACKAGING.md.

## Retest (RETEST.md)
- (a) 'hi': now gets the first count in the bot's 2nd message, with no form; this used to fail.
- (b) "am I non-resident?": no verdict; the engine gate was verified by tests. Partial: "March" isn't explicitly mapped to a tax year.
- (c) quick 3-month log: now meets the ask.
- (d) off-scope: passes, and is now graceful.

## Open questions for Koko
1. **Merging the engine patch updates every live install.** Installs self-update weekly from `main`, so merging it switches off the mid-year and empty-log verdicts for users already on the live bot, even before the skills change (the old core rules only say the sentence when the engine returns it). Do you want that fast path? It needs a push by you; I pushed nothing.
2. The repo's own `skills/` and `SYSTEM.md` still carry the old wording. Sync them to v2 or delete them from the repo? (They were not included in the patch.)
3. **How strict should the gate be?** It requires every tie answered even for the automatic overseas tests, where ties don't matter under RDR3. That's stricter than the law, but it's what you asked for. It does not yet require UK work days marked `unsure` to be resolved; that matters for the work tie and the third test. Should it?
4. Add a line to getting-started so "I left in March" gets clarified ("March 2026 falls in the 2025/26 tax year")?
5. Keep `destination-concierge` in the template (2.6 KB, on request only), or cut it for size and focus?
6. Rename generic slugs (`onboarding` → `nomad-pro-onboarding`, `dashboard` → …)? Not drafted, because every cross-reference would change.
7. Pack no routines (drafted), or pack them paused?
8. The live profile name uses a hyphen ("Nomad Pro - UK…") and the draft uses an en dash. Pick one before republishing.

---
## Round 2 (27 Sep 2026, after Koko's feedback: shorter and more visual)
The engine PR #3 is merged (`main` @ b6d51be, v0.1.2). Its `running_count` and `verdict_withheld` names match the drafts, and the merged version adds `counted` per figure, which the bars use. This round is still drafts only; nothing live was touched. The previous round's files are kept in `prev-round/`.

1. **Short, visual replies.** Core rules §1 is new, "Replies: short and visual": "Default: 1–3 short lines. No explanation paragraphs unless the user asks." Counts lead with a code-block bar such as `UK nights  ▓▓▓░░░░░░░  5 / 16`, built from `running_count.figures`, followed by at most 2 short lines, or the dashboard image for a whole year. L5 (`Source: … · not tax advice`) is now the default chat disclaimer; L4 is kept for rule explanations and result sentences. The verdict gate (§3) is unchanged in substance.
   - The first reply is now 2 lines (see RETEST.md).
   - Bar-first reply shapes were added to daily-checkin, trip-planning and travel-rules-watch. The explainer answers in 2–4 lines, and the dashboard is sent with an overview screenshot.
   - Unused disclaimers dropped: L1 and L7 (the template never emails).
2. **Listing** cut from 528 to 194 words of copy: one pitch line, 4 bullets, one line each for who and connect, 3 examples, one disclaimer line. The name now uses a hyphen, "Nomad Pro - UK Residency Tracker". Three visual ideas are listed separately.
3. **profile.json** description cut from 57 to 26 words: "Track your UK residency days, for nomads and expats who've lived in the UK. Built for British nomads. Records, not tax advice; not affiliated with HMRC."
4. **March line.** getting-started, onboarding chunk A and core rules §4 now say "March 2026 falls in the 2025/26 tax year."

Word counts:
- LISTING.md copy: 528 → 194.
- Core rules: 1785 (live) → 1353 (round 1) → 1186 (round 2).
- getting-started: 740 → 542.

---
## Round 3 (28 Sep 2026)
See `CHANGES-2026-09-28.md`. Koko approved three routines on by default (check-in, HMRC watch, travel-rules watch); this supersedes "pack no routines" above and open question 7.
