#!/usr/bin/env python3
"""The two cursor shaders must differ ONLY in their brand constants.

WHY THIS GUARD EXISTS. ghostty/shaders/rounded-cursor-lemonardo.glsl is a
derivation of rounded-cursor.glsl: same cursor maths, same 24pt lattice
geometry, different grounds, lattice colour and ink. The geometry is
typographic and the two design languages are meant to share it, so the
interesting failure is not "they differ" -- it is the two ways that sharing
rots:

  1. A FIX LANDS IN ONE FILE ONLY. The cursor maths in this repo has been
     wrong twice (BASELINE_LIFT 0.27 tuned against bogus baked dots; the OSC
     112 sentinel that drew the wrong mode's ink). The next such fix will be
     made in whichever file the author had open, and the other will keep the
     bug with no symptom until someone switches design language.
  2. A BRAND VALUE LEAKS ACROSS. Lemonardo ran on Midori's shader and
     inherited Midori's sage lattice for a day, because the grounds are
     matched by DISTANCE, not looked up by theme -- Paintpot sits 0.0372 from
     Midori Paper against a 0.09 tolerance. Nothing reported it. A hex from
     one file appearing in the other is the readable form of that bug.

So: strip comments and `const` declarations from both, require ZERO differing
executable lines, and separately require that neither file names the other
design language's grounds.
"""
import difflib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIDORI = ROOT / "ghostty" / "shaders" / "rounded-cursor.glsl"
LEMON = ROOT / "ghostty" / "shaders" / "rounded-cursor-lemonardo.glsl"

# Grounds each file is allowed to name, from ghostty/themes/*. A hex from the
# other column appearing in a file is a leak.
MIDORI_GROUNDS = {"#f3f1eb", "#1a1917"}
LEMON_GROUNDS = {"#f3eee2", "#2c2a28"}

FAIL = 0


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global FAIL
    print(f"  FAIL {msg}")
    FAIL = 1


def code_lines(path):
    """Executable GLSL: no comments, no blanks, no const declarations."""
    out = []
    for n, ln in enumerate(path.read_text().splitlines(), 1):
        s = ln.strip()
        if not s or s.startswith("//") or s.startswith("const "):
            continue
        out.append((n, ln))
    return out


def main():
    for p in (MIDORI, LEMON):
        if not p.exists():
            bad(f"{p.relative_to(ROOT)} does not exist")
    if FAIL:
        print("lemonardo shader: failures above")
        return 1

    a, b = code_lines(MIDORI), code_lines(LEMON)
    # A COMPARATOR THAT READ NOTHING LOOKS EXACTLY LIKE ONE THAT PASSED.
    if not a or not b:
        bad(f"stripped to {len(a)} and {len(b)} executable lines -- the "
            f"stripper is broken, not the shaders")
        print("lemonardo shader: failures above")
        return 1

    at, bt = [l for _, l in a], [l for _, l in b]
    diff = [l for l in difflib.unified_diff(at, bt, lineterm="")
            if l[:1] in "+-" and l[:3] not in ("---", "+++")]
    if diff:
        bad(f"the two shaders differ in {len(diff)} executable line(s) -- a "
            f"change landed in one file only; port it or re-derive")
        for l in diff[:12]:
            print(f"         {l}")
    else:
        ok(f"{len(at)} executable lines identical across both shaders "
           f"(comments and const blocks excluded by design)")

    for path, own, other, other_name in (
            (MIDORI, MIDORI_GROUNDS, LEMON_GROUNDS, "Lemonardo"),
            (LEMON, LEMON_GROUNDS, MIDORI_GROUNDS, "Midori")):
        text = path.read_text()
        hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", text)}
        # A quotation inside a correction record is how this repo keeps its
        # provenance, so only the CONST lines are policed, not the comments.
        consts = "\n".join(l for l in text.splitlines()
                           if l.strip().startswith("const "))
        chex = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", consts)}
        leaked = sorted(chex & other)
        if leaked:
            bad(f"{path.name} declares {other_name}'s ground(s) "
                f"{', '.join(leaked)} in a const -- the lattice will match the "
                f"wrong design language")
        else:
            ok(f"{path.name}: {len(chex)} const colour(s), none of "
               f"{other_name}'s {len(other)} grounds; {len(hexes)} hex(es) in "
               f"the file overall including comments")
        # BOTH grounds, not "at least one". The first version of this line read
        # `if not own & chex`, and a sabotage walked straight through it: with
        # PAPER_BG replaced by a grey and NIGHT_BG left alone, the file still
        # matched one of its own grounds and the guard reported all green. A
        # shader with one correct ground draws its lattice in exactly one mode,
        # which is the original Lemonardo bug with the modes swapped.
        absent = sorted(own - chex)
        if absent:
            bad(f"{path.name} does not declare its own ground(s) "
                f"{', '.join(absent)} in any const -- the lattice cannot "
                f"match that mode, so nothing was really checked for it")

    print("lemonardo shader: all green" if not FAIL
          else "lemonardo shader: failures above")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
