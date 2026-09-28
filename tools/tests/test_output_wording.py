"""Wording guardrails on what the tools actually render.

banned_scan.py reads the source prose; this reads the output. Every surface the user can end up looking at is
built here for a finished year, a mid-year log and a modelled trip, and checked for the words the product never
uses about someone's position. HTML is checked with <style> and <script> stripped (the inlined CSS and JS are not
prose) but with attributes left in, because tooltips and aria-labels are read out to the user.
"""
import csv
import io
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
import render_dashboard as RD  # noqa: E402
import render_pdf as RP  # noqa: E402
from test_engine import make_log  # noqa: E402

TY = "2026/27"
MID_YEAR = date(2026, 9, 27)
YEAR_END = date(2027, 4, 5)
RULES = str(KIT / "schema" / "country-rules.json")

# banned-list:start (the words the product never uses about the user or their log)
BANNED = [r"non[- ]resident", r"stay non[- ]resident", r"\bverdicts?\b", r"\bdetermin(e|es|ed|ing|ation)\b",
          r"\bsafe\b", r"\bqualify\b", r"\bqualifies\b", r"\bthe answer\b"]
# banned-list:end
STRIP = re.compile(r"<(style|script)\b[^>]*>.*?</\1>", re.S | re.I)


def offences(text: str, what: str) -> list[str]:
    return [f"{what}: {m.group(0)!r} in ...{text[max(0, m.start() - 70):m.end() + 70]}..."
            for pat in BANNED for m in re.finditer(pat, text, re.I)]


def prose(html: str) -> str:
    """Rendered HTML without its inlined stylesheet and script, which are not prose."""
    return STRIP.sub(" ", html)


class OutputWording(unittest.TestCase):
    def setUp(self):
        self.found: list[str] = []

    def tearDown(self):
        self.assertEqual(self.found, [], "\n".join(self.found))

    def check(self, text, what):
        self.found += offences(text, what)

    # ---------------------------------------------------------------- engine
    def test_engine_summary_and_reference(self):
        for label, log, as_of in (("finished year", make_log(TY, uk_days=5), YEAR_END),
                                  ("mid-year", make_log(TY, uk_days=5, fill_to=MID_YEAR), MID_YEAR),
                                  ("ties test", make_log(TY, uk_days=36, ties={"accommodation": "yes"}), YEAR_END),
                                  ("empty log", make_log(TY, fill_to=date(2026, 4, 5)), MID_YEAR)):
            out = E.full_summary(log, as_of, E.load_rules(RULES))
            self.check(json.dumps(out, default=str), f"srt_engine summary ({label})")
            self.check(" ".join(E.open_questions(log, TY, as_of)), f"open questions ({label})")

    def test_stage_line_for_a_finished_year(self):
        line = E.srt_reference(make_log(TY, uk_days=5), TY, YEAR_END)["stage_lines"][0]
        self.assertEqual(line["text"], "Your log matches the first automatic overseas test for this tax year.")
        self.check(line["text"] + " " + line["disclaimer"], "stage line")

    def test_trip_plan(self):
        log = make_log(TY, uk_days=5, fill_to=MID_YEAR)
        res = E.plan(log, [{"country": "GB", "from": "2026-12-20", "to": "2027-01-03"},
                           {"country": "ES", "from": "2027-01-10", "to": "2027-02-20"}],
                     MID_YEAR, E.load_rules(RULES))
        self.check(json.dumps(res, default=str), "srt_engine plan")

    def test_cli_summary_and_plan(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "daylog.json"
            p.write_text(json.dumps(make_log(TY, uk_days=5).data))
            for cmd in (["summary", str(p), "--as-of", YEAR_END.isoformat()],
                        ["plan", str(p), "--as-of", MID_YEAR.isoformat(), "--trip", "ES:2027-01-10:2027-02-20"]):
                out = subprocess.run([sys.executable, str(HERE.parent / "srt_engine.py")] + cmd + ["--rules", RULES],
                                     capture_output=True, text=True, check=True).stdout
                self.check(out, "srt_engine.py " + cmd[0])

    # ---------------------------------------------------------------- dashboard and export
    def test_dashboard(self):
        for label, log, as_of in (("finished year", make_log(TY, uk_days=5), YEAR_END),
                                  ("mid-year", make_log(TY, uk_days=5, fill_to=MID_YEAR), MID_YEAR)):
            self.check(prose(RD.render(log, as_of, E.load_rules(RULES))), f"dashboard ({label})")

    def test_pdf_export_html_and_csv(self):
        for label, log, as_of in (("finished year", make_log(TY, uk_days=5), YEAR_END),
                                  ("mid-year", make_log(TY, uk_days=5, fill_to=MID_YEAR), MID_YEAR)):
            html, base = RP.build_html(log, TY, as_of)
            self.check(prose(html), f"PDF export ({label})")
            self.check(base, f"PDF file name ({label})")
            start, end = E.tax_year_bounds(TY)
            buf = io.StringIO()
            csv.writer(buf).writerows(RP.csv_rows(log, start, min(end, as_of)))
            self.check(buf.getvalue(), f"export CSV ({label})")

    def test_the_shipped_example_data(self):
        """The fictional example folder: more populated than the test logs (evidence, trips, work rule)."""
        log = E.DayLog.load(KIT / "example" / "daylog.json")
        as_of = date(2026, 7, 31)
        rules = E.load_rules(RULES)
        self.check(prose(RD.render(log, as_of, rules)), "dashboard (example data)")
        self.check(prose(RP.build_html(log, "2025/26", as_of)[0]), "PDF export (example data)")
        self.check(json.dumps(E.full_summary(log, as_of, rules), default=str), "summary (example data)")

    # ---------------------------------------------------------------- the check itself
    def test_the_scan_would_catch_the_old_wording(self):
        old = "Your log points to " + "non" + "-resident under the first automatic overseas test."
        self.assertTrue(offences(old, "old stage line"))
        self.assertTrue(offences("It does not determine residence.", "old caption"))  # banned-list:skip
        self.assertEqual(offences("Educational, not tax advice. It records days; it doesn't decide your residence.",
                                  "new caption"), [])
        self.assertEqual(offences("take advice from a qualified professional", "L6"), [])


if __name__ == "__main__":
    unittest.main()
