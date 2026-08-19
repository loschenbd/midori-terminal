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

# THEME with comments stripped, for guards that match property/class names
# against raw text. This file's comments quote CSS constantly -- whole
# declarations, selectors, property names -- so a guard that scans THEME
# directly can be satisfied by a comment that merely discusses the real
# thing instead of the real thing itself. Computed once and shared, the way
# theme_var()/theme_vars() already strip comments internally.
THEME_NC = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)

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


def theme_vars(name):
    """EVERY declaration of a custom property, in source order.

    theme_var returns only the last one, which is a trap in a stylesheet that
    declares most colour tokens twice -- once per mode. A guard built on it
    proves at most one mode is wired: a reviewer deleted the light-mode
    --text-selection override and the whole suite stayed green, because dark's
    copy was textually last and answered for both.

    COMMENTS ARE STRIPPED FIRST, for the same reason theme_var() strips them:
    this file's comments quote CSS, whole declarations included, and a quoted
    declaration matches this pattern exactly as well as a real one. Nothing
    collides today, but this file uses that quoting pattern constantly, and an
    unstripped scan would silently inflate the count the moment a future
    comment quotes one of these properties.
    """
    return [m.group(1).strip()
            for m in re.finditer(re.escape(name) + r"\s*:\s*([^;]+);",
                                 re.sub(r"/\*.*?\*/", "", THEME, flags=re.S))]


def em_value(raw):
    """The em coefficient of a heading size, plain or scaled.

    Task 6 turned the heading ladder into
    `calc(1.870em * var(--midori-set-heading-scale))` so a reader could move
    it. The optical-step check below still wants the em coefficient, at the
    setting's default of 1 -- so calc() around a scale multiply is unwrapped
    rather than read as "not an em" the way a genuinely different unit still
    would be.
    """
    m = re.fullmatch(r"([0-9.]+)em", (raw or "").strip())
    if m:
        return float(m.group(1))
    m = re.fullmatch(
        r"calc\(\s*([0-9.]+)em\s*\*\s*var\(--midori-set-heading-scale\)\s*\)",
        (raw or "").strip())
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
    # THE CONSTANT MUST BE USED, NOT JUST CORRECT ELSEWHERE. The block below
    # this one checks --midori-avg-advance's own VALUE against the measured
    # constant, but that is silent about whether --file-line-width actually
    # MULTIPLIES by it. Delete `* var(--midori-avg-advance)` from the calc and
    # 70 characters silently becomes 70 EM (540px becomes 1120px at a 16px
    # base) while the agreement check below stays green, because
    # --midori-avg-advance is still declared with the right value -- it is
    # simply no longer read by anything.
    if "var(--midori-avg-advance)" not in raw:
        bad(f"--file-line-width is {raw!r}: does not multiply by "
            "var(--midori-avg-advance), so the measure setting is read in "
            "em, not characters -- 70 silently becomes 70em")
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
    """The grid is one variable, and no rule re-hardcodes the number.

    SABOTAGE-PROVED on a scratch copy of the repo:
      - `line-height: 24px` added to a new rule -> FAIL "1 rules still
        hardcode line-height: 24px". Also caught as `line-height:24px`.
      - dot grid reverted to `background-size: 24px 24px` -> FAIL "the dot
        grid still hardcodes 24px 24px".
      - both --midori-row declarations deleted -> FAIL "not defined", plus
        three sibling guards.

    WHAT IT DOES NOT CATCH, BY DESIGN: deleting only the plain `24px`
    fallback. theme_var() returns the textually LAST declaration -- the
    round() one inside @supports -- so this guard cannot see the fallback go.
    test_snapped_vars_all_have_plain_fallbacks is the guard for that, and it
    was proved on exactly that break.

    SABOTAGING THIS FILE HAS A TRAP: theme.css:25 and :232 quote these
    declarations in prose. A replace-first edit hits the COMMENT, the real
    declaration survives, and the suite is correctly green -- which reads as
    "the guard missed it". Any sabotage here must assert which line it edited.
    """
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


