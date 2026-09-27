#!/usr/bin/env python3
"""Banned-phrase and private-data scan for the template kit.

  python3 banned_scan.py KIT_DIR [--private-terms FILE]

1. Banned phrases (SYSTEM.md sections 3-4 + product decisions). The only sanctioned use of "non-resident" is the approved
   template "Your log points to non-resident under the <test>". Text between the markers
   <!-- banned-list:start --> and <!-- banned-list:end --> is the bot's own do-not-say reference list and is skipped,
   as is this file (it has to contain the patterns). A short list of official GOV.UK/HMRC names (OFFICIAL_TERMS, e.g.
   "temporary non-residence", "non-resident landlord", GOV.UK's "Safety and security" section) is exempt because
   those are titles being quoted, not statements about the user. PREFERENCE_TERMS exempts the listing's concierge line
   where "safety" is something the user says matters to them when choosing a place (a preference, never an outcome).
   Files mirrored verbatim from HMRC under hmrc/ (pages/, history/, catalogue.md, manifest.json, CHANGES.md) and the
   HMRC page-title list in HMRC-NOTICE.md are HMRC's own wording and are exempt from the banned-phrase check (they are still scanned for private data).
2. Private-data scan: terms that would only appear if a real user's data leaked into the template
   (names, addresses, employers, calendars, Mac paths). Only generic markers are built in; pass a person's own
   terms with --private-terms FILE (one per line) and keep that file outside the repo.
Exit 1 on any hit.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BANNED = [
    r"\bsafe\b", r"\bsafety\b", r"\bproofs?\b", r"\bproven\b", r"\bcompliant\b", r"\bcompliance\b", r"audit[- ]ready", r"audit[- ]safe",
    r"\bwatertight\b", r"\bprotection\b", r"\bprotects?\b", r"\byou pass\b", r"\bpasses\b", r"\bpass\b", r"\bqualify\b", r"\bqualifies\b",
    r"you are non[- ]resident", r"you're non[- ]resident", r"stay non[- ]resident", r"remain non[- ]resident",
    r"you are (not )?(uk )?resident", r"you're (not )?(uk )?resident", r"will be (non[- ])?resident",
    r"non[- ]residence\b", r"never worry", r"residency summary", r"residence summary", r"dated evidence", r"evidence for every",
    r"evidence pack", r"hmrc[- ]proof", r"\bcertified\b", r"\bguaranteed?\b", r"no surprises", r"year-end surprises",
    r"never accidentally", r"stands or fails", r"all clear", r"tests? failed", r"\bgamified\b", r"life admin support",
    r"183 was never the line", r"hundreds of pages", r"67[34] pages", r"self[- ]assessment deadline", r"january deadline",
    r"31 january", r"[£$]\s?\d", r"\bverdict:", r"\bat risk\b", r"\bdanger\b",
]
NON_RESIDENT_OK = re.compile(r"points to non-resident under the", re.I)
# Official names quoted from GOV.UK / HMRC (scheme, chapter and section titles), never used about the user's position.
# They are removed from a line before matching. Keep this list short and exact.
OFFICIAL_TERMS = re.compile(r"temporary non-residence|non-resident landlords?( scheme)?|capital-gains-tax-for-non-residents|"
                            r"\bsafety and security\b|lgbtqia\+ safety|crime safety", re.I)
# A user's own preference when choosing where to go (kit/LISTING.md concierge sentence). Exact phrase only.
PREFERENCE_TERMS = re.compile(r"what matters to you, whether it's rent, food, safety, crime or getting around", re.I)
# Generic leak markers only. Names, addresses, employers and places tied to a real person are NEVER listed here
# (this file is public): keep them in a private terms file outside the repo and pass it with --private-terms.
PRIVATE_DEFAULT = ["/users/", "~/library", "icloud drive", "macbook", "obsidian", "c:\\users\\"]
# HMRC's own guidance, mirrored verbatim under hmrc/ (pages, history, generated catalogue/manifest/change log), uses
# words such as "qualify" and "non-resident" as HMRC wrote them (HMRC-NOTICE.md lists HMRC's page titles).
# Those files are checked for private data only.
VERBATIM_HMRC = re.compile(r"(^|/)(hmrc/(pages/|history/|catalogue\.md$|manifest\.json$|CHANGES\.md$)|HMRC-NOTICE\.md$)")
EXTS = {".md", ".py", ".json", ".html", ".txt", ".csv", ".ts", ".js", ".yaml", ".yml"}


def scan(root: Path, private_terms: list[str]):
    banned_hits, private_hits = [], []
    me = Path(__file__).resolve()
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix not in EXTS or f.resolve() == me or "__pycache__" in f.parts:
            continue
        skip = False
        verbatim = bool(VERBATIM_HMRC.search(root.resolve().name + "/" + f.relative_to(root).as_posix()))
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "banned-list:start" in line:
                skip = True
            if "banned-list:end" in line:
                skip = False
                continue
            low = line.lower()
            line = OFFICIAL_TERMS.sub("[official term]", line)
            line = PREFERENCE_TERMS.sub("[user preference]", line)
            if f.suffix == ".py":  # the Python keyword, not the word
                line = re.sub(r"(^\s*|:\s*)pass\s*(#.*)?$", r"\1", line)
            for t in private_terms:
                # word boundaries only where the term starts/ends with a letter or digit ("/users/" must match "/users/x")
                pat = ((r"(?<![a-z0-9])" if t[:1].isalnum() else "") + re.escape(t) + (r"(?![a-z0-9])" if t[-1:].isalnum() else ""))
                if re.search(pat, low):
                    private_hits.append((str(f.relative_to(root)), n, t, line.strip()[:140]))
            if skip or verbatim:
                continue
            for pat in BANNED:
                for m in re.finditer(pat, line, re.I):
                    banned_hits.append((str(f.relative_to(root)), n, m.group(0), line.strip()[:140]))
            for m in re.finditer(r"non[- ]resident", line, re.I):
                ctx = line[max(0, m.start() - 12): m.end() + 10]
                if not NON_RESIDENT_OK.search(ctx):
                    banned_hits.append((str(f.relative_to(root)), n, "non-resident (outside approved template)", line.strip()[:140]))
    return banned_hits, private_hits


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("kit")
    ap.add_argument("--private-terms")
    a = ap.parse_args(argv)
    terms = list(PRIVATE_DEFAULT)
    if a.private_terms:
        terms += [t.strip().lower() for t in Path(a.private_terms).read_text().splitlines() if t.strip()]
    b, p = scan(Path(a.kit), terms)
    print(f"Banned-phrase hits: {len(b)}")
    for h in b:
        print("  {}:{}  [{}]  {}".format(*h))
    print(f"Private-data hits: {len(p)}")
    for h in p:
        print("  {}:{}  [{}]  {}".format(*h))
    return 1 if (b or p) else 0


if __name__ == "__main__":
    sys.exit(main())
