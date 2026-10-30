#!/usr/bin/env python3
"""Grade marktext/midori.css against a RUNNING MarkText, not against the file.

A static read of the stylesheet cannot see which of MarkText's two variable
families a given node actually consumes, and that is the whole difficulty here.
The first version of the theme set every colour correctly and still painted
every heading, the link, the blockquote rule, the list marker and the checkbox
in the LIGHT values while in dark mode, because the kebab-case mirror
(`--h1-color: var(--h1Color)`) was declared only on :root -- var() substitutes
at the declaring element, so the mirror had already frozen to the paper values
before body.dark redefined anything. Twelve of twenty-eight assertions, and not
one of them visible in the file.

    python3 -m venv /tmp/cdpenv && /tmp/cdpenv/bin/pip install websocket-client
    /Applications/MarkText.app/Contents/MacOS/MarkText \
        --user-data-dir=/tmp/mt-sandbox --remote-debugging-port=9333 sample.md &
    /tmp/cdpenv/bin/python tests/check_rendered_marktext.py

ALWAYS PASS --user-data-dir. setupEnvironment() calls app.setPath("userData")
before requestSingleInstanceLock(), so a sandbox directory gets its own lock and
this runs beside your real MarkText without touching its preferences.

AND KILL IT WITH SIGKILL. MarkText does not exit on SIGTERM. A relaunch after a
plain `pkill` loses the single-instance lock and exits silently while the OLD
instance keeps serving the debugging port -- at which point this tool grades the
PREVIOUS stylesheet and says so in green. The byte count of #custom-styles is
printed on every run for exactly that reason; if it has not changed after an
edit, you are looking at a stale window, not a pass.

A PROBE THAT MATCHES NOTHING IS A FAILURE. A selector that never fires is
indistinguishable from one that fired and agreed. Every probe prints how many
elements it matched, zero matches is reported as NO MATCH, and a run with fewer
than MIN_ASSERTIONS live assertions exits non-zero no matter how green the rest
looks.

Open a document with headings, a link, inline code, a blockquote, a list, a task
list and a fenced code block before running -- the sample under
`docs/` or any note with all of those will do.

Not stdlib and not in tests/lint.sh: it imports websocket and needs a live app,
the same split as tests/check_rendered_grid.py.
"""

import json
import sys
import urllib.request

import websocket  # not stdlib; see the module docstring

PORT = 9333
MIN_ASSERTIONS = 20
MIN_BLOCKS = 10

# --------------------------------------------------------------------------
# Expected colours. Copied from obsidian/theme.css (.theme-light / .theme-dark)
# -- these are the values the two apps are meant to share, so a mismatch here
# is either a bug in marktext/midori.css or real drift between the targets.
# --------------------------------------------------------------------------
LIGHT = {
    "editor ground": "#f3f1eb", "sidebar ground": "#edeae2",
    # The tab must equal the bar it sits in, so these three share a value by
    # design -- if "active tab" ever drifts from "header bar", that is the bug.
    "header bar": "#f3f1eb", "active tab": "#f3f1eb", "active tab rule": "#5f6f5e",
    "body text": "#3d3933",
    # All six levels are ONE colour -- the ramp was dropped on purpose, so a
    # per-level expectation here is also the guard against it creeping back.
    "h1": "#2a2825", "h2": "#2a2825", "h3": "#2a2825",
    "h4": "#2a2825", "h5": "#2a2825", "h6": "#2a2825",
    "link": "#3a5572",
    "blockquote rule": "#5f6f5e", "blockquote text": "#524d46",
    "list marker": "#5f6f5e", "checked box": "#5f6f5e",
    "thematic break": "#3c3a36",
    "inline code bg": "#faf9f6", "inline code fg": "#2a2825",
    "code fence bg": "#faf9f6", "code fence fg": "#2a2825",
    "token comment": "#8a8378", "token keyword": "#653f7f",
    "token string": "#6c7d52", "token function": "#3a5572",
    "token number": "#b88a3a", "token boolean": "#b88a3a",
    "token operator": "#7a4a4a", "token punctuation": "#524d46",
    "token property": "#548373",
}
DARK = {
    "editor ground": "#1a1917", "sidebar ground": "#161513",
    "header bar": "#1a1917", "active tab": "#1a1917", "active tab rule": "#9aab97",
    "body text": "#ebe8e2",
    "h1": "#ebe8e2", "h2": "#ebe8e2", "h3": "#ebe8e2",
    "h4": "#ebe8e2", "h5": "#ebe8e2", "h6": "#ebe8e2",
    "link": "#6c87a4",
    "blockquote rule": "#9aab97", "blockquote text": "#9c958a",
    "list marker": "#9aab97", "checked box": "#9aab97",
    "thematic break": "#ebe8e2",
    "inline code bg": "#22211e", "inline code fg": "#ebe8e2",
    "code fence bg": "#22211e", "code fence fg": "#ebe8e2",
    "token comment": "#9c958a", "token keyword": "#a079be",
    "token string": "#9eaf85", "token function": "#8ba3bd",
    "token number": "#d8b06a", "token boolean": "#d8b06a",
    "token operator": "#b8868a", "token punctuation": "#c5bfb4",
    "token property": "#9ebfb4",
}

