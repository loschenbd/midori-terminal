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

THE CURSOR TRAP. Neither Ghostty theme's cursor-color is a colour. Both set
`cell-background` (until Sept 2026, the EXACT background hex as a sentinel):
Ghostty composites the native cursor after the custom shader and
cursor-opacity=0 does not hide the hollow unfocused cursor, so matching the
cell under it is how they make it invisible, and the shader draws the indigo.
Copied verbatim into Moshi — which has no such shader — the hex is an invisible
cursor and the keyword is not a colour at all. So when cursor is a cell-*
keyword or == background we substitute palette 4, which IS the indigo ink in
both themes (#3a5572 paper, #6c87a4 night) and is exactly what the shader draws.
"""

import base64
import argparse
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

# ONE SET PER DESIGN LANGUAGE, EACH WITH ITS OWN FOLDER on the phone. Two
# themes in one folder means two import.html files, two READMEs and four QR
# codes to tell apart by filename on a 6-inch screen; one folder per set means
# you open the folder you want and everything in it belongs together.
#
# "fonts" is per set because the face is part of the design language, not of the
# app. Shipping Midori's M PLUS 1 Code alongside a Lemonardo theme would put the
# wrong face behind the right palette and read as a complete install.
#
# Lemonardo's list was empty for one release, with the recorded reason that its
# mono face was not vendored in fonts/. It now is: Sometype Mono, roman and
# italic, from google/fonts ofl/sometypemono, with its own OFL 1.1 alongside.
#
# EVERY CLAIM themes/lemonardo.json MAKES ABOUT THAT FACE WAS CHECKED AGAINST
# THESE BINARIES, not taken from the specimen page, and all of it held:
# post.isFixedPitch=1, all 94 printable ASCII glyphs present, exactly ONE
# advance width of 580/1000 = 0.5800em across them, wght axis 400-700,
# sxHeight 470/1000 = 0.4700em, sCapHeight 650/1000 = 0.6500em, OFL 1.1.
#
# ONE FILE PER MOSHI SLOT, AND MOSHI HAS TWO. The terminal font is imported
# from Files as a single face (Settings -> Terminal Fonts -> Import font, Moshi
# Pro; getmoshi.app/docs/personalization, read 2026-10-30), and the app has a
# second font setting for Chat View, the markdown reading surface. Nothing in
# the docs pairs a bold or italic file with an imported face -- they warn OFF
# collections that carry variants -- so a second file per slot is a file the
# app cannot use. The variable roman is the right single file: one face that
# carries every weight, usable through the axis where the app knows how and at
# its default weight where it does not.
#
# The ITALIC used to ship here with a paragraph arguing for it (metric-
# compatible with the roman: isFixedPitch=1, the same single 580/1000 advance
# across the same 94 glyphs, so safe in a grid). The measurements hold; the
# conclusion did not, because it assumed a second file would be picked up
# beside the first, and Moshi gives it no slot. It is still vendored in fonts/
# for the surfaces that can use it.
#
# CHAT VIEW TAKES THE LANGUAGE'S BODY FACE: Instrument Sans for Lemonardo
# (themes/lemonardo.json type.body) and M PLUS 2 Regular for Midori. Midori's
# prose face elsewhere is M PLUS 1p, and M PLUS 2 is chosen over it for one
# measured reason: 1p draws the ellipsis centred on the x-height (ink 290-430
# of 1000, the Japanese leader convention, no OpenType alternate) while M PLUS
# 2 puts it on the baseline like its full stop (0-107), and chat text is full
# of ellipses. Same designer, same 520 x-height, same lowercase widths within
# 0.4%; the differences are rounder dots and softer terminals. A static
# Regular because no variable M PLUS 2 is vendored; 1.8 MB like the 1p files.
SETS = {
    "midori": {
        "label": "Midori",
        "themes": [("midori-paper", "Midori Paper", "light"),
                   ("midori-night", "Midori Night", "dark")],
        "fonts": [("MPLUS1Code[wght].ttf", "fonts/MPLUS1Code[wght].ttf"),   # terminal
                  ("MPLUS2-Regular.ttf", "fonts/MPLUS2-Regular.ttf"),       # chat view
                  ("OFL-MPLUS.txt", "fonts/OFL-MPLUS.txt")],
        "readme": "README.md",
    },
    "lemonardo": {
        "label": "Lemonardo",
        "themes": [("lemonardo-paintpot", "Lemonardo Paintpot", "light"),
                   ("lemonardo-inkwell", "Lemonardo Inkwell", "dark")],
        "fonts": [("SometypeMono[wght].ttf", "fonts/SometypeMono[wght].ttf"),  # terminal
                  ("InstrumentSans[wdth,wght].ttf",
                   "fonts/InstrumentSans[wdth,wght].ttf"),                   # chat view
                  ("OFL-SometypeMono.txt", "fonts/OFL-SometypeMono.txt"),
                  ("OFL-InstrumentSans.txt", "fonts/OFL-InstrumentSans.txt")],
        # NO README, and this is the recorded reason. moshi/README.md is titled
        # "Midori for Moshi" and names midori-paper.json, the Midori QR files and
        # Midori's two background hexes -- thirteen Midori references. Copied into
        # this folder it would describe files that are not in it, which reads as a
        # complete install and is worse than no README at all. import.html carries
        # both deep links and is theme-specific because it is generated.
        "readme": None,
    },
}


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
    if cursor == bg or not cursor or cursor.startswith("cell-"):
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


# ------------------------------------------------------------ import page

# The QR is useless on the phone itself — you cannot scan your own screen — and
# a moshi:// link inside a .txt is not tappable in Files. So the phone path is
# an HTML page opened from Files: tap a row, Moshi takes the deep link.
IMPORT_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Midori for Moshi</title>
<style>
  :root {{ {light_vars} }}
  @media (prefers-color-scheme: dark) {{ :root {{ {dark_vars} }} }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; padding:2rem 1.25rem 3rem; background:var(--bg); color:var(--fg);
    font:16px/1.55 -apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif;
    -webkit-text-size-adjust:100%;
  }}
  main {{ max-width:30rem; margin:0 auto; }}
  h1 {{ font-size:1.5rem; margin:0 0 .25rem; letter-spacing:-.01em; }}
  p.sub {{ margin:0 0 2rem; color:var(--muted); font-size:.95rem; }}
  a.theme {{
    display:block; text-decoration:none; color:inherit; background:var(--card);
    border:1px solid var(--border); border-radius:14px; padding:1rem 1.15rem;
    margin-bottom:1rem; -webkit-tap-highlight-color:transparent;
  }}
  a.theme:active {{ background:var(--bg); }}
  .row {{ display:flex; align-items:center; gap:.85rem; }}
  .name {{ font-weight:600; font-size:1.05rem; }}
  .mode {{ color:var(--muted); font-size:.85rem; }}
  .go {{ margin-left:auto; color:var(--accent); font-weight:600; font-size:.9rem; }}
  .swatches {{ display:flex; gap:5px; margin-top:.85rem; }}
  .swatches i {{ width:100%; height:22px; border-radius:4px; display:block; }}
  ol {{ color:var(--muted); font-size:.9rem; padding-left:1.15rem; margin:2rem 0 0; }}
  li {{ margin-bottom:.4rem; }}
  code {{ font:13px ui-monospace,SFMono-Regular,Menlo,monospace; }}
</style>
</head>
<body>
<main>
  <h1>Midori for Moshi</h1>
  <p class="sub">Tap a theme on the device running Moshi.</p>
{cards}
  <ol>
    <li>If tapping does nothing, Moshi may not be installed on this device.</li>
    <li>Fallback: open <code>midori-paper.json</code> in Files, select all, copy,
        then Moshi &rarr; Settings &rarr; Theme &rarr; Import theme &rarr; paste.</li>
    <li>From another device, scan <code>midori-paper-qr.png</code> instead.</li>
  </ol>
</main>
</body>
</html>
"""

CARD = """  <a class="theme" href="{link}">
    <div class="row">
      <span class="name">{name}</span>
      <span class="mode">{mode}</span>
      <span class="go">Import &rsaquo;</span>
    </div>
    <div class="swatches">{swatches}</div>
  </a>
"""


def _vars(c, mode):
    """Page chrome, derived from the theme itself so the page can't drift from
    the palette it is handing out. The raised card surface flips side: on dark
    it is ANSI black (one step up from the ground), on light it is brightWhite
    (the paper white), because on a light theme those two swap roles."""
    card = c["black"] if mode == "dark" else c["brightWhite"]
    return (
        f"--bg:{c['background']}; --fg:{c['foreground']}; --muted:{c['brightBlack']}; "
        f"--card:{card}; --border:{c['selectionBackground']}; --accent:{c['blue']};"
    )


def write_import_html(built, out_name):
    light = next(t["colors"] for t, _ in built if t["mode"] == "light")
    dark = next(t["colors"] for t, _ in built if t["mode"] == "dark")
    cards = ""
    for theme, link in built:
        c = theme["colors"]
        sw = "".join(
            f'<i style="background:{c[k]}"></i>'
            for k in ("red", "green", "yellow", "blue", "magenta", "cyan")
        ) + f'<i style="background:{c["background"]};border:1px solid {c["selectionBackground"]}"></i>'
        cards += CARD.format(link=link, name=theme["name"], mode=theme["mode"], swatches=sw)
    html = IMPORT_HTML.format(
        light_vars=_vars(light, "light"), dark_vars=_vars(dark, "dark"), cards=cards
    )
    (OUT / out_name).write_text(html)
    return html


# --------------------------------------------------------------- publishing

# Phone-facing copies. iCloud is how the files reach the Files app, and a
# hand-copied snapshot is exactly the drift this generator exists to prevent —
# so publishing is part of the build, not a follow-up step. Skipped cleanly when
# there is no iCloud Drive (another machine, CI), never fatal.
# The Dev folder in iCloud Drive is where the phone picks things up. It holds a
# flat font library already -- M PLUS 1 Code, eight weights of M PLUS 1p, seven
# of M PLUS Code Latin 60 -- because iOS installs a font by tapping it in Files.
#
# EACH THEME SET GETS ITS OWN FOLDER under Dev, with its theme files and its own
# fonts inside it. An earlier pass mirrored the tappable files FLAT into Dev
# beside that font library, which put seven loose files with names like
# midori-paper.url next to sixteen .ttf files and made neither set findable.
ICLOUD_DEV = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Dev"


def set_dir(set_id):
    return ICLOUD_DEV / f"{set_id}-moshi-theme"


def publish(set_id, spec, built):
    """Publish one set into its own folder: themes, links, QR codes, fonts."""
    dest = set_dir(set_id)
    if not ICLOUD_DEV.parent.is_dir():           # no CloudDocs root at all
        print(f"\n-- iCloud Drive not present; skipped publishing to {dest}")
        return 0
    dest.mkdir(parents=True, exist_ok=True)

    names = [f"import-{set_id}.html"]
    if spec.get("readme"):
        names.append(spec["readme"])
    for slug, _, _ in spec["themes"]:
        names += [f"{slug}.json", f"{slug}.url", f"{slug}-qr.png"]

    copied, missing = [], []
    for name in names:
        src = OUT / name
        if not src.exists():
            missing.append(name)
            continue
        # import-<set>.html lands as plain import.html inside the folder: the
        # set is the folder name, so repeating it in the filename is noise.
        out_name = "import.html" if name.startswith("import-") else name
        (dest / out_name).write_bytes(src.read_bytes())
        copied.append((name, out_name))

    fonts_copied = []
    for name, rel in spec["fonts"]:
        src = ROOT / rel
        if not src.exists():
            missing.append(rel)
            continue
        (dest / name).write_bytes(src.read_bytes())
        fonts_copied.append((name, rel))

    # Read back rather than trust the write — this is a synced volume, and a
    # stale phone copy is indistinguishable from a fresh one by eye.
    bad = [o for n, o in copied
           if (dest / o).read_bytes() != (OUT / n).read_bytes()]
    bad += [n for n, rel in fonts_copied
            if (dest / n).read_bytes() != (ROOT / rel).read_bytes()]

    print(f"\n-- {spec['label']}: {len(copied)} file(s) -> {dest}")
    if fonts_copied:
        mb = sum((dest / n).stat().st_size for n, _ in fonts_copied) / 1_048_576
        print(f"   + {len(fonts_copied)} font file(s) ({mb:.1f} MB)")
    else:
        print("   + no fonts: this set's faces are not vendored in fonts/")
    if missing:
        print(f"   NOT copied (build them first): {', '.join(missing)}")
    if bad:
        print(f"   !! mismatch after copy: {', '.join(bad)}")
    return len(bad)


def main():
    ap = argparse.ArgumentParser(
        description="Build the Moshi themes and publish them to iCloud.")
    ap.add_argument("--set", action="append", choices=sorted(SETS),
                    help="theme set to build (repeatable; default: all)")
    ap.add_argument("--no-publish", action="store_true",
                    help="build into moshi/ but do not touch iCloud")
    a = ap.parse_args()
    chosen = a.set or sorted(SETS)

    OUT.mkdir(exist_ok=True)
    bad = 0
    for set_id in chosen:
        spec = SETS[set_id]
        built = []
        for slug, name, mode in spec["themes"]:
            theme = build(slug, name, mode)
            path = OUT / f"{slug}.json"
            path.write_text(json.dumps(theme, indent=2) + "\n")
            link = deep_link(theme)
            built.append((theme, link))
            (OUT / f"{slug}.url").write_text(link + "\n")

            try:
                subprocess.run(
                    ["qrencode", "-o", str(OUT / f"{slug}-qr.png"),
                     "-s", "8", "-m", "2", link],
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

        write_import_html(built, f"import-{set_id}.html")
        print(f"\n-- import-{set_id}.html rebuilt with both deep links")
        if not a.no_publish:
            bad += publish(set_id, spec, built)

    # A build that published nothing is not a success. The sets are declared
    # above; if a run reports zero, the loop found no work and said so.
    if not chosen:
        print("\n-- no theme sets selected; nothing built")
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
