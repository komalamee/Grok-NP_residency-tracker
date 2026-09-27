"""Tests for srt_engine. Run: python3 -m unittest discover -s tools/tests -v (from kit/)."""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import srt_engine as E  # noqa: E402

RULES = E.load_rules(HERE.parent.parent / "schema" / "country-rules.json")


def make_log(ty="2026/27", uk_days=0, ties=None, prior_resident="yes", start_country="TH", extra=None,
             uk_work_days=0, profile_extra=None, fill_to=None):
    """Fictional log: first `uk_days` days of the tax year in the UK, rest in start_country."""
    start, end = E.tax_year_bounds(ty)
    fill_to = fill_to or end
    days = []
    for i, d in enumerate(E.daterange(start, fill_to)):
        c = "GB" if i < uk_days else start_country
        pres = [c]
        if i == uk_days and uk_days > 0:
            pres = ["GB", c]
        row = {"date": d.isoformat(), "tax_year": ty, "midnight_country": c, "countries_present": pres,
               "confidence": "confirmed", "evidence": [{"type": "other", "pointer": "fictional"}],
               "accommodation_id": "acc1" if c == "GB" else None,
               "uk_work": {"over_3h": "yes" if (c == "GB" and i < uk_work_days) else ("no" if c == "GB" else "n/a")}}
        days.append(row)
    for r in extra or []:
        days = [x for x in days if x["date"] != r["date"]] + [r]
    t = ties or {}
    answers = {k: t.get(k, "no") for k in ("family", "accommodation", "work", "ninety_day", "country")}
    prior = [{"tax_year": E.prev_tax_year(ty, n), "uk_resident": prior_resident, "uk_days": 10} for n in (1, 2, 3)]
    profile = {"timezone": "Europe/London", "passports": ["GB"], "prior_years": prior,
               "accommodation_register": [{"id": "acc1", "label": "Fictional flat", "country": "GB", "relationship": "own"}],
               "family": {"partner_uk_resident": "no", "children_under_18_uk": []},
               "tax_years": {ty: {"tie_answers": answers, "only_home_in_uk_answer": "no", "full_time_uk_work_answer": "no",
                                  "accommodation_available_91_days": {"acc1": "yes" if answers["accommodation"] == "yes" else "no"}}}}
    profile.update(profile_extra or {})
    return E.DayLog({"schema_version": "1.0", "profile": profile, "days": days})


def pointers(ref):
    return [l["test"] for l in ref["stage_lines"]]


