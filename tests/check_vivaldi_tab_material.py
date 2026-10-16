#!/usr/bin/env python3
"""Measure the Lemonardo active-tab material layer in a RUNNING Vivaldi.

WHY THIS CANNOT BE A STATIC CHECK. tests/test_vivaldi_css_vars.py proves the
palette's VARIABLES resolve and that its selectors outrank Midori's on paper.
It cannot prove that a rule paints, and the material layer is exactly the kind
of rule that can parse, load, win every specificity contest and still do
nothing:

  - `.tab.active::before` and `::after` are already Vivaldi's own (corner joins
    + 64ms fade animations) and compute to `content: none`, so they LOOK free.
    A layer hung there would fight geometry we did not write.
  - `z-index: -1` is what keeps the veil under the label. One step too far
    negative, or a positioned ancestor appearing between .tab and .tab-header,
    and the layer disappears behind the accent fill entirely -- with no error.
  - Vivaldi's UI stylesheet arrives as chrome://vivaldi-data/css-mods/css,
    which is CROSS-ORIGIN to the UI page. `sheet.cssRules` THROWS, so a
    checker that counts matching rules counts zero and reports a confident
    absence. The first version of this check did exactly that. Everything here
    is therefore measured through getComputedStyle and through pixels.

So this reads the alphas out of the generated CSS, predicts the composite over
the theme's own accent, and then compares that prediction against a
SCREENSHOT of the active tab. A pass means the light is actually on the paint.

    open -na Vivaldi --args --remote-debugging-port=9222
    python3 -m venv /tmp/cdpenv
    /tmp/cdpenv/bin/pip install websocket-client Pillow
    /tmp/cdpenv/bin/python tests/check_vivaldi_tab_material.py

SUPPRESS THE ORIGIN HEADER. Chromium >= 111 rejects WebSocket clients that
send a non-allowlisted Origin and websocket-client sends one by default;
omitting it is allowed, so no relaunch flags are needed. Same reason as
tests/check_rendered_grid.py.

A LEMONARDO THEME MUST BE ACTIVE, and this refuses to run otherwise rather
than passing vacuously. The active theme is read off #browser's own
`theme-id-<uuid>` class and looked up in vivaldi/themes.json by id: graded
against Midori Paper every assertion below is trivially true, because the rule
is scoped to a theme id that is not applied. That is this repo's single
commonest green-but-vacuous shape.

Not stdlib and deliberately not in tests/lint.sh: it needs websocket-client,
Pillow and a running browser, the same split as the rendered Obsidian checks.
"""
import base64
import io
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

import websocket                      # not stdlib; see the module docstring
from PIL import Image                 # not stdlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import colorspace as cs               # noqa: E402

THEMES = ROOT / "vivaldi" / "themes.json"
PALETTE_NAME = "lemonardo-palette.css"

# dE2000 a measured pixel may sit from the predicted composite. The prediction
# is exact arithmetic on sRGB values; what is left is the screenshot's own
# rounding and the gradient being sampled at the pixel CENTRE rather than at
# its edge (the field's last row reads ~98.3% of the ramp, not 100%).
TOLERANCE = 1.5

# At least two tabs, so "the rule is scoped to .active" is a claim about two
# different measured elements rather than about one.
MIN_TABS = 2

FAIL = []


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    print(f"  FAIL {msg}")
    FAIL.append(msg)