def test_snapped_vars_all_have_plain_fallbacks():
    """Every custom property defined inside @supports also has one outside,
    UNDER THE SAME SELECTOR.

    A custom property parses as an arbitrary token stream, so `--x: 24px;
    --x: round(...)` hands the SECOND declaration to every consumer whatever
    the engine supports, and the failure lands at each use site as
    invalid-at-computed-value-time -- the consumer computes to its initial
    value, not to the fallback. var(--x, 24px) does not rescue it either:
    var()'s fallback is for an UNDEFINED property, and this one is defined.

    So the plain declaration OUTSIDE the query is the entire fallback, and
    deleting it is invisible: every other assertion here reads the @supports
    copy and stays green. Measured -- that is exactly what happened before this
    test existed.

    SELECTOR-SCOPED, NOT NAME-ONLY. Which declaration a non-supporting engine
    falls back to is decided by the CASCADE -- by selector, not by property
    name -- so that is what a guard for it has to check. A name-only version
    shipped here first and passed a real regression: deleting
    `body[class*="midori-accent-"] { --midori-accent-hover: var(--midori-accent) }`
    left the suite green, because `.theme-light` and `.theme-dark` ALSO
    declare --midori-accent-hover -- their own pre-accent-select default,
    --midori-sage-hover, a different rule answering a different question, not
    this one's fallback. A reader on an engine without color-mix, with the
    accent set to wine, silently got a SAGE hover: a defined, sane-looking
    value, so nothing crashed and the name-only guard never noticed.

    ONE NORMALISATION BEYOND WHITESPACE: a leading `body` is stripped before
    comparing selectors. Every class/attribute selector in this file is only
    ever applied to <body> -- Style Settings has nowhere else to write a
    class -- so `body.theme-light` and `.theme-light` select the exact same
    element and are the same rule for fallback purposes; only their
    specificity differs, which is irrelevant here. Without this, the
    genuinely-paired --text-selection fallback (`.theme-light { ... }`, no
    `body`) and its @supports override (`body.theme-light { ... }`, and the
    comment directly above it says in so many words that the two compute to
    the same colour) would read as two different selectors, and this guard
    would fail on the file exactly as shipped.
    """
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)

    def norm_selector(sel):
        return re.sub(r"^body(?=[.\[:])", "", " ".join(sel.split()))

    def prop_pairs(text):
        """(normalised selector, custom property) for every declaration in
        text. Mirrors rules(): split on '}', the head before the last '{' is
        the selector -- but scoped to a supplied fragment rather than the
        whole file, so "inside @supports" and "outside @supports" can be
        collected separately."""
        pairs = set()
        for chunk in text.split("}"):
            if "{" not in chunk:
                continue
            selector, _, decls = chunk.rpartition("{")
            sel = norm_selector(selector)
            for decl in decls.split(";"):
                name, sep, _ = decl.partition(":")
                name = name.strip()
                if sep and name.startswith("--"):
                    pairs.add((sel, name))
        return pairs

    inside, spans = set(), []
    for m in re.finditer(r"@supports[^{]*\{", body):
        start = m.end()
        depth, i = 1, start
        while i < len(body) and depth:
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
            i += 1
        inside |= prop_pairs(body[start:i])
        spans.append((m.start(), i))
    outside_text = body
    for s, e in reversed(spans):
        outside_text = outside_text[:s] + outside_text[e:]
    outside = prop_pairs(outside_text)

    missing = sorted(inside - outside)
    if missing:
        for sel, n in missing:
            shown = sel if sel else "body"
            bad(f"{n} is defined inside @supports for selector {shown!r} but "
                f"not outside it: an engine without the feature gets no "
                f"matching fallback for that rule, and either falls back to "
                f"the property's initial value or -- if some unrelated rule "
                f"happens to declare the same property name -- silently picks"
                f" up that rule's value instead")
    else:
        names = sorted({n for _, n in inside})
        ok(f"all {len(inside)} @supports-scoped declarations across "
           f"{len(names)} properties ({', '.join(names)}) have a plain "
           f"fallback under the same selector")


def row_px(base, leading=1.5):
    """Mirror of the CSS: round(up, max(24px, base * leading), 2px).

    LEADING IS A PARAMETER, NOT A HARDCODED 1.5. It used to be baked in, so
    the leading-across-the-slider check only ever modelled the shipped
    DEFAULT -- a reader who actually drags the leading slider to its stated
    minimum was never checked at all.
    """
    return math.ceil(max(24, base * leading) / 2) * 2


