#!/usr/bin/env python3
"""Overflow check for the HTML dashboard (needs Playwright + Chrome/Chromium; optional dev tool).

  python3 dashboard_layout_check.py DASHBOARD.html [--chrome /usr/bin/google-chrome]

Opens every tab x tax year at 1360px (desktop) and 390px (mobile, touch), opens all <details>, and reports any text
that crosses the edge of its card/chip/tile/row, any clipped (scroll) overflow outside the designated horizontal
scrollers (.scroll, .tbl, .trows, tab bar, month bars), SVG text outside its SVG, and page-level horizontal overflow.
Exit 1 on any finding.
"""
import argparse
import sys
from playwright.sync_api import sync_playwright
JS = r"""
() => {
  const SCROLLERS = '.scroll,.tbl,.trows,nav.tabs .in,.mbars';
  const boxes = document.querySelectorAll('.card,.alert,.tie,.chip,.kpi,.trow,.thead,.stat,.limit,.trip,.btn3d,.pointer,.quick,.legend li,.sh,.top,.hero>*,details.month,button.ty,button.tab');
  const out = [];
  const vis = e => e.offsetParent !== null && getComputedStyle(e).visibility !== 'hidden';
  for (const b of boxes) {
    if (!vis(b) || b.closest(SCROLLERS) && !b.matches(SCROLLERS)) { if (!vis(b)) continue; }
    const r = b.getBoundingClientRect();
    if (r.width === 0) continue;
    // text nodes inside the box (skip content inside a designated scroller that sits inside the box)
    const walker = document.createTreeWalker(b, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      if (!n.textContent.trim()) continue;
      const pe = n.parentElement;
      if (!vis(pe)) continue;
      const sc = pe.closest(SCROLLERS);
      if (sc && b.contains(sc) && sc !== b) continue;
      if (pe.closest('svg')) continue;
      const range = document.createRange(); range.selectNodeContents(n);
      for (const q of range.getClientRects()) {
        if (q.width === 0) continue;
        const o = Math.max(q.right - r.right, r.left - q.left, q.bottom - r.bottom, r.top - q.top);
        if (o > 1.5) out.push({box: b.className.baseVal ?? b.className, text: n.textContent.trim().slice(0, 50), over: Math.round(o)});
      }
    }
    if (!b.matches(SCROLLERS) && b.scrollWidth > b.clientWidth + 1 && getComputedStyle(b).overflowX !== 'visible')
      out.push({box: String(b.className), text: '(scroll overflow) ' + b.textContent.trim().slice(0, 40), over: b.scrollWidth - b.clientWidth});
  }
  // svg text outside its svg
  for (const t of document.querySelectorAll('svg text')) {
    const s = t.closest('svg'); if (!vis(s)) continue;
    const a = t.getBoundingClientRect(), r = s.getBoundingClientRect();
    if (a.width && (a.right > r.right + 2 || a.left < r.left - 2)) out.push({box: 'svg', text: t.textContent.slice(0, 40), over: Math.round(Math.max(a.right - r.right, r.left - a.left))});
  }
  // page-level horizontal overflow
  if (document.documentElement.scrollWidth > innerWidth + 1) out.push({box: 'page', text: 'horizontal page overflow', over: document.documentElement.scrollWidth - innerWidth});
  const seen = new Set();
  return out.filter(x => { const k = x.box + x.text; if (seen.has(k)) return false; seen.add(k); return true; });
}
"""
ap = argparse.ArgumentParser(); ap.add_argument("html"); ap.add_argument("--chrome", default=None)
a = ap.parse_args()
html = str(__import__("pathlib").Path(a.html).resolve())
tabs = ["overview", "uk", "schengen", "travel", "work", "ties", "daylog", "records"]
total = 0
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=a.chrome, args=["--no-sandbox"]) if a.chrome else p.chromium.launch()
    for w, h, mob in ((1360, 900, False), (390, 844, True)):
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mob, has_touch=mob, device_scale_factor=1)
        pg = ctx.new_page(); pg.goto(f"file://{html}"); pg.wait_for_timeout(400)
        years = pg.eval_on_selector_all("button.ty", "e => e.map(x => x.dataset.v)")
        for ty in years:
            pg.evaluate(f"sel('ty','{ty}')")
            for t in tabs:
                pg.evaluate(f"sel('tab','{t}')"); pg.wait_for_timeout(60)
                # open every details so hidden content is checked too
                pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
                res = pg.evaluate(JS)
                for r in res:
                    print(w, ty, t, r)
                total += len(res)
        ctx.close()
    b.close()
print("overflows:", total)
sys.exit(1 if total else 0)
