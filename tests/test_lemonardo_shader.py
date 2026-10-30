#!/usr/bin/env python3
"""The two cursor shaders must share their CURSOR and differ on everything else.

WHY THIS GUARD EXISTS. ghostty/shaders/rounded-cursor-lemonardo.glsl is a
derivation of rounded-cursor.glsl with the dot lattice removed. Two different
things have to hold, and only one of them is a similarity:

  1. THE CURSOR HALF MUST STAY IDENTICAL. The cursor maths in this repo has
     been wrong twice (BASELINE_LIFT 0.27, tuned against bogus baked dots; the
     OSC 112 sentinel that drew the wrong mode's ink). The next such fix will
     be made in whichever file the author had open, and the other keeps the
     bug with no symptom until someone switches design language.

  2. LEMONARDO MUST DECLARE NO GROUND. The lattice is drawn only where a pixel
     MATCHES a ground by RGB distance, so a ground constant IS the lattice's
     on-switch. Lemonardo ran on Midori's shader for a day and inherited
     Midori's sage lattice, because Paintpot #f3eee2 sits 0.0372 from Midori
     Paper against a 0.09 tolerance -- no theme lookup, just a distance that
     happened to be small. Nothing reported it. So the machine-readable form of
     "Lemonardo has no lattice" is "this file declares no ground", and that is
     asserted here rather than left to a reader.

Note the asymmetry: Midori's shader MUST declare both of its grounds (it draws
a real lattice) and Lemonardo's MUST declare none.
"""
import difflib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIDORI = ROOT / "ghostty" / "shaders" / "rounded-cursor.glsl"
LEMON = ROOT / "ghostty" / "shaders" / "rounded-cursor-lemonardo.glsl"

CURSOR_MARK = "---- rounded cursor"
# Every ground any theme in ghostty/themes/ paints. A lattice can only switch
# itself on by matching one of these, so a const naming one is the on-switch.
ALL_GROUNDS = {"#f3f1eb": "midori-paper", "#1a1917": "midori-night",
               "#f3eee2": "lemonardo-paintpot", "#2c2a28": "lemonardo-inkwell"}
MIDORI_OWN = {"#f3f1eb", "#1a1917"}

FAIL = 0


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global FAIL
    print(f"  FAIL {msg}")
    FAIL = 1


def cursor_code(path):
    """Executable GLSL from the cursor marker to the end: no comments, no
    blanks, no const declarations (those are each file's own brand)."""
    # Slice by LINE, not by character offset. str.find lands mid-comment (the
    # marker starts after the "// "), so the first line of the slice arrives
    # without its "//" and survives the comment strip as a fake code line --
    # which is exactly how this comparator first reported a one-line
    # difference between two files whose cursors were identical.
    lines = path.read_text().splitlines()
    i = next((n for n, l in enumerate(lines) if CURSOR_MARK in l), -1)
    if i < 0:
        return None
    out = []
    for ln in lines[i:]:
        s = ln.strip()
        if not s or s.startswith("//") or s.startswith("const "):
            continue
        out.append(ln)
    return out


CONST_VEC3 = re.compile(
    r"const\s+vec3\s+(\w+)\s*=\s*vec3\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,"
    r"\s*([\d.]+)\s*\)\s*/\s*255\.0")


def const_colours(path):
    """{name: #rrggbb} from each const's ACTUAL vec3 VALUE.

    READ THE NUMBERS, NOT THE COMMENT. The first version of this grepped
    `#[0-9a-f]{6}` out of the const lines, which meant it was reading the
    trailing `// #f3f1eb` documentation rather than the vec3 beside it. A
    sabotage walked through it: PAPER_BG's value was changed to a grey, the
    comment was left alone, and the guard reported Midori's lattice intact. The
    inverse is worse -- a ground const written with no comment at all would
    have been invisible to the "Lemonardo declares no ground" assertion, which
    is the one that exists to catch a lattice coming back.

    Returns the parsed value, and the comment is checked against it separately
    below, because a const whose comment and value disagree is a defect in its
    own right: every reader after it takes the comment on trust.
    """
    out, comments = {}, {}
    for ln in path.read_text().splitlines():
        # ONLY REAL CODE LINES. This repo records a removed block by QUOTING it
        # in a comment, and rounded-cursor-lemonardo.glsl quotes the six
        # lattice constants it no longer declares. A search that scans the
        # whole line reads that record as live code: it reported Lemonardo
        # declaring both of its grounds, i.e. a lattice, from the comment
        # explaining that the lattice was deleted.
        if not ln.lstrip().startswith("const "):
            continue
        m = CONST_VEC3.search(ln)
        if not m:
            continue
        name, *chan = m.groups()
        out[name] = "#" + "".join(f"{round(float(c)):02x}" for c in chan)
        said = re.search(r"//.*?(#[0-9a-fA-F]{6})", ln)
        if said:
            comments[name] = said.group(1).lower()
    return out, comments


