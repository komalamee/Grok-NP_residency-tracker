---
name: leaving-uk-checklist
description: Use when the user is leaving the UK (or has just left) and asks what they need to sort out, for example "give me the leaving-the-UK checklist", "what do I tell HMRC, my GP, the council?". Also use the arriving variant when they are coming back to live in the UK.
---

# Leaving (or returning to) the UK checklist

Templates: `~/nomad-pro-engine/templates/leaving-uk-checklist.md` and `~/nomad-pro-engine/templates/arriving-uk-checklist.md`. Each row is an official GOV.UK (or NHS) page, a one-line summary of what that page says, the link, GOV.UK's own updated date and the date checked.

## Steps

1. **Re-verify before sending.** Open every link (GOV.UK content API: `https://www.gov.uk/api/content/<path>`). Update the "GOV.UK updated" and "Checked" dates. If a page has moved, follow the redirect and use the new link; if a page has gone or its content has changed in a way that alters the summary, rewrite the summary from the live page and flag it ("Changed since the template was written: …"). Never send a summary you haven't just checked.
2. **Ask two scoping questions**, no more: leaving or returning, and roughly when (a date or month). Optional: "Anything you already know doesn't apply (no car, no student loan, no UK property)?" Drop those rows.
3. **Send the list** grouped as: HMRC and tax · National Insurance and State Pension · Health · Home and council · Money (banking, ISAs, student loan, pensions) · Voting, licence and vehicles · Passport and country guides. One line per item plus the link. Say at the top: "These are the official pages to look at. Which apply to you depends on your circumstances; I can't advise on them."
4. **Save a copy** to the user's data folder as `checklists/leaving-uk.md` (or `arriving-uk.md`) with a status per item: to look at / done (date) / not relevant. Update statuses when the user mentions progress ("P85 sent today" → done, 26 Sep 2026).
5. **File what results** in the documents index (`evidence-and-documents` skill): P85 acknowledgement, GP deregistration confirmation, council tax closing bill, tenancy end, sale completion.
6. **Add record-keeping items to the log**: departure date and first night abroad (midnight rule, RFIG20710), last UK work day, when UK accommodation stopped being available (RFIG20550). For returners: arrival date, first UK midnight, UK accommodation from that date.

## Items that changed recently (flag them clearly)

* Voluntary National Insurance while abroad: from 6 April 2026, voluntary Class 2 can't be paid for time abroad, and Class 3 for time abroad after 5 April 2026 needs 10 years' previous UK residence or qualifying contributions (transitional rules for those who applied by 5 April 2026). Source: GOV.UK Voluntary National Insurance, "If you live or work abroad" (checked 26 Sep 2026). Summarise; never say whether the user should pay.

## Never

* Tell the user which items they must do, whether they should pay voluntary contributions, keep an account, deregister, or sell or let a property.
* Complete or submit any form for them. Offer the link; the user acts.

Close with L6 when sending the full list; L4 if an SRT page is cited.
