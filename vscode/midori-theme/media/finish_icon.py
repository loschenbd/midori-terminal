"""Post-process the nano-banana icon per docs/brand-images.md.

The brand guide is explicit that the model must NOT draw the background
texture: generate on flat cream, then normalize the base to the exact hex
and composite the mint dot grid programmatically. That is the only way the
background stays pixel-identical across the brand's image set.
"""
import numpy as np
from PIL import Image, ImageDraw

import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "icon-raw.png"
OUT_1024 = "icon-1024.png"
OUT_256 = "icon-256.png"

CREAM = (0xF3, 0xF1, 0xEB)
MINT = (0x9E, 0xBF, 0xB4)
MINT_ALPHA = 0.55
# No bezel: the icon is edge-to-edge paper, deliberately.
#
# The tradeoff is known and accepted. Cream #f3f1eb against VS Code's light
# list background #f3f3f3 is 1.02:1, so on light chrome the square has no
# visible boundary and the mark reads as four bars floating free. A 4px
# ink-muted rule was tried and fixes it (7.54:1), but it frames the paper and
# turns the sheet into a card, which is not what this mark is. Every other
# theme in the top 40 keeps a defined silhouette — almost always a dark disc
# on transparency — so being the one borderless light square is the point.
BEZEL_AT_256 = 0

# The mark's sanctioned hexes. Everything in the render snaps to one of these.
PALETTE = {
    "cream": CREAM,
    "ink": (0x2A, 0x28, 0x25),
    "slate": (0x3A, 0x55, 0x72),
    "ochre": (0xB8, 0x8A, 0x3A),
    "sage": (0x5F, 0x6F, 0x5E),
}

SNAP_DIST = 42.0  # leave genuinely antialiased edge pixels alone

img = Image.open(SRC).convert("RGB")
if img.size != (1024, 1024):
    img = img.resize((1024, 1024), Image.LANCZOS)
a = np.asarray(img).astype(np.float64)

names = list(PALETTE)
targets = np.array([PALETTE[n] for n in names], dtype=np.float64)

# Nearest-palette-entry per pixel.
d = np.linalg.norm(a[:, :, None, :] - targets[None, None, :, :], axis=3)
idx = d.argmin(axis=2)
nearest_d = d.min(axis=2)

snapped = a.copy()
hit = nearest_d < SNAP_DIST
snapped[hit] = targets[idx[hit]]

print("pixel census (snapped):")
for i, n in enumerate(names):
    c = int(((idx == i) & hit).sum())
    print(f"  {n:6s} {PALETTE[n]}  {c:9d}  {100*c/a[:, :, 0].size:5.2f}%")
print(f"  unsnapped (AA edges)     {int((~hit).sum()):9d}"
      f"  {100*(~hit).sum()/a[:, :, 0].size:5.2f}%")

base = Image.fromarray(snapped.astype(np.uint8))

# Background mask: exactly-cream pixels only, so dots stop at the bars.
bg_mask = Image.fromarray(
    (np.all(snapped == np.array(CREAM, dtype=np.float64), axis=2) * 255).astype(np.uint8)
)

# Mint dot grid. The brand's 24px-on-1200 pitch is ~1/50 of frame width; at a
# 128px icon that would be 2.5px and vanish, so the grid is scaled up to 8
# columns (16px pitch at 128 / 128px at 1024) to survive the icon size.
SS = 4  # supersample, then downscale — same technique as the LinkedIn banners
PITCH, RADIUS = 128, 11
dots = Image.new("L", (1024 * SS, 1024 * SS), 0)
dd = ImageDraw.Draw(dots)
for y in range(PITCH // 2, 1024, PITCH):
    for x in range(PITCH // 2, 1024, PITCH):
        dd.ellipse(
            [(x - RADIUS) * SS, (y - RADIUS) * SS, (x + RADIUS) * SS, (y + RADIUS) * SS],
            fill=255,
        )
dots = dots.resize((1024, 1024), Image.LANCZOS)

# Dot alpha = coverage * 0.55, gated by the background mask.
alpha = (
    np.asarray(dots).astype(np.float64)
    * MINT_ALPHA
    * (np.asarray(bg_mask).astype(np.float64) / 255.0)
)
mint_layer = Image.new("RGB", (1024, 1024), MINT)
final = Image.composite(
    mint_layer, base, Image.fromarray(alpha.astype(np.uint8))
)

t = BEZEL_AT_256 * (1024 // 256)
if t:
    # Would sit over the dot grid as the edge of the sheet.
    ImageDraw.Draw(final).rectangle([0, 0, 1023, 1023], outline=INK_MUTED, width=t)

final.save(OUT_1024)
# 256 is what ships. 59% of the top-100 themes ship >= 256 on the long edge
# and only 18% are exactly 128; 128 is the documented minimum, not the target.
final.resize((256, 256), Image.LANCZOS).save(OUT_256)

edge = np.asarray(final)[1, 1]
print(f"\ncorner pixel: #{edge[0]:02x}{edge[1]:02x}{edge[2]:02x} (want #f3f1eb)")
print(f"wrote {OUT_1024} and {OUT_256}")
