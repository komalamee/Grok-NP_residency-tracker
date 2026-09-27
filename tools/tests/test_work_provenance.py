"""UK work comes from the user's answer or from the work-day rule they agreed; never from calendar presence alone."""
import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import srt_engine as E  # noqa: E402

RULE = {
    "id": "v1", "version": 1, "effective_from": "2026-01-01", "effective_to": None,
    "job_periods": [{"from": "2026-01-01", "to": "2026-03-13"}],
    "no_job_periods": [{"from": "2026-03-14", "to": None}],
    "weekdays": "work", "weekends": "no_work", "public_holidays": "no_work", "public_holiday_region": "england-and-wales",
    "travel_days": "ask",
    "exceptions": [{"keyword": "sick", "means": "no_work"}, {"keyword": "less than 3 hours", "aliases": ["<3h"], "means": "under_3h"}],
    "over_3h_basis": "A weekday in the UK counts as more than 3 hours unless marked less than 3 hours.",
    "agreed_at": "2026-01-01", "agreed_via": "agreed with user in chat",
    "wording_shown": "Weekends are non-work days; weekdays in the UK are work days unless my calendar says sick or less than 3 hours.",
    "user_answers_take_priority": True,
}


def _day(d, country="GB", work=None, present=None):
    return {"date": d, "tax_year": E.tax_year_of(d), "midnight_country": country, "countries_present": present or [country],
            "uk_work": work, "evidence": [{"type": "calendar", "pointer": "Calendar event 'London'"}],
            "confidence": "confirmed", "changes": []}


def _log(days, rules=(RULE,)):
    return {"profile": {"work_day_rules": [copy.deepcopy(r) for r in rules]}, "days": days}


class RuleOutcome(unittest.TestCase):
    def test_defaults_and_exceptions(self):
        data = _log([])
        cases = {
            ("2026-02-02", "GB", ()): ("yes", None),          # Monday, employed
            ("2026-02-07", "GB", ()): ("no", None),           # Saturday
            ("2026-01-01", "GB", ()): ("no", None),           # New Year's Day
            ("2026-04-07", "GB", ()): ("no", None),           # no job
            ("2026-02-03", "TH", ()): ("n/a", None),          # abroad
            ("2026-02-03", "GB", ("Sick day",)): ("no", "sick"),
            ("2026-02-04", "GB", ("<3h admin",)): ("no", "less than 3 hours"),
        }
        for (d, c, titles), (want, kw) in cases.items():
            w = E.apply_work_rule(data, _day(d, c), list(titles))
            self.assertEqual(w["over_3h"], want, d)
            if want in ("yes", "no"):
                self.assertEqual(w["source"], "rule:v1")
            self.assertEqual((w.get("exception") or {}).get("keyword"), kw, d)
        travel = E.apply_work_rule(data, _day("2026-02-05", "FR", present=["GB", "FR"]))
        self.assertEqual((travel["over_3h"], travel["source"]), ("unsure", "not_asked"))
        arrival = E.apply_work_rule(data, _day("2026-02-05", "GB", present=["FR", "GB"]))
        self.assertEqual(arrival["over_3h"], "unsure")   # flying in is a travel day too
        nw = _log([], rules=(dict(RULE, travel_days="no_work"),))
        for present, mc in ((["GB", "FR"], "FR"), (["FR", "GB"], "GB")):
            w = E.apply_work_rule(nw, _day("2026-02-05", mc, present=present))
            self.assertEqual((w["over_3h"], w["source"]), ("no", "rule:v1"))

    def test_no_rule_leaves_uk_day_unsure(self):
        w = E.apply_work_rule(_log([], rules=()), _day("2026-02-02"), ["Client meeting London"])
        self.assertEqual((w["over_3h"], w["source"]), ("unsure", "not_asked"))
        self.assertEqual(E.uk_work_unanswered("TH")["over_3h"], "n/a")


