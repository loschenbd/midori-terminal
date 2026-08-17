"""What does the theme actually deliver today, in the units the research is in?

Research talks in characters-per-line and apparent size; a stylesheet talks in
px and font names. This converts. Ink extents come from a BoundsPen on the real
outlines rather than from OS/2 sxHeight, which is designer-typed metadata and
has been wrong before.
"""
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

# Typical English prose, not a pangram: pangrams over-weight rare letters and
# come out ~4% wider, which is a whole character per line at this measure.
SAMPLE = ("The question of how long a line of text should be is older than the "
          "screen, and most of the answers that circulate were never measured "
          "at all. A writer revising a paragraph moves through it differently "
          "than a reader meeting it once.")

FONTS = {
    "M PLUS 1p (body)": "fonts/MPLUS1p-Regular.ttf",
    "Spectral (display)": "fonts/Spectral-Regular.ttf",
}
LINE_PX = 700.0        # Obsidian's default --file-line-width
GRID = 24.0            # the theme's baseline row

for name, path in FONTS.items():
    f = TTFont(path)
    upem = f["head"].unitsPerEm
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()

    def ink_height(ch):
        pen = BoundsPen(gs)
        gs[cmap[ord(ch)]].draw(pen)
        return (pen.bounds[3] - pen.bounds[1]) / upem

    x_em = ink_height("x")
    cap_em = ink_height("H")
    hmtx = f["hmtx"]
    total = sum(hmtx[cmap[ord(c)]][0] for c in SAMPLE if ord(c) in cmap)
    avg_em = total / len(SAMPLE) / upem

    print(f"\n{name}  (upem {upem})")
    print(f"  x-height {x_em*1000:7.1f}/1000   cap {cap_em*1000:7.1f}/1000"
          f"   avg advance {avg_em*1000:7.1f}/1000")
    for base in (15, 16, 17, 18):
        cpl = LINE_PX / (avg_em * base)
        print(f"  {base}px:  x-height {x_em*base:5.2f}px   cap {cap_em*base:5.2f}px"
              f"   {cpl:5.1f} chars in {LINE_PX:.0f}px"
              f"   leading {GRID/base:4.2f}x")

# What size would Spectral need to LOOK the size M PLUS 1p looks?
mp = TTFont(FONTS["M PLUS 1p (body)"]); sp = TTFont(FONTS["Spectral (display)"])
def xh(f):
    gs, cmap = f.getGlyphSet(), f.getBestCmap()
    pen = BoundsPen(gs); gs[cmap[ord("x")]].draw(pen)
    return (pen.bounds[3] - pen.bounds[1]) / f["head"].unitsPerEm
r = xh(mp) / xh(sp)
print(f"\nx-height parity: Spectral needs {r:.3f}x the em size of M PLUS 1p")
for base in (15, 16, 17, 18):
    print(f"  body {base}px  ->  Spectral {base*r:5.2f}px to match apparent size")
