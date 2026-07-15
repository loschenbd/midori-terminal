#!/usr/bin/env python3
"""Rewrite Claude Code's hardcoded diff + inline-code colours to Midori.

Operates on the JS that `tweakcc unpack` extracts from the native binary. Two
render paths bypass the theme token map (`~/.claude/themes/*.json` can't reach
them — Claude Code issues #66937 / #69445), so the only lever is the binary:

1. Diff bands — minified fn `eBa` returns literal `Xl(r,g,b)` triples for the
   add/remove line + word bands (a light and a dark variant). Matched by their
   parenthesised RGB, capturing whatever minified constructor name precedes the
   paren so a rename from `Xl` can't defeat us.

2. Inline code (`` `codespan` ``) — rendered by `<helper>("permission",t)(e.text)`.
   `<helper>(name,t)` looks up `UX(t)[name]`, but `UX` switches on the base-mode
   NAME ("light"/"dark"/…) and discards custom overrides, so midori's
   `permission` never applies and stock ansi-blue shows. `t` at the call site
   IS the base-mode string, so we swap the token for a literal chosen per mode
   (values starting with `#` bypass the broken lookup). The minified helper
   name churns between releases (Ro in 2.1.202, Zn in 2.1.210), so we capture
   it rather than hardcode it — same tactic as the diff constructor.

Idempotent: each patch is skipped if already applied, replaced if stock is
present, and FAILS LOUDLY if neither is found (Claude Code changed the code —
refresh the mappings, don't silently no-op).
"""
import re
import sys

# (stock RGB triple, Midori RGB triple, label) — midori-paper light / night dark
TRIPLE_PATCHES = [
    ("220,255,220", "201,206,187", "diffAdded       #c9cebb"),
    ("178,255,178", "169,177,151", "diffAddedWord   #a9b197"),
    ("255,220,220", "221,199,183", "diffRemoved     #ddc7b7"),
    ("255,199,199", "206,168,146", "diffRemovedWord #cea892"),
    ("2,40,0",   "54,60,43",  "diffAdded(dark)     #363c2b"),
    ("4,71,0",   "75,85,58",  "diffAddedWord(dark) #4b553a"),
    ("61,1,0",   "71,50,38",  "diffRemoved(dark)   #473226"),
    ("92,2,0",   "116,75,54", "diffRemovedWord(dark) #744b36"),
]

# Per-mode midori inline-code colour, injected into `<helper>("permission",t)`.
MIDORI_CODESPAN = 't.includes("dark")?"#6c87a4":"#3a5572"'  # light #3a5572 / dark #6c87a4

# (stock-call regex, replacement template, label) — helper name captured as \1
CALL_PATCHES = [
    (r'([A-Za-z_$][\w$]*)\("permission",t\)',
     rf'\g<1>({MIDORI_CODESPAN},t)',
     "codespan inline-code colour (per-mode)"),
]


def _apply_triple(src, stock, midori, label):
    if re.search(r"[A-Za-z_$][\w$]*\(" + re.escape(midori) + r"\)", src):
        return src, "skip"  # already patched
    pat = re.compile(r"([A-Za-z_$][\w$]*)\(" + re.escape(stock) + r"\)")
    hits = pat.findall(src)
    if len(hits) != 1:
        raise SystemExit(
            f"ABORT: stock triple ({stock}) [{label}] matched {len(hits)}x "
            f"(expected 1). Claude Code's palette changed — refresh {sys.argv[0]}."
        )
    return pat.sub(rf"\g<1>({midori})", src, count=1), "patch"


def _apply_call(src, stock_re, repl, label):
    if MIDORI_CODESPAN in src:
        return src, "skip"  # already patched
    pat = re.compile(stock_re)
    hits = pat.findall(src)
    if len(hits) != 1:
        raise SystemExit(
            f"ABORT: stock call [{label}] matched {len(hits)}x (expected 1). "
            f"Claude Code changed — refresh {sys.argv[0]}."
        )
    return pat.sub(repl, src, count=1), "patch"


def patch(src: str) -> str:
    patched = skipped = 0
    for stock, midori, label in TRIPLE_PATCHES:
        src, r = _apply_triple(src, stock, midori, label)
        patched += r == "patch"; skipped += r == "skip"
    for stock_re, repl, label in CALL_PATCHES:
        src, r = _apply_call(src, stock_re, repl, label)
        patched += r == "patch"; skipped += r == "skip"
    print(f"diff+inline patches: {patched} applied, {skipped} already present")
    return src


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <extracted.js>")
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        original = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(patch(original))
