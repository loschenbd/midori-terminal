#!/usr/bin/env python3
"""The writing surface, checked in the units the research is stated in.

A stylesheet says "34em" and "24px". The evidence says "characters per line"
and "ratio to base size". This converts, so a change that looks harmless in
CSS cannot quietly leave the band. Evidence and provenance for every number:
docs/superpowers/specs/2026-08-15-prose-typography-evidence.md

Font constants are measured from the real outlines with a BoundsPen (NOT from
OS/2, which is designer-typed metadata). They are inlined rather than read from
the TTFs so this runs on a stdlib interpreter in lint and CI; re-derive with
    obsidian/.fontenv/bin/python3 tests/measure_prose_type.py
"""

import math
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
THEME = (REPO / "obsidian" / "theme.css").read_text()

AVG_ADVANCE_EM = 0.4818     # M PLUS 1p, averaged over a prose sample
X_MPLUS = 0.520             # x-height, em
X_SPECTRAL = 0.450

# app.js clamps baseFontSize to 10..30 (Math.clamp(e, 10, 30)), so this is the
# whole reachable range, not a range we chose.
BASES = tuple(range(10, 31))

FAIL = []


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    print(f"  FAIL {msg}")
    FAIL.append(msg)


def theme_var(name):
    """Last declared value of a custom property, as a string.

    NOT anchored to the start of a line: an earlier draft was, and it silently
    reported "not set" for every declaration that shared a line with another
    one — which reads as a missing variable rather than as a regex that cannot
    see it. A `var(--x)` USE cannot match here, because a use has no colon
    after the name.

    COMMENTS ARE STRIPPED FIRST. This file's comments quote CSS, whole
    declarations included — the @supports block explains itself by quoting the
    broken two-declaration form it replaces. A quoted declaration matches this
    pattern exactly as well as a real one, so without the strip the answer
    depends on where the prose happens to sit relative to the code, and a
    failure prints comment text where a value should be.
    """
    hits = re.findall(rf"{re.escape(name)}\s*:\s*([^;]+);",
                      re.sub(r"/\*.*?\*/", "", THEME, flags=re.S))
    return hits[-1].strip() if hits else None


def em_value(raw):
    m = re.fullmatch(r"([0-9.]+)em", (raw or "").strip())
    return float(m.group(1)) if m else None


def settings_block():
    r"""The @settings YAML, parsed by hand because tests/ is stdlib-only.

    PyYAML is not available to the interpreter tests/lint.sh runs; verified by
    `python3 -c "import yaml"` failing. Rather than add a dependency to a suite
    that is deliberately stdlib-only, this reads exactly the subset Style
    Settings needs and this theme uses: top-level `key: value`, a `settings:`
    list whose items each begin with a bare `-`, `key: value` inside those
    items, and a nested list of bare scalars under `options:`.

    NO multi-line scalars. Every description in the block is one line, which is
    a deliberate constraint on the block rather than a limitation here -- it
    keeps this forty lines instead of a YAML implementation.
    """
    m = re.search(r"/\*\s*@settings\s*\n(.*?)\*/", THEME, re.S)
    if not m:
        return None
    top, items, cur, listkey = {}, [], None, None
    for raw in m.group(1).split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if line == "-":                       # a new setting begins
            cur = {}
            items.append(cur)
            listkey = None
            continue
        if line.startswith("- "):             # a bare scalar under options:
            if listkey and cur is not None:
                cur.setdefault(listkey, []).append(line[2:].strip())
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val == "":                         # a key that introduces a list
            listkey = key
            if cur is not None:
                cur.setdefault(key, [])
            continue
        listkey = None
        if cur is None or indent == 0:
            top[key] = val
        else:
            cur[key] = val
    top["settings"] = items
    return top


