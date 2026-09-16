#!/usr/bin/env python3
"""Static guards for table and code-block geometry.

SEPARATE FROM test_prose_typography.py BY SUBJECT, NOT BY ACCIDENT. That file
is 1300+ lines about prose -- measure, leading, the heading ladder, the indent
rhythm. Tables and code blocks are blocks, and they now carry enough geometry
of their own to be worth their own file.

HELPERS ARE IMPORTED, NOT COPIED. rules() carries a documented performance trap
(the obvious rule regex has two unbounded quantifiers around a literal and does
not finish against this 90KB stylesheet) and theme_var() carries a documented
correctness trap (this stylesheet's comments quote whole CSS declarations, so a
guard scanning unstripped text can be satisfied by prose discussing the real
thing). Copying either would fork those lessons away from their explanation.

WHAT THESE GUARDS CANNOT DO. Every defect here was a rendered one -- a
specificity contest lost to app.css, text 2.2px from an edge. These prove the
declarations exist; tests/check_rendered_blocks.py proves they take effect.
"""
import re
import sys

from test_prose_typography import FAIL, bad, ok, rules, theme_var

# Obsidian 1.13.7 re-adds a collapsed table's outer edges from these, all 1px,
# through app.css rules that out-specify the theme's own border-width: 0.
BORDER_VARS = ("--table-header-border-width",
               "--table-row-last-border-width",
               "--table-column-first-border-width",
               "--table-column-last-border-width")


def test_table_border_vars_are_zero():
    """All four of Obsidian's table edge widths must be zeroed by the theme.

    MEASURED: with them at their 1px default a five-row table is 122px against
    a wanted 120 and a dense four-column one is 410 against 408 -- in live
    preview AND in reading view -- because each 1px edge adds half its width to
    its row and half to the table in a collapsed-border table. At 0px the same
    tables measure exactly 120 and 408.

    SABOTAGE-PROVED: restoring any one of the four to 1px fails this test
    naming that variable, and deleting the body block fails it naming all four.
    """
    missing = [v for v in BORDER_VARS if theme_var(v) is None]
    if missing:
        bad("the theme never sets " + ", ".join(missing) + "; Obsidian's 1px "
            "default puts a collapsed table 2px off the grid in both views")
        return
    wrong = [(v, theme_var(v)) for v in BORDER_VARS
             if not re.fullmatch(r"0(px)?", theme_var(v).strip())]
    if wrong:
        for name, value in wrong:
            bad(f"{name} is {value!r}, not 0px; a 1px table edge adds half a "
                "pixel to its row and half to the table")
        return
    ok(f"all {len(BORDER_VARS)} Obsidian table edge widths are zeroed")


def test_cells_pad_half_a_row():
    """A cell pads half a row on all four sides, in both views.

    A cell of n lines is then row x n + 2 x (row / 2) = row x (n + 1), so a
    table totals whole rows however its cells wrap -- which is the property the
    old 8px padding lacked: it held on a desktop where every cell is one line
    and broke on a phone where the same cells wrap to two, because the
    line-height term scales with wrapping while a constant does not.

    Half a row is always a whole pixel: the theme rounds the row UP TO 2px (see
    "TWO PIXELS, NOT ONE" in theme.css), so the row is always even.

    THE LIVE-PREVIEW RULE MUST RESTATE IT. .cm-table-widget's own cell rule is
    (0,3,1) and beats the (0,1,1) reading-view rule, so a single declaration
    silently applies to reading view only -- the trap the existing comment in
    theme.css records with !important.

    SABOTAGE-PROVED: changing --midori-cell-pad to 0 fails naming the token;
    deleting the padding from the widget rule fails naming live preview.
    """
    pad = theme_var("--midori-cell-pad")
    if pad is None:
        bad("--midori-cell-pad is not set; a cell needs half a row of padding "
            "on all four sides for a table to total whole rows")
        return
    if not re.fullmatch(r"calc\(\s*var\(--midori-row\)\s*/\s*2\s*\)", pad.strip()):
        bad(f"--midori-cell-pad is {pad!r}; it must be "
            "calc(var(--midori-row) / 2) so it follows the reader's row")
        return

    def pads(selector_needle, extra=None):
        hits = []
        for sel, decls in rules():
            if selector_needle not in sel:
                continue
            if extra and extra not in sel:
                continue
            if re.search(r"(^|;)\s*padding:\s*var\(--midori-cell-pad\)", decls):
                hits.append(sel)
        return hits

    reading = [sel for sel in pads(".markdown-rendered td")]
    if not reading:
        bad("no .markdown-rendered td rule pads var(--midori-cell-pad); "
            "reading-view cells keep Obsidian's 8px and fall off the row")
    widget = [sel for sel in pads(".cm-table-widget td")]
    if not widget:
        bad("no .cm-table-widget td rule pads var(--midori-cell-pad); the "
            "widget's own (0,3,1) cell rule wins and live preview is unfixed")
    if not reading or not widget:
        return
    for sel in widget:
        for one in sel.split(","):
            if ".cm-table-widget" in one and "td" in one and "*" not in one:
                break
        else:
            bad(f"a widget padding rule targets no bare cell: {sel[:70]}")
            return
    ok(f"cells pad half a row in both views ({len(reading)} reading-view rule(s), "
       f"{len(widget)} live-preview rule(s))")


