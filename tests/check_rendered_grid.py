#!/usr/bin/env python3
"""Sweep the settings across their range and check the grid in the RUNNING app.

A static test reads the stylesheet. It cannot see what the browser laid out,
and this repo has already paid for that: a 16-of-16-green suite sat beside a
Live Preview where 6 of 31 lines were off the row, because the offenders were
CodeMirror's own furniture -- an <img class="cm-widgetBuffer"> with height: 1em
(a REPLACED element, so height applies) and an inline-block fold indicator on
the baseline. A harness that rebuilds the theme's DOM does not rebuild
CodeMirror's.

    open -a Obsidian --args --remote-debugging-port=9222
    python3 -m venv /tmp/cdpenv && /tmp/cdpenv/bin/pip install websocket-client
    /tmp/cdpenv/bin/python tests/check_rendered_grid.py

SUPPRESS THE ORIGIN HEADER. Chromium >= 111 rejects WebSocket clients that send
a non-allowlisted Origin, and websocket-client sends one by default. Omitting
it entirely is allowed, so no relaunch flags are needed.

Open a note with headings, a list, a code block and a footnote reference in
Live Preview before running -- the sweep measures what is on screen, and every
open window is enumerated and printed below so you can see which one got
graded.

ON ITS FIRST LIVE RUN THIS TOOL REPRODUCED THE EXACT FAILURE MODE IT EXISTS TO
CATCH. Obsidian had three windows open; connect() took the first `type: "page"`
target CDP happened to list -- a twelve-line note -- and printed a confident
"all 63 combinations hold." The same sweep against a second window, 31 lines
with headings, a list, code and a footnote, found 25 of 63 off the lattice,
including at the shipped default of 1.5 leading / 16px base. A green driven by
CDP target-list ordering the operator cannot see is worse than no tool, since
this tool's whole reason to exist is that a static check cannot be trusted to
have seen the real page. So connect() now enumerates every open `type: "page"`
target, evaluates each one's title and `.cm-line` count, prints that as a
table, and measures whichever window has the most lines -- the cheapest honest
proxy for "the real note is open here." Fewer than 15 lines is a hard error,
not a quiet pass: a pass earned by an empty or trivial note must be
impossible to produce.

Not stdlib, and deliberately not wired into tests/lint.sh: it imports
websocket (not in the standard library) and needs a running app to talk to,
so it can never be a CI check. This follows the same split as the font
metrics -- stdlib constants for the lint interpreter, a tool with a
dependency for re-deriving them against the real thing.
"""

import json
import sys
import urllib.request

import websocket   # not stdlib; see the module docstring

# A trivial note proves nothing -- see the module docstring for the run
# that measured a clean pass against a twelve-line note. The plan's sample
# note (headings, a list, code, a footnote) measured 31 lines; 15 is a floor
# well below that, not a target.
MIN_LINES = 15


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


def connect():
    targets = json.load(urllib.request.urlopen("http://localhost:9222/json"))
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        sys.exit("no page target; is Obsidian running with --remote-debugging-port=9222?")

    # ENUMERATE EVERY WINDOW, DON'T TRUST THE FIRST ONE. CDP's /json list order
    # is not "the window the operator meant" -- see the module docstring for
    # the run where the first target was a twelve-line note sitting beside a
    # 31-line one with 25 of 63 combinations off the lattice.
    rows = []
    for t in pages:
        ws = websocket.create_connection(t["webSocketDebuggerUrl"],
                                         timeout=40, suppress_origin=True)
        try:
            title = evaluate(ws, "document.title")
            lines = evaluate(ws, "document.querySelectorAll('.cm-line').length")
        finally:
            ws.close()
        rows.append((lines, title, t))

    print(f"{'lines':>5}  title")
    for lines, title, _ in sorted(rows, key=lambda r: -r[0]):
        print(f"{lines:>5}  {title}")
    print()

    lines, title, target = max(rows, key=lambda r: r[0])
    if lines < MIN_LINES:
        sys.exit(f"selected window {title!r} has only {lines} .cm-line elements "
                 f"(< {MIN_LINES}); open a note with headings, a list, a code "
                 "block and a footnote reference in Live Preview before "
                 "running -- an empty or trivial note proves nothing.")
    print(f"measuring: {title!r} ({lines} lines)\n")
    return websocket.create_connection(target["webSocketDebuggerUrl"],
                                       timeout=40, suppress_origin=True)


PROBE = """
(() => {
  const b = document.body;
  b.style.setProperty('--midori-set-leading', '%(lead)s');
  b.style.setProperty('--font-text-size', '%(base)spx');
  // The row is a token stream until a real property consumes it, so read a
  // consumer -- getPropertyValue returns the unresolved round(...) expression.
  const probe = document.createElement('div');
  probe.style.cssText = 'position:absolute;visibility:hidden;line-height:var(--midori-row)';
  b.appendChild(probe);
  const row = parseFloat(getComputedStyle(probe).lineHeight);
  probe.remove();
  const lines = [...document.querySelectorAll('.cm-line')];
  const off = lines.filter(el => {
    const h = el.getBoundingClientRect().height;
    return Math.min(h %% row, row - (h %% row)) > 0.5;
  }).length;
  return {row, lines: lines.length, off};
})()
"""


def main():
    ws = connect()
    saved = evaluate(ws, "(()=>{const b=document.body;return ["
                         "b.style.getPropertyValue('--midori-set-leading'),"
                         "b.style.getPropertyValue('--font-text-size')]})()")
    failures = 0
    print(f"{'lead':>5} {'base':>5} {'row':>5} {'even':>5} {'off-row lines':>14}")
    for lead in ("1.5", "1.6", "1.75"):
        for base in range(10, 31):
            r = evaluate(ws, PROBE % {"lead": lead, "base": base})
            row, off = r["row"], r["off"]
            even = row % 2 == 0
            bad = (not even) or row < 24 or off
            if bad:
                failures += 1
            if bad or base in (10, 16, 30):
                print(f"{lead:>5} {base:>5} {row:>5.0f} {str(even):>5} "
                      f"{off:>14}" + ("   <-- FAIL" if bad else ""))
    # Put the app back the way it was found. setProperty(prop, "") already
    # removes a custom property per the CSSOM spec, so this guard is a no-op
    # on a spec-compliant engine -- kept, and kept symmetric across both
    # properties, as cheap insurance against one that isn't.
    evaluate(ws, "(()=>{const b=document.body;"
                 f"b.style.setProperty('--midori-set-leading', {json.dumps(saved[0])});"
                 f"b.style.setProperty('--font-text-size', {json.dumps(saved[1])});"
                 "if(!b.style.getPropertyValue('--midori-set-leading'))"
                 "b.style.removeProperty('--midori-set-leading');"
                 "if(!b.style.getPropertyValue('--font-text-size'))"
                 "b.style.removeProperty('--font-text-size');"
                 "return 1})()")
    print()
    if failures:
        print(f"RENDERED GRID: {failures} of 63 combinations off the lattice")
        sys.exit(1)
    print("RENDERED GRID: all 63 combinations hold — even row, >= 24px, "
          "every line a whole number of rows")


if __name__ == "__main__":
    main()
