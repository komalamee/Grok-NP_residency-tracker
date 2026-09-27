"""Where the country-rules table is read from when --rules is not given.

The weekly travel-rules watch updates the user's own copy in their data folder, so that copy has to win over the
engine's shipped baseline; otherwise the counts keep using rules the watch has already replaced.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
import srt_engine as E  # noqa: E402

SHIPPED = KIT / "schema" / "country-rules.json"
TOOLS = ["srt_engine.py", "render_pdf.py", "render_dashboard.py", "records_pack.py", "travel_rules_check.py"]


def write_rules(folder: Path, th_limit: int) -> Path:
    """A copy of the shipped table with Thailand's limit changed, so the file in use is identifiable."""
    doc = json.loads(SHIPPED.read_text(encoding="utf-8"))
    for r in doc["rules"]:
        if r["zone"] == "TH":
            r["limit_days"] = th_limit
    p = folder / "country-rules.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


class RulesDefaultOrder(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.home = self.tmp / "home"
        (self.home / "nomad-pro-data").mkdir(parents=True)
        self.data = self.tmp / "data"
        self.data.mkdir()
        self._env = {k: os.environ.get(k) for k in ("HOME", "NOMAD_PRO_DATA")}
        os.environ["HOME"] = str(self.home)
        os.environ.pop("NOMAD_PRO_DATA", None)

    def tearDown(self):
        for k, v in self._env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def test_explicit_rules_wins(self):
        p = write_rules(self.data, 45)
        write_rules(self.home / "nomad-pro-data", 60)
        os.environ["NOMAD_PRO_DATA"] = str(self.data)
        other = write_rules(self.tmp, 15)
        self.assertEqual(E.default_rules_path(other), other)
        self.assertNotEqual(E.default_rules_path(other), p)

    def test_explicit_rules_that_do_not_exist_load_nothing(self):
        # A mistyped --rules must not silently fall back to a different table.
        self.assertIsNone(E.default_rules_path(self.tmp / "no-such-file.json"))
        self.assertEqual(E.load_rules(E.default_rules_path(self.tmp / "no-such-file.json")), [])

    def test_env_data_folder_wins_over_home_and_shipped(self):
        p = write_rules(self.data, 45)
        write_rules(self.home / "nomad-pro-data", 60)
        os.environ["NOMAD_PRO_DATA"] = str(self.data)
        self.assertEqual(E.default_rules_path(), p)

    def test_home_data_folder_wins_over_shipped(self):
        p = write_rules(self.home / "nomad-pro-data", 60)
        self.assertEqual(E.default_rules_path(), p)

    def test_env_data_folder_without_a_rules_file_falls_through(self):
        os.environ["NOMAD_PRO_DATA"] = str(self.data)
        p = write_rules(self.home / "nomad-pro-data", 60)
        self.assertEqual(E.default_rules_path(), p)

    def test_shipped_file_is_the_last_resort(self):
        os.environ["NOMAD_PRO_DATA"] = str(self.data)
        self.assertEqual(E.default_rules_path(), SHIPPED)

    def test_user_copy_is_the_one_counted(self):
        write_rules(self.home / "nomad-pro-data", 60)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        out = subprocess.run([sys.executable, str(KIT / "tools" / "srt_engine.py"), "summary",
                              str(KIT / "example" / "daylog.json"), "--as-of", "2026-07-31"],
                             capture_output=True, text=True, check=True, env=env).stdout
        limits = {row["zone"]: row["limit"] for row in json.loads(out)["limits"]}
        self.assertEqual(limits["TH"], 60)

    def test_every_tool_documents_the_same_order(self):
        for tool in TOOLS:
            with self.subTest(tool=tool):
                help_text = subprocess.run([sys.executable, str(KIT / "tools" / tool), "--help"],
                                           capture_output=True, text=True, check=True).stdout
                # argparse wraps the help line, so compare without whitespace.
                flat = "".join(help_text.split())
                self.assertIn("--rules", flat)
                self.assertIn("$NOMAD_PRO_DATA/country-rules.json", flat)
                self.assertIn("~/nomad-pro-data/country-rules.json", flat)
                self.assertIn("<engine>/schema/country-rules.json", flat)


if __name__ == "__main__":
    unittest.main()
