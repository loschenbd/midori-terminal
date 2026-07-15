#!/usr/bin/env python3
"""Rewrite Claude Code's hardcoded diff-band colors to the Midori washes.

Operates on the JS that `tweakcc unpack` extracts from the native binary. The
diff renderer (minified fn `eBa`) returns literal `Xl(r,g,b)` colour triples
for add/remove line + word bands, in a light and a dark variant, BYPASSING the
theme token map — so `~/.claude/themes/*.json` can't reach them (Claude Code
issues #66937 / #69445). We match each stock triple by its parenthesised RGB
(capturing whatever minified constructor name precedes it, so a minifier
rename from `Xl` doesn't break us) and swap in the Midori value.

Fails LOUDLY if any stock triple is missing or ambiguous — that means Claude
Code changed its diff palette and the mapping below needs refreshing, NOT that
the patch silently did nothing.
"""
import re
import sys

# stock RGB triple  ->  Midori RGB triple   (midori-paper light / midori-night dark)
PATCHES = [
    # LIGHT (midori-paper)
    ("220,255,220", "201,206,187", "diffAdded       #c9cebb"),
    ("178,255,178", "169,177,151", "diffAddedWord   #a9b197"),
    ("255,220,220", "221,199,183", "diffRemoved     #ddc7b7"),
    ("255,199,199", "206,168,146", "diffRemovedWord #cea892"),
    # DARK (midori-night)
    ("2,40,0",   "54,60,43",  "diffAdded       #363c2b"),
    ("4,71,0",   "75,85,58",  "diffAddedWord   #4b553a"),
    ("61,1,0",   "71,50,38",  "diffRemoved     #473226"),
    ("92,2,0",   "116,75,54", "diffRemovedWord #744b36"),
]


def patch(src: str) -> str:
    for stock, midori, label in PATCHES:
        # capture the constructor name so a minifier rename can't defeat us
        pat = re.compile(r"([A-Za-z_$][\w$]*)\(" + re.escape(stock) + r"\)")
        hits = pat.findall(src)
        if len(hits) != 1:
            raise SystemExit(
                f"ABORT: stock triple ({stock}) [{label}] matched {len(hits)} "
                f"times (expected exactly 1). Claude Code's diff palette likely "
                f"changed — refresh PATCHES in {sys.argv[0]}."
            )
        src = pat.sub(rf"\g<1>({midori})", src, count=1)
    return src


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <extracted.js>")
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        original = f.read()
    patched = patch(original)
    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"patched {len(PATCHES)} diff constants (4 light + 4 dark)")
