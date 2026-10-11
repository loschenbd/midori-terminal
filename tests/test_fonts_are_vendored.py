#!/usr/bin/env python3
"""Every custom family a theme NAMES must be a file in fonts/.

THE GAP THIS CLOSES. themes/lemonardo.json named Besley, Instrument Sans,
Special Elite and Reenie Beanie in its `type` stacks from the day it landed,
and fonts/ carried none of them, so install.sh installed none of them. Nothing
reported it: a CSS stack falls through to its next entry, and Ghostty resolves
an unknown family to its bundled default and exits 0 from +validate-config.
The theme looked correct in every file and rendered in the wrong faces.

This is the same shape as the bug where ghostty/themes/ held two Lemonardo
themes that install.sh's hand-written list never copied -- a declaration with
no delivery -- which is why install.sh now globs both directories.

WHAT COUNTS AS A CUSTOM FAMILY. Only the QUOTED entries and the first bare one
in each stack. `ui-serif`, `system-ui`, `Georgia`, `Menlo`, `monospace` and the
rest are generics or OS faces that a theme deliberately falls back to; demanding
those be vendored would be wrong, and shipping Georgia would be illegal.

WHAT THIS DOES NOT CHECK. That the file is INSTALLED, or that the machine can
resolve the name -- both are properties of a machine, not of the repo, so they
belong in install.sh's output and in a CoreText probe, not in lint.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
ROLES = ("ui", "heading", "body", "label", "aside", "mono")

# Generic CSS families and faces every OS ships. A theme naming one is
# declaring a FALLBACK, not a dependency.
GENERIC = {
    "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded", "system-ui",
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "-apple-system",
    "BlinkMacSystemFont", "Georgia", "Menlo", "Monaco", "Helvetica",
    "Helvetica Neue", "Arial", "Times", "Times New Roman", "Courier",
    "Courier New", "Segoe UI", "Roboto", "Consolas", "Cambria",
}

FAIL = 0


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global FAIL
    print(f"  FAIL {msg}")
    FAIL = 1


def families(stack):
    """The custom families in one CSS font stack, in order.

    A quoted entry is always custom -- the quotes are there because the name
    has a space. An unquoted entry is custom only in FIRST position: that is
    how `Besley, ui-serif, Georgia, serif` names one.
    """
    out = []
    for i, part in enumerate(p.strip() for p in stack.split(",")):
        unq = part.strip('"\'')
        if unq in GENERIC:
            continue
        if part.startswith(('"', "'")) or i == 0:
            out.append(unq)
    return out


def vendored():
    """{family: [files]} from the TTFs in fonts/, by their internal name."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("  skip fontTools not available -- family names unreadable")
        return None
    out = {}
    for f in sorted(FONTS.glob("*.ttf")):
        try:
            n = TTFont(f, lazy=True)["name"]
        except Exception as e:
            bad(f"fonts/{f.name} is not readable as a font: {e}")
            continue
        fam = n.getDebugName(16) or n.getDebugName(1)
        out.setdefault(fam, []).append(f.name)
    return out


def main():
    themes = sorted((ROOT / "themes").glob("*.json"))
    if not themes:
        bad("no themes/*.json found -- the scan examined nothing")
        print("fonts vendored: failures above")
        return 1

    have = vendored()
    if have is None:
        print("fonts vendored: skipped")
        return 0
    # A SCAN THAT FOUND NO FONTS LOOKS EXACTLY LIKE ONE WHERE NONE ARE NEEDED.
    if not have:
        bad(f"fonts/ yielded 0 readable families from "
            f"{len(list(FONTS.glob('*.ttf')))} ttf(s) -- the reader is broken")
        print("fonts vendored: failures above")
        return 1
    ok(f"fonts/ carries {len(have)} famil(ies) across "
       f"{sum(len(v) for v in have.values())} file(s): {', '.join(sorted(have))}")

    wanted = 0
    for tpath in themes:
        doc = json.loads(tpath.read_text())
        stacks = doc.get("type", {})
        named = []
        for role in ROLES:
            if isinstance(stacks.get(role), str):
                named += [(role, f) for f in families(stacks[role])]
        if not named:
            bad(f"{tpath.name} names no custom family in any of {ROLES} -- "
                f"either the theme has no type block or the parser is broken")
            continue
        seen = set()
        for role, fam in named:
            wanted += 1
            if fam in seen:
                continue
            seen.add(fam)
            if fam in have:
                ok(f"{tpath.stem}: {role:7} {fam:16} -> "
                   f"{', '.join(have[fam])}")
            else:
                bad(f"{tpath.stem}: {role:7} {fam!r} is named by the theme but "
                    f"no file in fonts/ carries that family -- install.sh will "
                    f"not install it and the stack will fall through silently")

    if wanted == 0:
        bad("0 families examined across all themes -- nothing was checked")
    print("fonts vendored: all green" if not FAIL
          else "fonts vendored: failures above")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
