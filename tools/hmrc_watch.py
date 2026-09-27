#!/usr/bin/env python3
"""Weekly HMRC guidance watch: compare every page in the knowledge-base mirror with live gov.uk.

  python3 hmrc_watch.py [--kb PATH/TO/hmrc] [--write] [--report OUT.json] [--limit N]

--kb defaults to $NOMAD_PRO_KB, else the engine's own mirror (<engine>/hmrc). A pages/ folder is also accepted.

For each page in the mirror (pages/*.md with frontmatter url + hmrc_updated), fetch the gov.uk content API,
compare HMRC's public_updated_at date and the page text (normalised words, so formatting churn is ignored).
Without --write nothing is changed (check mode). With --write, changed pages are rewritten in the mirror,
the old text is kept under history/<page>/<old-date>.md and a dated entry is appended to CHANGES.md.
Exit code 1 if any page's text changed. Quiet summary when nothing changed.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://www.gov.uk/api/content"
UA = "nomad-pro-hmrc-watch/1.0 (record-keeping template)"


def frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, m.group(2)


def number_ordered_lists(body: str) -> str:
    """Give <ol> items explicit numbers, as the mirror's Markdown does ("1. ")."""
    def repl(m):
        n = [0]
        def li(_):
            n[0] += 1
            return f"<li>{n[0]}. "
        return re.sub(r"<li[^>]*>", li, m.group(0))
    return re.sub(r"<ol[^>]*>.*?</ol>", repl, body, flags=re.S)


def strip_mirror_extras(md: str) -> str:
    md = re.sub(r"_\(contents page[^)]*\)_", " ", md)
    return md.split("## HMRC's own change history for this page")[0]


def words(text: str) -> list[str]:
    """Normalised word tokens: links reduced to their text, tags and punctuation dropped, lower case."""
    # Block-level tags break words; inline tags (span, abbr, strong, a, em) do not:
    # gov.uk sometimes wraps part of a word, e.g. "i</span>f".
    text = re.sub(r"</?(p|h\d|li|ol|ul|tr|td|th|table|div|br|blockquote|pre)\b[^>]*>", " ", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("****", "")  # empty bold run left by the mirror's converter, e.g. "not****e"
    return re.findall(r"[a-z0-9£%]+", text.lower().replace("\u2019", "'"))


def live_body(d: dict) -> str:
    det = d.get("details") or {}
    if det.get("body"):
        return det["body"]
    docs = det.get("documents") or []
    return " ".join(x for x in docs if isinstance(x, str))


def html_to_text(body: str) -> str:
    body = re.sub(r"</(p|h\d|li|tr|div)>", "\n", body)
    body = re.sub(r"<br\s*/?>", "\n", body)
    t = html.unescape(re.sub(r"<[^>]+>", "", body))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def fetch(url: str) -> dict:
    path = url.replace("https://www.gov.uk", "")
    req = urllib.request.Request(API + path, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", help="mirror root (contains pages/); default: $NOMAD_PRO_KB, else <engine>/hmrc")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--report")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--delay", type=float, default=0.25)
    a = ap.parse_args(argv)
    import os
    root = Path(a.kb or os.environ.get("NOMAD_PRO_KB") or Path(__file__).resolve().parent.parent / "hmrc").expanduser()
    if root.name == "pages" and not (root / "pages").is_dir():
        root = root.parent
    pages = sorted((root / "pages").glob("*.md"))[: a.limit]
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    results = []
    for f in pages:
        meta, body = frontmatter(f.read_text(encoding="utf-8"))
        url = meta.get("url")
        if not url:
            continue
        item = {"page": f.stem, "section": meta.get("section", f.stem.upper()), "url": url, "mirror_updated": meta.get("hmrc_updated")}
        try:
            d = fetch(url)
        except Exception as e:  # network or 404: report, never guess
            item.update(status="fetch_error", error=str(e))
            results.append(item)
            continue
        live_date = (d.get("public_updated_at") or "")[:10]
        lb = number_ordered_lists(live_body(d))
        lw, mw = words(lb), words(strip_mirror_extras(body))
        # the mirror body starts with an H1 title; ignore leading title words not in live body
        title_words = words(d.get("title", ""))
        if mw[: len(title_words)] == title_words:
            mw = mw[len(title_words):]
        same_text = lw == mw
        item.update(live_updated=live_date, date_changed=live_date != item["mirror_updated"], text_changed=not same_text)
        if not same_text:
            sm = difflib.SequenceMatcher(a=mw, b=lw, autojunk=False)
            ops = [(tag, " ".join(mw[i1:i2])[:200], " ".join(lw[j1:j2])[:200]) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]
            item["diff"] = ops[:12]
            item["similarity"] = round(sm.ratio(), 4)
        item["status"] = "text_changed" if not same_text else ("date_only" if item["date_changed"] else "unchanged")
        if a.write and item["status"] != "unchanged":
            hist = root / "history" / f.stem
            hist.mkdir(parents=True, exist_ok=True)
            (hist / f"{item['mirror_updated']}.md").write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
            new_body = html_to_text(lb)
            new_meta = dict(meta, hmrc_updated=live_date, fetched=now[:10], hash=hashlib.sha256(new_body.encode()).hexdigest())
            fm = "\n".join(f"{k}: {v}" for k, v in new_meta.items())
            f.write_text(f"---\n{fm}\n---\n\n# {d.get('title', '')}\n\n{new_body}\n", encoding="utf-8")
        results.append(item)
        time.sleep(a.delay)
    changed = [r for r in results if r["status"] == "text_changed"]
    dated = [r for r in results if r["status"] == "date_only"]
    errors = [r for r in results if r["status"] == "fetch_error"]
    summary = {"checked_at": now, "pages_checked": len(results), "text_changed": len(changed), "date_only": len(dated),
               "unchanged": len(results) - len(changed) - len(dated) - len(errors), "fetch_errors": len(errors), "results": results}
    if a.write and (changed or dated):
        with open(root / "CHANGES.md", "a", encoding="utf-8") as fh:
            fh.write(f"\n## {now[:10]} (hmrc_watch)\n")
            for r in changed + dated:
                fh.write(f"- {r['section']}: {r['status']} (mirror {r['mirror_updated']} -> live {r.get('live_updated')})\n")
    if a.report:
        Path(a.report).write_text(json.dumps(summary, indent=1), encoding="utf-8")
    if not changed and not dated and not errors:
        print(f"HMRC watch {now[:10]}: {len(results)} pages checked, nothing changed.")
    else:
        print(f"HMRC watch {now[:10]}: {len(results)} checked; text changed: {len(changed)}; HMRC date changed only: {len(dated)}; fetch errors: {len(errors)}")
        for r in changed:
            print(f"  TEXT  {r['section']} ({r['mirror_updated']} -> {r['live_updated']}), similarity {r.get('similarity')}")
        for r in dated:
            print(f"  DATE  {r['section']} ({r['mirror_updated']} -> {r['live_updated']}), wording unchanged")
        for r in errors:
            print(f"  ERROR {r['section']}: {r['error']}")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
