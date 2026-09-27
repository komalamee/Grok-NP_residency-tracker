"""The result gate: no stage line unless the tax year has ended, every day in it is logged,
residence for the previous 3 tax years is recorded and every applicable tie is answered.
Until then the engine returns what is missing plus a running count, and the dashboard and the
PDF export show that running count where the stage line would go."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import srt_engine as E  # noqa: E402
import dashboard_charts as C  # noqa: E402
import render_dashboard as RD  # noqa: E402
import render_pdf as RP  # noqa: E402
from test_engine import make_log  # noqa: E402

TY = "2026/27"
MID_YEAR = date(2026, 9, 27)
YEAR_END = date(2027, 4, 5)
RULES = str(KIT / "schema" / "country-rules.json")
MATCHES = "Your log matches the"


def figure(rc, n):
    return [f for f in rc["figures"] if f["figure"] == n][0]


class ResultGate(unittest.TestCase):
    def test_empty_log_mid_year_returns_no_result(self):
        log = make_log(TY, fill_to=date(2026, 4, 5))  # no days in 2026/27 at all
        ref = E.srt_reference(log, TY, MID_YEAR)
        self.assertEqual(ref["summary"]["logged"], 0)
        self.assertEqual(ref["stage_lines"], [])
        self.assertTrue(any("still running" in r for r in ref["result_withheld"]))
        self.assertTrue(any("175 days are not logged" in r for r in ref["result_withheld"]))
        rc = ref["running_count"]
        self.assertEqual(rc["uk_midnights"], 0)
        self.assertEqual(rc["year_ends"], "2027-04-05")
        self.assertEqual(rc["text"], "Your log so far: 0 UK midnights from 6 Apr 2026 to 27 Sep 2026 "
                                     "(0 of 175 days logged). The tax year ends on 5 Apr 2027.")
        self.assertNotIn(MATCHES, rc["text"])

    def test_mid_year_fully_logged_to_date_returns_no_result(self):
        log = make_log(TY, uk_days=5, fill_to=MID_YEAR)
        ref = E.srt_reference(log, TY, MID_YEAR)
        self.assertEqual(ref["summary"]["unlogged"], 0)
        self.assertEqual(ref["stage_lines"], [])
        self.assertEqual(ref["result_withheld"], ["the tax year is still running (it ends on 5 Apr 2027)"])
        rc = ref["running_count"]
        self.assertEqual(rc["uk_midnights"], 5)
        self.assertEqual(rc["text"], "Your log so far: 5 UK midnights from 6 Apr 2026 to 27 Sep 2026 "
                                     "(175 of 175 days logged). The tax year ends on 5 Apr 2027.")
        self.assertEqual(figure(rc, 16)["room"], 10)

    def test_finished_year_with_unlogged_days_returns_no_result(self):
        log = make_log(TY, uk_days=5, fill_to=date(2027, 3, 1))
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["stage_lines"], [])
        self.assertEqual(ref["result_withheld"], ["35 days are not logged"])
        self.assertIn("The tax year ended on 5 Apr 2027", ref["running_count"]["text"])

    def test_one_unlogged_day_is_reported_in_the_singular(self):
        log = make_log(TY, uk_days=5, fill_to=date(2027, 4, 4))
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["result_withheld"], ["1 day is not logged"])
        self.assertEqual(ref["stage_lines"], [])

    def test_finished_year_with_unanswered_tie_returns_no_result(self):
        log = make_log(TY, uk_days=5, ties={"family": "not_answered"})
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["stage_lines"], [])
        self.assertIn("ties not answered: family", ref["result_withheld"])

    def test_unanswered_ties_are_named_as_the_product_names_them(self):
        log = make_log(TY, uk_days=5, ties={"ninety_day": "not_answered", "country": "unsure"})
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertIn("ties not answered: 90-day, country", ref["result_withheld"])

    def test_finished_year_without_prior_years_returns_no_result(self):
        log = make_log(TY, uk_days=5, prior_resident="unsure")
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["stage_lines"], [])
        self.assertIn("residence for the previous 3 tax years is not recorded", ref["result_withheld"])
        # Neither table is known, so both automatic-overseas day figures are listed as conditional.
        rc = ref["running_count"]
        self.assertEqual([f["figure"] for f in rc["figures"]], [16, 46, 183])
        self.assertIn("applies if you were UK resident", figure(rc, 16)["text"])

    def test_finished_complete_answered_year_still_returns_its_line(self):
        log = make_log(TY, uk_days=5)
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["result_withheld"], [])
        self.assertIsNone(ref["running_count"])
        self.assertIn("first automatic overseas test", [l["test"] for l in ref["stage_lines"]])


class RunningCount(unittest.TestCase):
    def test_figures_are_the_ones_that_apply(self):
        log = make_log(TY, uk_days=5, ties={"accommodation": "yes"}, fill_to=MID_YEAR)
        rc = E.srt_reference(log, TY, MID_YEAR)["running_count"]
        self.assertEqual([f["figure"] for f in rc["figures"]], [16, 121, 183])  # Table A, so no 46
        self.assertEqual(figure(rc, 121)["room"], 115)  # 120-day line for 1 recorded tie
        self.assertEqual(figure(rc, 183)["room"], 177)
        self.assertEqual(figure(rc, 16)["room_text"], "10 UK days of room before 16: first automatic overseas test")
        self.assertEqual(figure(rc, 16)["cite"], E.cite("RFIG20120"))

    def test_arriver_figures_use_table_b(self):
        log = make_log(TY, uk_days=5, prior_resident="no", fill_to=MID_YEAR)
        rc = E.srt_reference(log, TY, MID_YEAR)["running_count"]
        self.assertEqual([f["figure"] for f in rc["figures"]], [46, 183])
        self.assertEqual(figure(rc, 46)["room"], 40)

    def test_days_past_a_figure_are_reported_as_past(self):
        log = make_log(TY, uk_days=20, fill_to=MID_YEAR)
        rc = E.srt_reference(log, TY, MID_YEAR)["running_count"]
        self.assertEqual(figure(rc, 16)["room"], -5)
        self.assertEqual(figure(rc, 16)["room_text"], "5 UK days past 16: first automatic overseas test")

    def test_third_automatic_overseas_figures_appear_with_the_users_claim(self):
        log = make_log(TY, uk_days=20, uk_work_days=4, fill_to=MID_YEAR)
        log.profile["tax_years"][TY]["overseas_full_time_work_claimed"] = "yes"
        rc = E.srt_reference(log, TY, MID_YEAR)["running_count"]
        self.assertEqual([f["figure"] for f in rc["figures"]], [16, 91, 31, 183])
        self.assertEqual(figure(rc, 91)["room"], 70)
        self.assertEqual(figure(rc, 31)["room"], 26)
        self.assertEqual(figure(rc, 31)["unit"], "UK work days")

    def test_the_nearest_uk_day_figure_ahead_is_the_one_marked_next(self):
        log = make_log(TY, uk_days=20, uk_work_days=4, ties={"accommodation": "yes"}, fill_to=MID_YEAR)
        log.profile["tax_years"][TY]["overseas_full_time_work_claimed"] = "yes"
        ref = E.srt_reference(log, TY, MID_YEAR)
        nxt = ref["running_count"]["next_figure"]
        self.assertEqual(nxt["figure"], 91)          # 16 is passed; 91 is nearer than 121 and 183
        self.assertEqual(nxt["room"], 70)
        self.assertEqual([f["figure"] for f in ref["applicable_figures"] if f["next"]], [91])

    def test_a_work_day_figure_is_never_the_figure_progress_is_shown_against(self):
        log = make_log(TY, uk_days=0, uk_work_days=0, fill_to=MID_YEAR)
        log.profile["tax_years"][TY]["overseas_full_time_work_claimed"] = "yes"
        ref = E.srt_reference(log, TY, MID_YEAR)     # 31 UK work days is the nearest figure by room, but not in days
        self.assertEqual(figure(ref["running_count"], 31)["room"], 30)
        self.assertEqual(ref["running_count"]["next_figure"]["figure"], 16)

    def test_applicable_figures_are_returned_for_a_year_with_a_result_too(self):
        ref = E.srt_reference(make_log(TY, uk_days=5), TY, YEAR_END)
        self.assertIsNone(ref["running_count"])
        self.assertEqual([f["figure"] for f in ref["applicable_figures"]], [16, 183])
        self.assertEqual([f["figure"] for f in ref["applicable_figures"] if f["next"]], [16])


class GateChecklist(unittest.TestCase):
    """gate_items(): the short labels behind the Reference card's checklist."""

    def labels(self, ref):
        return [(i["label"], i["done"]) for i in ref["gate"]]

    def test_mid_year_partial_log(self):
        log = make_log(TY, uk_days=5, ties={"family": "not_answered", "work": "unsure"}, fill_to=date(2026, 9, 20))
        ref = E.srt_reference(log, TY, MID_YEAR)
        self.assertEqual(self.labels(ref), [("Tax year ends 5 Apr 2027", False), ("7 days to log", False),
                                            ("Previous 3 years recorded", True), ("2 ties to answer", False)])

    def test_complete_year_is_all_ticks(self):
        ref = E.srt_reference(make_log(TY, uk_days=5), TY, YEAR_END)
        self.assertEqual(self.labels(ref), [("Tax year ended", True), ("Every day logged", True),
                                            ("Previous 3 years recorded", True), ("Ties answered", True)])

    def test_labels_and_reasons_stay_in_step(self):
        ref = E.srt_reference(make_log(TY, uk_days=5, prior_resident="unsure"), TY, YEAR_END)
        self.assertEqual([i["detail"] for i in ref["gate"] if not i["done"]], ref["result_withheld"])
        self.assertIn(("Previous 3 years to record", False), self.labels(ref))


