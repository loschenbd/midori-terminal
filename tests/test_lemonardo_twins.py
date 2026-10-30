#!/usr/bin/env python3
"""A Lemonardo twin must carry no Midori-only colour.

HOW THESE FILES ARE MADE IS THE BUG. Each twin below is derived from its Midori
counterpart by copying it and changing the colour values, because everything
else in those files -- which herdr version exposes which key, why tmux needs
three separate truecolor settings, which oh-my-posh template field means what --
is design-language-independent and was expensive to learn. Copying is the right
call and it has exactly one failure mode: a value that was missed. The result
looks finished, parses, installs, and renders one surface in the other brand.

That already happened at a larger scale: ghostty/config.lemonardo pointed at
Midori's shader for a day and wore Midori's sage dot lattice, and nothing
reported it.

SO: collect every hex each file declares, and fail if one is a value MIDORI
declares and Lemonardo does not. The asymmetry matters -- the two languages
share no ground, but they may legitimately share a value if both declare it,
and a shared value is not a leak.

WHAT THIS CANNOT SEE. A hex that belongs to neither palette (invented here),
and a value that is Lemonardo's but used in the wrong ROLE. The first is
covered for 4+-file values by tests/test_palette_is_defined.py; the second
needs a human reading the measurement comments beside it.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")

# (lemonardo twin, its midori counterpart). The counterpart is listed so a
# reader can diff them, and so this file fails loudly if one is renamed.
TWINS = [
    ("herdr/config.lemonardo.toml", "herdr/config.toml"),
    ("tmux/lemonardo.tmux.conf", "tmux/midori.tmux.conf"),
    ("prompt/lemonardo.omp.json", "prompt/midori.omp.json"),
    ("ghostty/config.lemonardo", "ghostty/config"),
]

FAIL = 0


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global FAIL
    print(f"  FAIL {msg}")
    FAIL = 1


def declared(theme_stem):
    """Every hex a design language declares: its palette plus its ghostty
    themes (grounds, selection, divider, split fill and all 16 slots)."""
    out = set()
    tpath = ROOT / "themes" / f"{theme_stem}.json"
    if tpath.exists():
        doc = json.loads(tpath.read_text())
        for role in doc.get("palette", {}).values():
            vals = role.values() if isinstance(role, dict) else [role]
            out |= {v.lower() for v in vals
                    if isinstance(v, str) and v.startswith("#")}
    n_themes = 0
    for g in sorted((ROOT / "ghostty" / "themes").glob(f"{theme_stem}-*")):
        out |= {h.lower() for h in HEX.findall(g.read_text())}
        n_themes += 1
    return out, n_themes


def live_hexes(path):
    """Hexes in the file's CODE, not in its prose.

    A comment may quote a Midori value on purpose -- every one of these files
    cites its counterpart's measurements, and forbidding that would delete the
    provenance this repo is built on. So prose is excluded. But excluding it by
    guessing at the first character does not work, and the first version of
    this function proved it: it dropped any line starting with a quote, which
    in tmux is the shape of an if-shell continuation --

        "set -g pane-border-style fg=#44484e" \\

    -- so it reported tmux/lemonardo.tmux.conf as having ZERO live hexes when
    it has exactly two, the only two in the file and the whole point of
    checking it. A guard that excludes the thing it is checking reads the same
    as a guard that passed.

    JSON has no comment syntax, so this repo's convention is a `_comment` array
    of strings; those are dropped by key, not by shape.
    """
    if path.suffix == ".json":
        def strip(o):
            if isinstance(o, dict):
                return {k: strip(v) for k, v in o.items() if k != "_comment"}
            if isinstance(o, list):
                return [strip(v) for v in o]
            return o
        return {h.lower() for h in
                HEX.findall(json.dumps(strip(json.loads(path.read_text()))))}
    live = [l for l in path.read_text().splitlines()
            if not l.lstrip().startswith(("#", "//"))]
    return {h.lower() for h in HEX.findall("\n".join(live))}


def main():
    mid, n_mid = declared("midori")
    lem, n_lem = declared("lemonardo")
    # A COMPARISON AGAINST AN EMPTY SET PASSES EVERYTHING.
    if not mid or not lem:
        bad(f"midori declares {len(mid)} colours and lemonardo {len(lem)} -- "
            f"the reader is broken, not the files")
        print("lemonardo twins: failures above")
        return 1
    if n_mid == 0 or n_lem == 0:
        bad(f"found {n_mid} midori and {n_lem} lemonardo ghostty themes -- "
            f"the glob matched nothing")
        print("lemonardo twins: failures above")
        return 1
    ok(f"midori declares {len(mid)} colours ({n_mid} ghostty themes), "
       f"lemonardo {len(lem)} ({n_lem}); {len(mid & lem)} shared")

    midori_only = mid - lem
    if not midori_only:
        bad("no colour is Midori-only -- the two palettes are identical, so "
            "this check cannot detect anything")
        print("lemonardo twins: failures above")
        return 1

    checked = 0
    for twin, counterpart in TWINS:
        tp, cp = ROOT / twin, ROOT / counterpart
        for p in (tp, cp):
            if not p.exists():
                bad(f"{p.relative_to(ROOT)} does not exist -- a twin pair is "
                    f"broken or a file was renamed")
        if not tp.exists() or not cp.exists():
            continue
        checked += 1
        found = sorted(live_hexes(tp))
        leaked = [h for h in found if h in midori_only]
        if leaked:
            bad(f"{twin}: {', '.join(leaked)} is Midori's and Lemonardo does "
                f"not declare it -- a value was missed when this file was "
                f"derived from {counterpart}")
        else:
            ok(f"{twin}: {len(found)} live hex(es), none Midori-only")

    if checked == 0:
        bad("0 twin pairs examined -- nothing was checked")
    print("lemonardo twins: all green" if not FAIL
          else "lemonardo twins: failures above")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
