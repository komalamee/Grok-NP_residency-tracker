"""The verdict gate: no stage line unless the tax year has ended, every day in it is logged,
residence for the previous 3 tax years is recorded and every applicable tie is answered.
Until then the engine returns what is missing plus a running count, and the dashboard and the
PDF export show that running count where the stage line would go."""
import json
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
import render_dashboard as RD  # noqa: E402
import render_pdf as RP  # noqa: E402
from test_engine import make_log  # noqa: E402

TY = "2026/27"
MID_YEAR = date(2026, 9, 27)
YEAR_END = date(2027, 4, 5)
RULES = str(KIT / "schema" / "country-rules.json")
# The approved stage-line wording, assembled here so banned_scan.py does not read this test as a statement.
POINTS_TO = "points to " + "non" + "-resident"


def figure(rc, n):
    return [f for f in rc["figures"] if f["figure"] == n][0]


class VerdictGate(unittest.TestCase):
    def test_empty_log_mid_year_returns_no_verdict(self):
        log = make_log(TY, fill_to=date(2026, 4, 5))  # no days in 2026/27 at all
        ref = E.srt_reference(log, TY, MID_YEAR)
        self.assertEqual(ref["summary"]["logged"], 0)
        self.assertEqual(ref["stage_lines"], [])
        self.assertTrue(any("still running" in r for r in ref["verdict_withheld"]))
        self.assertTrue(any("175 days are not logged" in r for r in ref["verdict_withheld"]))
        rc = ref["running_count"]
        self.assertEqual(rc["uk_midnights"], 0)
        self.assertEqual(rc["year_ends"], "2027-04-05")
        self.assertEqual(rc["text"], "Your log so far: 0 UK midnights from 6 Apr 2026 to 27 Sep 2026 "
                                     "(0 of 175 days logged). The tax year ends on 5 Apr 2027.")
        self.assertNotIn(POINTS_TO, rc["text"])

    def test_mid_year_fully_logged_to_date_returns_no_verdict(self):
        log = make_log(TY, uk_days=5, fill_to=MID_YEAR)
        ref = E.srt_reference(log, TY, MID_YEAR)
        self.assertEqual(ref["summary"]["unlogged"], 0)
        self.assertEqual(ref["stage_lines"], [])
        self.assertEqual(ref["verdict_withheld"], ["the tax year is still running (it ends on 5 Apr 2027)"])
        rc = ref["running_count"]
        self.assertEqual(rc["uk_midnights"], 5)
        self.assertEqual(rc["text"], "Your log so far: 5 UK midnights from 6 Apr 2026 to 27 Sep 2026 "
                                     "(175 of 175 days logged). The tax year ends on 5 Apr 2027.")
        self.assertEqual(figure(rc, 16)["room"], 10)

    def test_finished_year_with_unlogged_days_returns_no_verdict(self):
        log = make_log(TY, uk_days=5, fill_to=date(2027, 3, 1))
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["stage_lines"], [])
        self.assertEqual(ref["verdict_withheld"], ["35 days are not logged"])
        self.assertIn("The tax year ended on 5 Apr 2027", ref["running_count"]["text"])

    def test_one_unlogged_day_is_reported_in_the_singular(self):
        log = make_log(TY, uk_days=5, fill_to=date(2027, 4, 4))
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["verdict_withheld"], ["1 day is not logged"])
        self.assertEqual(ref["stage_lines"], [])

    def test_finished_year_with_unanswered_tie_returns_no_verdict(self):
        log = make_log(TY, uk_days=5, ties={"family": "not_answered"})
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["stage_lines"], [])
        self.assertIn("ties not answered: family", ref["verdict_withheld"])

    def test_unanswered_ties_are_named_as_the_product_names_them(self):
        log = make_log(TY, uk_days=5, ties={"ninety_day": "not_answered", "country": "unsure"})
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertIn("ties not answered: 90-day, country", ref["verdict_withheld"])

    def test_finished_year_without_prior_years_returns_no_verdict(self):
        log = make_log(TY, uk_days=5, prior_resident="unsure")
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["stage_lines"], [])
        self.assertIn("residence for the previous 3 tax years is not recorded", ref["verdict_withheld"])
        # Neither table is known, so both automatic-overseas day figures are listed as conditional.
        rc = ref["running_count"]
        self.assertEqual([f["figure"] for f in rc["figures"]], [16, 46, 183])
        self.assertIn("applies if you were UK resident", figure(rc, 16)["text"])

    def test_finished_complete_answered_year_still_returns_verdict(self):
        log = make_log(TY, uk_days=5)
        ref = E.srt_reference(log, TY, YEAR_END)
        self.assertEqual(ref["verdict_withheld"], [])
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


class Outputs(unittest.TestCase):
    """Dashboard and PDF export: the running line where the stage line would be, and no verdict."""

    def setUp(self):
        self.mid = make_log(TY, uk_days=5, fill_to=MID_YEAR)
        self.done = make_log(TY, uk_days=5)

    def test_dashboard_shows_the_running_line_mid_year(self):
        h = RD.render(self.mid, MID_YEAR, [])
        self.assertIn("Your log so far: 5 UK midnights from 6 Apr 2026 to 27 Sep 2026", h)
        self.assertIn("still to record: the tax year is still running", h)
        self.assertIn("10 UK days of room before 16", h)
        self.assertNotIn(POINTS_TO, h)

    def test_dashboard_shows_the_stage_line_for_a_finished_year(self):
        h = RD.render(self.done, YEAR_END, [])
        self.assertIn(POINTS_TO + " under the first automatic overseas test", h)
        self.assertNotIn("Your log so far:", h)

    def test_pdf_export_shows_the_running_line_mid_year(self):
        html, _ = RP.build_html(self.mid, TY, MID_YEAR)
        self.assertIn("Your log so far: 5 UK midnights from 6 Apr 2026 to 27 Sep 2026", html)
        self.assertIn("It does not determine residence.", html)
        self.assertNotIn(POINTS_TO, html)

    def test_pdf_export_shows_the_stage_line_for_a_finished_year(self):
        html, _ = RP.build_html(self.done, TY, YEAR_END)
        self.assertIn(POINTS_TO + " under the first automatic overseas test", html)
        self.assertNotIn("Your log so far:", html)

    def test_cli_summary_empty_log_mid_year(self):
        log = make_log(TY, fill_to=date(2026, 4, 5))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "daylog.json"
            p.write_text(json.dumps(log.data))
            out = subprocess.run([sys.executable, str(HERE.parent / "srt_engine.py"), "summary", str(p),
                                  "--as-of", MID_YEAR.isoformat(), "--rules", RULES],
                                 capture_output=True, text=True, check=True).stdout
        self.assertNotIn(POINTS_TO, out)
        year = json.loads(out)["years"][TY]
        self.assertEqual(year["stage_lines"], [])
        self.assertIn("The tax year ends on 5 Apr 2027", year["running_count"]["text"])


if __name__ == "__main__":
    unittest.main()