class ReferenceVisual(unittest.TestCase):
    """The gauge and the day strip the Reference card is built from."""

    def test_gauge_fills_to_the_count_and_ticks_the_figures(self):
        g = C.gauge(5, 16, [(183, "first automatic UK test")], width=660)
        self.assertIn("aria-label='5 UK midnights against the 16-day figure'", g)
        self.assertIn(">16</text>", g)
        self.assertNotIn(">183</text>", g)  # outside the scale: it belongs in the detail, not on the bar

    def test_day_strip_marks_uk_days_and_gaps(self):
        log = make_log(TY, uk_days=5, fill_to=date(2026, 5, 5))   # 30 days logged, 5 of them UK
        start, end = E.tax_year_bounds(TY)
        strip = C.day_strip(log, start, end, today=MID_YEAR)
        self.assertIn("30 logged", strip)
        self.assertIn(f"fill='{C.CORAL}'", strip)   # the UK run
        self.assertIn(f"fill='{C.AMBER}'", strip)   # the unlogged run

    def test_day_strip_leaves_the_days_to_come_empty(self):
        log = make_log(TY, uk_days=5, fill_to=date(2026, 5, 5))
        start, end = E.tax_year_bounds(TY)
        filled = lambda strip: sum(float(w) for w in re.findall(r"width='([\d.]+)' height='16' fill=", strip))
        whole_year = filled(C.day_strip(log, start, end))
        to_date = filled(C.day_strip(log, start, end, today=MID_YEAR))
        self.assertAlmostEqual(whole_year, 658, delta=1)
        self.assertAlmostEqual(to_date / whole_year, 175 / 365, delta=0.02)   # 6 Apr to 27 Sep


