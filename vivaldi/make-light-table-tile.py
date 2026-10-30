#!/usr/bin/env python3
"""Generate the light-table grid tiles behind the Lemonardo Vivaldi themes.

CURRENTLY NOT APPLIED -- the themes ship with no background image, and this
file is run with --clear. The grid was built, installed and looked at, and it
read as ARCHITECTURAL: ruled graph paper, drafting-office rather than
animation-studio. The motif was sound on paper -- a light table really does
have a field guide ruled under the glass -- but a continuous orthogonal grid
is the visual language of a drawing board, and Lemonardo is meant to feel hand
-painted. Rejected on sight, by the person who has to look at it all day.

KEEP THIS FILE ANYWAY. It carries two things worth more than the grid: the
measured loudness calibration against Midori's dot tile, and the opaque-field
finding below, which cost a full install cycle to discover and would be
re-discovered the hard way by anyone adding ANY background image here. If a
texture is wanted later -- peg-bar punch holes are the obvious candidate, being
the one motif unique to animation paper -- change the drawing in tile() and
run with --write. Do not start from scratch.

WHY A GENERATOR AND NOT A PASTED BLOB. Midori's two tiles live in themes.json
as base64 and nothing in this repo can rebuild them -- they predate the rule
that a value must be derivable. Changing Midori's dot spacing today means
opening an image editor and guessing. These two are built from stated numbers
instead, so the next person can move the grid by editing one constant.

THE MOTIF. A light table is the glass desk an animator works over: the field
guide beneath the paper shows a faint ruled grid, and every drawing is
registered against it. That grid is the quietest possible reference -- it is
there to be measured against, never to be looked at. So it is drawn in the
non-photo blue the graphic-arts camera could not see (#a4dded), the same
drafting blue the roughs were drawn in, and it is deliberately the least
assertive element in the browser chrome.

GEOMETRY. 24x24 at 1x, matching Midori's dot tile exactly so the two design
languages tile on the same pitch and a side-by-side comparison is about the
motif rather than about scale. Lines sit on the LAST row and column (x=23,
y=23) rather than the first: tiled, either produces the same grid, but drawing
on the last pixel means the tile's top-left corner is empty and a non-repeating
fallback render shows no stray line in the corner.

THE TILE IS OPAQUE, AND THAT IS NOT A STYLE CHOICE. Its field is set to the
theme's own ground colour and every pixel is alpha 255. The first version was
transparent except for the rules, which looked equivalent -- compositing a
transparent field over the ground gives the ground -- and was not: Vivaldi
derives the chrome's foreground colour from the window background it ends up
with, and a mostly-transparent background image made it read the window as
DARK. It then flipped every UI label to white and painted them over a cream
page: "Workspaces", every shortcut caption and the Shortcut/Widget buttons all
went invisible. Midori's tile is opaque with its field equal to the ground for
exactly this reason; that was discovered by measuring it after the fact, which
is why it is written down here.

ALPHA IS APPLIED TWICE, which is the thing to know before changing it. The
rule is pre-blended INTO the ground inside the PNG at fraction `k`, and
Vivaldi then composites the whole opaque image over the window at the theme's
`alpha` (0.25). The rule's effective strength is therefore k * 0.25, and the
field -- being the ground already -- composites to itself and changes nothing.

HOW THE TWO ALPHAS WERE SET, because the first attempt got this wrong. They
were initially 150 and 120, picked by eye, which composite to dE2000 6.2 and
7.2 against their grounds. That is louder than Midori's dot, and a grid inks
far more of the tile than scattered dots do, so the error compounds. Midori's
tile was then measured rather than assumed: it is an OPAQUE tile whose field
is the ground colour, with a 4px dot core at composited dE2000 4.90 and 8px of
antialiasing at dE2000 0.56 -- 2.1% inked coverage in total.

A 1px rule on a 24px pitch inks 8.2%, four times that. Matching Midori's
dE-weighted coverage exactly (0.042) would need a line at dE 0.5, which is
invisible. So the line is set to composited dE2000 ~2.8 instead -- about a
just-noticeable difference on adjacent patches, roughly 5x Midori's ink budget
in total, which is the right answer for a texture that is continuous rather
than scattered: a grid is felt as a surface, a dot field is seen as marks.
Measured results are printed on every run; if they drift from ~2.8, the tile
has been changed without re-deriving.
"""
import base64
import io
import json
import pathlib
import sys

# Pillow is not stdlib and nothing in this repo installs it. The venv
# tests/vivaldi-sandbox.sh builds has it; otherwise pip install Pillow into
# one of your own. This import was undocumented for long enough that the tile
# it builds was shipped by someone who had Pillow and the next reader did not.
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
THEMES = ROOT / "vivaldi" / "themes.json"