def test_leading_stays_above_the_measured_harm_floor():
    """The row's real leading must not fall under the floor this repo actually
    defends -- Rello et al.'s measured CSS ~1.2 -- at the default AND at
    whatever else the Leading slider lets a reader pick.

    RENAMED from test_leading_holds_across_the_slider, and rewritten, because
    an earlier version of this test asserted the wrong floor: WCAG 1.4.8's
    1.5, treated as a number the RENDERED page must reach. It is not that.
    1.4.8 is a Level AAA success criterion, and its own Understanding
    document is explicit that it does not require 1.5 to be rendered:

        "Content is not required to use these values. The requirement is
        that a mechanism is available for users to change these
        presentation aspects. The mechanism can be provided by the browser
        or other user agent. Content is not required to provide the
        mechanism."

    A Leading slider that lets a reader REACH 1.5 -- and go past it, to 2 --
    is that mechanism. Adding the setting moved this theme TOWARD 1.4.8, not
    away from it, and a guard that fails the build because a reader *can
    choose* something below 1.5 has the criterion backwards.

    Nor does the theme claim 1.5 as an unqualified floor to defend: the
    comment above --midori-set-leading in theme.css calls it "a policy floor
    and NOT AN EXPERIMENTAL RESULT" and "defensible rather than optimal",
    and docs/superpowers/specs/2026-08-15-prose-typography-evidence.md is
    blunter still -- "WCAG 1.4.8's 1.5 has no experimental basis in anything
    that survived here... Worth meeting; not a finding."

    THE NUMBER ACTUALLY DEFENDED is Rello et al.'s measured harm floor, CSS
    ~1.2 -- their 0.8 condition (CSS ~0.96) scored significantly worse than
    their 1.0/1.4/1.8 conditions. UNIT TRAP, same one the theme's own comment
    already carries: their "1.0" is Firefox's line-height default of 120% of
    font size, i.e. CSS ~1.2 -- so the tested conditions were ~0.96, ~1.2,
    ~1.68, ~2.16 in CSS terms, and the harmful one was ~0.96, not "1.0".
    Reading their guidance as line-height: 1.0 adopts the condition they
    found harmful.

    Checked at the DEFAULT (1.5) and at the slider's STATED MINIMUM (1.4),
    read from the @settings block rather than re-typed here. This is also
    the branch's own improvement on the pre-branch baseline, not a
    regression: with the row fixed at 24px, real leading was 1.5 at 16px and
    1.33 at 18px and up (README.md ~649) -- already under 1.5, already
    shipped, already argued. At the slider's minimum the worst case is
    1.400, which beats the old fixed-row behaviour at every base from 17px
    up, and comfortably clears the 1.2 floor this repo actually measured.
    """
    raw = theme_var("--midori-row")
    if raw is None or "--font-text-size" not in raw:
        bad(f"--midori-row is {raw!r}: fixed, so leading drops with every "
            "reader who raises their text size, and cannot be checked "
            "against the slider at all")
        return
    b = settings_block()
    s = next((x for x in (b or {}).get("settings", [])
              if x["id"] == "midori-set-leading"), None)
    if s is None:
        bad("no midori-set-leading control in the @settings block")
        return
    default = float(s["default"])
    slider_min = float(s["min"])
    HARM_FLOOR = 1.2  # Rello et al., in CSS terms -- see the docstring

    # A LOCAL flag, not the global FAIL: an unrelated earlier failure must not
    # silently swallow this test's own ok line.
    bad_here = False
    for label, leading in (("default", default), ("slider minimum", slider_min)):
        worst = min(((base, row_px(base, leading) / base) for base in BASES),
                    key=lambda p: p[1])
        failing = [(base, row_px(base, leading) / base) for base in BASES
                  if row_px(base, leading) / base < HARM_FLOOR - 1e-9]
        if failing:
            bad(f"at leading {leading:g} ({label}), {len(failing)} of "
                f"{len(BASES)} base sizes drop under the {HARM_FLOOR:g} "
                f"measured harm floor (Rello et al., CSS terms) -- worst "
                f"{worst[1]:.3f} at {worst[0]}px, e.g. base "
                f"{failing[0][0]}px gives {failing[0][1]:.3f}")
            bad_here = True
        else:
            ok(f"leading >= {HARM_FLOOR:g} across {BASES[0]}-{BASES[-1]}px "
               f"at leading {leading:g} ({label}) (worst {worst[1]:.2f} at "
               f"{worst[0]}px)")


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

    WHITESPACE-NORMALISED BEFORE MATCHING. The declaration is allowed to wrap
    across lines for readability -- see the three-line form in the @supports
    block -- and `.` in this regex does not cross a newline, so an unnormalised
    match would fail on correctly-wrapped source and read as a missing
    round(). The constraint belongs on the regex, not on how the next person
    is allowed to format the CSS.

    SABOTAGE-PROVED on a scratch copy: dropping round() for a bare
    `max(24px, var(--font-text-size) * 1.5)` -> FAIL quoting the value and
    naming the 0.5px baseline error; changing the 2px step to 1px -> FAIL
    "must round UP to 2px, not 1px".
    """
    raw = " ".join((theme_var("--midori-row") or "").split())
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


def max_operands(expr):
    """Top-level comma-separated operands of the first max(...) in expr.

    A SUBSTRING TEST FOR "max(24px" IS WRONG IN BOTH DIRECTIONS, and this
    guard shipped with it. `max(24px * 0, ...)` contains the substring while
    the floor is gone -- sabotaged on a scratch copy, the whole suite stayed
    green. And the declaration is allowed to wrap (the sibling even-row guard
    normalises whitespace and says so), but wrapping turns the text into
    `max( 24px,`, which does NOT contain "max(24px" -- so correct CSS failed
    with "must floor at 24px" while flooring at exactly 24px.

    Splitting into operands answers the question actually being asked: is 24px
    a whole argument of the max, rather than a substring inside one? Depth
    tracking keeps a nested `min(...)` or `calc(...)` comma from splitting an
    operand in half.
    """
    i = expr.find("max(")
    if i < 0:
        return []
    depth, start, out = 0, i + 4, []
    for j in range(i + 4, len(expr)):
        c = expr[j]
        if c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                out.append(expr[start:j].strip())
                return out
            depth -= 1
        elif c == "," and depth == 0:
            out.append(expr[start:j].strip())
            start = j + 1
    return out


def test_leading_setting_is_snapped():
    """The leading slider reaches the row only through round(..., 2px).

    TWO PIXELS, NOT ONE. --dotgrid-offset-y adds HALF the row's growth, so an
    odd row puts the baseline 0.50px off. Measured against the true baseline
    (a zero-size inline-block on vertical-align: baseline, whose rect top IS
    the baseline) at every base in the 10-30 clamp: exact at even rows, -0.50px
    at odd ones, because Chromium rounds half-leading to a whole pixel.

    SCANNED AGAINST THEME_NC, NOT THEME. theme.css:232 quotes two
    --midori-row declarations -- including one containing "round" -- inside a
    comment explaining why the two-declaration form fails. A raw scan over
    THEME finds that quote too, and "keep the last match containing round"
    only reads the real declaration by accident, because the real one happens
    to sit later in the file. Add a later comment that also says "round" and
    the guard would silently start reading prose instead of CSS.

    THE FLOOR CHECK WAS A SUBSTRING TEST AND WAS WRONG BOTH WAYS. It read
    `"max(24px" not in raw`. Sabotaged on a scratch copy:
      - `max(24px * 0, ...)` -- the floor destroyed, the row free to collapse
        below 24px -- kept the substring, and the WHOLE SUITE STAYED GREEN.
      - the same declaration merely wrapped across lines (which the sibling
        even-row guard explicitly permits, and normalises for) becomes
        `max( 24px,`, which does not contain "max(24px", so correct CSS FAILED
        with "must floor at 24px" while flooring at exactly 24px.
    It now asks max_operands() whether 24px is a whole argument. Re-proved
    after the fix: `24px * 0` FAILs and prints the operand list, `20px` FAILs,
    while the wrapped form and `max(var(...), 24px)` -- the floor as second
    operand, equally valid CSS -- both stay green.
    """
    raw = None
    for m in re.finditer(r"--midori-row\s*:\s*([^;]+);", THEME_NC):
        if "round" in m.group(1):
            raw = " ".join(m.group(1).split())
    if raw is None:
        bad("no rounded --midori-row declaration")
        return
    if "var(--midori-set-leading)" not in raw:
        bad(f"--midori-row is {raw!r}: expected it to derive from "
            "var(--midori-set-leading)")
        return
    if not re.search(r"round\(\s*up\s*,.*,\s*2px\s*\)", raw):
        bad(f"--midori-row is {raw!r}: must round UP to 2px, not 1px -- "
            "the dot offset adds half the row's growth")
        return
    if "24px" not in max_operands(raw):
        bad(f"--midori-row is {raw!r}: must floor at 24px "
            f"(max() operands are {max_operands(raw)})")
        return
    b = settings_block()
    s = next((x for x in (b or {}).get("settings", [])
              if x["id"] == "midori-set-leading"), None)
    if s is None:
        bad("no midori-set-leading control in the @settings block")
        return
    if float(s["default"]) != 1.5:
        bad(f"the leading default is {s['default']}, not the shipped 1.5")
        return
    ok(f"leading {s['min']}-{s['max']} reaches the row only through "
       f"round(up, ..., 2px)")


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

    PRESENCE IS NOT ENOUGH FOR THE SLIDERS WHOSE RANGE IS LOAD-BEARING. This
    used to check that min/max/step/default EXIST and nothing about what they
    ARE. The branch's entire mitigation for its one documented unquantised
    path -- an h1's glyph box overflowing its strut -- is "heading scale is
    capped at 1.1", asserted in three prose documents (the @settings
    description, the README, the evidence spec) and enforced by nothing
    executable: `max: 3` in the block above shipped green under the old
    version of this test. SLIDER_BOUNDS below is the executable form of that
    cap, plus the leading slider's 1.4-2 range, which WCAG 1.4.8 and the
    round-up-to-even-row mechanism both depend on staying put.
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
    # id -> (min floor or None, max ceiling or None, why the ceiling/floor
    # matters). Only sliders whose range is load-bearing are listed here --
    # this is not a blanket "ranges never change" rule.
    SLIDER_BOUNDS = {
        "midori-set-heading-scale": (
            None, 1.1,
            "above 1.1 the h1's glyph box overflows the strut further, and "
            "nothing quantises that path"),
        "midori-set-leading": (
            1.4, 2.0,
            "1.4-2 is the range the round-up-to-even-row mechanism and the "
            "WCAG 1.4.8 floor were verified against"),
    }
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
            bounds = SLIDER_BOUNDS.get(s["id"])
            if bounds is not None:
                lo_floor, hi_ceiling, why = bounds
                smin, smax = float(s["min"]), float(s["max"])
                if lo_floor is not None and smin < lo_floor - 1e-9:
                    bad(f"slider {s['id']} min is {smin:g}, below the "
                        f"required floor {lo_floor:g}: {why}")
                    return
                if hi_ceiling is not None and smax > hi_ceiling + 1e-9:
                    bad(f"slider {s['id']} max is {smax:g}, above the "
                        f"required ceiling {hi_ceiling:g}: {why}")
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

    MATCHED AGAINST THEME_NC, NOT THEME. This file's comments quote CSS
    constantly, including bare property and class names in prose (e.g. "the
    --midori-row grid"), so a raw scan can be satisfied by a comment that
    merely mentions the id instead of a real declaration or selector using it.
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
            if f"--{sid}:" not in THEME_NC:
                missing.append(f"{t} {sid} -> --{sid} is never declared")
        elif t == "class-toggle":
            if f".{sid}" not in THEME_NC:
                missing.append(f"class-toggle {sid} -> .{sid} is in no selector")
        elif t == "class-select":
            for opt in s.get("options", []):
                if f".{opt}" not in THEME_NC:
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

    BOTH HALVES BELOW WERE PROVEN VACUOUS BY SABOTAGE, on a scratch copy:

    THE EXISTENCE CHECK used to be "does any rule's SELECTOR mention
    midori-rhythm-space or -both", which `body.midori-rhythm-space
    { --midori-indent: 0; }` satisfies -- it shares the class name and
    declares nothing box-spacing at all. Deleting 'space's actual gap
    selector (`body.midori-rhythm-space .markdown-preview-view p,` off the
    `margin-block: 0 var(--midori-row)` rule) left the suite green. Now a
    match must also DECLARE a margin/padding/height, via _rule_gives_a_gap().

    THE WHOLE-ROW CHECK used to accept any token merely CONTAINING
    "var(--midori-row)", which `calc(var(--midori-row) / 2)` does -- a half
    row, wearing the row variable's name as camouflage. Changing the shipped
    `margin-block: 0 var(--midori-row)` to that halved form left the suite
    green too. Now a token must be exactly "0", "0px", or exactly
    "var(--midori-row)" with nothing wrapped around it; a calc() -- division,
    multiplication, anything -- is rejected rather than pattern-matched.
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

    def _rule_gives_a_gap(decls):
        """True if decls actually sets a non-empty margin/padding/height,
        not merely a rule that happens to share a rhythm-mode class name."""
        for decl in decls.split(";"):
            name, _, val = decl.partition(":")
            prop = name.strip()
            if (prop.startswith("margin") or prop.startswith("padding")
                    or prop == "height") and val.strip():
                return True
        return False

    # EACH MODE, NOT THE PAIR AGGREGATED. An "any rule gives space OR both a
    # gap" check is satisfied by 'both' alone, so deleting 'space's gap
    # selector while 'both' keeps its own left an aggregate check green --
    # measured, on a scratch copy, with exactly that deletion. Each mode is
    # checked on its own so either one going missing is caught by name.
    missing_gap = [cls for cls in ("midori-rhythm-space", "midori-rhythm-both")
                   if not any(cls in sel and _rule_gives_a_gap(decls)
                              for sel, decls in rules())]
    if missing_gap:
        for cls in missing_gap:
            bad(f"no rule gives {cls} a paragraph gap: a rule merely SHARING "
                f"the {cls} class name (e.g. the one zeroing --midori-indent) "
                f"does not count -- it must declare an actual "
                f"margin/padding/height")
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
                # EXACT MATCH, NOT SUBSTRING. "var(--midori-row)" being
                # present somewhere in the token is not the same as the
                # token BEING the row -- calc(var(--midori-row) / 2) contains
                # the substring and is still half a row.
                if tok in ("0", "0px") or tok == "var(--midori-row)":
                    continue
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

    CHECKS EVERY DECLARATION, NOT theme_var()'S LAST ONE. A leftover mode
    literal is always textually last in a two-mode file, so a guard built on
    theme_var() would trip its "expected it to multiply" branch on that
    literal and never reach the message that actually names it as a literal.
    theme_vars() sees every declaration, so a literal is caught wherever it
    sits, and the fix is reported by name instead of read as a missing
    multiply.

    COUNTED PER MODE, NOT JUST COUNTED. `n_rgb >= 2 and n_alpha >= 2` passes
    if both landed in the SAME mode block -- two rgb/alpha pairs under
    .theme-light, none under .theme-dark -- and dark would then read
    whichever earlier declaration the cascade lets through, silently ignoring
    its own tuned values. Confirmed instead against .theme-light and
    .theme-dark specifically, using rules() the way the accent-role checks
    already do.
    """
    n_rgb = THEME.count("--dotgrid-dot-rgb:")
    n_alpha = THEME.count("--dotgrid-dot-alpha:")
    if n_rgb < 2 or n_alpha < 2:
        bad(f"--dotgrid-dot is split in {min(n_rgb, n_alpha)} mode block(s); "
            f"both light and dark must be split or one stops responding")
        return
    mode_decls = {sel: decls for sel, decls in rules()
                  if sel in (".theme-light", ".theme-dark")}
    for mode in (".theme-light", ".theme-dark"):
        decls_for_mode = mode_decls.get(mode, "")
        if ("--dotgrid-dot-rgb:" not in decls_for_mode
                or "--dotgrid-dot-alpha:" not in decls_for_mode):
            bad(f"{mode} declares no --dotgrid-dot-rgb/-alpha of its own; a "
                f"bare count of 2 across the file can be satisfied entirely "
                f"by the OTHER mode, leaving this one silently unresponsive")
            return
    decls = theme_vars("--dotgrid-dot")
    if not decls:
        bad("--dotgrid-dot is not declared")
        return
    bad_here = False
    for raw in decls:
        if re.match(r"rgba\(\s*\d", raw):
            bad("a --dotgrid-dot declaration is still a literal rgba(), so that "
                "mode ignores the setting")
            bad_here = True
        elif "var(--midori-set-dot-alpha)" not in raw:
            bad(f"--dotgrid-dot is {raw!r}: expected it to multiply "
                "var(--midori-set-dot-alpha)")
            bad_here = True
    if not bad_here:
        n = len(decls)
        ok(f"the dot alpha is a multiplier on both modes' shipped values "
           f"({n} declaration{'s' if n != 1 else ''} checked)")


