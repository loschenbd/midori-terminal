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


if __name__ == "__main__":
    print("== block geometry ==")
    test_table_border_vars_are_zero()
    print("block geometry: all green" if not FAIL else "block geometry: failures above")
    sys.exit(1 if FAIL else 0)
