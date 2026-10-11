#!/usr/bin/env python3
"""Grade a RUNNING SilverBullet against silverbullet/midori.css, in both modes.

Deliberately not in tests/lint.sh: it needs a live server, a live browser and
the theme actually installed. See silverbullet/README.md for the harness setup
(it is four commands) and tests/check_rendered_marktext.py for the sibling that
does the same job for MarkText.

WHAT THIS REFUSES TO DO, because each one has already produced a confident
all-clear in this repo against nothing at all:

  - grade a window it did not open. Every page target is closed before one is
    created, because a server restart leaves the previous client running and
    still answering CDP. Graded stale, this checker reported "custom-styles:
    58 bytes, no midori token" for a theme that was in fact installed and
    working -- a false NEGATIVE that run, but the same mechanism yields a false
    positive the moment the stale client is the one with the old stylesheet.
  - grade a short viewport. CodeMirror builds DOM only for lines in view. At
    the headless default 800x600 this page renders 26 of its 91 lines, so every
    probe into a fenced code block finds nothing and a checker that treats
    "no match" as "nothing to check" passes while measuring no code at all.
    The viewport is forced to 1440x4200 and the line count is printed.
  - pass on a selector that matched nothing. A zero-match probe is a FAILURE
    here, not a skip, and the count for every probe is printed.
  - pass on too few assertions. MIN_ASSERTIONS guards against a run where most
    probes silently dropped out.
  - trust that the theme is installed. #custom-styles must be non-empty AND
    contain a --midori- token, and its byte count is printed every run so a
    truncated install (see the triple-backtick note in midori.css) is visible
    rather than inferred.

Usage:  python3 tests/check_rendered_silverbullet.py [URL] [--cdp PORT]
Needs:  websocket-client.  Exit 0 only if every assertion in both modes held.
"""
import importlib.util
import json
import pathlib
import re
import sys
import time
import urllib.request

import websocket

CDP_PORT = 9333
URL = "http://127.0.0.1:3099/"

# A run that makes fewer than this many live assertions has lost probes
# somewhere and is not evidence, whatever it prints.
MIN_ASSERTIONS = 52
# Fewer rendered lines than this means the sample page is not open, or the
# viewport override did not take.
MIN_LINES = 60

# ---------------------------------------------------------------------------
# The palette, as rendered sRGB. Taken from palette.json under the names the
# values carry in obsidian/theme.css; nothing is invented here.
# ---------------------------------------------------------------------------
PALETTE = {
    "light": {
        "ink": (42, 40, 37), "text": (61, 57, 51), "muted": (82, 77, 70),
        "faint": (138, 132, 123), "paper": (243, 241, 235),
        "card": (250, 249, 246), "secondary": (237, 234, 226),
        "sage": (95, 111, 94), "indigo": (58, 85, 114), "olive": (108, 125, 82),
        "wine": (122, 74, 74), "ochre": (184, 138, 58), "purple": (101, 63, 127),
        "mint": (84, 131, 115), "clay": (201, 145, 107), "mythic": (107, 95, 82),
        "code_comment": (138, 131, 120), "code_punct": (82, 77, 70),
    },
    "dark": {
        "ink": (235, 232, 226), "text": (235, 232, 226), "muted": (156, 149, 138),
        "faint": (110, 104, 95), "paper": (26, 25, 23),
        "card": (34, 33, 30), "secondary": (22, 21, 19),
        "sage": (154, 171, 151), "indigo": (139, 163, 189), "olive": (158, 175, 133),
        "wine": (184, 134, 138), "ochre": (216, 176, 106), "purple": (160, 121, 190),
        "mint": (158, 191, 180), "clay": (212, 160, 122), "mythic": (196, 184, 168),
        "code_comment": (156, 149, 138), "code_punct": (197, 191, 180),
    },
}

