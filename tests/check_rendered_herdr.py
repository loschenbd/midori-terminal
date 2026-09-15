"""Attribute every glyph in a herdr render to its (fg, bg) pair, and fail on the
colours the Midori herdr config exists to eliminate.

    usage: check_rendered_herdr.py <capture.ansi> [expected-hex ...]

<capture.ansi> is `tmux capture-pane -p -e` output of a running herdr; the
isolated capture recipe is in herdr/README.md, "Verifying". Needs a render, so
like the other check_rendered_* scripts it is deliberately not in lint.

Pass the per-appearance surfaces you expect to see, e.g. '#ced1c8' '#e1dfd9'
for a light capture. Exits 1 if any expected hex is absent, if a banned role is
present, or if no cells were parsed at all (an empty capture must not pass).

Sabotage-proven, Sept 2026, herdr 0.9.0, 1010-cell captures:
  * auto_switch = false  -> FAILS: "bg ansi8" (58 cells), "fg ansi8 on accent"
    (8 cells), both expected hexes missing. The light/dark blocks only apply
    under auto_switch, so every surface fell back to the ANSI 8 slab.
  * overlay0 + subtext0 removed -> FAILS: "fg ansi7" (41 cells).
  * a light capture checked for the night surface '#40453d' -> FAILS (missing).
"""
import re
import sys
from collections import Counter, defaultdict

NAMED = {**{30 + i: f"ansi{i}" for i in range(8)}, **{90 + i: f"ansi{8 + i}" for i in range(8)}}
NAMED_BG = {**{40 + i: f"ansi{i}" for i in range(8)}, **{100 + i: f"ansi{8 + i}" for i in range(8)}}


# What herdr's "terminal" base emits for the roles Midori re-points. ANSI 8 as a
# FOREGROUND is intended (darkgray = Midori dim text); as a background it is the
# slab, and as text on the sage accent it is the 1.22:1 tab label. ANSI 7/15
# (Gray/White) are near-white and must not appear at all.
def banned(fg, bg):
    hits = []
    if bg in ("ansi7", "ansi8", "ansi15"):
        hits.append(f"bg {bg}")
    if fg in ("ansi7", "ansi15"):
        hits.append(f"fg {fg}")
    if fg == "ansi8" and bg == "ansi2":
        hits.append("fg ansi8 on accent")
    return hits


def parse(text):
    fg = bg = "default"
    cells = []
    for row, line in enumerate(text.split("\n")):
        i = 0
        while i < len(line):
            m = re.match(r"\x1b\[([0-9;]*)m", line[i:])
            if m:
                params = [int(p) if p else 0 for p in m.group(1).split(";")]
                j = 0
                while j < len(params):
                    p = params[j]
                    if p == 0:
                        fg = bg = "default"
                    elif p in (38, 48) and j + 1 < len(params):
                        if params[j + 1] == 2:
                            val = "#%02x%02x%02x" % tuple(params[j + 2:j + 5])
                            j += 4
                        else:
                            val = f"idx{params[j + 2]}"
                            j += 2
                        if p == 38:
                            fg = val
                        else:
                            bg = val
                    elif p == 39:
                        fg = "default"
                    elif p == 49:
                        bg = "default"
                    elif p in NAMED:
                        fg = NAMED[p]
                    elif p in NAMED_BG:
                        bg = NAMED_BG[p]
                    j += 1
                i += len(m.group(0))
                continue
            cells.append((row, line[i], fg, bg))
            i += 1
    return cells


def main():
    cells = parse(open(sys.argv[1], encoding="utf-8", errors="replace").read())
    pairs = Counter((f, b) for _, ch, f, b in cells if ch != " " or b != "default")
    samples = defaultdict(str)
    for _, ch, f, b in cells:
        if len(samples[(f, b)]) < 34:
            samples[(f, b)] += ch
    print(f"{len(cells)} cells parsed")
    for (f, b), n in pairs.most_common():
        hits = banned(f, b)
        flag = f"  <-- BANNED: {', '.join(hits)}" if hits else ""
        print(f"  fg={f:9} bg={b:9} {n:5}  {samples[(f, b)].strip()[:34]!r}{flag}")
    seen = {c for _, _, f, b in cells for c in (f, b)}
    missing = [h for h in sys.argv[2:] if h.lower() not in seen]
    bad = sorted({h for (f, b) in pairs for h in banned(f, b)})
    print("banned roles present:", bad or "none")
    print("expected hexes missing:", missing or "none")
    sys.exit(1 if (missing or bad or not cells) else 0)


if __name__ == "__main__":
    main()