def test_measure():
    """The measure, in characters, and in a unit that survives its consumers.

    app.css applies --file-line-width as max-width on .cm-line, and .cm-line is
    also the heading element (.HyperMD-header-1 sets font-size: var(--h1-size)
    on it). An em there resolves against the element's OWN font-size, so an em
    measure gives heading lines a wider column than body lines: measured, 34em
    is 544px on a body line and 880px on an h1. calc(var(--font-text-size) * N)
    resolves numerically before it reaches any consumer.

    THE SUBJECT CHANGED WHEN THE MEASURE BECAME A SETTING. "The value" is now
    whatever the reader chose, so this cannot assert it. It asserts the two
    things that are still the theme's to get right: the DEFAULT sits in the
    conventional band, and the slider BOUNDS stay inside what the evidence can
    carry. Widening the band here instead of splitting it would have silently
    deleted the check rather than loosened it.
    """
    raw = theme_var("--file-line-width")
    if raw is None:
        bad("--file-line-width is not set; Obsidian's 700px default is ~91 cpl at 16px")
        return
    if em_value(raw) is not None:
        bad(f"--file-line-width is {raw!r}: an em measure is resolved against the "
            "font-size of .cm-line, which is 1.618em on a heading line")
        return
    if "var(--midori-set-measure)" not in raw:
        bad(f"--file-line-width is {raw!r}: expected it to derive from "
            "var(--midori-set-measure)")
        return
    if "var(--font-text-size)" not in raw:
        bad(f"--file-line-width is {raw!r}: must be a multiple of "
            "--font-text-size so it tracks the reader's text size")
        return
    css_adv = theme_var("--midori-avg-advance")
    if css_adv is None or abs(float(css_adv) - AVG_ADVANCE_EM) > 1e-9:
        bad(f"--midori-avg-advance is {css_adv!r} but the suite measured "
            f"{AVG_ADVANCE_EM}; the cpl conversion and the CSS disagree")
        return
    b = settings_block()
    s = next((x for x in (b or {}).get("settings", [])
              if x["id"] == "midori-set-measure"), None)
    if s is None:
        bad("no midori-set-measure control in the @settings block")
        return
    dflt, lo, hi = float(s["default"]), float(s["min"]), float(s["max"])
    if not 55.0 <= dflt <= 75.0:
        bad(f"the measure default is {dflt:g} cpl, outside the conventional 55-75")
        return
    if lo < 40.0 or hi > 100.0:
        bad(f"the measure slider spans {lo:g}-{hi:g} cpl; 40-100 is what the "
            f"evidence carries (preference floor to the ~95 cpl speed peak)")
        return
    ok(f"measure default {dflt:g} cpl in 55-75, slider {lo:g}-{hi:g} inside 40-100")


def test_row_is_one_number():
    raw = theme_var("--midori-row")
    if raw is None:
        bad("--midori-row is not defined; the grid is still a literal in every rule")
        return
    ok(f"--midori-row = {raw}")

    # The refactor is only real if the literals are gone. Comments are stripped
    # first: the file explains the grid in prose and those mentions are fine.
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)
    stray = re.findall(r"line-height:\s*24px", body)
    if stray:
        bad(f"{len(stray)} rules still hardcode line-height: 24px")
    else:
        ok("no rule hardcodes line-height: 24px")

    if re.search(r"background-size:\s*24px\s+24px", body):
        bad("the dot grid still hardcodes 24px 24px")
    else:
        ok("the dot grid is expressed in --midori-row")


