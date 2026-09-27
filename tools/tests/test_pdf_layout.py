"""The PDF export must not let any text spill out of its box (WeasyPrint layout tree + static SVG label extents)."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import srt_engine as E  # noqa: E402

try:
    import weasyprint  # noqa: F401
    HAVE_WP = True
except Exception:
    HAVE_WP = False

KIT = Path(__file__).resolve().parents[2]
EX = KIT / "example"


@unittest.skipUnless(HAVE_WP, "weasyprint not installed")
class PdfLayout(unittest.TestCase):
    def test_no_text_overflow_in_example_export(self):
        import pdf_layout_check as P
        import render_pdf as RP
        log = E.DayLog.load(str(EX / "daylog.json"))
        for ty in ("2025/26",):
            html, _ = RP.build_html(log, ty, date(2026, 9, 26), prefix="")
            self.assertEqual(P.overflows(html), [], ty)
            self.assertEqual(P.svg_text_overflows(html), [], ty)

    def test_checker_catches_overflow(self):
        import pdf_layout_check as P
        self.assertTrue(P.overflows("<div style='width:30mm'><span style='white-space:nowrap'>an unbreakable line that is far too long</span></div>"))
        self.assertTrue(P.svg_text_overflows("<svg viewBox='0 0 100 20'><text x='90' font-size='12'>overflowing</text></svg>"))


if __name__ == "__main__":
    unittest.main()
