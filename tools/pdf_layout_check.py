#!/usr/bin/env python3
"""Overflow check for the WeasyPrint export: every text/inline/replaced box must stay inside the content box of the
block that contains it (and every block inside its parent block's padding box), and nothing may spill past the page.

  python3 pdf_layout_check.py DAYLOG.json --tax-year 2026/27 [--as-of YYYY-MM-DD] [--data-root DIR]

Library use: overflows(html) -> list of dicts (page, kind, text, overflow_px). Tolerance 0.75 px.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

TOL = 0.75


def _text(box, n=60):
    out = []

    def walk(b):
        if hasattr(b, "text") and b.text:
            out.append(b.text)
        for c in getattr(b, "children", []) or []:
            walk(c)
    walk(box)
    return " ".join(out)[:n]


def overflows(html: str, base_url=None) -> list[dict]:
    from weasyprint import HTML
    from weasyprint.formatting_structure import boxes as B
    doc = HTML(string=html, base_url=base_url).render()
    found = []
    for pn, page in enumerate(doc.pages, 1):
        root = page._page_box
        pl, pr = root.content_box_x(), root.content_box_x() + root.width

        def walk(box, block):
            if str(getattr(box, "element_tag", "")).endswith("::marker"):
                return
            is_block = isinstance(box, (B.BlockBox, B.TableCellBox, B.FlexBox, B.InlineBlockBox)) and not isinstance(box, B.PageBox)
            if block is not None and isinstance(box, (B.TextBox, B.InlineReplacedBox, B.BlockReplacedBox, B.InlineBlockBox)) and box is not block:
                left = block.content_box_x()
                right = left + block.width
                bx0 = box.position_x
                bx1 = box.position_x + box.margin_width()
                over = max(bx1 - right, left - bx0)
                if not isinstance(block, B.TableCellBox) or True:
                    ptop = block.padding_box_y()
                    pbot = ptop + block.padding_height()
                    by0, by1 = box.position_y, box.position_y + box.margin_height()
                    vover = max(by1 - pbot, ptop - by0) if block.height != "auto" else 0
                    if vover > TOL and not getattr(block, "is_table_wrapper", False):
                        found.append({"page": pn, "kind": type(box).__name__ + " (vertical)", "in": getattr(block, "element_tag", "?") + "." + (block.element.get("class", "") if getattr(block, "element", None) is not None else ""),
                                      "text": (box.text if isinstance(box, B.TextBox) else _text(box)) or getattr(box, "element_tag", ""), "overflow_px": round(vover, 1)})
                if over > TOL:
                    found.append({"page": pn, "kind": type(box).__name__, "in": getattr(block, "element_tag", "?") + "." + (block.element.get("class", "") if getattr(block, "element", None) is not None else ""),
                                  "text": ((box.text if isinstance(box, B.TextBox) else _text(box)) or getattr(box, "element_tag", "")) + f" [box {box.margin_width():.0f}px in {block.width:.0f}px]", "overflow_px": round(over, 1)})
            if is_block and block is not None and box is not block and not isinstance(box, (B.TableCellBox,)):
                pleft = block.padding_box_x() if hasattr(block, "padding_box_x") else block.content_box_x()
                pright = pleft + block.padding_width()
                over = max(box.position_x + box.margin_width() - pright, pleft - box.position_x)
                if block.style["height"] != "auto":
                    vb = max(box.position_y + box.margin_height() - (block.padding_box_y() + block.padding_height()), 0)
                    if vb > TOL:
                        found.append({"page": pn, "kind": "block (vertical)", "in": getattr(block, "element_tag", "?"), "text": _text(box), "overflow_px": round(vb, 1)})
                if over > TOL and box.width > 0:
                    found.append({"page": pn, "kind": "block", "in": getattr(block, "element_tag", "?"), "text": _text(box), "overflow_px": round(over, 1)})
            if isinstance(box, (B.TextBox, B.InlineReplacedBox, B.BlockReplacedBox)):
                if box.position_x + box.margin_width() > pr + TOL:
                    found.append({"page": pn, "kind": "page", "in": "page", "text": getattr(box, "text", "") or "", "overflow_px": round(box.position_x + box.margin_width() - pr, 1)})
            nb = box if is_block else block
            for c in getattr(box, "children", []) or []:
                walk(c, nb)
        walk(root, None)
    return found


def svg_text_overflows(html: str) -> list[dict]:
    """Static SVG text is outside the CSS box tree: estimate each label's extent (Inter, ~0.58em per character,
    0.62em bold) and flag any that leave the viewBox, or that cross into the bar track of a timeline row."""
    import re
    found = []
    for n, m in enumerate(re.finditer(r"<svg\b([^>]*)>(.*?)</svg>", html, re.S)):
        head, body = m.group(1), m.group(2)
        vb = re.search(r"viewBox='0 0 ([\d.]+) ([\d.]+)'", head)
        if not vb:
            continue
        W = float(vb.group(1))
        timeline_row = "height='" not in head and float(vb.group(2)) == 34 and W == 700
        for t in re.finditer(r"<text\b([^>]*)>([^<]*)</text>", body):
            attrs, txt = t.group(1), t.group(2).replace("&amp;", "&").replace("&#x27;", "'")
            if not txt.strip():
                continue
            g = lambda k, d=None: (re.search(rf"\b{k}='([^']*)'", attrs) or [None, d])[1]
            try:
                x = float(g("x", 0) or 0)
            except ValueError:
                continue  # percentage x (centred donut labels)
            fs = float(g("font-size", 12) or 12)
            w = len(txt) * fs * (0.62 if (g("font-weight") or "400") in ("700", "800") else 0.58)
            anchor = g("text-anchor", "start")
            x0 = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
            x1 = x0 + w
            limit = 296 if (timeline_row and x < 100) else W + 1
            if x0 < -1 or x1 > limit:
                found.append({"svg": n, "text": txt, "x0": round(x0), "x1": round(x1), "limit": limit})
    return found


def main(argv=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import srt_engine as E
    import render_pdf as RP
    from render_common import file_prefix
    ap = argparse.ArgumentParser()
    ap.add_argument("daylog"); ap.add_argument("--tax-year", required=True)
    ap.add_argument("--as-of", default=date.today().isoformat()); ap.add_argument("--data-root"); ap.add_argument("--kb", help="HMRC mirror (root or pages/ dir); default: $NOMAD_PRO_KB, else <engine>/hmrc")
    a = ap.parse_args(argv)
    E.load_hmrc_dates(E.default_kb(a.kb))
    log = E.DayLog.load(a.daylog)
    html, _ = RP.build_html(log, a.tax_year, E.parse_date(a.as_of), file_prefix(a.data_root, ".") if a.data_root else "")
    f = overflows(html)
    for x in f:
        print(f"p{x['page']:>3} {x['kind']:<18} +{x['overflow_px']:>6}px in {x['in']:<24} {x['text']!r}")
    g = svg_text_overflows(html)
    for x in g:
        print(f"svg#{x['svg']} {x['text']!r} spans {x['x0']}..{x['x1']} (limit {x['limit']})")
    print(f"overflows: {len(f)}  svg text overflows: {len(g)}")
    return 1 if (f or g) else 0


if __name__ == "__main__":
    sys.exit(main())