# ---------------------------------------------------------------------------
# PROBES: (name, selector, css property, expected role or literal check)
#
# The selectors are the non-obvious half of this file. SilverBullet's live
# preview does not emit the element you would guess from the markdown:
#
#   thing              what you reach for      what is actually there
#   ------------------ ----------------------- ----------------------------
#   page ground        body                    #sb-root (html paints the TOP
#                                              BAR colour, not the page)
#   a heading          h1                      .cm-line.sb-line-h1 -- a LINE,
#                                              and the colour is on the line
#   inline code        code                    span.sb-code, but .sb-code also
#                                              appears INSIDE fenced blocks
#                                              where it is forced transparent,
#                                              so the probe must exclude
#                                              .sb-line-fenced-code
#   blockquote bar     border-left             a repeating-linear-gradient in
#                                              background-image; there is no
#                                              border at all
#   list bullet        ::marker                span.cm-list-bullet
#   a wiki link        a[href]                 .sb-wiki-link, and a BROKEN one
#                                              is .sb-wiki-link-missing, which
#                                              is a different colour on purpose
#   syntax marks       no element              span.sb-meta, 30 of them
# ---------------------------------------------------------------------------
PROBES = [
    # grounds and chrome
    ("outer ground", "html", "backgroundColor", "secondary"),
    ("page ground", "#sb-root", "backgroundColor", "paper"),
    ("body text", "#sb-root", "color", "text"),
    ("top bar bg", "#sb-top", "backgroundColor", "secondary"),
    ("top bar text", "#sb-top", "color", "muted"),
    # headings: all six levels are one colour by construction in SilverBullet
    ("h1", "#sb-editor .cm-line.sb-line-h1", "color", "ink"),
    ("h2", "#sb-editor .cm-line.sb-line-h2", "color", "ink"),
    ("h3", "#sb-editor .cm-line.sb-line-h3", "color", "ink"),
    ("h4", "#sb-editor .cm-line.sb-line-h4", "color", "ink"),
    # type
    ("h1 font", "#sb-editor .cm-line.sb-line-h1", "fontFamily", "@Spectral"),
    ("body font", "#sb-editor .cm-content", "fontFamily", "@M PLUS 1p"),
    ("ui font", "#sb-top .main #sb-current-page .sb-input", "fontFamily", "@Spectral"),
    ("fenced font", "#sb-editor .cm-line.sb-line-fenced-code", "fontFamily", "@M PLUS 1 Code"),
    ("inline code font", "#sb-editor .cm-line:not(.sb-line-fenced-code):not(.sb-line-code) .sb-code", "fontFamily", "@M PLUS 1 Code"),
    # code grounds and tokens
    ("fenced bg", "#sb-editor .cm-line.sb-line-fenced-code", "backgroundColor", "card"),
    ("inline code bg", "#sb-editor .cm-line:not(.sb-line-fenced-code):not(.sb-line-code) .sb-code", "backgroundColor", "card"),
    ("comment tok", "#sb-editor .sb-line-fenced-code .sb-comment", "color", "code_comment"),
    ("string tok", "#sb-editor .sb-string", "color", "olive"),
    ("number tok", "#sb-editor .sb-number", "color", "ochre"),
    ("variable tok", "#sb-editor .sb-variableName", "color", "indigo"),
    ("operator tok", "#sb-editor .sb-operator", "color", "wine"),
    ("atom tok", "#sb-editor .sb-atom", "color", "purple"),
    ("keyword tok", "#sb-editor .sb-keyword", "color", "purple"),
    ("punct tok", "#sb-editor .sb-punctuation", "color", "code_punct"),
    # references
    ("link", "#sb-editor .sb-link:not(.sb-meta)", "color", "indigo"),
    ("naked url", "#sb-editor .sb-naked-url", "color", "indigo"),
    ("at-mention", "#sb-editor .sb-at-mention", "color", "indigo"),
    ("wiki link", "#sb-editor .sb-wiki-link:not(.sb-wiki-link-missing)", "color", "indigo"),
    ("wiki missing", "#sb-editor .sb-wiki-link-missing", "color", "clay"),
    ("hashtag", "#sb-editor .sb-hashtag", "color", "sage"),
    # structure
    ("list bullet", "#sb-editor .cm-list-bullet", "color", "sage"),
    ("blockquote bar", "#sb-editor .sb-line-blockquote", "backgroundImage", "~sage"),
    ("syntax marks", "#sb-editor .sb-meta", "color", "sage"),
    ("checkbox accent", "#sb-editor .sb-checkbox", "accentColor", "sage"),
    ("caret", "#sb-editor .cm-cursor", "borderLeftColor", "ink"),
    ("table head bg", "#sb-editor thead tr", "backgroundColor", "secondary"),
    ("table head fg", "#sb-editor thead tr", "color", "ink"),
    # admonitions: the four colours SilverBullet keeps outside its token set
    ('note admonition', '#sb-editor .sb-admonition[admonition="note" i]', "borderLeftColor", "indigo"),
    ('warning admonition', '#sb-editor .sb-admonition[admonition="warning" i]', "borderLeftColor", "ochre"),
    ('danger admonition', '#sb-editor .sb-admonition[admonition="danger" i]', "borderLeftColor", "wine"),
    ('success admonition', '#sb-editor .sb-admonition[admonition="success" i]', "borderLeftColor", "olive"),
    # FONT WEIGHT, capped at the site's scale: sans prose 500, serif headings
    # and chrome 600, nothing at 700 or above. These are literal-equality
    # probes because the point is the exact computed number -- a browser that
    # synthesises will still report what was asked for, so a pass here means
    # the cascade resolved as intended, NOT that the face exists. The face is
    # a separate question, answered by FONTS_URL in silverbullet-hub.
    #
    # Stock SilverBullet declares 900 on .sb-strong and bold on the heading
    # lines. The heading probe is the one that matters most: the stock rule is
    # (1,3,0) via `.cm-line`, so a theme rule written at group 1's (1,2,0)
    # loses silently, and this assertion is what catches that.
    ("strong weight", "#sb-editor .sb-strong", "fontWeight", "=500"),
    ("tbl header weight", "#sb-editor .sb-line-tbl-header", "fontWeight", "=500"),
    ("thead weight", "#sb-editor thead tr", "fontWeight", "=500"),
    ("h1 weight", "#sb-editor .cm-line.sb-line-h1", "fontWeight", "=600"),
    ("h2 weight", "#sb-editor .cm-line.sb-line-h2", "fontWeight", "=600"),
    ("h3 weight", "#sb-editor .cm-line.sb-line-h3", "fontWeight", "=600"),
    ("page title weight", "#sb-top .main #sb-current-page .sb-input", "fontWeight", "=600"),
    # NOT capped, asserted so a later change to either is a deliberate one:
    # .sb-keyword stays bold because M PLUS 1 Code is served only at 400;700,
    # and .sb-hr is a divider glyph rather than text emphasis.
    ("keyword weight", "#sb-editor .sb-keyword", "fontWeight", "=700"),
    # the measure
    # filled in below from the same source the stylesheet is generated from
    ("content maxwidth", "#sb-editor .cm-content", "maxWidth", None),
]