# Selector, CSS property, optional pseudo-element.
#
# Three of these look wrong and are not. The blockquote rule is NOT a
# border-left -- muya draws it as a 2px ::before, and probing border-left-color
# returns currentColor off a 0px border, which happens to be a plausible grey.
# A link is NOT an <a> -- it is span.mu-inline-rule.mu-link, and the only <a>
# nodes in the document are the code-fence copy buttons. Inline code is
# code.mu-inline-rule, which matches none of Prism's [class*='language-']
# selectors, so it has to be named on its own.
PROBES = [
    ("editor ground",    ".editor-with-tabs",            "backgroundColor", None),
    ("header bar",       ".title-bar-editor-bg",         "backgroundColor", None),
    ("active tab",       ".tabs-container > li.active",  "backgroundColor", None),
    ("active tab rule",  ".tabs-container > li.active",  "backgroundColor", "::after"),
    ("sidebar ground",   ".side-bar",                    "backgroundColor", None),
    ("body text",        ".mu-container p",              "color",           None),
    ("h1",               "h1.mu-atx-heading",            "color",           None),
    ("h2",               "h2.mu-atx-heading",            "color",           None),
    ("h3",               "h3.mu-atx-heading",            "color",           None),
    ("h4",               "h4.mu-atx-heading",            "color",           None),
    ("h5",               "h5.mu-atx-heading",            "color",           None),
    ("h6",               "h6.mu-atx-heading",            "color",           None),
    ("h1 font",          "h1.mu-atx-heading",            "fontFamily",      None),
    ("link",             ".mu-link",                     "color",           None),
    ("blockquote rule",  "blockquote.mu-block-quote",    "backgroundColor", "::before"),
    ("blockquote text",  "blockquote.mu-block-quote",    "color",           None),
    ("list marker",      "li.mu-list-item",              "color",           "::marker"),
    ("checked box",      ".mu-checkbox-checked",         "backgroundColor", "::before"),
    ("thematic break",   ".mu-thematic-break",           "borderTopColor",  "::before"),
    ("inline code bg",   "code.mu-inline-rule",          "backgroundColor", None),
    ("inline code fg",   "code.mu-inline-rule",          "color",           None),
    ("code fence bg",    "pre.mu-code-block",            "backgroundColor", None),
    ("code fence fg",    "pre.mu-code-block code",       "color",           None),
    ("token comment",    "span.token.comment",           "color",           None),
    ("token keyword",    "span.token.keyword",           "color",           None),
    ("token string",     "span.token.string",            "color",           None),
    ("token function",   "span.token.function",          "color",           None),
    ("token number",     "span.token.number",            "color",           None),
    ("token boolean",    "span.token.boolean",           "color",           None),
    ("token operator",   "span.token.operator",          "color",           None),
    ("token punctuation", "span.token.punctuation",      "color",           None),
    ("token property",   "span.token.property",          "color",           None),
]

PROBE_JS = """
(() => {
  const spec = %s;
  const hex = v => {
    const m = String(v).match(/rgba?\\(([^)]+)\\)/);
    if (!m) return String(v);
    const p = m[1].split(',').map(s => parseFloat(s));
    const h = '#' + p.slice(0, 3)
      .map(n => Math.round(n).toString(16).padStart(2, '0')).join('');
    return (p[3] !== undefined && p[3] < 1) ? h + '@' + p[3] : h;
  };
  const out = {};
  for (const [name, sel, prop, pseudo] of spec) {
    const els = [...document.querySelectorAll(sel)];
    out[name] = els.length
      ? { n: els.length, value: hex(getComputedStyle(els[0], pseudo)[prop]) }
      : { n: 0, value: null };
  }
  const custom = document.querySelector('#custom-styles');
  return JSON.stringify({
    dark: document.body.classList.contains('dark'),
    customCssBytes: custom ? custom.innerHTML.length : 0,
    styleOrder: [...document.querySelectorAll('style')].map(s => s.id || '(anon)'),
    probes: out
  });
})()
"""


