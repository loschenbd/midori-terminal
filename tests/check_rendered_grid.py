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


def connect():
    targets = json.load(urllib.request.urlopen("http://localhost:9222/json"))
    page = next((t for t in targets if t.get("type") == "page"), None)
    if page is None:
        sys.exit("no page target; is Obsidian running with --remote-debugging-port=9222?")
    return websocket.create_connection(page["webSocketDebuggerUrl"],
                                       timeout=40, suppress_origin=True)


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
    # Put the app back the way it was found.
    evaluate(ws, "(()=>{const b=document.body;"
                 f"b.style.setProperty('--midori-set-leading', {json.dumps(saved[0])});"
                 f"b.style.setProperty('--font-text-size', {json.dumps(saved[1])});"
                 "if(!b.style.getPropertyValue('--midori-set-leading'))"
                 "b.style.removeProperty('--midori-set-leading');return 1})()")
    print()
    if failures:
        print(f"RENDERED GRID: {failures} of 63 combinations off the lattice")
        sys.exit(1)
    print("RENDERED GRID: all 63 combinations hold — even row, >= 24px, "
          "every line a whole number of rows")


if __name__ == "__main__":
    main()
