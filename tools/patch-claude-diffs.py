#!/usr/bin/env python3
"""Rewrite Claude Code's hardcoded diff + inline-code + suggestion colours to Midori.

Operates on the JS that `tweakcc unpack` extracts from the native binary. Three
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

3. The `suggestion` token — tips, ghost-text, and other hints render via the
   SAME broken helper: `<helper>("suggestion",<mode>)(text)`. Because `UX`
   discards custom overrides, midori's `suggestion` (#3a5572 light / #6c87a4
   dark) never applies and stock periwinkle rgb(87,105,247) shows — e.g. the
   blue `ultracode` keyword in the workflow tip. Same fix as codespan, but the
   mode arg varies per call site (`e.theme` / `d.theme` / `ey`), so we capture
   it and reuse it for the per-mode pick. All call sites are rewritten, so the
   theme's dead `suggestion` value finally takes effect everywhere.

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

# Per-mode midori suggestion colour (indigo ink), injected into every
# `<helper>("suggestion",<mode>)`. `<mode>` is captured (\2) so the dark check
# reuses the same base-mode string zn already receives — mirrors MIDORI_CODESPAN.
MIDORI_SUGGESTION_LIGHT = "#3a5572"
MIDORI_SUGGESTION_DARK = "#6c87a4"
# Skip marker: only the patched suggestion calls carry `.theme.includes("dark")`
# (codespan uses bare `t.includes`), so its presence means we already ran.
SUGGESTION_MARKER = f'.theme.includes("dark")?"{MIDORI_SUGGESTION_DARK}":"{MIDORI_SUGGESTION_LIGHT}"'

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


# `<helper>("suggestion",<mode>)` — helper name (\1) and mode arg (\2) captured.
# <mode> is a dotted/plain ident (e.theme, d.theme, ey), never a literal, so the
# regex won't re-match our own `#`-literal output.
_SUGGESTION_RE = re.compile(
    r'([A-Za-z_$][\w$]*)\("suggestion",([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\)'
)


def _apply_suggestion(src):
    hits = _SUGGESTION_RE.findall(src)
    if not hits:
        if SUGGESTION_MARKER in src:
            return src, "skip", 0  # already patched
        raise SystemExit(
            'ABORT: no <helper>("suggestion",<mode>) calls found (expected >=1). '
            f"Claude Code changed the suggestion render path — refresh {sys.argv[0]}."
        )
    repl = (
        rf'\g<1>(\g<2>.includes("dark")?"{MIDORI_SUGGESTION_DARK}":'
        rf'"{MIDORI_SUGGESTION_LIGHT}",\g<2>)'
    )
    return _SUGGESTION_RE.sub(repl, src), "patch", len(hits)


def patch(src: str) -> str:
    patched = skipped = 0
    for stock, midori, label in TRIPLE_PATCHES:
        src, r = _apply_triple(src, stock, midori, label)
        patched += r == "patch"; skipped += r == "skip"
    for stock_re, repl, label in CALL_PATCHES:
        src, r = _apply_call(src, stock_re, repl, label)
        patched += r == "patch"; skipped += r == "skip"
    src, r, n = _apply_suggestion(src)
    patched += r == "patch"; skipped += r == "skip"
    if r == "patch":
        print(f"suggestion (indigo ink): {n} call sites rewritten")
    print(f"diff+inline+suggestion patches: {patched} applied, {skipped} already present")
    return src


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <extracted.js>")
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        original = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(patch(original))
