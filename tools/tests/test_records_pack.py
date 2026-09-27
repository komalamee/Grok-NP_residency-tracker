"""Records pack, evidence column and dashboard/PDF shape tests (fictional example data only)."""
import json
import re
import sys
import tempfile
import unittest
import zipfile
import hashlib
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import srt_engine as E  # noqa: E402
import render_common as RC  # noqa: E402
import render_dashboard as RD  # noqa: E402
import render_pdf as RP  # noqa: E402

EX = KIT / "example"
AS_OF = date(2026, 7, 31)
try:
    import weasyprint  # noqa: F401
    HAVE_WP = True
except Exception:
    HAVE_WP = False


class EvidenceColumn(unittest.TestCase):
    def test_link_file_pointer(self):
        row = {"evidence": [{"type": "email", "url": "https://mail.google.com/mail/u/0/#all/x", "label": "Hotel email"},
                            {"type": "screenshot", "file": "evidence/a.png", "label": "Ticket"},
                            {"type": "card", "pointer": "Revolut spend"}]}
        h = RC.evidence_html(row, "../")
        self.assertIn("href='https://mail.google.com/mail/u/0/#all/x'", h)
        self.assertIn("href='../evidence/a.png'", h)
        self.assertIn("Revolut spend", h)
        self.assertEqual(h.count("<a "), 2)
        self.assertIn("Ticket <evidence/a.png>", RC.evidence_text(row))

    def test_prefix(self):
        self.assertEqual(RC.file_prefix("/u/data", "/u/data"), "")
        self.assertEqual(RC.file_prefix("/u/data", "/u/data/exports"), "../")

    def test_csv_has_evidence_column(self):
        log = E.DayLog.load(EX / "daylog.json")
        rows = list(RP.csv_rows(log, date(2025, 5, 11), date(2025, 5, 11)))
        self.assertIn("evidence", rows[0])
        self.assertIn("evidence/2025-05-11-train-ticket-sample.png", rows[1][rows[0].index("evidence")])


class DashboardAndPdfShape(unittest.TestCase):
    def setUp(self):
        self.log = E.DayLog.load(EX / "daylog.json")
        self.rules = E.load_rules(KIT / "schema" / "country-rules.json")

    def test_dashboard_self_contained_with_tabs_and_evidence(self):
        docs = json.loads((EX / "documents" / "index.json").read_text())["documents"]
        h = RD.render(self.log, AS_OF, self.rules, "", docs)
        self.assertNotRegex(h, r"<script[^>]+src=|<link[^>]+stylesheet|@import|url\(http")
        for tab in ("overview", "daylog", "records", "schengen"):
            self.assertIn(f"data-v='{tab}'", h)
        self.assertIn("href='evidence/2025-05-11-train-ticket-sample.png'", h)
        self.assertIn("href='documents/2024-03-01-employment-contract-sample.pdf'", h)

    def test_pdf_html_has_no_tab_ui(self):
        html, _ = RP.build_html(self.log, "2025/26", AS_OF)
        self.assertNotIn("<button", html)
        self.assertNotIn("<script", html)
        self.assertNotRegex(html, r"class='(tab|view|year)\b")
        self.assertIn("<th>Evidence</th>", html)


@unittest.skipUnless(HAVE_WP, "weasyprint not installed")
class PdfCli(unittest.TestCase):
    def test_cli_writes_pdf_and_csv_with_relative_evidence_link(self):
        import contextlib, io, zlib
        with tempfile.TemporaryDirectory() as out:
            with contextlib.redirect_stdout(io.StringIO()):
                RP.main([str(EX / "daylog.json"), "--tax-year", "2025/26", "--out-dir", out, "--as-of", AS_OF.isoformat(), "--data-root", str(EX)])
            pdf = Path(out) / "Travel and day log 2025-26.pdf"
            self.assertTrue(pdf.exists() and pdf.stat().st_size > 20000)
            self.assertTrue((Path(out) / "Travel and day log 2025-26.csv").exists())
            self.assertFalse((Path(out) / "Travel and day log 2025-26.html").exists())
            b = pdf.read_bytes()
            uris = set()
            for m in re.finditer(rb"stream\r?\n(.*?)endstream", b, re.S):
                try:
                    uris |= set(re.findall(rb"/URI ?\(([^)]*)\)", zlib.decompress(m.group(1))))
                except Exception:
                    continue
            self.assertTrue(any(u.endswith(b"evidence/2025-05-11-train-ticket-sample.png") and not u.startswith(b"file:") for u in uris))


@unittest.skipUnless(HAVE_WP, "weasyprint not installed")
class RecordsPack(unittest.TestCase):
    def test_pack_contents_links_and_manifest(self):
        import records_pack as RPK
        with tempfile.TemporaryDirectory() as out:
            zp = RPK.build(str(EX / "daylog.json"), ["2025/26"], out, str(EX), AS_OF)
            self.assertTrue(zp.name.startswith("Records pack 2025-26"))
            self.assertNotRegex(zp.name.lower(), r"audit")
            with zipfile.ZipFile(zp) as z:
                names = z.namelist()
                root = names[0].split("/")[0]
                need = ["00 Index.pdf", "01 Travel and day logs/Travel and day log 2025-26.pdf", "01 Travel and day logs/Travel and day log 2025-26.csv",
                        "02 Evidence index/Evidence index.csv", "02 Evidence index/Evidence index.pdf", "03 Status documents/Documents index.csv",
                        "evidence/2025-05-11-train-ticket-sample.png", "documents/2024-03-01-employment-contract-sample.pdf", "manifest.json"]
                for n in need:
                    self.assertIn(f"{root}/{n}", names)
                man = json.loads(z.read(f"{root}/manifest.json"))
                for rel, h in man["files"].items():
                    self.assertEqual(hashlib.sha256(z.read(f"{root}/{rel}")).hexdigest(), h, rel)
                pdf = z.read(f"{root}/01 Travel and day logs/Travel and day log 2025-26.pdf")
                import zlib
                uris = set(re.findall(rb"/URI ?\(([^)]*)\)", pdf))
                for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
                    try:
                        uris |= set(re.findall(rb"/URI ?\(([^)]*)\)", zlib.decompress(m.group(1))))
                    except Exception:
                        continue
                self.assertIn(b"../evidence/2025-05-11-train-ticket-sample.png", uris)
                self.assertFalse(any(u.startswith(b"file:") for u in uris))
                ev = z.read(f"{root}/02 Evidence index/Evidence index.csv").decode()
                self.assertIn("2025-05-11", ev)
                self.assertIn("https://mail.google.com/mail/u/0/#all/sample-message-id-0002", ev)


if __name__ == "__main__":
    unittest.main()