# The text column, checked as a number rather than as the variable that sets
# it: measure_chars characters at the body font's average advance, at the
# editor size, with --editor-width carrying the border-box padding on top.
# Asserting the rendered width is what proves the two agree.
#
# DERIVED, NOT TYPED, and that is the whole point of this block. Until the
# measure moved from 70 characters to 80 these numbers lived here as literals --
# "=647px" below and `70 * 0.4818 * 18.0` here -- which made this file the THIRD
# place the same constant was written, after themes/midori.json and the adapter
# in tools/emit-theme.py. A check that hardcodes what it is checking stops being
# a check the moment the thing moves: it would have gone red against a correct
# stylesheet and sent the reader to fix the theme. Both now come from the same
# source the stylesheet is generated from, so this file cannot disagree with it.
MEASURE_TERMS = {}


def _measure():
    root = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("emit", root / "tools" / "emit-theme.py")
    emit = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(emit)
    except SystemExit:
        pass
    theme = json.loads((root / "themes" / "midori.json").read_text())
    target = emit.TARGETS["silverbullet"]
    met = {**theme.get("metrics", {}), **target.get("metrics", {})}
    theme = dict(theme, metrics=met)
    text = emit._calc("measure_chars * avg_advance * editor_font_px", theme)
    total = round(text + met["editor_padding_px"])
    MEASURE_TERMS.update(chars=met["measure_chars"],
                         advance=theme["type"]["avg_advance_em"],
                         size=met["editor_font_px"])
    return text, total


EXPECTED_TEXT_COLUMN, EXPECTED_EDITOR_WIDTH = _measure()
TEXT_COLUMN_TOLERANCE = 0.6

# Fill the one PROBES row that is a derived number. Asserted, not assumed: a
# None left in the table would compare against nothing and pass.
_filled = 0
for _i, _row in enumerate(PROBES):
    if _row[0] == "content maxwidth":
        PROBES[_i] = _row[:3] + (f"={EXPECTED_EDITOR_WIDTH}px",)
        _filled += 1
if _filled != 1:
    sys.exit(f"check_rendered_silverbullet: expected exactly one derived "
             f"PROBES row, filled {_filled} -- the table changed shape")