TILE = 24                      # px, matching Midori's dot tile pitch
THEME_ALPHA = 0.25             # themes.json `alpha`, applied by Vivaldi

# (rule rgb, effective strength). The dark tile is NOT the light one
# recoloured: a line darker than its ground disappears on paper-cream and a
# line lighter than its ground disappears on ink, so each mode draws the grid
# in the direction its ground leaves room for. The strengths are the effective
# (post-theme-alpha) values solved for TARGET_DE below.
TILES = {
    "Lemonardo Paintpot": ((0x5f, 0xa8, 0xc8), 0.065,
                           "non-photo blue, darker than animation bond"),
    "Lemonardo Inkwell":  ((0x8f, 0xc8, 0xe0), 0.041,
                           "non-photo blue, lighter than the inkwell ground"),
}

# Composited dE2000 each tile should land at, re-measured on every run.
TARGET_DE = 2.8
TARGET_TOLERANCE = 0.5


def _cs():
    sys.path.insert(0, str(ROOT / "tools"))
    import colorspace as cs
    return cs


def composite_de(rgb, a, bg):
    """dE2000 of the line against its ground, at effective opacity `a`."""
    cs = _cs()
    b = cs.hex_to_rgb(bg)
    out = cs.rgb_to_hex(tuple((rgb[i] / 255) * a + b[i] * (1 - a)
                              for i in range(3)))
    return cs.ciede2000(out, bg)


def blend(rgb, k, bg):
    """`rgb` mixed k of the way into the ground hex `bg`, as an 8-bit triple."""
    b = [round(c * 255) for c in _cs().hex_to_rgb(bg)]
    return tuple(round(rgb[i] * k + b[i] * (1 - k)) for i in range(3))


def tile(rgb, eff, ground):
    # Opaque, field = the ground. See the module docstring: a transparent
    # field makes Vivaldi read the window as dark and whiten every label.
    gb = tuple(round(c * 255) for c in _cs().hex_to_rgb(ground))
    img = Image.new("RGBA", (TILE, TILE), (*gb, 255))
    px = img.load()
    rule = (*blend(rgb, eff / THEME_ALPHA, ground), 255)
    for i in range(TILE):
        px[TILE - 1, i] = rule              # right edge -> vertical rule
        px[i, TILE - 1] = rule              # bottom edge -> horizontal rule
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def main():
    write = "--write" in sys.argv
    clear = "--clear" in sys.argv
    pkg = json.loads(THEMES.read_text())
    by_name = {t["name"]: t for t in pkg["themes"]}
    missing = [n for n in TILES if n not in by_name]
    if missing:
        sys.exit(f"themes.json has no theme named {missing} -- renamed?")

    if clear:
        for name in TILES:
            by_name[name]["backgroundImage"] = ""
        with open(THEMES, "w") as f:
            json.dump(pkg, f, indent=2)
            f.write("\n")
        print(f"cleared the background image on {len(TILES)} theme(s) -- "
              f"the grid read as architectural, see the module docstring")
        return

    bad = []
    for name, (rgb, eff, why) in TILES.items():
        ground = by_name[name]["colorWindowBg"]
        raw = tile(rgb, eff, ground)
        uri = "data:image/png;base64," + base64.b64encode(raw).decode()
        got = composite_de(rgb, eff, ground)
        flag = "" if abs(got - TARGET_DE) <= TARGET_TOLERANCE else \
            f"  <-- OFF TARGET {TARGET_DE}+-{TARGET_TOLERANCE}"
        print(f"{name}")
        print(f"   {TILE}x{TILE} PNG, {len(raw)} bytes -> {len(uri)} chars base64")
        k = eff / THEME_ALPHA
        print(f"   #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x} pre-blended k={k:.3f} "
              f"into {ground}, x theme alpha {THEME_ALPHA} = {eff:.3f} "
              f"effective  ({why})")
        print(f"   opaque tile, field = {ground} (see docstring: a transparent "
              f"field whitens every UI label)")
        print(f"   composited on {ground}: dE2000 {got:.2f}{flag}")
        if flag:
            bad.append(name)
        if write:
            t = by_name[name]
            t["backgroundImage"] = uri
            t["backgroundPosition"] = "repeat"
            t["alpha"] = THEME_ALPHA

    if bad:
        sys.exit(f"\nrefusing to write: {bad} are off the loudness target")

    if write:
        with open(THEMES, "w") as f:
            json.dump(pkg, f, indent=2)
            f.write("\n")
        print(f"\nwrote {len(TILES)} tile(s) into {THEMES.relative_to(ROOT)}")
    else:
        print("\n(dry run -- pass --write to embed into themes.json)")


if __name__ == "__main__":
    main()