def test_no_stray_grid_literals():
    """Grid-derived dimensions must use the row variable, not a literal.

    Now that the row is a function of the reader's text size, any literal
    multiple of 24px that measures vertical space or padding will break: the
    row grows and the literal does not, pushing lines off the grid.

    THIS CHECKS THE MULTIPLES IT NAMES, NOT ALL px. The stylesheet is full of
    legitimate px — hairlines, glyph measurements, knob diameters — so the
    pattern is the specific values a 24px grid produces (24, 48, 72, 96) and
    nothing else. A grid literal at some other multiple would still slip
    through; widening this to every px literal would drown in false positives.

    Allowances are explicit: --midori-row's own declaration, which is the
    fallback the @supports block refines (see test_row_has_a_plain_fallback),
    and --dotgrid-offset-y, which is an offset FROM the historical row rather
    than a length on the grid.
    """
    # Strip comments: the design record mentions 24px in prose, which is fine.
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)

    ALLOWED = (
        "--midori-row",        # the row's own declaration
        "--dotgrid-offset-y",  # was measured against 24px; now an offset from it
    )

    # SPLIT, DO NOT MATCH. A regex over whole declarations has to guess where
    # a property name starts, and the obvious guess -- a leading hyphen for
    # custom properties -- silently skips every unhyphenated name, so
    # `height: 24px` and `margin: 24px 0 0` slip through. Splitting on the
    # delimiters CSS actually uses cannot miss one.
    non_allowed = []
    for chunk in body.split("}"):
        if "{" not in chunk:
            continue
        _, _, decls = chunk.rpartition("{")
        for decl in decls.split(";"):
            prop, sep, value = decl.partition(":")
            if not sep or prop.strip() in ALLOWED:
                continue
            if re.search(r"\b(?:24|48|72|96)px\b", value):
                non_allowed.append(f"{prop.strip()}: {value.strip()}")

    if non_allowed:
        bad(f"{len(non_allowed)} properties still use a literal 24/48/72/96px")
        for decl in non_allowed[:5]:
            bad(f"  {decl}")
        if len(non_allowed) > 5:
            bad(f"  ... and {len(non_allowed) - 5} more")
    else:
        ok("no declaration outside the two allowances uses a literal "
           "24/48/72/96px")


