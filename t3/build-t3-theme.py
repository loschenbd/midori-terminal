#!/usr/bin/env python3
"""Emit the Midori theme file for T3 Code (github.com/pingdotgg/t3code).

    ./t3/build-t3-theme.py          # writes t3/midori-t3.json
    ./t3/build-t3-theme.py --check  # verify the committed file matches

THE SCHEMA BELOW WAS READ OUT OF THE SHIPPED BUNDLE, NOT OUT OF THE DOCS.
As of t3@0.0.33 the documentation (pingdotgg-t3code.mintlify.app) does not
mention theming at all, while the app carries a full theme editor and a
file-import path. Everything asserted here was recovered from the minified
client at package/dist/client/assets/index-*.js and is cited by the validator
it produced, so a future reader can re-derive it rather than trust it:

  version      must be exactly 1, or "unsupported version. Expected 1."
  name         1-48 chars after trim
  id           optional; /^[a-z0-9](?:[a-z0-9-]{0,47})$/, derived from name if
               omitted. Reserved: system, light, dark, t3-grove, t3-ocean,
               t3-ember, t3-iris (plus the default t3-chat).
  appearance   exactly "light" or "dark"
  colors       object, >= 1 role. Unknown role THROWS. Value must match
               /^#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i -- HEX ONLY.
               rgb(), oklch() and named colours are all rejected.
  variants     optional; keys "light"/"dark" only, and must NOT repeat the
               base appearance. This is how ONE theme carries both modes.

TWO IMPORT PATHS WITH DIFFERENT STRICTNESS, which matters for debugging.
Importing a theme FILE validates strictly and throws a named error. But a
theme written straight into localStorage["t3code:themes:v1"] goes through a
different validator that SILENTLY DROPS any unknown key and any malformed
value, falling back to the built-in default for that role. A typo'd role name
is a loud error through one door and an invisible no-op through the other.
Always import the file.

WHY THE TERMINAL CURSOR IS NOT ghostty's cursor-color. In ghostty/themes/*
`cursor-color` is set to the EXACT background hex as a sentinel -- the shader
detects it and substitutes the indigo ink. Copying that value here would
render an invisible cursor while looking perfectly faithful to the source.
The real ink is used instead: #3a5572 on paper, #6c87a4 on night.

  This line has now been wrong twice, in opposite directions, because the
  paper terminal briefly moved onto the night ground and moved back. The
  rule that survives both: the cursor ink must match the ground it is drawn
  on, not the mode it is named after. #3a5572 is tuned for cream, #6c87a4
  for #1a1917 -- read the terminalBackground beside it before changing it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "midori-t3.json"

# Recovered from the bundle. Kept as literals so this script can validate
# without the package present.
ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,47})$")
HEX_RE = re.compile(r"^#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$", re.I)
RESERVED_IDS = {"system", "light", "dark",
                "t3-chat", "t3-grove", "t3-ocean", "t3-ember", "t3-iris"}

# The 57 roles t3 accepts, in the bundle's own order. A role NOT in this set
# is a hard error on file import, so the list is load-bearing, not decorative.
ROLES = [
    "canvas", "chrome", "toolbar", "toolbarForeground", "toolbarBorder",
    "toolbarControl", "toolbarControlForeground", "toolbarControlHover",
    "surface", "surfaceRaised", "surfaceOverlay", "text", "textMuted",
    "border", "input", "focus", "accent", "accentForeground", "secondary",
    "secondaryForeground", "muted", "mutedForeground", "placeholder",
    "secondaryLabel", "iconMuted", "error", "errorForeground", "errorSurface",
    "warning", "warningForeground", "warningSurface", "update",
    "updateForeground", "updateSurface", "accentSurface",
    "accentSurfaceForeground", "messageSurface", "messageForeground",
    "messageAction", "messageActionForeground", "messageActionHover",
    "codeBackground", "codeForeground", "sidebar", "sidebarForeground",
    "sidebarMutedForeground", "sidebarControlSurface", "sidebarRowHover",
    "sidebarRowActive", "sidebarRowSelected", "sidebarBorder",
    "terminalBackground", "terminalForeground", "terminalCursor",
    "terminalSelection", "terminalScrollbar", "terminalScrollbarHover",
]

# WHY PAPER'S INK IS #2a2825 AND NOT --text-normal #3d3933. It was #3d3933
# and read washed out. Nothing was broken -- sampled from a retina screenshot,
# the prose ground came back #f3f1ec and the darkest glyph #3d3934, i.e. the
# token rendering exactly as set. The value itself was the wrong one to pick.
#
# theme.css calls #3d3933 "--foreground lifted a step": it is Obsidian's BODY
# text, softened on purpose for long-form reading on paper. t3 is a UI at
# ~15px, not a writing surface, and that lift reads as faint here.
#
# It was also an asymmetry of my own making. Night took #ebe8e2 -- ghostty's
# night FOREGROUND, the un-lifted ink -- while Paper took Obsidian's lifted
# body value. Both modes now take the ghostty ink for their ground:
#
#   paper  #2a2825 on #f3f1eb  13.01:1   (was #3d3933, 10.15:1)
#   night  #ebe8e2 on #1a1917  14.37:1   (unchanged)
#
# ---------------------------------------------------------------------------
# Midori values. Every hex here already exists in this repo -- these are the
# same tokens obsidian/theme.css and ghostty/themes/* ship, not new colours
# picked to suit T3. The three *Surface washes are the only derived values and
# they are computed below, marked, and never hand-typed.
# ---------------------------------------------------------------------------
PAPER = {
    "canvas": "#f3f1eb",                    # --background-primary
    "chrome": "#edeae2",                    # --background-secondary
    "toolbar": "#edeae2",
    "toolbarForeground": "#2a2825",         # ghostty paper foreground
    "toolbarBorder": "#e1dfd9",             # ghostty split divider
    "toolbarControl": "#faf9f6",            # --background-primary-alt
    "toolbarControlForeground": "#2a2825",
    "toolbarControlHover": "#e4e0d6",       # the light hover rung
    "surface": "#faf9f6",
    "surfaceRaised": "#faf9f6",
    "surfaceOverlay": "#faf9f6",
    "text": "#2a2825",
    "textMuted": "#524d46",                 # --text-muted
    "border": "#e1dfd9",
    "input": "#faf9f6",
    "focus": "#5f6f5e",                     # sage: Midori's accent
    "accent": "#5f6f5e",
    "accentForeground": "#f3f1eb",
    "secondary": "#edeae2",
    "secondaryForeground": "#2a2825",
    "muted": "#edeae2",
    "mutedForeground": "#524d46",
    "placeholder": "#8a847b",               # --text-faint
    "secondaryLabel": "#524d46",
    "iconMuted": "#8a847b",
    "error": "#7a4a4a",                     # wine
    "errorForeground": "#7a4a4a",
    "warning": "#b88a3a",                   # ochre
    "warningForeground": "#b88a3a",
    "update": "#3a5572",                    # indigo
    "updateForeground": "#3a5572",
    "accentSurface": "#ced1c8",             # ghostty selection-background
    "accentSurfaceForeground": "#2a2825",
    "messageSurface": "#ebe8e0",            # the userMessage rung
    "messageForeground": "#2a2825",
    "messageAction": "#5f6f5e",
    "messageActionForeground": "#f3f1eb",
    "messageActionHover": "#6c7d52",        # olive, one step off sage
    "codeBackground": "#faf9f6",
    "codeForeground": "#2a2825",
    "sidebar": "#edeae2",
    "sidebarForeground": "#2a2825",
    "sidebarMutedForeground": "#524d46",
    "sidebarControlSurface": "#faf9f6",
    "sidebarRowHover": "#e4e0d6",
    "sidebarRowActive": "#ced1c8",
    "sidebarRowSelected": "#ced1c8",
    "sidebarBorder": "#e1dfd9",
    # THE PAPER TERMINAL IS LIGHT, AND THAT ONLY WORKS BECAUSE THE PROMPT
    # STOPPED USING ANSI. t3 hardcodes its ANSI palette -- no ansi role among
    # the 57, no --ansi-* variable -- and both palettes it ships are
    # bright-on-dark, so a prompt painting with ANSI names is unreadable here:
    #
    #   VGA      on paper #f3f1eb  median 2.33  11 of 16 fail 4.5:1
    #   VS Code  on paper #f3f1eb  median 2.48  13 of 15 fail
    #
    # The escape is that t3 passes 24-bit truecolor through VERBATIM -- its
    # SGR parser returns the literal rgb for `38;2;R;G;B` and only falls back
    # to the hardcoded table for named and 256-colour codes. So
    # prompt/midori.omp.json now names hex instead of `green`/`cyan`, and the
    # prompt renders in exact Midori ink on any ground. Nothing else in the
    # pane is under this theme's control; `ls` and friends still emit ANSI and
    # will still look wrong on cream.
    # THE LIGHTEST GROUND WINS, WHICH IS BACKWARDS FROM THE INSTINCT. The
    # prompt inks are mid-tone (L 52-66), so a deeper paper REDUCES their
    # contrast. Measured worst-ink across candidate grounds:
    #   #faf9f6 alt 2.96 | #f3f1eb canvas 2.76 | #edeae2 2.59 | #ced1c8 2.02
    # so the pane uses the alt paper, not the canvas -- which also separates
    # the terminal from the app body without a border.
    "terminalBackground": "#faf9f6",
    "terminalForeground": "#2a2825",        # 13.96:1 on the ground above
    "terminalCursor": "#3a5572",            # indigo tuned for a cream bed
    "terminalSelection": "#ced1c8",
    "terminalScrollbar": "#e1dfd9",
    "terminalScrollbarHover": "#ced1c8",
}

NIGHT = {
    "canvas": "#1a1917",
    "chrome": "#22211e",
    "toolbar": "#22211e",
    "toolbarForeground": "#ebe8e2",
    "toolbarBorder": "#2f2e2b",
    "toolbarControl": "#282723",            # list.hoverBackground lift
    "toolbarControlForeground": "#ebe8e2",
    "toolbarControlHover": "#2f2e2b",
    "surface": "#22211e",
    "surfaceRaised": "#282723",
    "surfaceOverlay": "#2f2e2b",
    "text": "#ebe8e2",
    "textMuted": "#9c958a",
    "border": "#2f2e2b",
    "input": "#22211e",
    "focus": "#9aab97",                     # sage, dark half
    "accent": "#9aab97",
    "accentForeground": "#1a1917",
    "secondary": "#2f2e2b",
    "secondaryForeground": "#ebe8e2",
    "muted": "#282723",
    "mutedForeground": "#9c958a",
    "placeholder": "#6e685f",
    "secondaryLabel": "#9c958a",
    "iconMuted": "#6e685f",
    "error": "#b8868a",                     # wine, dark half
    "errorForeground": "#b8868a",
    "warning": "#d8b06a",                   # ochre, dark half
    "warningForeground": "#d8b06a",
    "update": "#6c87a4",                    # indigo, dark half
    "updateForeground": "#6c87a4",
    "accentSurface": "#40453d",             # ghostty night selection
    "accentSurfaceForeground": "#ebe8e2",
    "messageSurface": "#2c2b26",            # the night userMessage rung
    "messageForeground": "#ebe8e2",
    "messageAction": "#9aab97",
    "messageActionForeground": "#1a1917",
    "messageActionHover": "#9eaf85",        # olive, dark half
    "codeBackground": "#22211e",
    "codeForeground": "#ebe8e2",
    "sidebar": "#1a1917",
    "sidebarForeground": "#ebe8e2",
    "sidebarMutedForeground": "#9c958a",
    "sidebarControlSurface": "#22211e",
    "sidebarRowHover": "#282723",
    "sidebarRowActive": "#2f2e2b",
    "sidebarRowSelected": "#40453d",
    "sidebarBorder": "#2f2e2b",
    "terminalBackground": "#1a1917",
    "terminalForeground": "#ebe8e2",
    "terminalCursor": "#6c87a4",            # the real ink; see the header
    "terminalSelection": "#40453d",
    "terminalScrollbar": "#2f2e2b",
    "terminalScrollbarHover": "#40453d",
}


def mix(fg, bg, ratio):
    """fg over bg at `ratio`, as a 6-digit hex.

    The three *Surface roles are washes -- a tint of the status colour on the
    canvas. Midori has no hand-tuned token for them, so rather than invent
    three hexes and pass them off as part of the palette, they are computed
    from two values that ARE in the palette and marked derived in the output.
    """
    f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * ratio + y * (1 - ratio)):02x}"
                         for x, y in zip(f, b))


def complete(base):
    """Fill the derived *Surface roles so every one of the 57 is present."""
    out = dict(base)
    canvas = base["canvas"]
    for role, source in (("errorSurface", "error"),
                         ("warningSurface", "warning"),
                         ("updateSurface", "update")):
        out[role] = mix(base[source], canvas, 0.14)
    return out


def validate(theme):
    """Re-implement t3's own file validator and fail loudly.

    Written from the bundle's parser so the failures here are the failures the
    app would raise, discovered at build time instead of at import time. It
    counts what it checked and refuses an empty colours object, because a
    theme that validates zero roles is the exact shape of a vacuous pass.
    """
    problems = []
    if theme.get("version") != 1:
        problems.append("version must be exactly 1")
    name = theme.get("name", "")
    if not (isinstance(name, str) and 0 < len(name.strip()) <= 48):
        problems.append("name must be 1-48 characters")
    tid = theme.get("id", "")
    if not ID_RE.match(tid or ""):
        problems.append(f"id {tid!r} fails {ID_RE.pattern}")
    if tid in RESERVED_IDS:
        problems.append(f"id {tid!r} is reserved by t3")
    if theme.get("appearance") not in ("light", "dark"):
        problems.append("appearance must be 'light' or 'dark'")

    allowed = set(ROLES)
    checked = 0
    blocks = [("colors", theme.get("colors", {}))]
    for mode, cols in (theme.get("variants") or {}).items():
        if mode not in ("light", "dark"):
            problems.append(f"variant {mode!r} must be 'light' or 'dark'")
        if mode == theme.get("appearance"):
            problems.append(f"variant {mode!r} repeats the base appearance")
        blocks.append((f"variants.{mode}", cols))

    for where, cols in blocks:
        if not cols:
            problems.append(f"{where} is empty; t3 requires at least one role")
            continue
        for role, value in cols.items():
            checked += 1
            if role not in allowed:
                problems.append(f"{where}.{role} is not a supported role")
            if not HEX_RE.match(str(value)):
                problems.append(f"{where}.{role} = {value!r} is not hex")
        missing = allowed - set(cols)
        if missing:
            problems.append(f"{where} omits {len(missing)} role(s): "
                            f"{', '.join(sorted(missing)[:4])}...")
    if checked == 0:
        problems.append("validated ZERO roles -- the input set was empty")
    return checked, problems


def build():
    return {
        "version": 1,
        "id": "midori",
        "name": "Midori",
        "appearance": "light",
        "colors": complete(PAPER),
        "variants": {"dark": complete(NIGHT)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the committed file matches this source")
    args = ap.parse_args()

    theme = build()
    checked, problems = validate(theme)
    print(f"validated {checked} role assignments across "
          f"{1 + len(theme.get('variants', {}))} mode(s)")
    if problems:
        for p in problems:
            print(f"  FAIL {p}")
        sys.exit(1)
    print(f"  ok   {len(ROLES)} roles set in both light and dark")
    print(f"  ok   id {theme['id']!r} is not reserved")

    text = json.dumps(theme, indent=2) + "\n"
    if args.check:
        if not OUT.exists():
            sys.exit(f"FAIL {OUT.name} does not exist; run without --check")
        if OUT.read_text() != text:
            sys.exit(f"FAIL {OUT.name} differs from this source -- "
                     f"regenerate it rather than editing it by hand")
        print(f"  ok   {OUT.name} matches this source")
        return
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