def main():
    for p in (MIDORI, LEMON):
        if not p.exists():
            bad(f"{p.relative_to(ROOT)} does not exist")
    if FAIL:
        print("lemonardo shader: failures above")
        return 1

    a, b = cursor_code(MIDORI), cursor_code(LEMON)
    for p, c in ((MIDORI, a), (LEMON, b)):
        if c is None:
            bad(f"{p.name} has no {CURSOR_MARK!r} marker -- the comparator "
                f"cannot find the cursor half, so it compared nothing")
    if a is None or b is None:
        print("lemonardo shader: failures above")
        return 1
    # A COMPARATOR THAT READ NOTHING LOOKS EXACTLY LIKE ONE THAT PASSED.
    if len(a) < 10 or len(b) < 10:
        bad(f"the cursor half stripped to {len(a)} and {len(b)} executable "
            f"lines -- under the 10 a real cursor needs, so the stripper is "
            f"broken, not the shaders")
        print("lemonardo shader: failures above")
        return 1

    diff = [l for l in difflib.unified_diff(a, b, lineterm="")
            if l[:1] in "+-" and l[:3] not in ("---", "+++")]
    if diff:
        bad(f"the cursor halves differ in {len(diff)} executable line(s) -- a "
            f"fix landed in one file only; port it")
        for l in diff[:12]:
            print(f"         {l}")
    else:
        ok(f"{len(a)} cursor lines identical across both shaders "
           f"(comments and const blocks excluded by design)")

    # A const whose comment contradicts its value misleads every later reader,
    # and is how the first version of this guard was fooled.
    for path in (MIDORI, LEMON):
        vals, said = const_colours(path)
        if not vals:
            bad(f"{path.name}: 0 const vec3 colours parsed -- the parser is "
                f"broken, not the shader")
        for name, c in sorted(said.items()):
            if c != vals[name]:
                bad(f"{path.name}: {name} is {vals[name]} but its comment "
                    f"says {c} -- correct one to match the other")
        ok(f"{path.name}: {len(vals)} const colour(s) parsed from their vec3 "
           f"values, {len(said)} with a hex comment, all agreeing"
           if not FAIL else f"{path.name}: comment/value mismatch above")

    # Midori draws a lattice, so it must name both of its own grounds.
    mc = set(const_colours(MIDORI)[0].values())
    absent = sorted(MIDORI_OWN - mc)
    if absent:
        bad(f"{MIDORI.name} does not declare its own ground(s) "
            f"{', '.join(absent)} in any const -- its lattice cannot match "
            f"that mode, so nothing was really checked for it")
    else:
        ok(f"{MIDORI.name} declares both of its grounds ({len(mc)} const "
           f"colours in all) -- its lattice is intact")

    # Lemonardo draws none, so it must name NO ground at all. This is the
    # assertion that would have caught the original bug.
    lc = set(const_colours(LEMON)[0].values())
    found = sorted(lc & set(ALL_GROUNDS))
    if found:
        bad(f"{LEMON.name} declares ground(s) "
            + ", ".join(f"{h} ({ALL_GROUNDS[h]})" for h in found)
            + " in a const -- a ground constant is a lattice's on-switch, and "
              "Lemonardo is specified to draw none (see the shader header)")
    else:
        ok(f"{LEMON.name} declares no ground of any theme "
           f"({len(lc)} const colours, all cursor ink) -- no lattice")
    if "mix(fragColor.rgb" in LEMON.read_text():
        bad(f"{LEMON.name} composites into fragColor.rgb -- that is a lattice "
            f"draw; the cursor writes fragColor whole")

    print("lemonardo shader: all green" if not FAIL
          else "lemonardo shader: failures above")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
