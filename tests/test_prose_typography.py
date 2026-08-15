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
    """
    hits = re.findall(rf"{re.escape(name)}\s*:\s*([^;]+);", THEME)
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


if __name__ == "__main__":
    print("== prose typography ==")
    test_measure()
    print("prose typography: all green" if not FAIL else "prose typography: failures above")
    sys.exit(1 if FAIL else 0)
