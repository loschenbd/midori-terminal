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


def test_measure():
    """The measure, in characters, and in a unit that survives its consumers.

    app.css applies --file-line-width as max-width on .cm-line, and .cm-line is
    also the heading element (.HyperMD-header-1 sets font-size: var(--h1-size)
    on it). An em there resolves against the element's OWN font-size, so an em
    measure gives heading lines a wider column than body lines: measured, 34em
    is 544px on a body line and 880px on an h1. calc(var(--font-text-size) * N)
    resolves numerically before it reaches any consumer.
    """
    raw = theme_var("--file-line-width")
    if raw is None:
        bad("--file-line-width is not set; Obsidian's 700px default is ~91 cpl at 16px")
        return
    if em_value(raw) is not None:
        bad(f"--file-line-width is {raw!r}: an em measure is resolved against the "
            "font-size of .cm-line, which is 1.618em on a heading line")
        return
    m = re.fullmatch(r"calc\(\s*var\(--font-text-size\)\s*\*\s*([0-9.]+)\s*\)", raw)
    if not m:
        bad(f"--file-line-width is {raw!r}: expected "
            "calc(var(--font-text-size) * N), which both tracks the reader's "
            "text size and is immune to the consuming element's font-size")
        return
    cpl = float(m.group(1)) / AVG_ADVANCE_EM
    if 55.0 <= cpl <= 75.0:
        ok(f"measure {raw} = {cpl:.1f} characters per line, inside 55-75")
    else:
        bad(f"measure {raw} = {cpl:.1f} characters per line, outside 55-75")


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

    When the row becomes a function of the reader's text size (Task 3), any
    literal 24px or 48px that measures vertical space or padding will break:
    the row will grow and the literal won't, pushing lines off the grid.

    Allowances are explicit: --midori-row's own declaration, and
    body.is-ios --midori-line-box, which is the caret plugin's band constant,
    measured separately against the title's 22px box, not the row.
    """
    # Strip comments: the design record mentions 24px in prose, which is fine.
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)

    ALLOWED = (
        "--midori-row",        # the row's own declaration
        "--dotgrid-offset-y",  # was measured against 24px; now an offset from it
        "--midori-line-box",   # body.is-ios; the caret plugin's band constant,
                               # measured against the title's 22px box, not the row
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
            if re.search(r"\b(?:24|48)px\b", value):
                non_allowed.append(f"{prop.strip()}: {value.strip()}")

    if non_allowed:
        bad(f"{len(non_allowed)} properties still use literal 24px/48px")
        for decl in non_allowed[:5]:
            bad(f"  {decl}")
        if len(non_allowed) > 5:
            bad(f"  ... and {len(non_allowed) - 5} more")
    else:
        ok("all grid dimensions use var(--midori-row) or calc(...var(--midori-row)...)")
        ok("  (except body.is-ios --midori-line-box: 24px, which is the caret plugin's constant)")


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
    """Every (selector, declarations) pair in theme.css, comments stripped.

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


def test_zen_header_rules_are_gated():
    """A zen rule that compensates for the view header must check it exists.

    app.css: `body:not(.show-view-header):not(.is-phone) .view-header
    { display: none }`. With the setting off there is no header, so an
    ungated `padding-top: var(--header-height)` adds a header's worth of
    empty space above the note and shifts the dot grid to match.
    """
    ungated = []
    for selector, decls in rules():
        if "body.zen-mode" not in selector:
            continue
        if "--header-height" in decls and "show-view-header" not in selector:
            ungated.append(selector[:70])
    if ungated:
        for sel in ungated:
            bad(f"zen rule uses --header-height but is not gated on "
                f".show-view-header: {sel}")
    else:
        ok("every zen rule that compensates for the view header checks it exists")


if __name__ == "__main__":
    print("== prose typography ==")
    test_measure()
    test_row_is_one_number()
    test_no_stray_grid_literals()
    test_leading_holds_across_the_slider()
    test_row_is_an_even_number_of_pixels()
    test_heading_ladder_is_optical()
    test_zen_header_rules_are_gated()
    print("prose typography: all green" if not FAIL else "prose typography: failures above")
    sys.exit(1 if FAIL else 0)
