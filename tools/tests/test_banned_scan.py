import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import banned_scan as B  # noqa: E402


class BannedScanTest(unittest.TestCase):
    def scan(self, text):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "x.md").write_text(text, encoding="utf-8")
            return B.scan(Path(d), [])[0]

    def test_listing_preference_safety_allowed(self):
        self.assertEqual(self.scan("Tell Nomad Pro your budget and what matters to you, whether it's rent, food, safety, crime or getting around.\n"), [])

    def test_safety_as_outcome_still_banned(self):
        # banned-list:start (deliberate examples of banned wording)
        self.assertTrue(self.scan("Your log keeps you safe.\n"))
        self.assertTrue(self.scan("Check your safety margin before you travel.\n"))
        # banned-list:end


    def test_verbatim_hmrc_mirror_checked_for_private_data_only(self):
        # banned-list:start (deliberate examples of banned wording)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "hmrc", "pages"); p.mkdir(parents=True)
            p.joinpath("rfig20760.md").write_text("They will not qualify for full-time work overseas.\n", encoding="utf-8")
            Path(d, "notes.md").write_text("You qualify.\n", encoding="utf-8")
            p.joinpath("x.md").write_text("see " + "/" + "Users" + "/someone/Library\n", encoding="utf-8")
            banned, private = B.scan(Path(d), list(B.PRIVATE_DEFAULT))
        # banned-list:end
        self.assertEqual([h[0] for h in banned], ["notes.md"])
        self.assertEqual([h[0] for h in private], ["hmrc/pages/x.md"])


if __name__ == "__main__":
    unittest.main()