def test_accent_options_are_palette_tokens():
    """Every accent option is an existing token, and none is a new hue.

    'The palette is closed' is a documented decision with an argument behind it:
    the ANSI-16 seam has six chromatic slots and all six are filled, and below
    C 12 hue does almost no work at body size, so an eighth accent would share
    a lightness rung with an existing role and read as a duplicate of it. A
    colour picker here would reopen that silently. A select over the existing
    tokens cannot.

    NOT JUST THAT THE RULE EXISTS -- THAT IT ASSIGNS THE MATCHING TOKEN.
    body.midori-accent-wine { --midori-accent: var(--midori-clay); } used to
    pass this test: the class existed, the token existed, and nothing checked
    that one selector actually points at the other. Eight nearly-identical
    hand-written rules are exactly where a copy-paste swap hides, so the
    correlation is the check that matters.
    """
    b = settings_block()
    s = next((x for x in (b or {}).get("settings", [])
              if x["id"] == "midori-accent"), None)
    if s is None:
        bad("no midori-accent control in the @settings block")
        return
    if s["type"] != "class-select":
        bad(f"midori-accent is {s['type']}; a variable-select writes a STRING, "
            f"which cannot name a colour, and a variable-color reopens the "
            f"closed palette")
        return
    rule_decls = {sel: decls for sel, decls in rules()}
    for opt in s.get("options", []):
        token = opt.replace("midori-accent-", "")
        if f"--midori-{token}:" not in THEME:
            bad(f"accent option {opt} has no --midori-{token} token")
            return
        selector = f"body.{opt}"
        decls = rule_decls.get(selector)
        if decls is None:
            bad(f"accent option {opt} has no body.{opt} rule")
            return
        if not re.search(rf"--midori-accent\s*:\s*var\(--midori-{re.escape(token)}\)",
                          decls):
            bad(f"body.{opt} does not set --midori-accent to "
                f"var(--midori-{token}) -- check for a copy-paste swap")
            return
    ok(f"all {len(s.get('options', []))} accent options are existing palette "
       f"tokens, correctly wired to their own rule")