if any(r[3] is None for r in PROBES):
    sys.exit("check_rendered_silverbullet: a PROBES row still has no expected "
             "value, which would compare against nothing and pass")


def cdp_targets(port):
    raw = urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=10).read()
    return [t for t in json.loads(raw) if t.get("type") == "page"]


def ev(ws, expr, _id=[0]):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True,
                                   "awaitPromise": True}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == _id[0]:
            r = m.get("result", {})
            if "exceptionDetails" in r:
                sys.exit("page error: " + json.dumps(r["exceptionDetails"])[:600])
            return r["result"].get("value")


def cdp_cmd(ws, method, params=None, _id=[9000]):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": method, "params": params or {}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == _id[0]:
            return m


def open_fresh(port, url):
    """Close every page target, then open exactly one on url. See the module
    docstring: grading a window this process did not open is the single
    failure mode that has cost the most time here."""
    before = cdp_targets(port)
    for t in before:
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/close/{t['id']}", timeout=10).read()
        except Exception:
            pass
    print(f"  closed {len(before)} pre-existing page target(s)")
    time.sleep(1)
    req = urllib.request.Request(f"http://127.0.0.1:{port}/json/new?{url}", method="PUT")
    urllib.request.urlopen(req, timeout=15).read()
    time.sleep(9)

    ts = cdp_targets(port)
    if len(ts) != 1:
        sys.exit(f"FAIL: expected exactly 1 page target after opening one, got {len(ts)}: "
                 + ", ".join(t["url"][:50] for t in ts))
    ws = websocket.create_connection(ts[0]["webSocketDebuggerUrl"], suppress_origin=True)
    cdp_cmd(ws, "Emulation.setDeviceMetricsOverride",
            {"width": 1440, "height": 4200, "deviceScaleFactor": 2, "mobile": False})
    time.sleep(2)
    return ws


def parse_colour(v):
    """Return (r, g, b) from either rendered form. color-mix() computes to
    `color(srgb 0.37 0.43 0.37 / 0.35)` in Chromium, not to rgba(), so a
    checker that only parses rgb() silently skips every wash in the theme."""
    if v is None:
        return None
    m = re.match(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)", v)
    if m:
        return tuple(int(round(float(x))) for x in m.groups())
    m = re.match(r"color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", v)
    if m:
        return tuple(int(round(float(x) * 255)) for x in m.groups())
    return None