def test_row_has_a_plain_fallback():
    """A plain --midori-row must exist OUTSIDE the @supports block.

    The whole reason the row is written as one plain declaration refined by a
    feature query, rather than two declarations in a row, is that a custom
    property is a token stream: an engine that cannot parse round() would keep
    the unparseable value and hand it to all ~45 consumers, and line-height
    would compute to `normal` rather than to 24px. The @supports form degrades
    instead — but only because the plain declaration is there to degrade TO.

    NOTHING ELSE IN THIS FILE CAN SEE IT GO. theme_var() returns the LAST
    match, which is the copy inside @supports, so deleting the base
    declaration leaves every other assertion here green while an engine
    without round() loses the grid entirely. Deleting the @supports block is
    already caught; this is the other half.

    So: excise the @supports block from the source and check what is left.
    """
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)

    # Excise @supports blocks by brace-counting from the at-rule. A regex
    # cannot do this: the block contains nested {} of its own.
    out, i = [], 0
    while True:
        at = body.find("@supports", i)
        if at == -1:
            out.append(body[i:])
            break
        out.append(body[i:at])
        depth, j = 0, body.find("{", at)
        if j == -1:
            break
        while j < len(body):
            if body[j] == "{":
                depth += 1
            elif body[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        i = j + 1
    outside = "".join(out)

    hits = re.findall(r"--midori-row\s*:\s*([^;]+);", outside)
    if not hits:
        bad("no --midori-row declaration outside @supports: an engine without "
            "round() gets an undefined row, and ~45 consumers fall back to "
            "their initial values instead of to the historical 24px grid")
        return
    plain = [h.strip() for h in hits if re.fullmatch(r"\d+px", h.strip())]
    if not plain:
        bad(f"--midori-row outside @supports is {hits[-1].strip()!r}: the "
            "fallback has to be a plain px literal, or the engine that cannot "
            "parse round() cannot parse the fallback either")
        return
    if int(plain[-1][:-2]) % 2 != 0:
        bad(f"the --midori-row fallback is {plain[-1]}, which is odd; "
            "--dotgrid-offset-y adds half the row")
        return
    ok(f"--midori-row falls back to a plain {plain[-1]} outside @supports")


def row_px(base):
    """Mirror of the CSS: round(up, max(24px, base * 1.5), 2px)."""
    return math.ceil(max(24, base * 1.5) / 2) * 2


def test_leading_holds_across_the_slider():
    raw = theme_var("--midori-row")
    if raw is None or "--font-text-size" not in raw:
        bad(f"--midori-row is {raw!r}: fixed, so leading falls below 1.5 "
            "as soon as the reader raises their text size")
        return
    # A LOCAL flag, not the global FAIL: an unrelated earlier failure must not
    # silently swallow this test's own ok line.
    bad_here = False
    worst = min(((base, row_px(base) / base) for base in BASES), key=lambda p: p[1])
    for base in BASES:
        ratio = row_px(base) / base
        if ratio < 1.5 - 1e-9:
            bad(f"base {base}px gives leading {ratio:.2f}, under the 1.5 policy floor")
            bad_here = True
    if not bad_here:
        ok(f"leading >= 1.5 across {BASES[0]}-{BASES[-1]}px "
           f"(worst {worst[1]:.2f} at {worst[0]}px)")


def test_row_is_an_even_number_of_pixels():
    """The row must be even, because --dotgrid-offset-y adds half of it.

    row_px() returns even pixels by construction, so asserting on it proves
    nothing. What can actually regress is the stylesheet dropping the rounding
    — `max(24px, var(--font-text-size) * 1.5)` alone can be odd (e.g. 25.5px
    at a 17px base), and an odd row makes half the row fractional. Chromium
    rounds the half-leading to a whole pixel, leaving the baseline 0.5px off
    the L/2 model that the offset formula assumes. Rounding to 2px keeps every
    row in the 10-30px clamp even, and the measured baseline then matches L/2
    exactly at all 21 of them.
    """
    raw = theme_var("--midori-row") or ""
    if re.search(r"round\(\s*up\s*,.*,\s*2px\s*\)", raw):
        ok("the row is rounded up to even pixels")
    else:
        bad(f"--midori-row is {raw!r}: no round(..., 2px), so an odd row makes "
            "half of it fractional, and the baseline lands 0.5px off the L/2 "
            "that --dotgrid-offset-y assumes")

    # Every row across the clamp must be even for the offset formula to work.
    bad_here = False
    for base in BASES:
        row = row_px(base)
        if row % 2 != 0:
            bad(f"base {base}px gives row {row}px, which is odd")
            bad_here = True
    if not bad_here:
        ok(f"all rows across {BASES[0]}-{BASES[-1]}px are even")


# Obsidian's defaults, in em of the base size.
OBSIDIAN_H = {1: 1.618, 2: 1.462, 3: 1.318, 4: 1.188}


def test_heading_ladder_is_optical():
    """Each heading should be as much BIGGER TO THE EYE as its em says.

    Spectral carries 0.450 of x-height per em against Midori Text's 0.520, so
    a heading set at the app's default em is 13.5% smaller optically than the
    ladder claims. The test is on x-height ratio, not on em.
    """
    for level, default in OBSIDIAN_H.items():
        raw = theme_var(f"--h{level}-size")
        em = em_value(raw)
        if em is None:
            bad(f"--h{level}-size is {raw!r}; at Obsidian's default {default}em "
                f"the visual step is {default * X_SPECTRAL / X_MPLUS:.2f}x body, "
                f"not {default:.2f}x")
            continue
        visual = em * X_SPECTRAL / X_MPLUS
        if abs(visual - default) <= 0.02:
            ok(f"h{level} {raw} reads {visual:.2f}x body (intended {default:.2f}x)")
        else:
            bad(f"h{level} {raw} reads {visual:.2f}x body, intended {default:.2f}x")


def rules():
    r"""Every (selector, declarations) pair in theme.css, comments stripped.

    SPLIT, DO NOT MATCH. The obvious regex for a CSS rule —
    `([^{}]*KEYWORD[^{}]*)\{([^{}]*)\}` — has two unbounded quantifiers on
    either side of a literal, which is polynomial: against this 90KB
    stylesheet it does not finish. Splitting on braces is linear and needs no
    cleverness. Nested at-rules degrade gracefully: the inner rule is found
    and the wrapper is ignored, which is all any check here wants.
    """
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)
    out = []
    for chunk in body.split("}"):
        if "{" not in chunk:
            continue
        selector, _, decls = chunk.rpartition("{")
        out.append((" ".join(selector.split()), decls))
    return out