def _ev(ws, expr, _id=[0]):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == _id[0]:
            res = msg.get("result", {})
            if "exceptionDetails" in res:
                sys.exit("page error: "
                         + json.dumps(res["exceptionDetails"])[:400])
            return res["result"].get("value")


def connect():
    """Enumerate every page target, print them, grade the richest one.

    tests/check_rendered_grid.py learned this the hard way: taking whichever
    target CDP listed first graded a twelve-line note and printed a confident
    all-clear while a second window was 25-of-63 off the lattice. Same shape of
    mistake is available here -- MarkText opens a window per file.
    """
    raw = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json").read()
    pages = [t for t in json.loads(raw) if t.get("type") == "page"]
    if not pages:
        sys.exit("FAIL: no page targets -- is MarkText running with "
                 f"--remote-debugging-port={PORT}?")
    rows = []
    for t in pages:
        ws = websocket.create_connection(t["webSocketDebuggerUrl"],
                                         suppress_origin=True)
        rows.append((_ev(ws, "document.querySelectorAll('h1,h2,h3,p,pre').length"),
                     _ev(ws, "document.title"), ws))
    print(f"  {len(rows)} page target(s):")
    for n, title, _ in rows:
        print(f"    blocks={n:<4} {title!r}")
    rows.sort(key=lambda r: -(r[0] or 0))
    for _, _, ws in rows[1:]:
        ws.close()
    blocks, title, ws = rows[0]
    if not blocks or blocks < MIN_BLOCKS:
        sys.exit(f"FAIL: richest window has {blocks} blocks, need >= "
                 f"{MIN_BLOCKS} -- open a real sample document first")
    print(f"  grading {title!r} ({blocks} blocks)\n")
    return ws


def main():
    ws = connect()
    data = json.loads(_ev(ws, PROBE_JS % json.dumps(
        [[n, s, p, ps] for n, s, p, ps in PROBES])))

    mode = "dark" if data["dark"] else "light"
    want = DARK if data["dark"] else LIGHT
    print(f"mode: {mode}   body.dark={data['dark']}   "
          f"#custom-styles={data['customCssBytes']} bytes")
    print(f"  <style> order: {' -> '.join(data['styleOrder'])}")
    if not data["customCssBytes"]:
        sys.exit("FAIL: #custom-styles is empty -- the stylesheet never "
                 "reached this window")
    if "custom-styles" not in data["styleOrder"] or \
       data["styleOrder"].index("custom-styles") < data["styleOrder"].index("ag-theme"):
        sys.exit("FAIL: #custom-styles is not after #ag-theme -- the override "
                 "order this theme relies on does not hold in this build")

    print(f"\n{'probe':<22} {'n':>4}  {'got':<16} {'want':<10}")
    print("-" * 62)
    bad, empty, checked = [], [], 0
    for name, _, _, _ in PROBES:
        r = data["probes"][name]
        exp, n, got = want.get(name), r["n"], r["value"]
        if n == 0:
            empty.append(name)
            status = "NO MATCH"
        elif exp is None:
            status = "(informational)"
        else:
            checked += 1
            ok = (got or "").lower().split("@")[0] == exp
            status = "ok" if ok else "MISMATCH"
            if not ok:
                bad.append((name, got, exp))
        shown = str(got)[:16]
        print(f"{name:<22} {n:>4}  {shown:<16} {str(exp or '-'):<10} {status}")
    print("-" * 62)
    print(f"{checked} colour assertions checked, {len(bad)} mismatched, "
          f"{len(empty)} selectors matched nothing")
    for name in empty:
        print(f"  NO MATCH {name}")
    for name, got, exp in bad:
        print(f"  MISMATCH {name}: got {got}, want {exp}")

    if checked < MIN_ASSERTIONS:
        sys.exit(f"FAIL: only {checked} assertions ran, need >= "
                 f"{MIN_ASSERTIONS} -- a pass this thin proves nothing")
    if empty:
        sys.exit(f"FAIL: {len(empty)} selector(s) matched nothing")
    if bad:
        sys.exit(f"FAIL: {len(bad)} colour(s) wrong")
    print(f"marktext {mode}: all green")


main()