class TaxYears(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(E.tax_year_of("2025-04-05"), "2024/25")
        self.assertEqual(E.tax_year_of("2025-04-06"), "2025/26")
        self.assertEqual(E.tax_year_of("2026-01-01"), "2025/26")
        self.assertEqual(E.tax_year_bounds("2026/27"), (date(2026, 4, 6), date(2027, 4, 5)))

    def test_leap_year_length(self):
        log = make_log("2027/28", 0)
        s = E.summarise_year(log, "2027/28", date(2028, 4, 5))
        self.assertEqual(s["days_in_year_to_date"], 366)


class Tables(unittest.TestCase):
    def test_table_a_more_than_boundaries(self):
        cases = {15: None, 16: 4, 45: 4, 46: 3, 90: 3, 91: 2, 120: 2, 121: 1, 182: 1}
        for days, need in cases.items():
            self.assertEqual(E.ties_needed("A", days), need, days)

    def test_table_b_more_than_boundaries(self):
        cases = {45: None, 46: 4, 90: 4, 91: 3, 120: 3, 121: 2}
        for days, need in cases.items():
            self.assertEqual(E.ties_needed("B", days), need, days)

    def test_lines(self):
        self.assertEqual(E.line_for_ties("A", 1), 120)
        self.assertEqual(E.line_for_ties("A", 2), 90)
        self.assertEqual(E.line_for_ties("A", 3), 45)
        self.assertEqual(E.line_for_ties("A", 4), 15)
        self.assertIsNone(E.line_for_ties("A", 0))
        self.assertEqual(E.line_for_ties("B", 2), 120)
        self.assertIsNone(E.line_for_ties("B", 1))

    def test_proximity_levels(self):
        self.assertEqual(E.proximity(84), "comfortable room")
        self.assertEqual(E.proximity(20), "getting close")
        self.assertEqual(E.proximity(5), "at the line")
        self.assertEqual(E.proximity(0), "at the line")
        self.assertEqual(E.proximity(-1), "over the line")


class LeaverBoundary(unittest.TestCase):
    """Exactly 120 UK days with 1 tie as a leaver = below the Table A requirement; 121 = over."""

    def test_120_days_one_tie(self):
        log = make_log(uk_days=120, ties={"accommodation": "yes"})
        ref = E.srt_reference(log, "2026/27", date(2027, 4, 5))
        self.assertEqual(ref["summary"]["uk_midnights"], 120)
        self.assertEqual(ref["ties_test"]["table"], "A")
        self.assertEqual(ref["ties"]["recorded_count"], 1)
        self.assertEqual(ref["ties_test"]["ties_needed"], 2)
        self.assertEqual(ref["ties_test"]["room"], 0)
        self.assertEqual(ref["ties_test"]["proximity"], "at the line")
        self.assertIn("sufficient ties test", pointers(ref))
        self.assertIn("0 days of room before the 120-day line for 1 tie", ref["ties_test"]["room_text"])

    def test_121_days_one_tie(self):
        log = make_log(uk_days=121, ties={"accommodation": "yes"})
        ref = E.srt_reference(log, "2026/27", date(2027, 4, 5))
        self.assertEqual(ref["ties_test"]["ties_needed"], 1)
        self.assertEqual(ref["ties_test"]["room"], -1)
        self.assertEqual(ref["ties_test"]["proximity"], "over the line")
        self.assertNotIn("sufficient ties test", pointers(ref))
        self.assertIn("1 days over the 120-day line", ref["ties_test"]["room_text"])

    def test_84_days_room_example(self):
        log = make_log(uk_days=36, ties={"accommodation": "yes"})
        ref = E.srt_reference(log, "2026/27", date(2027, 4, 5))
        self.assertEqual(ref["ties_test"]["room_text"], "84 days of room before the 120-day line for 1 tie")
        self.assertEqual(ref["ties_test"]["proximity"], "comfortable room")

    def test_arriver_table_b(self):
        log = make_log(uk_days=120, ties={"accommodation": "yes", "work": "yes"}, prior_resident="no")
        ref = E.srt_reference(log, "2026/27", date(2027, 4, 5))
        self.assertEqual(ref["ties_test"]["table"], "B")
        self.assertEqual(ref["ties_test"]["line"], 120)
        self.assertIn("sufficient ties test", pointers(ref))
        self.assertFalse(ref["ties"]["ties"]["country"]["applies"])


class AutomaticTests(unittest.TestCase):
    def test_first_automatic_overseas_15_vs_16(self):
        r15 = E.srt_reference(make_log(uk_days=15), "2026/27", date(2027, 4, 5))
        r16 = E.srt_reference(make_log(uk_days=16), "2026/27", date(2027, 4, 5))
        self.assertIn("first automatic overseas test", pointers(r15))
        self.assertNotIn("first automatic overseas test", pointers(r16))

    def test_second_automatic_overseas_45_vs_46(self):
        r45 = E.srt_reference(make_log(uk_days=45, prior_resident="no"), "2026/27", date(2027, 4, 5))
        r46 = E.srt_reference(make_log(uk_days=46, prior_resident="no"), "2026/27", date(2027, 4, 5))
        self.assertIn("second automatic overseas test", pointers(r45))
        self.assertNotIn("second automatic overseas test", pointers(r46))

    def test_183_no_pointer(self):
        ref = E.srt_reference(make_log(uk_days=183), "2026/27", date(2027, 4, 5))
        self.assertEqual(ref["stage_lines"], [])
        self.assertTrue(any("183" in n for n in ref["notes"]) or ref["automatic_uk_open"])

    def test_third_automatic_overseas_uses_user_claim(self):
        log = make_log(uk_days=90, uk_work_days=30)
        log.profile["tax_years"]["2026/27"]["overseas_full_time_work_claimed"] = "yes"
        ref = E.srt_reference(log, "2026/27", date(2027, 4, 5))
        self.assertIn("third automatic overseas test", pointers(ref))
        log2 = make_log(uk_days=91, uk_work_days=30)
        log2.profile["tax_years"]["2026/27"]["overseas_full_time_work_claimed"] = "yes"
        self.assertNotIn("third automatic overseas test", pointers(E.srt_reference(log2, "2026/27", date(2027, 4, 5))))
        log3 = make_log(uk_days=60, uk_work_days=31)
        log3.profile["tax_years"]["2026/27"]["overseas_full_time_work_claimed"] = "yes"
        self.assertNotIn("third automatic overseas test", pointers(E.srt_reference(log3, "2026/27", date(2027, 4, 5))))

    def test_approved_phrasing_and_l4(self):
        ref = E.srt_reference(make_log(uk_days=36, ties={"accommodation": "yes"}), "2026/27", date(2027, 4, 5))
        line = ref["stage_lines"][0]
        self.assertEqual(line["text"], "Your log points to non-resident under the sufficient ties test.")
        self.assertEqual(line["disclaimer"], "Not tax advice \u2014 always check your own position. Source: RFIG20520 (updated 3 Jul 2026).")


class Ties(unittest.TestCase):
    def test_work_tie_39_vs_40(self):
        t39 = E.evaluate_ties(make_log(uk_days=60, uk_work_days=39), "2026/27", date(2027, 4, 5))
        t40 = E.evaluate_ties(make_log(uk_days=60, uk_work_days=40), "2026/27", date(2027, 4, 5))
        self.assertFalse(t39["ties"]["work"]["log_indicates"])
        self.assertTrue(t40["ties"]["work"]["log_indicates"])
        self.assertIn("differ", t40["ties"]["work"]["status"])  # user said no, log shows 40

    def test_ninety_day_more_than_90(self):
        for prev_days, expect in ((90, False), (91, True)):
            log = make_log(uk_days=10)
            log.profile["prior_years"][0]["uk_days"] = prev_days
            t = E.evaluate_ties(log, "2026/27", date(2027, 4, 5))
            self.assertEqual(t["ties"]["ninety_day"]["log_indicates"], expect, prev_days)

    def test_ninety_day_missing_year_is_unknown(self):
        log = make_log(uk_days=10)
        log.profile["prior_years"][1]["uk_days"] = None
        t = E.evaluate_ties(log, "2026/27", date(2027, 4, 5))
        self.assertIsNone(t["ties"]["ninety_day"]["log_indicates"])
        self.assertEqual(t["ties"]["ninety_day"]["missing_years"], ["2024/25"])

    def test_country_tie_equal_goes_to_uk(self):
        # 100 UK midnights, then 100 TH, then 165 JP -> JP top; make TH == UK top instead
        log = make_log(uk_days=150, start_country="TH")
        s = E.summarise_year(log, "2026/27", date(2026, 4, 6) + timedelta(days=299))  # 150 UK, 150 TH
        t = E.evaluate_ties(log, "2026/27", date(2026, 4, 6) + timedelta(days=299), s)
        self.assertEqual(s["countries"]["GB"], 150)
        self.assertEqual(s["countries"]["TH"], 150)
        self.assertTrue(t["ties"]["country"]["log_indicates"])

    def test_accommodation_close_relative_16_nights(self):
        for nights, expect in ((15, False), (16, True)):
            log = make_log(uk_days=nights, ties={"accommodation": "not_answered"})
            log.profile["accommodation_register"][0]["relationship"] = "close_relative"
            log.profile["tax_years"]["2026/27"]["accommodation_available_91_days"] = {"acc1": "yes"}
            t = E.evaluate_ties(log, "2026/27", date(2027, 4, 5))
            self.assertEqual(t["ties"]["accommodation"]["log_indicates"], expect, nights)

    def test_accommodation_one_night_own(self):
        log = make_log(uk_days=1, ties={"accommodation": "not_answered"})
        log.profile["tax_years"]["2026/27"]["accommodation_available_91_days"] = {"acc1": "yes"}
        t = E.evaluate_ties(log, "2026/27", date(2027, 4, 5))
        self.assertTrue(t["ties"]["accommodation"]["log_indicates"])

    def test_family_partner_uk_resident(self):
        log = make_log(uk_days=10)
        log.profile["family"]["partner_uk_resident"] = "yes"
        t = E.evaluate_ties(log, "2026/27", date(2027, 4, 5))
        self.assertTrue(t["ties"]["family"]["log_indicates"])


class MidnightRuleAndGaps(unittest.TestCase):
    def test_day_trip_is_not_a_uk_midnight(self):
        extra = [{"date": "2026-05-01", "midnight_country": "FR", "countries_present": ["GB", "FR"], "confidence": "confirmed",
                  "evidence": [{"pointer": "x"}], "uk_work": {"over_3h": "yes"}}]
        log = make_log(uk_days=0, start_country="FR", extra=extra)
        s = E.summarise_year(log, "2026/27", date(2027, 4, 5))
        self.assertEqual(s["uk_midnights"], 0)
        self.assertEqual(s["uk_work_days_over_3h"], 1)  # work day counts even without a UK midnight
        self.assertIn("2026-05-01", s["qualifying_days_not_midnight"])

    def test_unlogged_days_are_not_guessed(self):
        log = make_log(uk_days=5, fill_to=date(2026, 5, 1))
        s = E.summarise_year(log, "2026/27", date(2026, 5, 10))
        self.assertEqual(s["unlogged"], 9)
        self.assertEqual(s["uk_midnights"], 5)
        self.assertEqual(sum(s["countries"].values()), 26)

    def test_deeming_rule_applied_only_when_supported(self):
        extra = []
        for i in range(40):
            d = date(2026, 6, 1) + timedelta(days=i)
            extra.append({"date": d.isoformat(), "midnight_country": "FR", "countries_present": ["GB", "FR"],
                          "confidence": "confirmed", "evidence": [{"pointer": "x"}]})
        log = make_log(uk_days=50, start_country="FR", extra=extra,
                       ties={"accommodation": "yes", "family": "yes", "work": "yes"})
        ref = E.srt_reference(log, "2026/27", date(2027, 4, 5))
        self.assertEqual(ref["ties_test"]["uk_days_used"], 50 + (41 - 30))  # 40 + the day of first departure
        log2 = make_log(uk_days=50, start_country="FR", extra=extra, ties={"accommodation": "yes"})
        self.assertEqual(E.srt_reference(log2, "2026/27", date(2027, 4, 5))["ties_test"]["uk_days_used"], 50)


def zone_log(spans):
    days = []
    for c, a, b in spans:
        for d in E.daterange(E.parse_date(a), E.parse_date(b)):
            days.append({"date": d.isoformat(), "midnight_country": c, "countries_present": [c], "confidence": "confirmed"})
    return E.DayLog({"schema_version": "1.0", "profile": {}, "days": days})


class Schengen(unittest.TestCase):
    def test_rolling_90_180(self):
        log = zone_log([("FR", "2026-01-01", "2026-03-31"), ("TH", "2026-04-01", "2026-12-31")])  # 90 days
        st = E.rolling_status(log, date(2026, 3, 31))
        self.assertEqual(st["used"], 90)
        self.assertEqual(st["room"], 0)
        self.assertEqual(st["earliest_drop_off"], "2026-06-30")  # 1 Jan + 180
        self.assertEqual(E.rolling_status(log, date(2026, 6, 29))["used"], 90)
        self.assertEqual(E.rolling_status(log, date(2026, 6, 30))["used"], 89)

    def test_exit_day_counts_any_part(self):
        log = zone_log([("IT", "2026-04-03", "2026-04-11"), ("TH", "2026-04-12", "2026-04-27")])
        log.days[date(2026, 4, 12)]["countries_present"] = ["IT", "TH"]
        self.assertEqual(E.rolling_status(log, date(2026, 4, 27))["used"], 10)

    def test_max_stay(self):
        log = zone_log([("ES", "2026-01-01", "2026-02-19"), ("TH", "2026-02-20", "2026-12-31")])  # 50 days
        self.assertEqual(E.max_stay_from(log, date(2026, 3, 1)), 40)

    def test_cyprus_separate_until_accession(self):
        log = zone_log([("CY", "2026-01-01", "2026-01-31")])
        self.assertEqual(E.rolling_status(log, date(2026, 1, 31))["used"], 0)
        self.assertEqual(E.rolling_status(log, date(2026, 1, 31), "CY")["used"], 31)
        saved = dict(E._SCHENGEN)
        try:
            E._SCHENGEN["CY"] = "2026-01-16"
            self.assertEqual(E.rolling_status(log, date(2026, 1, 31))["used"], 16)
        finally:
            E._SCHENGEN.clear(); E._SCHENGEN.update(saved)

    def test_bulgaria_romania_members(self):
        self.assertIn("BG", E.schengen_members_on(date(2025, 1, 1)))
        self.assertNotIn("RO", E.schengen_members_on(date(2024, 12, 31)))


class CountryLimits(unittest.TestCase):
    def test_thailand_30_after_15_sep_2026(self):
        log = zone_log([("TH", "2026-11-03", "2026-11-13")])
        th = [x for x in E.country_limit_status(log, date(2026, 11, 13), RULES) if x["zone"] == "TH"][0]
        self.assertEqual(th["limit"], 30)
        self.assertEqual(th["days_used"], 11)
        self.assertEqual(th["last_day_of_limit"], "2026-12-02")

    def test_thailand_60_for_earlier_entry(self):
        log = zone_log([("TH", "2026-08-20", "2026-09-12")])
        th = [x for x in E.country_limit_status(log, date(2026, 9, 12), RULES) if x["zone"] == "TH"][0]
        self.assertEqual(th["limit"], 60)

    def test_entries_per_calendar_year(self):
        log = zone_log([("TH", "2026-02-01", "2026-02-10"), ("LA", "2026-02-11", "2026-02-12"), ("TH", "2026-02-13", "2026-02-20")])
        self.assertEqual(len(E.entries_in_calendar_year(log, "TH", 2026)), 2)


class Planning(unittest.TestCase):
    def test_plan_adds_uk_midnights(self):
        log = make_log(uk_days=36, ties={"accommodation": "yes"}, fill_to=date(2026, 9, 30))
        res = E.plan(log, [{"country": "GB", "from": "2026-12-18", "to": "2027-01-03"}], date(2026, 9, 30), RULES)
        y = res["years"][0]
        self.assertEqual(y["uk_midnights_with_plan"], 36 + 17)
        self.assertEqual(y["ties_test_with_plan"]["room"], 120 - 53)


class Validation(unittest.TestCase):
    def test_validate_flags(self):
        errs = E.validate({"days": [{"date": "2026-04-05", "tax_year": "2026/27", "midnight_country": "GB", "confidence": "sure"}]})
        self.assertTrue(any("tax_year" in e for e in errs))
        self.assertTrue(any("confidence" in e for e in errs))

    def test_example_is_valid(self):
        import json
        data = json.loads((HERE.parent.parent / "schema" / "example-daylog.json").read_text())
        self.assertEqual(E.validate(data), [])


if __name__ == "__main__":
    unittest.main()