def test_blank_line_keeps_the_grid():
    """The blank line the caret sits on must be a whole grid row.

    pretty-paragraphs gives it `line-height: normal` — about 16.8px at a 14px
    base, which is not a multiple of 24 — so every line below it leaves the
    lattice whenever the caret rests on an empty line.
    """
    for selector, decls in rules():
        if ".cm-line" in selector and re.search(r"line-height:\s*normal", decls):
            bad(f"a .cm-line rule sets line-height: normal, which is not a "
                f"grid row: {selector[:70]}")
            return
    ok("no .cm-line rule sets line-height: normal")


def test_indent_excludes_non_prose():
    """Only prose is indented.

    The obvious selector — the line after a blank one — also matches a heading
    that follows a blank line, which is every heading in a real note.

    CHECK EACH SELECTOR, NOT THE RULE. rules() hands back everything before the
    brace as one string, so a comma-separated list arrives joined, and asking
    whether an exclusion appears in that string asks whether ANY selector
    carries it. This rule has two selectors; dropping :not(.HyperMD-header)
    from the "line after a blank line" half — the half that causes the bug —
    left the earlier version of this test green. Measured, not assumed.
    """
    EXCLUDE = ("HyperMD-header", "HyperMD-list-line", "HyperMD-codeblock",
               "HyperMD-quote", "HyperMD-table-row", "HyperMD-callout")
    indented = [sel for sel, decls in rules()
                if "text-indent: var(--midori-indent)" in decls and ".cm-line" in sel]
    if not indented:
        bad("no Live Preview rule applies --midori-indent")
        return
    missing = []
    for rule in indented:
        for selector in rule.split(","):
            if ".cm-line" not in selector:
                continue
            for kind in EXCLUDE:
                if kind not in selector:
                    missing.append((kind, " ".join(selector.split())[:60]))
    if missing:
        for kind, selector in missing:
            bad(f"the Live Preview indent does not exclude .{kind}: {selector}")
    else:
        ok(f"every Live Preview indent selector excludes all "
           f"{len(EXCLUDE)} non-prose kinds")


def test_zen_header_rules_are_gated():
    """A zen rule compensating for the view header must check BOTH conditions.

    app.css: `body:not(.show-view-header):not(.is-phone) .view-header
    { display: none }`. TWO negations, so the header is drawn whenever
    .show-view-header OR .is-phone holds, and a gate has to name both.

    One class is not enough, and each half fails on a different platform.
    Ungated, the desktop with the setting off gets a header's worth of empty
    space above the note plus a dot grid shifted to match it. Gated on
    .show-view-header alone, a PHONE with the setting off still draws the
    header and no longer compensates, so the note's first line sits
    --header-height (40px there) too high, under the controls — the same
    defect inverted. An earlier version of this test asked only that
    "show-view-header" was PRESENT, which `body.zen-mode.show-view-header`
    satisfies, so it could not tell the correct gate from the half of it that
    regressed phones. Both names, or it is not a gate.
    """
    ungated = []
    for selector, decls in rules():
        if "body.zen-mode" not in selector:
            continue
        if "--header-height" not in decls:
            continue
        missing = [cls for cls in ("show-view-header", "is-phone")
                   if cls not in selector]
        if missing:
            ungated.append((", ".join("." + c for c in missing), selector[:70]))
    if ungated:
        for missing, sel in ungated:
            bad(f"zen rule uses --header-height but its gate omits "
                f"{missing}: {sel}")
    else:
        ok("every zen rule that compensates for the view header names both "
           "conditions app.css negates")