def test_accent_derived_roles_follow_the_accent():
    """A role documented as accent-derived must read the accent, not a literal.

    --text-selection shipped as rgba(95, 111, 94, 0.25) with the comment
    "--accent (sage) @ 25%" -- true when written, and silently false the moment
    the accent became selectable. Every other accent role turned wine; the
    selection band stayed sage, and no test noticed because the literal was
    still a perfectly valid colour.

    COUNTS THE MODE OVERRIDES, NOT theme_var()'S LAST DECLARATION.
    --text-selection carries the SAME fallback discipline as
    --midori-accent-hover: a plain rgba() literal outside @supports for an
    engine without color-mix, and a var(--midori-accent)-derived override
    inside @supports for EACH of the two colour modes -- so requiring every
    declaration to read the accent would fail on the deliberate literal
    fallbacks. theme_var() answers with whichever declaration is textually
    last, so a guard built on it proves at most one mode's override exists: a
    reviewer deleted only the light-mode override and this suite stayed green,
    because dark's copy came later in the file and answered for both.
    Requiring TWO accent-reading declarations -- one per mode -- catches
    either mode going missing, not just the one that sorts last.

    ACCENT_DERIVED_ROLES IS THE ENUMERATION, AND MUST GROW WHEN A ROLE IS
    ADDED. This test's name promises "every accent-derived colour role", and
    for a while it checked exactly one: three more roles (--tag-background,
    --raised-edge, --dotgrid-accent-wash) shipped as the same kind of stale
    sage literal that --text-selection was, and this test could not have
    caught it -- it never looked at them. Whenever a role is given the same
    color-mix-in-@supports treatment as --text-selection, its name belongs in
    this tuple, or the promise in the docstring is false again.
    """
    ACCENT_DERIVED_ROLES = (
        "--text-selection",
        "--tag-background",
        "--raised-edge",
        "--dotgrid-accent-wash",
    )
    total = 0
    for name in ACCENT_DERIVED_ROLES:
        decls = theme_vars(name)
        if not decls:
            bad(f"{name} is not declared")
            return
        derived = [d for d in decls if "var(--midori-accent)" in d]
        if len(derived) < 2:
            bad(f"{name} reads var(--midori-accent) in only {len(derived)} of "
                f"{len(decls)} declarations: an accent-derived role that does "
                f"not read var(--midori-accent) in BOTH mode overrides stops "
                f"following the accent setting in whichever mode lost it")
            return
        total += len(decls)
    ok(f"every accent-derived colour role reads var(--midori-accent) in both "
       f"mode overrides ({total} declarations checked)")