def main():
    args = [a for a in sys.argv[1:]]
    port = CDP_PORT
    if "--cdp" in args:
        i = args.index("--cdp")
        port = int(args[i + 1])
        del args[i:i + 2]
    url = args[0] if args else URL

    print(f"CDP {port} -> {url}")
    try:
        cdp_targets(port)
    except Exception as exc:
        sys.exit(f"FAIL: no browser answering CDP on {port} ({exc}). "
                 "See silverbullet/README.md for the harness setup.")

    ws = open_fresh(port, url)

    lines = ev(ws, "document.querySelectorAll('#sb-editor .cm-line').length") or 0
    print(f"  rendered cm-lines: {lines}")
    if lines < MIN_LINES:
        sys.exit(f"FAIL: only {lines} cm-lines rendered (need >= {MIN_LINES}). "
                 "Either the sample page is not open, or the viewport override "
                 "did not take and CodeMirror has virtualised away the part of "
                 "the document these probes read.")

    # WHICH ROUTE IS THIS, and is the theme actually here? Both documented
    # install routes must be gradeable, and they land in different places:
    # space-style fills <div id="custom-styles"> at the end of <body>, while
    # headHtml puts a <style> in <head>. Reporting the route and the byte count
    # every run is what makes a TRUNCATED install visible -- sabotage case (d)
    # cut the stylesheet in half and the --midori- token check still passed,
    # because the raw-token block survives the cut. The probes caught it; this
    # line is what tells you where to look.
    route = ev(ws, """(() => {
      const d = document.getElementById('custom-styles');
      const inBody = d ? d.innerHTML : '';
      const inHead = [...document.head.querySelectorAll('style')]
                       .map(s => s.textContent).join('');
      if (inBody.includes('--midori-')) return ['space-style', inBody.length];
      if (inHead.includes('--midori-')) return ['headHtml', inHead.length];
      return [null, inBody.length + inHead.length];
    })()""")
    where, css_bytes = route
    print(f"  theme route: {where or 'NONE FOUND'}, {css_bytes} bytes of CSS")
    if not where:
        sys.exit("FAIL: no --midori- token in #custom-styles or in a <head> "
                 "<style> -- the theme is not installed in this space, so "
                 "nothing below would be measuring it. If you installed it as a "
                 "space-style page, the client's IndexedDB may be holding a "
                 "stale zero-byte copy of that page: compare the server's own "
                 "listing (GET /.fs) against the client's, and if they "
                 "disagree, wipe the browser profile -- 'Space: Reindex' does "
                 "not repair it.")

    failures = []
    asserted = 0

    for mode in ("light", "dark"):
        print(f"\n{mode.upper()}")
        ev(ws, f"document.documentElement.setAttribute('data-theme', {mode!r})")
        time.sleep(0.6)
        got_mode = ev(ws, "document.documentElement.dataset.theme")
        if got_mode != mode:
            sys.exit(f"FAIL: asked for data-theme={mode!r}, element reports {got_mode!r}")

        want = PALETTE[mode]
        js = """(() => { const out = [];
          for (const [name, sel, prop] of %s) {
            const all = document.querySelectorAll(sel);
            out.push([name, prop, all.length,
                      all.length ? getComputedStyle(all[0])[prop] : null]);
          } return out; })()""" % json.dumps([[n, s, p] for n, s, p, _ in PROBES])
        rows = ev(ws, js)
        expected_by_name = {n: e for n, _, _, e in PROBES}

        for name, prop, count, value in rows:
            exp = expected_by_name[name]
            if count == 0:
                failures.append(f"{mode}/{name}: selector matched NOTHING "
                                f"(a zero-match probe is a failure, not a skip)")
                print(f"  !! {name:20} n=0   {prop:17} selector matched nothing")
                continue

            asserted += 1
            ok, detail = False, ""
            if exp.startswith("@"):                      # font-family contains
                ok = exp[1:].lower() in (value or "").lower()
                detail = value
            elif exp.startswith("="):                    # literal equality
                ok = (value or "").strip() == exp[1:]
                detail = value
            elif exp.startswith("~"):                    # role rgb appears in value
                r, g, b = want[exp[1:]]
                ok = f"rgb({r}, {g}, {b})" in (value or "")
                detail = f"{(value or '')[:46]} (want rgb({r}, {g}, {b}))"
            else:                                        # role colour equality
                r, g, b = want[exp]
                got = parse_colour(value)
                ok = got == (r, g, b)
                detail = f"{value} (want rgb({r}, {g}, {b}) = {exp})"

            print(f"  {'ok' if ok else 'FAIL':>4} {name:20} n={count:<4}{prop:17} {str(detail)[:60]}")
            if not ok:
                failures.append(f"{mode}/{name}: {prop} = {value!r}, expected {exp}")

        # The measure, as a measured width rather than as the variable.
        w = ev(ws, """(() => {
          const p = [...document.querySelectorAll('#sb-editor .cm-line')]
                      .find(n => n.classList.length === 1);
          if (!p) return null;
          const s = getComputedStyle(p.parentElement);
          return p.parentElement.clientWidth
                 - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
        })()""")
        asserted += 1
        if w is None:
            failures.append(f"{mode}/text column: found no plain .cm-line to measure")
            print(f"  !! {'text column':20} no plain .cm-line found")
        else:
            ok = abs(w - EXPECTED_TEXT_COLUMN) <= TEXT_COLUMN_TOLERANCE
            print(f"  {'ok' if ok else 'FAIL':>4} {'text column':20} "
                  f"{w:.2f}px (want {EXPECTED_TEXT_COLUMN:.2f}px "
                  f"= {MEASURE_TERMS['chars']}ch x "
                  f"{MEASURE_TERMS['advance']}em x {MEASURE_TERMS['size']}px)")
            if not ok:
                failures.append(f"{mode}/text column: {w:.2f}px, "
                                f"expected {EXPECTED_TEXT_COLUMN:.2f}px")

    print(f"\n{asserted} live assertion(s) across 2 modes, {len(failures)} failure(s)")
    if asserted < MIN_ASSERTIONS:
        sys.exit(f"FAIL: only {asserted} assertions ran (need >= {MIN_ASSERTIONS}). "
                 "Probes dropped out; this run is not evidence.")
    if failures:
        print("\nFAILURES")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("all green")


if __name__ == "__main__":
    main()
