# SRT explainer: checked answers

Part of the Nomad Pro engine. The `srt-explainer` skill reads this file from
`~/nomad-pro-engine/reference/srt-checked-answers.md` (engine 0.1.6 or later) when one of these questions comes up.
Never edit the installed copy; updates arrive with the weekly engine update. Citations verified 26–27 Sep 2026.
Re-open the page in `~/nomad-pro-data/hmrc/pages/` before quoting it: if the page's wording has changed since, quote
the page as it is now. The skill's rules come first (quote, never apply to the user, end with L4 or L3).

* **UK GP register:** RFIG21920 (updated 4 Apr 2025) lists "registration at that address with local medical practitioners" among information that helps establish whether someone had a home in the UK or abroad; the only mention in the SRT guidance; weight depends on the full facts (adviser). Offer to note it.
* **Bank account / driving licence address:** same page lists "the address to which the individual's driving license is registered" and "bank accounts and credit cards linked to the individual's address": facts, not a rule.
* **Voting / electoral register:** not mentioned in any of the 143 pages. Say so; L3.
* **What counts as a UK day:** present at midnight (RFIG20710); deeming (RFIG20720) and transit days (RFIG20730) are recorded, applied only if every condition is met.
* **Overnight transit:** not counted on a through journey between two non-UK countries when nothing is done "to a substantial extent unrelated to their passage through the UK"; hotel dinner or breakfast is related (RFIG20730). Record with a transit flag.
* **Parent's flat:** close relative's home: 16+ nights, available for a continuous 91 days (RFIG20550); show the count against 16.
* **Emails in the UK as work:** work has its everyday meaning (RFIG20740); RFIG21930 gives "reviewing and responding to emails, meetings" as work activity to note; work tie = more than 3 hours on at least 40 days (RFIG20560).
* **Partner in the UK:** family tie covers a UK-resident spouse or civil partner (unless separated) or a partner living as if married (RFIG20530, updated 10 Mar 2026). The partner's residence is their own question; record the reply and date.
* **90-day tie:** more than 90 UK days in either of the two previous years (RFIG20570, updated 8 Jan 2026); exactly 90 isn't more than 90.
* **Stuck by a cancelled flight:** exceptional circumstances beyond control may be ignored, up to 60 days a year, "a limit, not an allowance or entitlement" (RFIG22220, RFIG22240; e.g. natural disasters, civil unrest, war, sudden serious illness). Whether a case fits: adviser question; days stay counted with a note.
* **Travelling for a work event:** RFIG20740 counts "travelling time where the cost would have been a deductible expense for tax purposes had the individual incurred and paid for the costs themselves, regardless of whether or not they worked during the travel in question", and travel time they work during. HMRC's example (RFIG20750, updated 7 Apr 2025) treats Heathrow to a London meeting, the meeting and the return as UK work; a private detour to family isn't. Deductibility depends on their facts (adviser). Tagged work travel follows their `work_travel` setting; their own answer wins.