def test_settings_block_parses():
    """The @settings block exists and every entry is well formed.

    A malformed block does not error in Obsidian -- Style Settings simply shows
    nothing, so the settings silently do not exist. This is the only thing that
    notices.
    """
    b = settings_block()
    if b is None:
        bad("no /* @settings */ block in theme.css")
        return
    for key in ("name", "id"):
        if key not in b:
            bad(f"the @settings block has no top-level {key}")
            return
    if not b["settings"]:
        bad("the @settings block declares no settings")
        return
    for s in b["settings"]:
        for key in ("id", "title", "type"):
            if key not in s:
                bad(f"a setting is missing {key}: {s}")
                return
        if s["type"] == "variable-number-slider":
            for key in ("default", "min", "max", "step"):
                if key not in s:
                    bad(f"slider {s['id']} is missing {key}, which Style "
                        f"Settings requires")
                    return
        if s["type"] == "class-select":
            if "allowEmpty" not in s:
                bad(f"class-select {s['id']} is missing allowEmpty, which "
                    f"Style Settings requires")
                return
            if not s.get("options"):
                bad(f"class-select {s['id']} declares no options")
                return
    ok(f"the @settings block parses: {len(b['settings'])} entries")


def test_settings_ids_are_real():
    """Every control points at something the stylesheet actually defines.

    Style Settings writes `--<id>` for a variable-* control and adds `<id>` as a
    body class for a class-* one. Either way a typo produces a control that
    moves nothing, and the UI still looks correct -- which is the failure mode
    worth a test.
    """
    b = settings_block()
    if b is None:
        bad("no @settings block to check")
        return
    missing = []
    for s in b["settings"]:
        t, sid = s["type"], s["id"]
        if t == "heading":
            continue
        if t.startswith("variable-"):
            if f"--{sid}:" not in THEME:
                missing.append(f"{t} {sid} -> --{sid} is never declared")
        elif t == "class-toggle":
            if f".{sid}" not in THEME:
                missing.append(f"class-toggle {sid} -> .{sid} is in no selector")
        elif t == "class-select":
            for opt in s.get("options", []):
                if f".{opt}" not in THEME:
                    missing.append(f"class-select {sid} option {opt} -> "
                                   f".{opt} is in no selector")
    if missing:
        for m in missing:
            bad(m)
    else:
        ok("every @settings control maps to a real variable or class")


def test_settings_defaults_match_the_css():
    """Every variable control's `default:` equals the value the CSS ships.

    Style Settings persists only DEVIATIONS from the shipped stylesheet, so
    these two numbers are one fact written twice: the block's `default:` is
    what the panel shows and what "reset" restores, and the CSS declaration is
    what a reader who never opens settings actually gets. Let them drift and
    the panel confidently reports a value the theme is not using -- with no
    error anywhere, because each is internally consistent.
    """
    b = settings_block()
    if b is None:
        bad("no @settings block to check")
        return
    mismatched = []
    for s in b["settings"]:
        if not s["type"].startswith("variable-") or "default" not in s:
            continue
        css = theme_var(f"--{s['id']}")
        if css is None:
            mismatched.append(f"--{s['id']} is declared nowhere in the theme")
            continue
        # A control can declare `format: em` etc., in which case the CSS
        # carries the unit and the block's default is the bare number -- strip
        # it before comparing rather than let a future unit-bearing control
        # (Task 3's line-height, e.g.) false-positive here.
        css_cmp = css.strip()
        fmt = s.get("format")
        if fmt and css_cmp.endswith(fmt):
            css_cmp = css_cmp[: -len(fmt)]
        default_cmp = s["default"].strip()
        # COMPARE NUMERICALLY WHEN BOTH SIDES PARSE. String equality is a
        # foot-gun once a control's value is a number rather than a class name:
        # "1" != "1.0" and ".46" != "0.46" would fail a control that is
        # actually in sync. Fall back to the string compare for anything that
        # is not a bare number -- a class-select default, say -- where there is
        # no numeric reading to fall back to.
        try:
            mismatch = float(css_cmp) != float(default_cmp)
        except ValueError:
            mismatch = css_cmp != default_cmp
        if mismatch:
            mismatched.append(f"--{s['id']} ships {css.strip()!r} but the "
                              f"@settings block advertises {s['default']!r}")
    if mismatched:
        for m in mismatched:
            bad(m)
    else:
        ok("every control's default matches the value the CSS ships")