def test_table_colours_derive_from_theme_vars():
    """Rules and the header band derive from theme variables, not literals.

    Both modes then follow for free -- --text-normal and --background-primary
    are already per-mode -- so there is no second copy to forget. theme_vars()
    exists because this stylesheet declares most colour tokens twice, once per
    mode, and a guard built on the last one proves at most one mode is wired;
    deriving instead means there is only ever one declaration to check.

    Cells must also be OPAQUE. --background-primary is the paper the dot grid
    is painted on, so an opaque cell hides the dots inside the table; a
    transparent or alpha cell lets them show through every cell, which is the
    single biggest reason the old tables read as noisy.

    SABOTAGE-PROVED: replacing either token with a hex literal fails naming it.
    """
    for name, needles in (("--table-border-color", ("color-mix", "var(--text-normal)")),
                          ("--midori-table-header-bg", ("color-mix", "var(--text-normal)",
                                                        "var(--background-primary)"))):
        value = theme_var(name)
        if value is None:
            bad(f"{name} is not set; the table rules and header band have no "
                "derived colour and dark mode needs a second copy")
            return
        missing = [n for n in needles if n not in value]
        if missing:
            bad(f"{name} is {value!r}, which does not derive from "
                + ", ".join(missing) + "; a literal here needs a dark-mode copy")
            return

    # A SUBSTRING TEST WOULD NOT BE A CELL TEST. "th" appears in .theme-light,
    # .theme-dark, body.theme-dark and a dozen .mermaid selectors: measured on
    # this stylesheet, 16 selectors contain "td" or "th" and only 3 are cell
    # selectors. None of the other 13 sets a cell background today, so a
    # substring guard would pass for the right reason BY LUCK -- exactly the
    # shape of check this repo has been burned by. Match the element as a token.
    CELL = re.compile(r"(^|[ ,>+~])(td|th)\b")
    HEAD = re.compile(r"(^|[ ,>+~])th\b")
    opaque = [sel for sel, decls in rules()
              if CELL.search(sel)
              and re.search(r"background:\s*var\(--background-primary\)", decls)]
    if not opaque:
        bad("no cell rule sets background: var(--background-primary); the dot "
            "grid shows through every cell")
        return
    banded = [sel for sel, decls in rules()
              if HEAD.search(sel)
              and re.search(r"background:\s*var\(--midori-table-header-bg\)", decls)]
    if not banded:
        bad("no th rule sets background: var(--midori-table-header-bg); the "
            "header differs from the body by weight alone")
        return
    ok(f"table colours derive from theme variables; cells opaque in "
       f"{len(opaque)} rule(s), header banded in {len(banded)}")


if __name__ == "__main__":
    print("== block geometry ==")
    test_table_border_vars_are_zero()
    test_cells_pad_half_a_row()
    test_table_colours_derive_from_theme_vars()
    print("block geometry: all green" if not FAIL else "block geometry: failures above")
    sys.exit(1 if FAIL else 0)
