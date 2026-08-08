"""Measure each bar's bounding box so the indentation claim is checked, not eyeballed.

Measuring on the raw render does not work: antialiased edge pixels between
cream and ink pass through colours that sit within any useful distance
threshold of slate, so the bounding boxes bleed into each other. Snap every
pixel to its nearest palette entry first, then match exactly.
"""
import sys
import numpy as np
from PIL import Image

PALETTE = {
    "cream": (0xF3, 0xF1, 0xEB),
    "ink":   (0x2A, 0x28, 0x25),
    "slate": (0x3A, 0x55, 0x72),
    "ochre": (0xB8, 0x8A, 0x3A),
    "sage":  (0x5F, 0x6F, 0x5E),
}
TARGET = {
    "ink":   (160, 238, 800, 330),
    "slate": (256, 390, 880, 482),
    "ochre": (352, 542, 700, 634),
    "sage":  (256, 694, 620, 786),
}

img = Image.open(sys.argv[1]).convert("RGB")
if img.size != (1024, 1024):
    img = img.resize((1024, 1024), Image.LANCZOS)
a = np.asarray(img).astype(np.float64)

names = list(PALETTE)
targets = np.array([PALETTE[n] for n in names], dtype=np.float64)
d = np.linalg.norm(a[:, :, None, :] - targets[None, None, :, :], axis=3)
idx = d.argmin(axis=2)
# Only trust pixels that are unambiguously one palette entry: nearest must be
# clearly closer than runner-up, which excludes the AA ramps entirely.
srt = np.sort(d, axis=2)
confident = (srt[:, :, 0] < 42) & (srt[:, :, 1] - srt[:, :, 0] > 25)


def solid_runs(mask, min_len=50):
    """Keep only pixels inside a horizontal run of >= min_len.

    Nearest-colour matching alone is not enough: the ink-to-cream antialiasing
    ramp passes through mid-greys that land almost exactly on sage, so sage's
    bounding box swallows the whole image. Those ramp pixels are ~3px wide,
    while a real bar is hundreds, so run length separates them cleanly.
    """
    out = np.zeros_like(mask)
    for y in range(mask.shape[0]):
        row = mask[y]
        if not row.any():
            continue
        # Run boundaries via diff on the padded row.
        p = np.concatenate(([0], row.view(np.int8), [0]))
        edges = np.flatnonzero(p[1:] != p[:-1])
        for s, e in zip(edges[::2], edges[1::2]):
            if e - s >= min_len:
                out[y, s:e] = True
    return out

print(f"{'bar':6s} {'measured l,t,r,b':>24s} {'target':>24s}    dL    dR    dH")
rows = {}
for name in ("ink", "slate", "ochre", "sage"):
    m = solid_runs((idx == names.index(name)) & confident)
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        print(f"{name:6s} {'NOT FOUND':>24s}")
        continue
    l, r, t, b = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    rows[name] = (l, t, r, b)
    g = TARGET[name]
    print(f"{name:6s} {str((l, t, r, b)):>24s} {str(g):>24s} "
          f"{l-g[0]:+5d} {r-g[2]:+5d} {(b-t)-(g[3]-g[1]):+5d}")

lefts = [rows[n][0] for n in ("ink", "slate", "ochre", "sage")]
print(f"\nleft edges top->bottom: {lefts}   (want a 0,1,2,1 staircase)")
print(f"  step 1->2 {lefts[1]-lefts[0]:+d}   2->3 {lefts[2]-lefts[1]:+d}   3->4 {lefts[3]-lefts[2]:+d}")
ok = [
    ("bar1 alone at the outermost left", lefts[0] < min(lefts[1:]) - 20),
    ("bar3 the most indented",           lefts[2] > max(lefts[0], lefts[1], lefts[3]) + 20),
    ("bar2 level with bar4 (<=12px)",    abs(lefts[1] - lefts[3]) <= 12),
    ("bar2 indented past bar1",          lefts[1] > lefts[0] + 20),
]
for label, passed in ok:
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
print(f"\n{'ALL CHECKS PASS' if all(p for _, p in ok) else 'GEOMETRY WRONG'}")
