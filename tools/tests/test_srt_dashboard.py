"""The tabbed SRT Residency dashboard (srt_dashboard.py, default design of render_dashboard.py from 0.1.5).

Fictional data only. Covers: the exact tab set and tax-year switch; no residence-outcome wording (rule 3); no UK day
limit, headroom or days remaining from the ties table (rule 4); "Your own limit" blank by default (rule 5); links only
to real http(s) documents that open, everything else plain text (rule 6); 2-4 index bullets with no addresses, IDs or
amounts (rule 7); "Your note" export and --import-notes (rule 8); private places shown as "<city> (family home)" (rule 9);
per-test marks shown for a finished tax year and hidden while the selected year is unfinished.
The browser tests run only where Google Chrome or Chromium is installed.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import srt_engine as E  # noqa: E402
import srt_dashboard as SD  # noqa: E402

TOOLS = HERE.parent
AS_OF = date(2026, 9, 27)
PRIVATE_LABEL = "Fictional parents' house, 9 Sample Street, Leeds LS1 1AA"
TABS = ["Overview", "UK Days", "Schengen", "Full Timeline", "Work Days", "SRT Status", "Documentation"]
# Words the dashboard never shows (dashboard rules 3 and 4); HMRC's rule name "temporary non-residence"
# and the user's own "Your own limit" / "Your chosen limit" are allowed.
# banned-list:start
BANNED = [r"non[- ]?residen(t|ce|cy)", r"\bcomplian", r"\bsafe\b", r"\bsafety\b", r"\bat risk\b", r"\bproofs?\b", r"\bproven\b",
          r"(?-i:\bPASS(ED|ES)?\b)", r"(?-i:\bFAIL(ED|S)?\b)", r"\bfailed\b", r"\bverdicts?\b", r"\bqualif(y|ies)\b",
          r"you are (non[- ])?resident", r"UK tax resident", r"all clear", r"audit[- ]ready", r"guaranteed", r"headroom",
          r"\bremaining\b", r"\bmax\b", r"\blimit\b", r"allowed (UK )?days", r"days of room", r"\bdetermin(e|es|ed|ing|ation)\b"]
ALLOW = [r"temporary non-residence", r"your (chosen|own) limit"]
# banned-list:end


def fixture(user_limit=None, private=True) -> dict:
    """2025/26 in full and 2026/27 to AS_OF: Valencia, then a UK stay at a private family address, then Tbilisi."""
    days = []
    d = date(2025, 4, 6)
    while d <= AS_OF:
        if date(2025, 8, 1) <= d <= date(2025, 8, 20) or date(2026, 5, 1) <= d <= date(2026, 5, 10):
            cc, place, acc = "GB", PRIVATE_LABEL, "acc-fam"
        elif d < date(2026, 1, 1):
            cc, place, acc = "ES", "Calle Ficticia 12, Valencia", None
        else:
            cc, place, acc = "GE", "Fictional Apartments, 5 Test Avenue, Tbilisi", None
        ev = [{"type": "booking", "pointer": "Booking receipt R-1234 EUR 45.00 for coffee and pastries (fictional)", "source_id": "msg-9f8e7d"}]
        if d in (date(2025, 8, 1), date(2026, 5, 1)):
            ev.append({"type": "ticket", "pointer": "Flight ZZ 101 (1 Aug) fictional", "label": "Ticket"})
        if cc == "GB":
            ev.append({"type": "card", "pointer": "Card payment at 9 Sample Street shop GBP 3.20 (fictional)"})
        w = {"over_3h": "n/a"}
        if cc == "GB":
            w = {"over_3h": "yes", "hours": 7, "source": "user_answer"} if d.day in (4, 5) else {"over_3h": "no", "source": "user_answer"}
        days.append({"date": d.isoformat(), "tax_year": E.tax_year_of(d), "midnight_country": cc, "midnight_place": place,
                     "accommodation_id": acc, "countries_present": [cc], "uk_work": w, "evidence": ev,
                     "confidence": "inferred" if d == date(2025, 8, 10) else "confirmed", "logged_via": "checkin"})
        d += timedelta(days=1)
    prof = {"display_name": "Sample Person (fictional)", "left_uk_on": "2025-04-05", "passports": ["GB"],
            "prior_years": [{"tax_year": t, "uk_resident": "yes", "uk_days": 300} for t in ("2022/23", "2023/24", "2024/25")],
            "accommodation_register": [{"id": "acc-fam", "label": PRIVATE_LABEL, "country": "GB", "relationship": "close_relative",
                                        "private": private, "city": "Leeds"}],
            "uk_addresses": [{"label": PRIVATE_LABEL, "accommodation_id": "acc-fam"}],
            "family": {"partner_uk_resident": "no", "children_under_18_uk": []},
            "work_periods": [{"type": "contractor", "from": "2025-04-06", "to": None, "overseas_full_time_claimed": "no"}],
            "evidence_sources": [{"type": "calendar", "label": "Fictional calendar"}],
            "tax_years": {t: {"tie_answers": {"family": "no", "accommodation": "yes", "work": "no", "ninety_day": "yes", "country": "not_answered"},
                              "accommodation_available_91_days": {"acc-fam": "yes"}, "only_home_in_uk_answer": "no",
                              "full_time_uk_work_answer": "no"} for t in ("2025/26", "2026/27")}}
    if user_limit is not None:
        prof["user_limit"] = {"value": user_limit, "updated_at": "2026-09-01T00:00:00Z"}
    return {"schema_version": "1.0", "profile": prof, "days": days, "planned_trips": [],
            "user_notes": [{"key": "stay:2025-08-01..2025-08-20", "kind": "stay", "start": "2025-08-01", "end": "2025-08-20",
                            "country": "United Kingdom", "text": "Fictional note", "updated_at": "2026-09-01T10:00:00Z"}]}


DOCS = [{"id": "doc-a", "type": "employment_contract", "title": "Fictional contract", "tax_years": ["2025/26"], "url": "https://example.org/ok",
         "date_added": "2026-01-01", "status": "link_only"},
        {"id": "doc-b", "type": "other", "title": "Fictional dead link", "tax_years": ["2025/26"], "url": "https://example.org/dead",
         "date_added": "2026-01-01", "status": "link_only"},
        {"id": "doc-c", "type": "other", "title": "Fictional local file", "tax_years": ["2025/26"], "file": "documents/x.pdf",
         "date_added": "2026-01-01", "status": "filed"},
        {"id": "doc-d", "type": "other", "title": "Fictional pointer", "tax_years": ["2025/26"], "pointer": "Paper copy at home",
         "date_added": "2026-01-01", "status": "pointer_only"},
        {"id": "doc-e", "type": "other", "title": "Fictional bad scheme", "tax_years": ["2025/26"], "url": "file:///srv/fictional/x.pdf",
         "date_added": "2026-01-01", "status": "link_only"}]


def fake_link_ok(url, timeout=8.0):
    return url != "https://example.org/dead" and url.startswith("https://")


def np_data(html: str) -> dict:
    m = re.search(r"const NP = (\{.*?\});\nconst TAX_YEARS", html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


CODE_WORDS = {r"\bmax\b", r"\blimit\b"}     # also chart and input settings in code; the rendered text is checked in the browser


def offences(text: str, code: bool = False) -> list[str]:
    for a in ALLOW:
        text = re.sub(a, "", text, flags=re.I)
    pats = [p for p in BANNED if not (code and p in CODE_WORDS)]
    return [f"{p} -> ...{text[max(0, m.start() - 50):m.end() + 50]}..." for p in pats for m in [re.search(p, text, re.I)] if m]


class SrtDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._orig = SD.link_ok
        SD.link_ok = fake_link_ok
        cls.log = E.DayLog(fixture())
        cls.html = SD.render(cls.log, AS_OF, DOCS, "Source: fictional test")
        cls.data = np_data(cls.html)

    @classmethod
    def tearDownClass(cls):
        SD.link_ok = cls._orig

    # ---- rule 1: the exact tabbed design + tax-year switch
    def test_tabs_and_year_switch(self):
        self.assertEqual(re.findall(r'<button class="tab[^"]*" data-tab="\w+"[^>]*>([^<]+)</button>', self.html), TABS)
        self.assertIn('id="global-ty-selector"', self.html)
        self.assertEqual([t["label"] for t in self.data["taxYears"]], ["2025/26", "2026/27"])
        self.assertEqual(self.data["selectedTaxYear"], "2026/27")
        self.assertNotIn("@@NP_", self.html)
        self.assertIn(E.L6, self.html.replace("&#x27;", "'"))

    # ---- rule 3: no residence-outcome wording in the page code or the data
    def test_no_outcome_wording_in_page_or_data(self):
        page = re.sub(r"<script>\s*/\*!.*?</script>", "", self.html, flags=re.S)   # minus the vendored libraries
        page = re.sub(r"//[^\n]*", "", page)                                        # code comments are not shown
        page = re.sub(r"\bmax-(width|height)\b|\bMath\.max\b|\bmax=\"\d+\"", "", page)                 # CSS and maths, not wording
        self.assertEqual(offences(re.sub(r"\b(USER_LIMIT_KEY|getUserLimit|userLimit\w*|_userLimit\w*|SEED_USER_LIMIT|\w+UserLimit|user-limit[\w-]*)\b", "", page), code=True), [])
        self.assertEqual(offences(json.dumps(self.data, ensure_ascii=False).replace("userLimit", "")), [])

    # ---- rule 4: no limit, headroom or days remaining from the ties table
    def test_no_limit_from_ties_band(self):
        for bad in ("applicableLimit", "days of room", "headroom", "Days Remaining", "daysRemaining", "maxDays -", "- tiesBand"):
            self.assertNotIn(bad, re.sub(r"//[^\n]*", "", self.html), bad)          # code comments are not shown
        # the ties table appears only as the five table rows plus the one comparison that picks the stage label
        self.assertEqual(len(re.findall(r"maxDays", self.html)), 6)
        self.assertEqual(len(re.findall(r"tiesBand", self.html)), 2)
        self.assertIn("16, 46, 91, 121, 183", self.html)                 # HMRC day bands, reference only
        self.assertIn("— reference only", self.html)
        self.assertIn("HMRC reference: fewer than 31", self.html)       # work days: count + HMRC's figure as reference
        self.assertNotIn("userLimit", json.dumps({k: v for k, v in self.data.items() if k != "userLimit"}))

    # ---- rule 5: your own limit is blank unless the user set it
    def test_user_limit_blank_by_default_and_seeded_from_profile(self):
        self.assertIsNone(self.data["userLimit"])
        h = SD.render(E.DayLog(fixture(user_limit=40)), AS_OF, [], check_links=False)
        self.assertEqual(np_data(h)["userLimit"]["value"], 40)
        for bad in (0, 400, True, "40"):
            self.assertIsNone(np_data(SD.render(E.DayLog(fixture(user_limit=bad)), AS_OF, [], check_links=False))["userLimit"])

    # ---- rule 6: links only to real http(s) documents that open; the rest is plain text saying where it lives
    def test_documentation_links(self):
        docs = {d["title"]: d for d in self.data["docs"]}
        self.assertEqual(docs["Fictional contract"]["link"], "https://example.org/ok")
        self.assertNotIn("link", docs["Fictional dead link"])
        self.assertIn("could not be opened", docs["Fictional dead link"]["where"])
        self.assertEqual(docs["Fictional local file"]["where"], "Stored in your Nomad Pro data folder: documents/x.pdf")
        self.assertEqual(docs["Fictional pointer"]["where"], "Paper copy at home")
        self.assertNotIn("link", docs["Fictional bad scheme"])
        for d in self.data["docs"]:
            self.assertTrue(d.get("link") or d.get("where"), d)
            if "link" in d:
                self.assertRegex(d["link"], r"^https?://")
        self.assertIn("if (d.where)", self.html.replace("${d.where ?", "if (d.where)"))
        self.assertIn("const isUrl = /^https?:\\/\\//.test(d.link || '');", self.html)
        self.assertNotRegex(self.html, r"href=\"#\"|href='#'")

    def test_link_check_off_keeps_https_only(self):
        h = SD.render(self.log, AS_OF, DOCS, check_links=False)
        links = [d.get("link") for d in np_data(h)["docs"] if d.get("link")]
        self.assertIn("https://example.org/dead", links)              # untested, but still a real https link
        self.assertNotIn("file:///srv/fictional/x.pdf", links)

    # ---- rule 7: 2-4 index bullets, no addresses, IDs, amounts or purchase details
    def test_notes_are_short_index_bullets(self):
        rows = self.data["travel"] + self.data["workDays"]
        self.assertTrue(rows)
        for r in rows:
            self.assertTrue(2 <= len(r["bullets"]) <= 4, r["bullets"])
            for b in r["bullets"]:
                self.assertLessEqual(len(b), 120, b)
        blob = json.dumps(rows, ensure_ascii=False)
        for bad in ("R-1234", "EUR", "45.00", "GBP", "coffee", "pastries", "msg-9f8e7d", "Calle", "12,", "Test Avenue", "Fictional Apartments", "Sample Street"):
            self.assertNotIn(bad, blob, bad)
        uk = next(r for r in self.data["travel"] if r["country"] == "United Kingdom")
        self.assertEqual(uk["bullets"][0], "Stay: Leeds (family home)")
        self.assertIn("Flights on record: ZZ101 (1 Aug)", uk["bullets"])
        self.assertEqual(next(r for r in self.data["travel"] if r["country"] == "Georgia")["accom"], "Tbilisi")
        self.assertTrue(uk["notes"].startswith("[INFERRED] "))

    # ---- rule 8: notes boxes, export format, import into the day log
    def test_note_ui_and_export_format(self):
        for s in ("Your note", "Export my notes", "nomad-pro-dashboard-notes", "nomad-pro-notes-${_todayISO()}.json", "localStorage.setItem(NOTES_STORE_KEY"):
            self.assertIn(s, self.html)
        uk = next(r for r in self.data["travel"] if r["start"] == "2025-08-01")
        self.assertEqual(uk["userNote"], "Fictional note")

    def test_import_notes(self):
        with tempfile.TemporaryDirectory() as td:
            dl = Path(td) / "daylog.json"
            dl.write_text(json.dumps(fixture()), encoding="utf-8")
            exp = {"format": "nomad-pro-dashboard-notes", "version": 1, "user_limit": {"value": 45, "updated_at": "2026-09-20T00:00:00Z"},
                   "notes": [{"key": "stay:2025-08-01..2025-08-20", "kind": "stay", "start": "2025-08-01", "end": "2025-08-20", "country": "United Kingdom",
                              "text": "Older edit", "updated_at": "2026-08-01T00:00:00Z"},
                             {"key": "work:2025-08-04..2025-08-04", "kind": "work", "start": "2025-08-04", "end": "2025-08-04", "text": "New work note",
                              "updated_at": "2026-09-20T00:00:00Z"},
                             {"kind": "stay", "start": "not-a-date", "end": "2025-01-01", "text": "ignored"}]}
            ef = Path(td) / "notes.json"
            ef.write_text(json.dumps(exp), encoding="utf-8")
            out = subprocess.run([sys.executable, str(TOOLS / "render_dashboard.py"), str(dl), "--import-notes", str(ef)],
                                 capture_output=True, text=True, check=True).stdout
            self.assertIn("imported 1 note(s); your own limit: set to 45", out)
            log = json.loads(dl.read_text(encoding="utf-8"))
            notes = {n["key"]: n["text"] for n in log["user_notes"]}
            self.assertEqual(notes["stay:2025-08-01..2025-08-20"], "Fictional note")     # the newer note already in the log wins
            self.assertEqual(notes["work:2025-08-04..2025-08-04"], "New work note")
            self.assertEqual(log["profile"]["user_limit"]["value"], 45)
            self.assertTrue(list(Path(td).glob("daylog.backup-*-before-import-notes.json")))
            h = SD.render(E.DayLog(log), AS_OF, [], check_links=False)
            self.assertEqual(np_data(h)["userLimit"]["value"], 45)
            self.assertEqual(next(w for w in np_data(h)["workDays"] if w["date"] == "2025-08-04")["userNote"], "New work note")
            # a cleared limit in the export clears profile.user_limit; a foreign file is refused
            exp.update(user_limit={"value": None, "updated_at": "2026-09-21T00:00:00Z"}, notes=[])
            ef.write_text(json.dumps(exp), encoding="utf-8")
            SD.import_notes(ef, dl)
            self.assertNotIn("user_limit", json.loads(dl.read_text(encoding="utf-8"))["profile"])
            ef.write_text(json.dumps({"format": "something-else", "notes": []}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                SD.import_notes(ef, dl)

    # ---- rule 9: a place the user marks private shows only as "<city> (family home)"
    def test_private_place_never_shown(self):
        for frag in (PRIVATE_LABEL, "parents' house", "9 Sample Street", "LS1 1AA", "Sample Street"):
            self.assertNotIn(frag.lower(), self.html.lower(), frag)
        self.assertIn("Leeds (family home)", self.html)
        ties = self.data["taxYearConfig"]["2025/26"]["tiesNotes"]["accommodation"]
        self.assertIn("Leeds (family home)", ties)
        self.assertTrue(all(w["location"] == "Leeds (family home), UK" for w in self.data["workDays"]))

    def test_private_places_free_text_rule(self):
        data = fixture(private=False)
        data["profile"]["private_places"] = [{"match": "parents' house", "city": "Leeds", "label": "parents' home"}]
        h = SD.render(E.DayLog(data), AS_OF, [], check_links=False)
        self.assertIn("Leeds (parents' home)", h.replace("&#x27;", "'"))
        self.assertNotIn("9 Sample Street", h)

    def test_unmarked_place_is_city_level_only(self):
        h = SD.render(E.DayLog(fixture(private=False)), AS_OF, [], check_links=False)
        uk = next(r for r in np_data(h)["travel"] if r["country"] == "United Kingdom")
        self.assertEqual(uk["accom"], "Leeds")                         # no street or postcode even when not marked private

    # ---- template scrub: the shipped page holds no data of its own
    def test_template_has_no_baked_in_data(self):
        page = SD.TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("const NP = /*@@NP_DATA@@*/{};", page)
        for blk in ("SEED_TRAVEL = NP.travel", "SEED_WORK_DAYS = NP.workDays", "SEED_DOCS = NP.docs", "SEED_TAX_YEAR_CONFIG = NP.taxYearConfig"):
            self.assertIn(blk, page)
        self.assertNotRegex(page, r"\b20\d\d-\d\d-\d\d\b")             # no dates
        self.assertNotRegex(page, r"https?://(?!www\.chartjs|github\.com/chartjs)")  # no links of its own


def _chrome():
    for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if shutil.which(c):
            return shutil.which(c)
    return None


@unittest.skipUnless(_chrome(), "Chrome/Chromium not installed")
class SrtDashboardInBrowser(unittest.TestCase):
    """Every tab rendered by the page's own script (headless Chrome, deep link #tab=...): visible text and tooltips."""

    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.TemporaryDirectory()
        cls.file = Path(cls.td.name) / "dashboard.html"
        cls.file.write_text(SD.render(E.DayLog(fixture()), AS_OF, DOCS, check_links=False), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.td.cleanup()

    def dom(self, tab, ty="2026/27"):
        out = subprocess.run([_chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=4000", "--dump-dom",
                              f"file://{self.file}#tab={tab}&ty={ty}"], capture_output=True, text=True, timeout=90)
        return out.stdout

    def test_every_tab(self):
        for ty in ("2025/26", "2026/27"):
            for tab in ("overview", "uk", "schengen", "timeline", "work", "srt", "docs"):
                with self.subTest(tab=tab, ty=ty):
                    h = self.dom(tab, ty)
                    self.assertIn(f'class="tab active" data-tab="{tab}"', h)
                    sec = h[h.index(f'id="section-{tab}"'):]
                    sec = sec[:sec.index("<footer")]
                    text = re.sub(r"<(style|script)\b.*?</\1>", " ", h[:h.index("<footer")], flags=re.S)
                    text = re.sub(r"<[^>]+?(?:title|aria-label)=\"([^\"]*)\"[^>]*>", r" \1 ", text)
                    text = re.sub(r"<[^>]+>", " ", text)
                    self.assertEqual(offences(text), [])
                    self.assertGreater(len(re.sub(r"<[^>]+>", "", sec).strip()), 50)
                    self.assertNotRegex(text, r"UK days?[^.]{0,40}/\s?(15|45|90|120|182)\b")
                    for href in re.findall(r'href="([^"]*)"', sec):
                        self.assertRegex(href, r"^https?://")
                    self.assertNotIn("Sample Street", h)
                    if tab in ("timeline", "uk", "work"):
                        for cell in re.findall(r'<td class="note">(.*?)</td>', sec, re.S):
                            self.assertTrue(2 <= cell.count("<li>") <= 4, cell[:200])
                            self.assertIn('class="user-note"', cell)

    # ---- per-test marks: shown for a finished tax year, hidden while the selected year is unfinished
    MARKS = (r"\bMET\b|TRIGGERED|REACHED|\bReached\b|SO FAR\b(?<!FIGURES SO FAR)|✓|✗|\bvia\b|Pathway:|Ends at|"
             r"figures? (not )?met|At or above the 183|Below the 183|stage not reached|test figures")

    def visible(self, tab, ty):
        h = self.dom(tab, ty)
        text = re.sub(r"<(style|script)\b.*?</\1>", " ", h[:h.index("<footer")], flags=re.S)
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))

    def test_finished_year_shows_marks(self):
        srt = self.visible("srt", "2025/26")
        for mark in ("NOT MET — CONTINUE", "NONE MET", "STAGE REACHED", "Reached Sufficient Ties", "Day-count figure not met."):
            self.assertIn(mark, srt)
        self.assertNotIn("FIGURES SO FAR", srt)
        self.assertNotIn("Year not finished", srt)
        overview = self.visible("overview", "2025/26")
        self.assertIn("via Sufficient Ties", overview)
        self.assertIn("Pathway:", overview)

    def test_unfinished_year_hides_marks(self):
        for tab in ("overview", "uk", "srt"):
            with self.subTest(tab=tab):
                text = self.visible(tab, "2026/27")
                self.assertIn("Year not finished; figures so far", text)
                self.assertEqual(re.findall(self.MARKS, text), [])
                self.assertEqual(offences(text), [])
        srt = self.visible("srt", "2026/27")
        self.assertIn("FIGURES SO FAR", srt)
        self.assertRegex(srt, r"UK Days / Ties \d+ / \d+ ties")                  # the figures stay


class OpenYearData(unittest.TestCase):
    def test_year_open_flags(self):
        html = SD.render(E.DayLog(fixture()), AS_OF, [], check_links=False)
        self.assertEqual(np_data(html)["yearOpen"], {"2025/26": False, "2026/27": True})
        self.assertIn("const NP_OPEN_NOTE = 'Year not finished; figures so far';", html)


if __name__ == "__main__":
    unittest.main()
