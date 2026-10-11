#!/usr/bin/env python3
"""The Lemonardo ghostty themes must still be what their rules produce.

TWO SEPARATE FAILURES THIS CATCHES, and they are not the same failure.

  1. A HAND EDIT. Someone opens ghostty/themes/lemonardo-inkwell, nudges a
     hex, and the file is now a colour nobody can re-derive -- the exact state
     the first Lemonardo ANSI map was in, which is how ten of its thirty-two
     slots came to sit within dE 10 of Midori's without anyone noticing.

  2. A RULE CHANGE THAT BREAKS A GATE. Someone widens a chroma cap or moves an
     anchor hue, every file regenerates cleanly, and a slot quietly lands back
     on top of a Midori value. The byte comparison alone would pass that,
     because the file and the rules would agree. So the gates are re-evaluated
     here too, not just the file contents.

The colour arithmetic itself is checked by tools/colorspace.py's own selftest
against published CIEDE2000 pairs and WCAG anchors; this file assumes it and
checks the palette. Both are in lint.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAIL = 0


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global FAIL
    print(f"  FAIL {msg}")
    FAIL = 1


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    print("== the colour arithmetic the palette is built on ==")
    cs = load("tools/colorspace.py", "colorspace")
    if cs.selftest(verbose=False):
        bad("tools/colorspace.py selftest failed -- every number below is "
            "suspect until that is fixed")
        print("lemonardo ansi: failures above")
        return 1
    ok("tools/colorspace.py selftest passed")

    gen = load("tools/make-lemonardo-ansi.py", "make_lemonardo_ansi")
    import json
    theme = json.loads((ROOT / "themes" / "lemonardo.json").read_text())

    print("\n== the themes match what the rules produce ==")
    modes = sorted(gen.MODES)
    if not modes:
        bad("the generator declares no modes -- nothing was checked")
        print("lemonardo ansi: failures above")
        return 1

    gates = 0
    for mode_id in modes:
        built = gen.build(mode_id, theme)
        path = ROOT / "ghostty" / "themes" / built["id"]
        if not path.exists():
            bad(f"{path.name} does not exist -- run "
                f"tools/make-lemonardo-ansi.py --write")
            continue
        want = gen.emit(built)
        got = path.read_text()
        if got == want:
            ok(f"{path.name} is byte-identical to its rules "
               f"({len(want.splitlines())} lines)")
        else:
            wl, gl = want.splitlines(), got.splitlines()
            first = next((i for i in range(max(len(wl), len(gl)))
                          if wl[i:i + 1] != gl[i:i + 1]), 0)
            bad(f"{path.name} differs from its rules, first at line "
                f"{first + 1}:\n"
                f"         on disk: {gl[first] if first < len(gl) else '<eof>'}\n"
                f"         rules:   {wl[first] if first < len(wl) else '<eof>'}")

        rows = gen.measure(built)
        failing = [r for r in rows if not r[0]]
        gates += len(rows)
        if not rows:
            bad(f"{built['id']}: zero gates evaluated")
        elif failing:
            bad(f"{built['id']}: {len(failing)} of {len(rows)} gates failing")
            for _, label, detail in failing:
                print(f"         {label}: {detail}")
        else:
            ok(f"{built['id']}: all {len(rows)} gates pass")

    # A GUARD THAT EVALUATED NOTHING LOOKS EXACTLY LIKE ONE THAT PASSED.
    if gates == 0:
        bad("0 gates evaluated in total -- the check examined nothing")
    else:
        ok(f"{gates} gate(s) evaluated across {len(modes)} mode(s)")

    print("lemonardo ansi: all green" if not FAIL
          else "lemonardo ansi: failures above")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