# --------------------------------------------------------------------------
# CDP
# --------------------------------------------------------------------------
class UI:
    def __init__(self, ws):
        self.ws, self._id = ws, 0

    def cmd(self, method, params=None):
        self._id += 1
        self.ws.send(json.dumps({"id": self._id, "method": method,
                                 "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    sys.exit(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def ev(self, expr):
        res = self.cmd("Runtime.evaluate",
                       {"expression": expr, "returnByValue": True,
                        "awaitPromise": True})
        if "exceptionDetails" in res:
            sys.exit("page error: "
                     + json.dumps(res["exceptionDetails"])[:600])
        return res["result"].get("value")

    def shot(self, rect):
        res = self.cmd("Page.captureScreenshot",
                       {"format": "png", "captureBeyondViewport": False,
                        "clip": {**rect, "scale": 1}})
        return Image.open(io.BytesIO(base64.b64decode(res["data"]))).convert("RGB")


def connect():
    """Every browser-UI target, printed, and the one with the most tabs graded.

    check_rendered_grid.py exists because a sweep graded whichever window CDP
    listed first and printed an all-clear from a twelve-line note. The same
    trap is here: a second Vivaldi window with one tab would pass the
    .active-vs-inactive comparison by having nothing to compare.
    """
    try:
        targets = json.load(urllib.request.urlopen("http://localhost:9222/json"))
    except OSError as e:
        sys.exit(f"no CDP on localhost:9222 ({e}); start Vivaldi with "
                 f"--remote-debugging-port=9222")
    ui = [t for t in targets if t.get("url", "").endswith("window.html")]
    if not ui:
        sys.exit("no window.html target -- that is Vivaldi's own UI page, and "
                 "without it there is nothing to measure. Is this Vivaldi?")
    rows = []
    for t in ui:
        ws = websocket.create_connection(t["webSocketDebuggerUrl"],
                                         timeout=40, suppress_origin=True)
        try:
            n = UI(ws).ev("document.querySelectorAll('.tab-wrapper').length")
        finally:
            ws.close()
        rows.append((n, t))
    print(f"  {len(rows)} browser window(s):")
    for n, t in sorted(rows, key=lambda r: -r[0]):
        print(f"      {n:>3} tabs  {t['id']}")
    n, target = max(rows, key=lambda r: r[0])
    if n < MIN_TABS:
        sys.exit(f"the fullest window has {n} tab(s) (< {MIN_TABS}); open a "
                 f"second tab so the inactive-tab comparison has something to "
                 f"measure -- a pass earned by one tab proves nothing.")
    print(f"  grading the window with {n} tabs\n")
    return UI(websocket.create_connection(target["webSocketDebuggerUrl"],
                                          timeout=40, suppress_origin=True))


# --------------------------------------------------------------------------
# what the generated CSS claims
# --------------------------------------------------------------------------
def palette_path(ui):
    """The palette file THIS browser loaded, asked of the browser itself.

    Not the repo's copy. On this machine
    ~/Library/Application Support/Vivaldi/CSSMods is a SYMLINK to
    vivaldi/css-mods, so the two happen to be the same file and the
    distinction looks academic -- right up until something points a profile
    somewhere else, and then a checker reading the repo grades a file the
    browser never saw. Vivaldi keeps the directory in a pref it will hand over
    on request, so there is no reason to guess.
    """
    d = ui.ev("""
    new Promise(res => vivaldi.prefs.get(
      'vivaldi.appearance.css_ui_mods_directory', v => res(v && v.value)))""")
    if not d:
        sys.exit("this profile has no vivaldi.appearance.css_ui_mods_directory, "
                 "so it is loading no UI mods at all and there is nothing to "
                 "measure. Run vivaldi/install-vivaldi.sh, or "
                 "tests/vivaldi-sandbox.sh for a throwaway profile.")
    p = pathlib.Path(d) / PALETTE_NAME
    if not p.exists():
        sys.exit(f"the browser is loading UI mods from {d}, which has no "
                 f"{PALETTE_NAME} in it")
    return p


def declared(palette):
    """{theme id: {dir, lit alpha, field alpha, field start}} from the CSS.

    Read from the FILE Vivaldi loaded, not from make-lemonardo-palette.py's
    constants. A hand edit has to be checked rather than trusted to match the
    generator -- and separately, `make-lemonardo-palette.py --check` in lint
    is what owns the question of whether the generator agrees.
    """
    text = palette.read_text()
    out = {}
    for m in re.finditer(
            r"#browser\.theme-id-([0-9a-f-]{36})\.theme-id-\1\s+"
            r"\.tab\.active \.tab-header::after\s*\{([^}]*)\}", text):
        tid, body = m.group(1), m.group(2)
        g = re.findall(r"linear-gradient\(to (top|bottom),\s*"
                       r"rgb\(([\d ]+) / ([\d.]+)\)[^)]*\)?[^,]*,\s*"
                       r"rgb\([\d ]+ / 0\) 1px\)", body)
        f = re.findall(r"linear-gradient\(to (top|bottom),\s*"
                       r"rgb\(0 0 0 / 0\) (\d+)%,\s*rgb\(0 0 0 / ([\d.]+)\)\)",
                       body)
        if not g or not f:
            bad(f"theme {tid}: the rule is present but its two gradient layers "
                f"do not parse -- this checker reads the alphas out of them, "
                f"so it cannot grade what it cannot read:\n{body.strip()}")
            continue
        out[tid] = {"dir": g[0][0], "lit": float(g[0][2]),
                    "start": int(f[0][1]), "field": float(f[0][2]),
                    "zindex": re.search(r"z-index:\s*(-?\d+)", body),
                    "body": body}
    return out


def over(fg, a, bg):
    f, b = cs.hex_to_rgb(fg), cs.hex_to_rgb(bg)
    return cs.rgb_to_hex(tuple(f[i] * a + b[i] * (1 - a) for i in range(3)))


PATCH = 24          # px per calibration swatch
PATCH_AT = (300, 300)


def calibrate(ui, base, veils):
    """Paint `base` with each (lamp, alpha) veil over it; return what we read.

    TWO SEPARATE REASONS THIS IS MEASURED AGAINST A PATCH RATHER THAN AGAINST
    ARITHMETIC, both found the hard way here.

    1. PAGE.CAPTURESCREENSHOT DOES NOT RETURN sRGB. A div painted `#dc931e`
       screenshots as `#d6882c`, and the window background themes.json sets to
       `#f3eee2` screenshots as `#f1ebdf` -- a ~4.9 dE2000 shift on
       everything, because the capture comes back in the display's colour
       space. That alone fails every prediction in this file while the CSS is
       perfect, and it is the trap already recorded for the t3 night grounds:
       check the ICC profile before comparing screenshots.

    2. THE ALPHA IS COMPOSITED AFTER THAT TRANSFORM, NOT BEFORE IT. Painting
       the pre-blended sRGB value as a patch is still wrong, because
       blend-then-transform and transform-then-blend are not the same
       operation. The lit rim measured #e0a661 while a patch of its sRGB
       composite #e5ae57 read back #e1a555 -- 2.0 dE2000 apart, all of it in
       blue. So the patch reproduces the MECHANISM: an opaque base with an
       alpha layer over it, exactly as .tab.active is an accent fill with a
       veil on ::after. Then the transform cancels and what is left is the
       alpha itself, which is the thing this file is here to check.

    A consequence worth stating plainly: the dE targets in
    make-lemonardo-palette.py are sRGB-space intent, and sRGB is the right
    space to design in because it is the one that does not vary by monitor.
    The dE a given display actually renders is a little different, and this
    check does not and should not assert that number.
    """
    x, y = PATCH_AT
    cells = "".join(
        '<i style="position:relative;width:%dpx;height:%dpx;background:%s">'
        '<b style="position:absolute;inset:0;background:rgb(%s / %.4f)"></b>'
        '</i>' % (PATCH, PATCH, base,
                  "255 255 255" if lamp == "#ffffff" else "0 0 0", alpha)
        for lamp, alpha in veils)
    js = """
    (() => {
      let s = document.getElementById('__cal');
      if (!s) { s = document.createElement('div'); s.id = '__cal';
                document.body.appendChild(s); }
      s.style.cssText = 'position:fixed;left:%dpx;top:%dpx;z-index:2147483647;'
        + 'display:flex;pointer-events:none';
      s.innerHTML = %s;
      return s.getBoundingClientRect().width;
    })()
    """ % (x, y, json.dumps(cells))
    width = ui.ev(js)
    if not width:
        sys.exit("the calibration strip did not lay out; there is nothing to "
                 "compare the tab against, so this is a hard stop rather than "
                 "a fallback to comparing against nominal hexes")
    img = ui.shot({"x": x, "y": y, "width": width, "height": PATCH})
    read = ["#%02x%02x%02x" % img.getpixel((round((i + 0.5) * PATCH),
                                            PATCH // 2))
            for i in range(len(veils))]
    ui.ev("document.getElementById('__cal')?.remove(), 1")
    return read


def focus(ui):
    """Raise Vivaldi's window. Kept, but NOT for the reason first written here.

    THE EXPLANATION THIS FUNCTION WAS BUILT ON WAS WRONG, and it is left
    recorded because it was convincing. Every row of the active tab came in
    ~4.9 dE2000 dark of prediction, including a row with no material layer
    over it at all. #browser carried `isblurred` at the time, Vivaldi does put
    that class on when the window loses focus, and "a blurred window is a
    dimmed window" explained the constant offset completely. So this function
    was written to chase focus, which took finding that SystemInfo only
    answers on the browser target.

    It worked -- `isblurred` went away -- and the pixels did not move by one
    count. The offset was the SCREENSHOT COLOUR PROFILE, not dimming; see
    calibrate(). The reasoning that was actually sound is the part about a
    constant offset on every sample meaning the surface under test is not the
    surface that was predicted. That was right, and it pointed at the wrong
    surface.

    Kept anyway, cheaply: raising the window costs one osascript call and
    removes focus state as a variable in a check whose whole value is that its
    numbers are explainable. Note the PID, not the application name --
    `tell application "Vivaldi" to activate` raises whichever Vivaldi macOS
    feels like, and during development that is the operator's own browser
    rather than the one on the debugging port.
    """
    ui.cmd("Page.bringToFront")
    # SystemInfo lives on the BROWSER target, not on a page one -- asked of the
    # UI page it answers "only supported on the browser target", and the first
    # version of this silently gave up there.
    try:
        url = json.load(urllib.request.urlopen(
            "http://localhost:9222/json/version"))["webSocketDebuggerUrl"]
        bws = websocket.create_connection(url, timeout=20, suppress_origin=True)
        try:
            bws.send(json.dumps({"id": 1, "method": "SystemInfo.getProcessInfo"}))
            info = json.loads(bws.recv()).get("result", {}).get("processInfo", [])
        finally:
            bws.close()
        pid = next(p["id"] for p in info if p.get("type") == "browser")
    except (OSError, KeyError, ValueError, StopIteration) as e:
        print(f"  note: could not find the browser process to focus ({e!r}); "
              f"continuing with whatever focus state the window has")
        return
    r = subprocess.run(
        ["osascript", "-e",
         f'tell application "System Events" to set frontmost of '
         f'(first process whose unix id is {pid}) to true'],
        capture_output=True, text=True)
    if r.returncode:
        print(f"  note: osascript could not focus pid {pid}: "
              f"{r.stderr.strip()[:200]}")


def main():
    themes = {t["id"]: t for t in json.loads(THEMES.read_text())["themes"]}
    ui = connect()
    palette = palette_path(ui)
    try:
        shown = palette.relative_to(ROOT)
    except ValueError:
        shown = palette
    spec = declared(palette)
    if not spec:
        bad(f"{shown} declares no .tab.active .tab-header::after rule at all "
            f"-- every check below would pass against an empty input set")
        return 1
    ok(f"{shown}: {len(spec)} material rule(s) declared")

    # THE TWO BENCHES MUST BE MIRRORS, and that is checkable statically even
    # though only one theme can be live at a time. The whole motif is one
    # surface lit from opposite sides -- paint under a window, ink on a light
    # table -- so if both rules read the same direction the design has
    # collapsed into one room at two exposures, which is the exact failure the
    # palette's docstring exists to prevent. Nothing downstream would notice:
    # each rule would still paint, and the live check below follows whichever
    # direction it is told.
    dirs = {tid: v["dir"] for tid, v in spec.items()}
    if len(spec) == 2 and len(set(dirs.values())) == 1:
        bad(f"both material rules run {next(iter(set(dirs.values())))} -- the "
            f"two benches are meant to be the same surface lit from opposite "
            f"sides, so one of them must be flipped")
    elif len(spec) == 2:
        ok("the two benches are mirrors: " + ", ".join(
            f"{themes.get(t, {}).get('name', t)} {d}"
            for t, d in sorted(dirs.items(), key=lambda kv: kv[1])))

    focus(ui)
    classes = ui.ev("document.getElementById('browser').className").split()
    ids = [c[len("theme-id-"):] for c in classes if c.startswith("theme-id-")]
    if len(ids) != 1:
        bad(f"#browser carries {len(ids)} theme-id classes ({ids}) -- expected "
            f"exactly one; the scoping assumption behind the whole palette is "
            f"that this names the active theme")
        return 1
    tid = ids[0]
    name = themes.get(tid, {}).get("name", "<not in themes.json>")
    if tid not in spec:
        sys.exit(f"the live theme is {name!r} (id {tid}), which has no material "
                 f"rule. Switch to a Lemonardo theme and re-run: graded "
                 f"against a theme the rule does not target, every assertion "
                 f"below is vacuously true.")
    s = spec[tid]
    accent = themes[tid]["colorAccentBg"]
    print(f"  live theme: {name}  accent {accent}  "
          f"gradients {s['dir']}  lit {s['lit']}  field {s['field']}")

    live_accent = ui.ev("getComputedStyle(document.getElementById('browser'))"
                        ".getPropertyValue('--colorAccentBg').trim()")
    if live_accent.lower() != accent.lower():
        bad(f"themes.json says this theme's accent is {accent} but the live "
            f"--colorAccentBg is {live_accent!r} -- the prediction below is "
            f"built on the accent, so it would be measuring the wrong surface")
        return 1
    ok(f"live --colorAccentBg matches themes.json ({accent})")

    # ---- 1. the pseudo-element computes, on the active tab only -----------
    probe = r"""
    (() => {
      const q = (s) => document.querySelector(s);
      const act = q('.tab-wrapper.active .tab-header');
      const ina = q('.tab-wrapper:not(.active) .tab-header');
      const read = (e) => {
        if (!e) return null;
        const c = getComputedStyle(e, '::after'), r = e.getBoundingClientRect();
        return {content: c.content, zIndex: c.zIndex, position: c.position,
                pointerEvents: c.pointerEvents, bgImg: c.backgroundImage,
                rect: {x: r.x, y: r.y, width: r.width, height: r.height},
                parentOverflow: getComputedStyle(e).overflow,
                selfPosition: getComputedStyle(e).position};
      };
      return JSON.stringify({active: read(act), inactive: read(ina),
                             tabs: document.querySelectorAll('.tab-wrapper').length,
                             actives: document.querySelectorAll('.tab-wrapper.active').length});
    })()
    """
    d = json.loads(ui.ev(probe))
    if d["actives"] != 1:
        bad(f"{d['actives']} tabs carry .active -- expected exactly 1")
        return 1
    a, i = d["active"], d["inactive"]
    if a is None:
        bad("no .tab-wrapper.active .tab-header in the DOM -- the selector "
            "names a structure this Vivaldi does not build")
        return 1
    if a["content"] in ("none", "normal"):
        bad(f"the active tab's ::after computes content: {a['content']} -- the "
            f"rule is not reaching it, so nothing is painted")
    else:
        ok(f"active tab ::after: content {a['content']}, "
           f"position {a['position']}, z-index {a['zIndex']}")
    if a["pointerEvents"] != "none":
        bad(f"::after pointer-events is {a['pointerEvents']}, not none -- a "
            f"veil over the whole tab header should never be a hit-test target")
    if a["zIndex"] != "-1":
        bad(f"::after z-index is {a['zIndex']}, not -1 -- at 0 or above the "
            f"veil crosses the title glyphs instead of lying on the paint")
    layers = a["bgImg"].count("linear-gradient")
    if layers != 2:
        bad(f"::after background has {layers} gradient layer(s), want 2 "
            f"(the lit rim and the soft field): {a['bgImg'][:160]}")
    else:
        ok("::after carries both gradient layers")
    if i is not None and i["content"] not in ("none", "normal"):
        bad(f"an INACTIVE tab's ::after also computes content {i['content']} "
            f"-- the layer is meant to mark the one tab whose accent is a "
            f"filled surface")
    elif i is not None:
        ok("inactive tabs carry no material layer")

    # ---- 2. the pixels ----------------------------------------------------
    r = a["rect"]
    if r["width"] < 40 or r["height"] < 12:
        bad(f"the active tab measures {r['width']}x{r['height']} CSS px, too "
            f"small to sample a 1px rim in")
        return 1
    img = ui.shot({"x": r["x"], "y": r["y"],
                   "width": r["width"], "height": r["height"]})
    w, h = img.size
    if (w, h) != (round(r["width"]), round(r["height"])):
        print(f"  note: screenshot is {w}x{h} for a "
              f"{r['width']:.0f}x{r['height']:.0f} CSS-px clip; sampling by "
              f"fraction of height")

    def sample(row):
        """Median of the middle third of a row -- the ends are rounded off and
        the favicon and close button live at the two edges."""
        xs = range(w // 3, 2 * w // 3)
        px = sorted(img.getpixel((x, row)) for x in xs)
        return "#%02x%02x%02x" % px[len(px) // 2]

    # `to bottom` puts the lit rim on row 0 and builds the field downwards;
    # `to top` is the same gradient flipped, so both swap ends.
    lit_row, plain_row = (0, 4) if s["dir"] == "bottom" else (h - 1, h - 5)
    field_row = h - 1 if s["dir"] == "bottom" else 0
    # Distance along the gradient axis, as a percentage, of that row's CENTRE
    # -- not of its edge. The last row's centre sits at (h-0.5)/h, so the field
    # reads a little short of its endpoint alpha and predicting the endpoint
    # would leave a standing dE the tolerance would have to absorb.
    pos = (field_row + 0.5) / h * 100
    if s["dir"] == "top":
        pos = 100 - pos
    frac = max((pos - s["start"]) / (100 - s["start"]), 0.0)

    # Each row is compared against a patch built the same way the tab is: the
    # theme's accent with this row's veil over it. See calibrate() for why
    # neither a nominal hex nor a pre-blended one works.
    rows = (("unlit face", plain_row, ("#ffffff", 0.0)),
            ("lit rim", lit_row, ("#ffffff", s["lit"])),
            ("shaded end", field_row, ("#000000", s["field"] * frac)))
    patches = calibrate(ui, accent, [v for _, _, v in rows])
    shift = cs.ciede2000(patches[0], accent)
    print(f"  capture profile: a patch painted {accent} reads back as "
          f"{patches[0]} (dE2000 {shift:5.2f}); every row below is compared "
          f"against a patch carrying the same veil, not against a hex")

    for (label, row, (lamp, alpha)), patch in zip(rows, patches):
        got = sample(row)
        de = cs.ciede2000(got, patch)
        detail = (f"a {alpha:.4f} of {lamp} over the accent" if alpha
                  else "the accent, unveiled")
        srgb = over(lamp, alpha, accent)
        line = (f"{label:11} row {row:>3}: measured {got}  patch {patch}  "
                f"dE2000 {de:5.2f}  ({detail}; sRGB intent {srgb})")
        if de <= TOLERANCE:
            ok(line)
        else:
            bad(line + f"  (> {TOLERANCE})")

    print()
    print("vivaldi tab material: all green" if not FAIL
          else f"vivaldi tab material: {len(FAIL)} failure(s) above")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