def test_inputs_are_never_read_by_a_real_property():
    """An input may only be read by another custom property.

    This is what makes "no setting can break the grid" enforceable rather than
    aspirational. A user value reaches the page only through a derived variable,
    and the derivation is where clamping and round() live. The moment a real
    property reads a --midori-set-* directly, the value has bypassed every
    guard on the way in.
    """
    offenders = []
    for selector, decls in rules():
        for decl in decls.split(";"):
            if "--midori-set-" not in decl:
                continue
            name = decl.split(":", 1)[0].strip()
            if not name.startswith("--"):
                offenders.append(f"{name} in {' '.join(selector.split())[:52]}")
    if offenders:
        for o in offenders:
            bad(f"a real property reads an input directly: {o}")
    else:
        ok("inputs are read only by derived custom properties")


def _length_tokens(value):
    """Split a shorthand CSS value into its space-separated lengths.

    `margin: 0 0 18px 0` needs each length checked on its own -- a naive
    substring/equality check on the whole value would miss a bad length
    sitting next to good ones. Splits respect parens, so `var(--midori-row)`
    (or a future fallback-bearing `var(--x, 24px)`) survives as one token
    rather than being cut on an internal space.
    """
    tokens, depth, cur = [], 0, ""
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch.isspace() and depth == 0:
            if cur:
                tokens.append(cur)
                cur = ""
        else:
            cur += ch
    if cur:
        tokens.append(cur)
    return tokens


def test_rhythm_modes_all_exist():
    """Each rhythm option has rules, and only 'space' and 'both' add a gap.

    The theme's own argument for owning paragraph rhythm is that only the
    grid's owner can keep it on the lattice. That argument survives a setting
    only if every mode is a whole number of rows: an indent costs no height,
    and a gap must cost exactly one row, never a fraction.
    """
    b = settings_block()
    s = next((x for x in (b or {}).get("settings", [])
              if x["id"] == "midori-rhythm"), None)
    if s is None:
        bad("no midori-rhythm control in the @settings block")
        return
    want = ["midori-rhythm-indent", "midori-rhythm-space", "midori-rhythm-both"]
    if s.get("options") != want:
        bad(f"midori-rhythm options are {s.get('options')}, expected {want}")
        return
    gaps = [sel for sel, decls in rules()
            if "midori-rhythm-space" in sel or "midori-rhythm-both" in sel]
    if not gaps:
        bad("no rule gives the 'space' or 'both' modes a paragraph gap")
        return
    # ANY BOX-SPACING PROPERTY, NOT JUST THE THREE margin-* NAMES THE BRIEF'S
    # RULES HAPPENED TO USE. A shorthand (`margin: 0 0 18px 0`) or a
    # different property (padding-bottom, height) can shove a paragraph off
    # the grid exactly the same way, and margin-block/-bottom/-top alone
    # would not have noticed. A shorthand's value is split into its
    # individual lengths, because only one length among several needs to be
    # off-grid to break it.
    for sel, decls in rules():
        if "midori-rhythm-" not in sel:
            continue
        for decl in decls.split(";"):
            name, _, val = decl.partition(":")
            prop = name.strip()
            if not (prop.startswith("margin") or prop.startswith("padding")
                     or prop == "height"):
                continue
            v = val.strip()
            if not v:
                continue
            for tok in _length_tokens(v):
                if tok not in ("0", "0px") and "var(--midori-row)" not in tok:
                    bad(f"a rhythm mode sets {prop}: {v}, which is not "
                        f"a whole row: {' '.join(sel.split())[:50]}")
                    return
    ok("all three rhythm modes exist and every gap is a whole row")


