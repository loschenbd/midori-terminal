#!/usr/bin/env python3
"""Measure Live Preview heading box heights PER LEVEL against the grid row.

WHY THIS EXISTS SEPARATELY FROM check_rendered_grid.py. That sweep counts
`.cm-line` boxes whose height is not a multiple of the row and reports a
number. It never says WHICH element is off, and for a year the answer was
carried by a hand-read of one h1 plus a mechanism nobody re-derived: the
record said the h1's glyph box overflowed the strut by 1px and that only a
two-row h1 could fix it. Every part of that was wrong. It was 1.5px; headings
are Spectral, whose ascent+descent+lineGap ratio is 1.5220 across hhea, OS/2
typo and OS/2 win alike (a 45.5px glyph box at 29.92px, not 26px); and the
real cause was `img.cm-widgetBuffer` anchoring to the font content area via
`vertical-align: text-top`, which costs nothing to fix.

A count told us something was wrong. Only a per-level measurement told us
what, and the difference was a year of believing the fix was expensive.

Run with Obsidian started as:
    open -a Obsidian --args --remote-debugging-port=9222
and a note carrying h1/h2/h3 open in Live Preview. Not wired into lint: it
needs a live app and the non-stdlib `websocket` module.
"""
import json
import sys
import urllib.request

import websocket


def evaluate(ws, expr, _id=[0]):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == _id[0]:
            res = msg.get("result", {})
            if "exceptionDetails" in res:
                sys.exit(f"page error: {res['exceptionDetails'].get('text')}")
            return res["result"].get("value")


PROBE = r"""
(() => {
  const p = document.createElement('div');
  p.style.cssText = 'position:absolute;visibility:hidden;line-height:var(--midori-row)';
  document.body.appendChild(p);
  const row = parseFloat(getComputedStyle(p).lineHeight);
  p.remove();
  const out = {row, levels: {}, total: document.querySelectorAll('.cm-line').length};
  for (let n = 1; n <= 6; n++) {
    const els = [...document.querySelectorAll('.cm-line.HyperMD-header-' + n)];
    if (!els.length) continue;
    out.levels[n] = els.map(el => {
      const cs = getComputedStyle(el), h = el.getBoundingClientRect().height;
      return {h: +h.toFixed(2),
              off: +Math.min(h % row, row - (h % row)).toFixed(2),
              fs: cs.fontSize,
              text: (el.textContent || '').slice(0, 30)};
    });
  }
  return out;
})()
"""


def pick_window():
    """The window with the most heading lines, chosen by CONTENT not title.

    SELECTING THE WRONG WINDOW IS HOW THIS FAMILY OF SCRIPT LIES. The grid
    sweep once graded a twelve-line note and printed a confident all-clear
    while another window had 25 of 63 combinations off. Titles also shift with
    focus, so they are not a stable key either.

    RANK BY h1 FIRST, NOT BY HEADING COUNT -- and this script shipped the bug
    it was written to warn about. h1 is the only level that has ever left the
    row, so a window without one cannot show the defect at all. CodeMirror
    VIRTUALIZES: only rendered lines exist in the DOM, so a note that contains
    an h1 does not have one once it scrolls past. A 31-line note with eight
    headings and no rendered h1 outranked a window whose h1 was sitting at
    49.5px, and this script duly printed "every heading level present sits on
    the row" against a live, sabotaged page. "Present" was doing load-bearing
    work in that sentence, so it now refuses instead.
    """
    targets = [t for t in json.load(urllib.request.urlopen("http://localhost:9222/json"))
               if t.get("type") == "page"]
    if not targets:
        sys.exit("no page target; is Obsidian running with "
                 "--remote-debugging-port=9222?")
    rows = []
    for t in targets:
        ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=40,
                                         suppress_origin=True)
        try:
            title = evaluate(ws, "document.title")
            n = evaluate(ws, "document.querySelectorAll("
                             "'.cm-line[class*=\"HyperMD-header-\"]').length")
            h1 = evaluate(ws, "document.querySelectorAll("
                              "'.cm-line.HyperMD-header-1').length")
        finally:
            ws.close()
        rows.append((h1, n, title, t))

    print(f"{'h1':>4} {'hdrs':>5}  title")
    for h1, n, title, _ in sorted(rows, key=lambda r: (-r[0], -r[1])):
        print(f"{h1:>4} {n:>5}  {title}")
    print()

    h1, n, title, target = max(rows, key=lambda r: (r[0], r[1]))
    if not h1:
        sys.exit("no window has a RENDERED h1 -- open a note with an h1 in "
                 "Live Preview and scroll so the h1 is on screen (CodeMirror "
                 "only keeps visible lines in the DOM). h1 is the only level "
                 "that has ever left the row, so measuring without one proves "
                 "nothing and would print a clean sheet.")
    print(f"measuring: {title!r} ({h1} h1, {n} heading lines)\n")
    return websocket.create_connection(target["webSocketDebuggerUrl"],
                                       timeout=40, suppress_origin=True)


def main():
    ws = pick_window()
    d = evaluate(ws, PROBE)
    ws.close()
    row = d["row"]
    print(f"row = {row}px   ({d['total']} .cm-line total)\n")
    print(f"{'lvl':>3} {'height':>8} {'off-row':>8} {'font':>10}  text")
    worst = 0.0
    for lvl, els in sorted(d["levels"].items()):
        for e in els:
            flag = "   <-- OFF" if e["off"] > 0.5 else ""
            worst = max(worst, e["off"])
            print(f"{lvl:>3} {e['h']:>8} {e['off']:>8} {e['fs']:>10}  "
                  f"{e['text']!r}{flag}")
    print()
    if worst > 0.5:
        sys.exit(f"FAIL: worst heading is {worst}px off the {row}px row")
    print(f"ok: every heading level present sits on the {row}px row")


if __name__ == "__main__":
    main()
