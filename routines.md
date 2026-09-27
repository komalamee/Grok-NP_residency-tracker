# Routines to create in each user's copy

Create these routines at the end of onboarding (routine 4 only if Google Calendar is connected), in the user's timezone. Each prompt is written as an intent: it tells the bot what outcome to reach, and the matching skill says how.

## 1. Check-in (at the user's chosen rhythm)

* **Schedule:** daily at the time the user chose (default 21:00 local). Weekly option: the chosen weekday and time. "When I move" option: daily at the chosen time but only sends a message when a calendar event, email or the user's last message suggests travel, plus a weekly sweep on the chosen weekday.
* **Prompt (intent):**
  > Run my Nomad Pro check-in using the daily-checkin-and-catchup skill. First make sure every day since my last entry is logged: if any are missing, ask me to fill them all in one go (suggest from my calendar or email if connected, never guess). Then ask me the four check-in questions for today in one short message: where I was, whether I worked, whether UK work was more than 3 hours, and where the record sits. Record my answers, rerun the counts, and tell me only what changed. If today is on or after 6 April and last tax year has no Travel and day log yet, make it with the export-travel-day-log skill and send it to me. If I've missed three check-ins in a row, offer to switch rhythm.

## 2. Weekly travel-rules watch

* **Schedule:** weekly, Monday 09:00 local (or the user's chosen day).
* **Prompt (intent):**
  > Using the travel-rules-watch skill, re-check the entry rules for every country I'm in or have a trip planned to, from GOV.UK foreign travel advice (and the destination government or European Commission where a rule changed recently), including Cyprus's Schengen status and Thailand's visa-exemption length. Update my country-rules table with sources and today's date, keeping previous versions. Then model all my upcoming trips against the rules and my log. Message me only if a rule changed or a planned trip would break or come close to a limit, with the source link, the date checked and the counts. Otherwise stay quiet. End any message with the L8 line.

## 3. Weekly HMRC guidance watch

* **Schedule:** weekly, Wednesday 09:00 local.
* **Prompt (intent):**
  > First, using the engine-setup skill, check whether a newer Nomad Pro engine is published (compare VERSION); if so, update it with install.sh, and tell me only if the update or its test run did not complete cleanly. Then, using the hmrc-guidance-watch skill, compare every page in my HMRC knowledge base with live gov.uk. If wording changed, update my mirror, keep the old version in history, log the change, and tell me in one message which pages changed (with HMRC's old and new dates), what the text now says in plain words, and what, if anything, it does to the counts in my log. If only HMRC's dates moved, update them quietly. If nothing changed, stay quiet. End any message with the L4 line citing the changed page.

## 4. End-of-week calendar review (only if Google Calendar is connected)

* **Schedule:** weekly, Sunday 18:00 local (or the user's chosen day and time). Skip a week if every day of it is already logged and has a link or pointer, and say nothing.
* **Prompt (intent):**
  > Using the end-of-week calendar review in the daily-checkin-and-catchup skill, read my calendar (and Gmail, if connected) for the week just ended and any unlogged days before it. Send me one message: "Here's what I think your week was. Is this right?" with one line per night (date, country and place, and what it's based on), and show the UK work each UK day gets under my agreed work-day rule, asking me only about exceptions (with no rule, ask about UK work over 3 hours; unanswered UK days stay unsure). Go back and forth with me until every line is confirmed or corrected. Record confirmed days, log every correction to an existing day in its change log with my words as the reason, record the review in weekly_reviews, and attach the calendar or email links I approve as evidence. Leave anything I can't place as not logged; never guess.

## Notes

* Routines never send email, post or share anything; they message the user in chat only.
* When the user changes rhythm, update routine 1 rather than creating another. If they disconnect the calendar, pause routine 4.
* If a routine's tool run fails (network, gov.uk down), say so in the next message and retry next run; never estimate.
