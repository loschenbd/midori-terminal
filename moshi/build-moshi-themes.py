#!/usr/bin/env python3
"""Generate Moshi terminal themes from the Ghostty themes.

Moshi (getmoshi.app) is the iOS/Android terminal client for driving coding
agents over SSH/Mosh. Its themes are a flat 20-colour JSON — the same data the
Ghostty themes already carry — so these are DERIVED, never hand-maintained.
Edit ghostty/themes/midori-* and re-run this; do not edit the JSON.

Format, reverse-engineered from https://getmoshi.app/themes/rose-pine.json and
the deep link on that page (the schema is not documented):

    {"v":1,"name":...,"mode":"light"|"dark","colors":{...20 keys...}}

  * exactly 20 colour keys, in the order below — Moshi's own pages emit them
    in this order, so matching it keeps a diff against a published theme legible
  * the deep link is  moshi://theme?d=<base64 of the COMPACT json>
  * base64 is STANDARD (+/), and the trailing '=' padding is STRIPPED
  * Moshi restyles its whole UI from the theme, not just the terminal grid,
    so these colours have to survive as chrome as well as as text

THE CURSOR TRAP. Both Ghostty themes set cursor-color to the EXACT background
hex as a sentinel: Ghostty composites the native cursor after the custom shader
and cursor-opacity=0 does not hide the hollow unfocused cursor, so bg-on-bg is
how they make it invisible and the shader substitutes the indigo. Copied
verbatim into Moshi — which has no such shader — that sentinel is just an
invisible cursor. So when cursor == background we substitute palette 4, which
IS the indigo ink in both themes (#3a5572 paper, #6c87a4 night) and is exactly
what the shader draws.
"""

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GHOSTTY = ROOT / "ghostty" / "themes"
OUT = ROOT / "moshi"

# ANSI index -> Moshi key. Moshi's own ordering; keep it.
ANSI = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "brightBlack", "brightRed", "brightGreen", "brightYellow",
    "brightBlue", "brightMagenta", "brightCyan", "brightWhite",
]

THEMES = [
    ("midori-paper", "Midori Paper", "light"),
    ("midori-night", "Midori Night", "dark"),
]


def parse_ghostty(path):
    """Pull the palette and the named colours out of a Ghostty theme file."""
    palette, named = {}, {}
    for line in path.read_text().splitlines():
        # Ghostty comments are whole-line only. Do NOT strip from the first '#'
        # — every value in this file is a hex colour that starts with one.
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if key == "palette":
            idx, _, hexv = val.partition("=")
            palette[int(idx)] = hexv.strip().lower()
        else:
            named[key] = val.lower()
    return palette, named


def build(slug, name, mode):
    palette, named = parse_ghostty(GHOSTTY / slug)
    missing = [i for i in range(16) if i not in palette]
    if missing:
        sys.exit(f"{slug}: palette incomplete, missing {missing}")

    bg = named["background"]
    cursor = named.get("cursor-color", "")
    # See the cursor trap in the module docstring.
    if cursor == bg or not cursor:
        cursor = palette[4]

    colors = {
        "background": bg,
        "foreground": named["foreground"],
        "cursor": cursor,
    }
    colors.update({k: palette[i] for i, k in enumerate(ANSI)})
    colors["selectionBackground"] = named["selection-background"]

    return {"v": 1, "name": name, "mode": mode, "colors": colors}


def deep_link(theme):
    compact = json.dumps(theme, separators=(",", ":"))
    return "moshi://theme?d=" + base64.b64encode(compact.encode()).decode().rstrip("=")


# ------------------------------------------------------------------ contrast

def _lin(c):
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexv):
    r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def report(theme):
    """Every ink colour against its own background. Moshi paints UI chrome from
    these too, so a colour that is merely 'decorative' in a terminal grid still
    has to hold up as a label."""
    bg = theme["colors"]["background"]
    rows = []
    for key, val in theme["colors"].items():
        if key in ("background", "selectionBackground"):
            continue
        rows.append((key, val, contrast(val, bg)))
    rows.sort(key=lambda r: r[2])
    return bg, rows


def main():
    OUT.mkdir(exist_ok=True)
    links = {}
    for slug, name, mode in THEMES:
        theme = build(slug, name, mode)
        path = OUT / f"{slug}.json"
        path.write_text(json.dumps(theme, indent=2) + "\n")
        link = deep_link(theme)
        links[slug] = link
        (OUT / f"{slug}.url").write_text(link + "\n")

        try:
            subprocess.run(
                ["qrencode", "-o", str(OUT / f"{slug}-qr.png"), "-s", "8", "-m", "2", link],
                check=True,
            )
            qr = "qr ok"
        except (FileNotFoundError, subprocess.CalledProcessError):
            qr = "qr SKIPPED (install qrencode)"

        bg, rows = report(theme)
        print(f"\n=== {name} ({mode}) — background {bg} — {qr}")
        print(f"    {len(link)} char deep link -> {path.name}")
        worst = [r for r in rows if r[2] < 4.5]
        for key, val, ratio in rows:
            flag = "  <- under 4.5:1" if ratio < 4.5 else ""
            print(f"    {key:<15} {val}  {ratio:5.2f}:1{flag}")
        print(f"    {len(worst)}/{len(rows)} below 4.5:1")

    return links


if __name__ == "__main__":
    main()