def test_space_rhythm_zeroes_the_indent_variable():
    """The 'space' mode kills the indent through the VARIABLE, not a property.

    The Live Preview indent selector carries eleven class-level components
    (:first-child or :has(), plus five :not() clauses), so any plain
    `text-indent: 0` written against a body class loses the cascade and the
    mode silently does nothing -- which is what shipped, green, until a
    reviewer computed the specificity by hand. Overriding --midori-indent
    instead resolves before any consumer's selector is considered.
    """
    for selector, decls in rules():
        if "midori-rhythm-space" not in selector:
            continue
        for decl in decls.split(";"):
            name, _, val = decl.partition(":")
            if name.strip() == "--midori-indent" and val.strip() in ("0", "0em", "0px"):
                ok("the 'space' mode zeroes --midori-indent, so no consumer indents")
                return
    bad("no rule zeroes --midori-indent for midori-rhythm-space; a plain "
        "text-indent: 0 loses to the eleven-component Live Preview selector")


def test_dot_alpha_is_split_in_both_modes():
    """Both mode blocks must be split, or dark silently stops responding.

    --dotgrid-dot was a whole rgba() literal in each mode. The setting is a
    MULTIPLIER on the shipped per-mode alpha rather than a flat value, because
    0.46 on paper against 0.1748 on dark paper is not an accident -- one flat
    slider would flatten a relationship that was tuned twice. Split one block
    and not the other and the theme still looks right in the mode you tested.
    """
    n_rgb = THEME.count("--dotgrid-dot-rgb:")
    n_alpha = THEME.count("--dotgrid-dot-alpha:")
    if n_rgb < 2 or n_alpha < 2:
        bad(f"--dotgrid-dot is split in {min(n_rgb, n_alpha)} mode block(s); "
            f"both light and dark must be split or one stops responding")
        return
    raw = theme_var("--dotgrid-dot")
    if raw is None or "var(--midori-set-dot-alpha)" not in raw:
        bad(f"--dotgrid-dot is {raw!r}: expected it to multiply "
            "var(--midori-set-dot-alpha)")
        return
    if re.search(r"--dotgrid-dot:\s*rgba\(\s*\d", THEME):
        bad("a --dotgrid-dot declaration is still a literal rgba(), so that "
            "mode ignores the setting")
        return
    ok("the dot alpha is a multiplier on both modes' shipped values")


if __name__ == "__main__":
    print("== prose typography ==")
    test_measure()
    test_settings_block_parses()
    test_settings_ids_are_real()
    test_settings_defaults_match_the_css()
    test_inputs_are_never_read_by_a_real_property()
    test_row_is_one_number()
    test_no_stray_grid_literals()
    test_row_has_a_plain_fallback()
    test_leading_holds_across_the_slider()
    test_row_is_an_even_number_of_pixels()
    test_heading_ladder_is_optical()
    test_blank_line_keeps_the_grid()
    test_indent_excludes_non_prose()
    test_zen_header_rules_are_gated()
    test_rhythm_modes_all_exist()
    test_space_rhythm_zeroes_the_indent_variable()
    test_dot_alpha_is_split_in_both_modes()
    print("prose typography: all green" if not FAIL else "prose typography: failures above")
    sys.exit(1 if FAIL else 0)