def test_widget_buffer_is_baseline_anchored():
    """CodeMirror's zero-width buffers must not anchor to the font content area.

    `vertical-align: text-top` ties img.cm-widgetBuffer to the top of the
    parent's FONT CONTENT AREA (font-size x ~0.90), not to the top of its
    inline box (line-height, pinned to one row). Zeroing the buffer's height
    removes its extent but NOT that anchor, so at the h1's 29.92px the content
    area stood 1.5px proud and dragged the line box to 49.5px against a 24px
    row. Measured 3/49 and 1/31 lines off the lattice; baseline takes both
    to 0, across heading scale 0.85..1.1.

    THIS GUARD PROVES THE RULE EXISTS, NOT THAT IT TAKES EFFECT -- the whole
    defect was a rendered line box, invisible to any source check. The
    instrument that actually catches a regression is
    tests/check_rendered_headings.py, which needs a running Obsidian.
    """
    found = [(sel, d) for sel, d in rules()
             if "cm-widgetBuffer" in sel and "vertical-align" in d]
    if not found:
        bad("no rule sets vertical-align on cm-widgetBuffer; the buffer "
            "reverts to CodeMirror's text-top and the h1 leaves the lattice")
        return
    for sel, decls in found:
        m = re.search(r"vertical-align:\s*([^;]+)", decls)
        value = m.group(1).strip() if m else "?"
        if value != "baseline":
            bad(f"cm-widgetBuffer sets vertical-align: {value}; only "
                f"'baseline' keeps the h1 on the row ({sel})")
            return
    ok(f"cm-widgetBuffer is baseline-anchored ({len(found)} rule(s) checked)")

if __name__ == "__main__":
    print("== prose typography ==")
    test_measure()
    test_settings_block_parses()
    test_settings_ids_are_real()
    test_settings_defaults_match_the_css()
    test_inputs_are_never_read_by_a_real_property()
    test_row_is_one_number()
    test_no_stray_grid_literals()
    test_snapped_vars_all_have_plain_fallbacks()
    test_leading_stays_above_the_measured_harm_floor()
    test_row_is_an_even_number_of_pixels()
    test_leading_setting_is_snapped()
    test_heading_ladder_is_optical()
    test_blank_line_keeps_the_grid()
    test_indent_excludes_non_prose()
    test_zen_header_rules_are_gated()
    test_rhythm_modes_all_exist()
    test_space_rhythm_zeroes_the_indent_variable()
    test_dot_alpha_is_split_in_both_modes()
    test_accent_options_are_palette_tokens()
    test_accent_derived_roles_follow_the_accent()
    test_widget_buffer_is_baseline_anchored()
    print("prose typography: all green" if not FAIL else "prose typography: failures above")
    sys.exit(1 if FAIL else 0)