class Outputs(unittest.TestCase):
    """Dashboard and PDF export: one visual read, a checklist, and no result until the gate opens."""

    def setUp(self):
        self.mid = make_log(TY, uk_days=5, fill_to=MID_YEAR)
        self.done = make_log(TY, uk_days=5)

    def check_visual(self, html, count, figure):
        self.assertIn("class='refnum'", html)
        self.assertIn(f"aria-label='{count} UK midnights against the {figure}-day figure'", html)
        self.assertIn("Every day from 6 Apr 2026 to 5 Apr 2027", html)   # the day strip
        self.assertIn("Educational, not tax advice. It records days; it doesn't decide your residence.", html)

    def test_dashboard_mid_year_is_a_count_a_chip_and_a_checklist(self):
        h = RD.render(self.mid, MID_YEAR, [])
        self.check_visual(h, 5, 16)
        self.assertIn("10 days left before 16", h)
        self.assertIn("No result for 2026/27 yet", h)
        self.assertIn("Tax year ends 5 Apr 2027", h)
        self.assertIn("Every box is ticked before a result is given.", h)
        self.assertNotIn(MATCHES, h)
        self.assertNotIn("Your log so far:", h)   # the long running sentence stays in the engine output

    def test_dashboard_folds_the_figure_detail_away(self):
        h = RD.render(self.mid, MID_YEAR, [])
        detail = h.split("<details><summary>Figures and sources</summary>", 1)[1].split("</details>", 1)[0]
        self.assertIn("10 UK days of room before 16: first automatic overseas test", detail)
        self.assertIn("RFIG20120 (updated", detail)
        self.assertIn("183: first automatic UK test", detail)

    def test_dashboard_shows_the_stage_line_for_a_finished_year(self):
        h = RD.render(self.done, YEAR_END, [])
        self.check_visual(h, 5, 16)
        self.assertIn(MATCHES + " first automatic overseas test for this tax year.", h)
        self.assertIn("Not tax advice \u2014 always check your own position. Source: RFIG20120", h)
        self.assertIn("Every day logged", h)
        self.assertNotIn("No result for", h)
        self.assertNotIn("class='todo'", h)

    def test_pdf_export_mid_year_matches_the_dashboard(self):
        html, _ = RP.build_html(self.mid, TY, MID_YEAR)
        self.check_visual(html, 5, 16)
        self.assertIn("10 days left before 16", html)
        self.assertIn("No result for 2026/27 yet", html)
        self.assertIn("<div class='fine'><b>Figures and sources</b>", html)
        self.assertGreater(html.index("10 UK days of room before 16"), html.index("<div class='fine'>"))
        self.assertNotIn(MATCHES, html)
        self.assertNotIn("Your log so far:", html)

    def test_pdf_export_shows_the_stage_line_for_a_finished_year(self):
        html, _ = RP.build_html(self.done, TY, YEAR_END)
        self.check_visual(html, 5, 16)
        self.assertIn(MATCHES + " first automatic overseas test for this tax year.", html)
        self.assertNotIn("Your log so far:", html)

    def test_cli_summary_empty_log_mid_year(self):
        log = make_log(TY, fill_to=date(2026, 4, 5))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "daylog.json"
            p.write_text(json.dumps(log.data))
            out = subprocess.run([sys.executable, str(HERE.parent / "srt_engine.py"), "summary", str(p),
                                  "--as-of", MID_YEAR.isoformat(), "--rules", RULES],
                                 capture_output=True, text=True, check=True).stdout
        self.assertNotIn(MATCHES, out)
        year = json.loads(out)["years"][TY]
        self.assertEqual(year["stage_lines"], [])
        self.assertIn("The tax year ends on 5 Apr 2027", year["running_count"]["text"])


if __name__ == "__main__":
    unittest.main()