class WorkTravel(unittest.TestCase):
    def _data(self, **kw):
        return _log([], rules=(dict(RULE, travel_days="no_work", **kw),))

    def test_default_is_ask(self):
        w = E.apply_work_rule(self._data(), _day("2026-02-05", "GB", present=["FR", "GB"]), ["Flight CDG-LHR", "Client meeting London"])
        self.assertEqual((w["over_3h"], w["source"]), ("unsure", "not_asked"))
        plain = E.apply_work_rule(self._data(), _day("2026-02-05", "GB", present=["FR", "GB"]), ["Flight CDG-LHR"])
        self.assertEqual(plain["over_3h"], "no")    # plain travel day follows travel_days

    def test_settings(self):
        row = _day("2026-02-05", "GB", present=["FR", "GB"])
        w = E.apply_work_rule(self._data(work_travel="work"), row, ["Conference day 1"])
        self.assertEqual((w["over_3h"], w["source"], w["work_travel"]["keyword"]), ("yes", "rule:v1", "conference"))
        w = E.apply_work_rule(self._data(work_travel="travel_day"), row, ["Work trip to London"])
        self.assertEqual(w["over_3h"], "no")
        w = E.apply_work_rule(self._data(work_travel="work", work_travel_keywords=["onsite"]), row, ["Onsite with client"])
        self.assertEqual(w["over_3h"], "yes")
        # not a travel day: work-travel keywords change nothing
        w = E.apply_work_rule(self._data(work_travel="work"), _day("2026-02-07", "GB"), ["Conference"])
        self.assertEqual(w["over_3h"], "no")

    def test_user_tag_and_validate(self):
        data = self._data(work_travel="work")
        row = _day("2026-02-05", "GB", present=["FR", "GB"],
                   work={"over_3h": "yes", "hours": None, "note": "", "source": "rule:v1", "work_travel": {"by": "user_answer"}})
        data["days"] = [row]
        self.assertEqual(E.validate(data), [])
        row["uk_work"].pop("work_travel")
        self.assertTrue(E.validate(data))           # untagged travel day: rule gives 'no'
        self.assertTrue(any("work_travel" in e for e in E.validate(self._data(work_travel="sometimes"))))

    def test_explainer_quotes_hmrc_verbatim(self):
        t = (KIT / "skills/srt-explainer/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("travelling time to the extent than an individual works during their journey, regardless of the rules on deductibility", t)
        self.assertIn("regardless of whether or not they worked during the travel in question", t)
        self.assertIn("RFIG20740 (updated 4 Apr 2025)", t)
        self.assertIn("RFIG20750 (updated 7 Apr 2025)", t)
        self.assertIn("Maalav", t)
        ob = (KIT / "skills/onboarding/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("**travelling for work**", ob)
        self.assertIn("work_travel", json.dumps(json.loads((KIT / "schema/daylog.schema.json").read_text(encoding="utf-8"))))


class Validate(unittest.TestCase):
    def test_rule_sourced_work_is_allowed(self):
        days = [_day("2026-02-02", work={"over_3h": "yes", "hours": None, "note": "", "source": "rule:v1"}),
                _day("2026-02-03", work={"over_3h": "no", "hours": None, "note": "", "source": "rule:v1",
                                         "exception": {"keyword": "sick", "event": "Sick day"}}),
                _day("2026-02-04", work=E.uk_work_from_answer("no", note="user: took the day off")),
                _day("2026-02-05", work={"over_3h": "yes", "hours": None, "note": "Calendar-confirmed UK presence, no exclusion event"})]
        self.assertEqual(E.validate(_log(days)), [])

    def test_errors_without_answer_or_rule(self):
        days = [_day("2025-11-03", work={"over_3h": "yes", "hours": None, "note": "Calendar-confirmed UK presence, no exclusion event"}),
                _day("2025-11-04", work={"over_3h": "yes", "hours": None, "note": "", "source": "not_asked"}),
                _day("2025-11-05", work={"over_3h": "yes", "hours": None, "note": "", "source": "rule:v1"}),   # before the rule starts
                _day("2026-02-02", work={"over_3h": "no", "hours": None, "note": "", "source": "rule:v1"}),   # rule gives yes
                _day("2026-02-03", work={"over_3h": "no", "hours": None, "note": "", "source": "rule:v1",
                                         "exception": {"keyword": "dentist", "event": "Dentist"}}),           # not a rule keyword
                _day("2026-02-06", work={"over_3h": "yes", "hours": None, "note": "", "source": "calendar"}),
                _day("2025-11-06", work=E.uk_work_from_answer("yes", note="user said 6 hours")),
                _day("2025-11-07", work=E.uk_work_unanswered("GB"))]
        flagged = {e.split(":")[0] for e in E.validate(_log(days))}
        self.assertEqual(flagged, {"2025-11-03", "2025-11-04", "2025-11-05", "2026-02-02", "2026-02-03", "2026-02-06"})
        self.assertEqual(E.work_inferred_dates(_log(days)), ["2025-11-03", "2025-11-04", "2025-11-05", "2026-02-02", "2026-02-03", "2026-02-06"])

    def test_rule_versions(self):
        v2 = dict(RULE, id="v2", version=2, effective_from="2026-03-01", agreed_at="2026-03-01", weekends="ask")
        errs = E.validate(_log([], rules=(RULE, v2)))
        self.assertTrue(any("overlap" in e for e in errs), errs)
        v1 = dict(RULE, effective_to="2026-02-28")
        self.assertEqual(E.validate(_log([], rules=(v1, v2))), [])
        self.assertEqual(E.rule_for(_log([], rules=(v1, v2)), "2026-03-07")["id"], "v2")
        retro = dict(RULE, effective_from="2025-01-01", agreed_at="2026-01-01")
        self.assertTrue(any("before it was agreed" in e for e in E.validate(_log([], rules=(retro,)))))
        retro["applies_to_earlier_days_agreed"] = True
        self.assertEqual(E.validate(_log([], rules=(retro,))), [])
        for k in ("wording_shown", "weekends", "public_holidays", "travel_days", "exceptions", "user_answers_take_priority"):
            bad = dict(RULE)
            del bad[k]
            self.assertTrue(any(k in e for e in E.validate(_log([], rules=(bad,)))), k)   # never assumed: must be asked


class Report(unittest.TestCase):
    def test_counts_and_disagreements(self):
        days = [_day("2026-02-02", work={"over_3h": "yes", "hours": None, "note": "", "source": "rule:v1"}),
                _day("2026-02-03", work={"over_3h": "no", "hours": None, "note": "", "source": "rule:v1",
                                         "exception": {"keyword": "sick", "event": "Sick"}}),
                _day("2026-02-04", work=E.uk_work_from_answer("no")),
                _day("2026-02-05", work={"over_3h": "no", "hours": None, "note": "Calendar `Dentist`"}),
                _day("2026-02-06", "TH", work={"over_3h": "n/a", "hours": None, "note": ""})]
        rep = E.work_rule_report(_log(days), "2025/26")
        self.assertEqual(rep["counts"], {"rule": 1, "rule_exception": 1, "user_answer": 1, "unrecorded": 1})
        self.assertEqual([x["date"] for x in rep["disagree"]], ["2026-02-05"])
        self.assertEqual([x["date"] for x in rep["answered_differently"]], ["2026-02-04"])
        log = E.DayLog(_log(days))
        qs = E.open_questions(log, "2025/26", date(2026, 2, 28))
        self.assertTrue(any("differ from your work-day rule" in q for q in qs), qs)


class KitText(unittest.TestCase):
    def test_example_open_question_without_rule(self):
        base = json.loads((KIT / "example" / "daylog.json").read_text(encoding="utf-8"))
        data = copy.deepcopy(base)
        data.get("profile", {}).pop("work_day_rules", None)
        r = next(x for x in data["days"] if x.get("midnight_country") == "GB")
        r["uk_work"] = {"over_3h": "yes", "hours": None, "note": "Calendar-confirmed — no exclusion event"}
        qs = E.open_questions(E.DayLog(data), E.tax_year_of(r["date"]), date.fromisoformat(r["date"]))
        self.assertTrue(any("no agreed work-day rule" in q for q in qs), qs)

    def test_answer_helper_rejects_non_answers(self):
        with self.assertRaises(ValueError):
            E.uk_work_from_answer("n/a")
        with self.assertRaises(ValueError):
            E.uk_work_from_answer("yes", hours=2)

    def test_schema(self):
        s = json.loads((KIT / "schema" / "daylog.schema.json").read_text(encoding="utf-8"))
        wdr = s["properties"]["profile"]["properties"]["work_day_rules"]
        for k in ("effective_from", "effective_to", "weekdays", "weekends", "public_holidays", "exceptions", "no_job_periods",
                  "over_3h_basis", "agreed_at", "agreed_via", "wording_shown"):
            self.assertIn(k, wdr["items"]["properties"], k)
        self.assertIn("rule:", json.dumps(s))

    def test_skills_describe_the_rule(self):
        for p in ["SYSTEM.md", "README.md", "skills/onboarding/SKILL.md", "skills/daily-checkin-and-catchup/SKILL.md",
                  "skills/evidence-and-documents/SKILL.md", "skills/export-travel-day-log/SKILL.md"]:
            t = (KIT / p).read_text(encoding="utf-8").lower()
            self.assertIn("work-day rule", t, p)
        ob = (KIT / "skills/onboarding/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("wording_shown", ob)
        self.assertIn("agreed with user in chat", ob)
        for k in ("never assume a default", "**weekends**", "**UK bank holidays**", "**travel days**", "**calendar exception keywords**"):
            self.assertIn(k, ob)
        for p in ["SYSTEM.md", "skills/onboarding/SKILL.md", "skills/daily-checkin-and-catchup/SKILL.md"]:
            self.assertIn("always takes priority over the rule", (KIT / p).read_text(encoding="utf-8"), p)
        self.assertIn("always take priority over this rule", (KIT / "tools/render_pdf.py").read_text(encoding="utf-8").lower())

    def test_example_data_validates(self):
        for p in ["example/daylog.json", "schema/example-daylog.json"]:
            f = KIT / p
            if f.exists():
                self.assertEqual(E.work_inferred_dates(json.loads(f.read_text(encoding="utf-8"))), [], p)


if __name__ == "__main__":
    unittest.main()
