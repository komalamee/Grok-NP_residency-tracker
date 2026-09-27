#!/usr/bin/env python3
"""Mirror HMRC's Statutory Residence Test guidance and detect what changed.

Fetches the official guidance from the gov.uk content API, writes one Markdown
file per page under pages/, and records a hash + HMRC's own "last updated" date
for every page in manifest.json. Re-running diffs against that manifest, so the
question "did HMRC change the rules?" gets a page-level answer instead of a
yes/no.

Nothing here is written by hand or from memory. Every word under pages/ came
from gov.uk on the date in its frontmatter.

    python3 hmrc/refresh.py            # fetch, write, report changes
    python3 hmrc/refresh.py --check    # report only, write nothing
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGES = ROOT / "pages"
MANIFEST = ROOT / "manifest.json"
CHANGES = ROOT / "CHANGES.md"

API = "https://www.gov.uk/api/content"
SITE = "https://www.gov.uk"
UA = "nomad-pro-srt-catalogue/1.0 (record-keeping template)"
DELAY = 0.3  # be polite to gov.uk

# What we mirror. Add a path here to widen the corpus; the crawler recurses
# through any manual contents page on its own.
ROOTS = [
    "/hmrc-internal-manuals/residence-and-fig-regime-manual/rfig20000",  # the SRT itself
    "/government/publications/rdr3-statutory-residence-test-srt",        # the public summary
]


# --------------------------------------------------------------------------
# HTML -> Markdown
# --------------------------------------------------------------------------

BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "tr", "div", "table"}


class ToMarkdown(HTMLParser):
    """Small, deterministic HTML->Markdown converter for gov.uk manual bodies."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str] = []
        self.list_depth = 0
        self.ordered: list[bool] = []
        self.counter: list[int] = []
        self.href: str | None = None
        self.in_cell = False
        self.row: list[str] = []
        self.cell: list[str] = []
        self.header_row = False
        self.wrote_header_rule = False

    # -- helpers
    def emit(self, text: str) -> None:
        if self.in_cell:
            self.cell.append(text)
        else:
            self.out.append(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.stack.append(tag)
        if tag in ("h2", "h3", "h4", "h5", "h6"):
            self.out.append("\n\n" + "#" * min(int(tag[1]) , 6) + " ")
        elif tag == "p":
            self.out.append("\n\n")
        elif tag in ("ul", "ol"):
            self.list_depth += 1
            self.ordered.append(tag == "ol")
            self.counter.append(0)
            self.out.append("\n")
        elif tag == "li":
            indent = "  " * (self.list_depth - 1)
            if self.ordered and self.ordered[-1]:
                self.counter[-1] += 1
                self.out.append(f"\n{indent}{self.counter[-1]}. ")
            else:
                self.out.append(f"\n{indent}- ")
        elif tag == "a":
            self.href = a.get("href")
            self.emit("[")
        elif tag in ("strong", "b"):
            self.emit("**")
        elif tag in ("em", "i"):
            self.emit("*")
        elif tag == "br":
            self.emit("  \n")
        elif tag == "table":
            self.out.append("\n\n")
            self.wrote_header_rule = False
        elif tag == "tr":
            self.row = []
            self.header_row = False
        elif tag in ("td", "th"):
            self.in_cell = True
            self.cell = []
            if tag == "th":
                self.header_row = True

    def handle_endtag(self, tag):
        if self.stack and tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass
        if tag in ("ul", "ol"):
            self.list_depth = max(0, self.list_depth - 1)
            if self.ordered:
                self.ordered.pop()
            if self.counter:
                self.counter.pop()
            self.out.append("\n")
        elif tag == "a":
            text = "]"
            if self.href:
                href = self.href
                if href.startswith("/"):
                    href = SITE + href
                text += f"({href})"
            else:
                text += "()"
            self.emit(text)
            self.href = None
        elif tag in ("strong", "b"):
            self.emit("**")
        elif tag in ("em", "i"):
            self.emit("*")
        elif tag in ("td", "th"):
            self.in_cell = False
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
        elif tag == "tr":
            if self.row:
                self.out.append("\n| " + " | ".join(self.row) + " |")
                if self.header_row and not self.wrote_header_rule:
                    self.out.append("\n| " + " | ".join("---" for _ in self.row) + " |")
                    self.wrote_header_rule = True
            self.row = []
        elif tag == "table":
            self.out.append("\n")

    def handle_data(self, data):
        if not data:
            return
        if self.in_cell:
            self.cell.append(data)
            return
        self.out.append(re.sub(r"[ \t]*\n[ \t]*", " ", data))

    def markdown(self) -> str:
        text = "".join(self.out)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_markdown(html: str) -> str:
    p = ToMarkdown()
    p.feed(html or "")
    p.close()
    return p.markdown()


def plain_text(markdown: str) -> str:
    """Normalised prose used for hashing, so formatting churn is not a change."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", markdown)  # links -> label
    text = re.sub(r"[#*|>`_-]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


# --------------------------------------------------------------------------
# Fetch + crawl
# --------------------------------------------------------------------------

def fetch(base_path: str) -> dict:
    """GET a gov.uk content-API document.

    Uses curl rather than urllib: behind a filtering proxy urllib sees a
    Content-Length that does not match the delivered body and raises
    IncompleteRead on some pages. curl is tolerant of that and gets the
    complete document.
    """
    url = API + base_path
    cmd = [
        "curl", "-sSL", "--fail", "--max-time", "45",
        "--retry", "2", "--retry-delay", "2",
        "-H", f"User-Agent: {UA}",
        "-H", "Accept: application/json",
        "-H", "Accept-Encoding: identity",
        url,
    ]
    for attempt in range(3):
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode == 0:
            try:
                return json.loads(proc.stdout.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                err = f"unparseable response ({exc})"
        else:
            err = proc.stderr.decode("utf-8", "replace").strip() or f"curl exit {proc.returncode}"
        if attempt == 2:
            raise SystemExit(
                f"FAILED to fetch {url}: {err}\nNo data was written. Fix the connection and "
                f"re-run; this script never invents content."
            )
        time.sleep(1.5 * (attempt + 1))
    raise SystemExit("unreachable")


def children(doc: dict) -> list[tuple[str, str]]:
    """Sub-pages to follow: manual contents entries, plus HTML attachments.

    RDR3 is a publication whose landing page carries only a blurb; the actual
    2,300-word guidance note is an HTML attachment with its own base path.
    """
    out = []
    details = doc.get("details", {})
    for group in details.get("child_section_groups") or []:
        for child in group.get("child_sections") or []:
            if child.get("base_path"):
                out.append((child.get("title", "").strip(), child["base_path"]))
    for att in details.get("attachments") or []:
        url = att.get("url") or ""
        if att.get("attachment_type") == "html" and url.startswith("/"):
            out.append((att.get("title", "").strip(), url))
    return out


def body_html(doc: dict) -> str:
    details = doc.get("details", {})
    body = details.get("body")
    if isinstance(body, str):
        return body
    # Publications (RDR3) carry their text in govspeak documents.
    parts = []
    for att in details.get("attachments") or []:
        if isinstance(att.get("body"), str):
            parts.append(att["body"])
    for key in ("documents", "government_documents"):
        for d in details.get(key) or []:
            if isinstance(d, str):
                parts.append(d)
    return "\n".join(parts)


def slug(base_path: str) -> str:
    return base_path.rstrip("/").rsplit("/", 1)[-1]


def crawl() -> dict:
    pages: dict[str, dict] = {}
    order = 0
    seen: set[str] = set()

    def walk(base_path: str, parent: str | None, depth: int) -> None:
        nonlocal order
        if base_path in seen:
            return
        seen.add(base_path)
        doc = fetch(base_path)
        time.sleep(DELAY)
        key = slug(base_path)
        md = html_to_markdown(body_html(doc))
        history = doc.get("details", {}).get("change_history") or []
        if history:
            md += "\n\n## HMRC's own change history for this page\n"
            for h in history:
                when = (h.get("public_timestamp") or "")[:10]
                md += f"\n- **{when}** — {h.get('note', '').strip()}"
        kids = children(doc)
        order += 1
        pages[key] = {
            "title": (doc.get("title") or "").strip(),
            "base_path": base_path,
            "url": SITE + base_path,
            "hmrc_updated": (doc.get("public_updated_at") or "")[:10],
            "parent": parent,
            "depth": depth,
            "order": order,
            "is_contents": bool(kids),
            "words": len(plain_text(md).split()),
            "hash": hashlib.sha256(plain_text(md).encode("utf-8")).hexdigest(),
            "markdown": md,
        }
        sys.stderr.write(f"  {'  ' * depth}{key}  {pages[key]['title'][:64]}\n")
        for _, child_path in kids:
            walk(child_path, key, depth + 1)

    for root in ROOTS:
        sys.stderr.write(f"crawling {root}\n")
        walk(root, None, 0)
    return pages


# --------------------------------------------------------------------------
# Write
# --------------------------------------------------------------------------

def write_pages(pages: dict, today: str) -> None:
    keep = set()
    for key, p in pages.items():
        keep.add(f"{key}.md")
        fm = [
            "---",
            f'title: "{p["title"].replace(chr(34), chr(39))}"',
            f"section: {key.upper()}",
            f"url: {p['url']}",
            f"hmrc_updated: {p['hmrc_updated']}",
            f"fetched: {today}",
            f"words: {p['words']}",
            f"hash: {p['hash']}",
            "---",
            "",
            f"# {p['title']}",
            "",
            p["markdown"] or "_(contents page — no body text)_",
            "",
        ]
        (PAGES / f"{key}.md").write_text("\n".join(fm), encoding="utf-8")
    for stale in PAGES.glob("*.md"):
        if stale.name not in keep:
            stale.unlink()


def write_manifest(pages: dict, today: str) -> None:
    data = {
        "generated_at": today,
        "source": "gov.uk content API",
        "roots": ROOTS,
        "page_count": len(pages),
        "word_count": sum(p["words"] for p in pages.values()),
        "pages": {
            k: {kk: vv for kk, vv in v.items() if kk != "markdown"}
            for k, v in sorted(pages.items(), key=lambda kv: kv[1]["order"])
        },
    }
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def short_title(page: dict, pages: dict) -> str:
    """Trim the boilerplate HMRC repeats in every title.

    "Statutory Residence Test (SRT): The ties test: Work tie" -> "Work tie".
    The catalogue's indentation already shows which chapter a page sits in.
    """
    title = re.sub(r"^\s*Statutory Residence Test \(SRT\)\s*:?\s*", "", page["title"]).strip()
    parent = pages.get(page.get("parent") or "")
    if parent:
        stem = re.sub(r"^\s*Statutory Residence Test \(SRT\)\s*:?\s*", "", parent["title"])
        stem = re.sub(r"\s*:?\s*contents\s*$", "", stem, flags=re.I).strip()
        if stem and title.lower().startswith(stem.lower()):
            trimmed = title[len(stem):].lstrip(" :-").strip()
            if trimmed:
                title = trimmed
    return title or page["title"]


def write_catalogue(pages: dict, today: str) -> None:
    ordered = sorted(pages.values(), key=lambda p: p["order"])
    total_words = sum(p["words"] for p in ordered)
    lines = [
        "# The SRT catalogue — every page of HMRC's Statutory Residence Test guidance",
        "",
        f"**{len(ordered)} pages · {total_words:,} words · mirrored {today} from gov.uk.**",
        "",
        "Generated by `refresh.py`. Do not edit by hand — it is overwritten on every refresh.",
        "Each row links to the local mirror and to the live gov.uk page. `HMRC updated` is",
        "HMRC's own last-changed date for that page, not the date we fetched it.",
        "",
        "| | Page | Words | HMRC updated | Source |",
        "|---|---|---|---|---|",
    ]
    for p in ordered:
        key = p["base_path"].rstrip("/").rsplit("/", 1)[-1]
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * p["depth"]
        title = short_title(p, pages).replace("|", "\\|")
        label = f"**{title}**" if p["is_contents"] else title
        lines.append(
            f"| `{key.upper()}` | {indent}[{label}](pages/{key}.md) | "
            f"{p['words'] or ''} | {p['hmrc_updated']} | [gov.uk]({p['url']}) |"
        )
    lines += ["", "## Roots mirrored", ""]
    lines += [f"- {SITE}{r}" for r in ROOTS]
    lines += [
        "",
        "*Generated file. Page titles, dates and URLs are HMRC's; contains public sector information licensed "
        "under the Open Government Licence v3.0 (see HMRC-NOTICE.md).*",
        "",
    ]
    (ROOT / "catalogue.md").write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# Diff
# --------------------------------------------------------------------------

def load_previous() -> dict:
    if not MANIFEST.exists():
        return {}
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8")).get("pages", {})
    except json.JSONDecodeError:
        return {}


def old_body(key: str) -> str:
    f = PAGES / f"{key}.md"
    if not f.exists():
        return ""
    text = f.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    return parts[2] if len(parts) > 2 else text


def diff_report(previous: dict, pages: dict) -> dict:
    added = [k for k in pages if k not in previous]
    removed = [k for k in previous if k not in pages]
    changed = []
    redated = []
    for k, p in pages.items():
        prev = previous.get(k)
        if not prev:
            continue
        if prev.get("hash") != p["hash"]:
            changed.append(k)
        elif prev.get("hmrc_updated") != p["hmrc_updated"]:
            redated.append(k)
    return {"added": added, "removed": removed, "changed": changed, "redated": redated}


def render_change_log(report: dict, previous: dict, pages: dict, today: str) -> str:
    out = [f"\n## {today}", ""]
    if not any(report.values()):
        out.append("No change. Every mirrored page matches the previous refresh.")
        return "\n".join(out) + "\n"

    def name(k):
        src = pages.get(k) or previous.get(k, {})
        return f"`{k.upper()}` {src.get('title', '')}"

    if report["changed"]:
        out.append(f"### Content changed ({len(report['changed'])})")
        out.append("")
        for k in report["changed"]:
            p = pages[k]
            out.append(f"**{name(k)}**  ")
            out.append(f"HMRC updated {previous[k].get('hmrc_updated')} → {p['hmrc_updated']} · "
                       f"{previous[k].get('words')} → {p['words']} words · [gov.uk]({p['url']})")
            out.append("")
            before = old_body(k).splitlines()
            after = ("\n# " + p["title"] + "\n\n" + p["markdown"]).splitlines()
            delta = [l for l in difflib.unified_diff(before, after, lineterm="", n=1)
                     if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
            if delta:
                out.append("```diff")
                out.extend(delta[:60])
                if len(delta) > 60:
                    out.append(f"... {len(delta) - 60} more changed lines")
                out.append("```")
                out.append("")
    for label, keys in (("Pages added", report["added"]), ("Pages removed", report["removed"])):
        if keys:
            out.append(f"### {label} ({len(keys)})")
            out.append("")
            out.extend(f"- {name(k)}" for k in keys)
            out.append("")
    if report["redated"]:
        out.append(f"### Re-dated by HMRC, text identical ({len(report['redated'])})")
        out.append("")
        out.extend(f"- {name(k)} → {pages[k]['hmrc_updated']}" for k in report["redated"])
        out.append("")
    out.append("> Not tax advice. A change here is a signal to review, not a published "
               "interpretation. Read the page itself before relying on it.")
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report changes without writing the mirror")
    ap.add_argument("--offline", action="store_true",
                    help="rebuild catalogue.md from manifest.json without fetching")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    PAGES.mkdir(parents=True, exist_ok=True)

    previous = load_previous()

    if args.offline:
        if not previous:
            raise SystemExit("No manifest.json to rebuild from. Run a real refresh first.")
        write_catalogue(previous, json.loads(MANIFEST.read_text())["generated_at"])
        print(f"catalogue.md rebuilt from manifest.json ({len(previous)} pages)")
        return 0

    pages = crawl()
    report = diff_report(previous, pages)
    log = render_change_log(report, previous, pages, today)

    if args.check:
        print(log)
        return 1 if any(report.values()) else 0

    if previous:
        header = "" if CHANGES.exists() else (
            "# HMRC SRT guidance — change log\n\n"
            "Appended by `refresh.py`. Newest at the bottom. Every entry is a real diff "
            "between two fetches of gov.uk.\n")
        with CHANGES.open("a", encoding="utf-8") as f:
            if header:
                f.write(header)
            f.write(log)

    write_pages(pages, today)
    write_manifest(pages, today)
    write_catalogue(pages, today)

    print(f"{len(pages)} pages, {sum(p['words'] for p in pages.values()):,} words -> {ROOT}")
    print(log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
