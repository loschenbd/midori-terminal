#!/usr/bin/env python3
"""Bake the Midori Ghostty background assets (dot tiles + glow washes).

Pure python (zlib + struct) — no Pillow required.

The shipped PNGs in ghostty/backgrounds/ were baked with this tool's
defaults and calibrated on the original displays. You only need to run it
when a NEW display class needs different geometry:

  # dot tile + glow for a 1x display at 1920x1080, default phase
  ./bake-backgrounds.py --scale 1x --glow-size 1920x1080

  # recalibrated vertical phase (see README "Calibrating the dot phase")
  ./bake-backgrounds.py --scale 1x --glow-size 2560x1080 --dot-cy 10.75

Key facts (learned the hard way):
- Ghostty draws background images at PHYSICAL pixels (fit=none), so retina
  displays need the @2x assets and 1x externals the @1x ones. The launchd
  watcher flips symlinks between them.
- The vertical dot phase does NOT scale cleanly between displays: 11.5 @2x
  did not land as 5.75 @1x in practice (measured 10.75). Calibrate each
  scale from its own screenshot; never derive one from the other.
- Dots align to TEXT BASELINES (ruled-paper convention). Box-drawing rules
  render at cell center and can never share the lattice — that's expected.
"""
import argparse, struct, sys, zlib
from math import hypot
from pathlib import Path

# ---- Midori constants (from benjaminloschen.com globals.css) --------------
MODES = {
    "paper": {
        "bg": (0xF3, 0xF1, 0xEB),
        "dot": (158, 191, 180),
        "dot_alpha": 0.46,
        # --page-glow, light: CSS lists topmost first -> composite reversed
        "glow": [
            # (rx%, ry%, cx%, cy%, (r,g,b), alpha, end%)
            (1.00, 0.55, 0.50, -0.15, (255, 252, 247), 0.95, 0.52),
            (0.55, 0.40, 0.00, 1.00, (236, 233, 224), 0.55, 0.50),
            (0.45, 0.45, 1.00, 0.60, (232, 236, 229), 0.40, 0.48),
        ],
    },
    "night": {
        "bg": (0x1A, 0x19, 0x17),
        "dot": (154, 189, 179),
        "dot_alpha": 0.38 * 0.46,  # site dark dot alpha x overlay opacity
        "glow": [
            (1.00, 0.55, 0.50, -0.15, (45, 44, 40), 0.90, 0.52),
            (0.55, 0.40, 0.00, 1.00, (55, 52, 46), 0.45, 0.50),
            (0.45, 0.45, 1.00, 0.60, (48, 52, 46), 0.35, 0.48),
        ],
    },
}

# Per-scale defaults: tile size, dot solid/fade radii, calibrated dot center.
# cy values were measured from screenshots on the original displays (16"
# MacBook Pro retina @2x; LG ultrawide @1x) — see README for the procedure.
# CALIBRATED FOR CHROMELESS WINDOWS (macos-titlebar-style = hidden): Ghostty
# anchors the background to the window top INCLUDING chrome, so a titlebar
# shifts the dots by its height mod the pitch (~12px @2x). Titled-window
# values were cy 11.5 (2x) / 10.75 (1x); hidden-titlebar = those - 12 / - 6.
# The 1x value is PREDICTED, not yet verified on the LG — recalibrate there.
SCALES = {
    "2x": {"tile": 48, "r_in": 2.0, "r_out": 2.7, "cx": 24.0, "cy": 47.5},
    "1x": {"tile": 24, "r_in": 1.0, "r_out": 1.35, "cx": 12.0, "cy": 4.75},
}


def write_png(path, w, h, rows, rgba):
    """rows: list of bytes/bytearray scanlines (RGBA or RGB, no filter byte)."""
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    color_type = 6 if rgba else 2
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    Path(path).write_bytes(png)


def dot_coverage(x, y, cx, cy, r_in, r_out, ss=4):
    """Supersampled radial-gradient dot: solid to r_in, linear fade to r_out."""
    total = 0.0
    for sy in range(ss):
        for sx in range(ss):
            d = hypot(x + (sx + 0.5) / ss - cx, y + (sy + 0.5) / ss - cy)
            if d <= r_in:
                total += 1.0
            elif d < r_out:
                total += (r_out - d) / (r_out - r_in)
    return total / (ss * ss)


def dot_alpha_map(sc, mode):
    """Sparse {(x, y): alpha 0-255} for one tile."""
    out = {}
    for y in range(sc["tile"]):
        for x in range(sc["tile"]):
            cov = dot_coverage(x, y, sc["cx"], sc["cy"], sc["r_in"], sc["r_out"])
            a = round(cov * MODES[mode]["dot_alpha"] * 255)
            if a > 0:
                out[(x, y)] = a
    return out


def bake_dots(mode, scale, outdir):
    sc = SCALES[scale]
    t = sc["tile"]
    amap = dot_alpha_map(sc, mode)
    r, g, b = MODES[mode]["dot"]
    rows = []
    for y in range(t):
        row = bytearray(t * 4)
        for x in range(t):
            a = amap.get((x, y), 0)
            if a:
                row[x * 4:x * 4 + 4] = bytes((r, g, b, a))
        rows.append(row)
    path = outdir / f"midori-{mode}-dots@{scale}.png"
    write_png(path, t, t, rows, rgba=True)
    return path


def bake_glow(mode, scale, width, height, outdir):
    """Full-screen opaque bake: bg color + --page-glow washes + dot lattice.

    Perf: gradients are computed at 1/4 resolution and block-expanded (they
    are low-frequency), then the sparse dot lattice is overlaid per row.
    """
    m = MODES[mode]
    sc = SCALES[scale]
    bgr, bgg, bgb = m["bg"]
    q = 4
    qw, qh = (width + q - 1) // q, (height + q - 1) // q

    # gradients composited bottom-up (CSS lists topmost first)
    grads = []
    for rxp, ryp, cxp, cyp, col, alpha, end in reversed(m["glow"]):
        grads.append((rxp * width, ryp * height, cxp * width, cyp * height,
                      col, alpha, end))

    qrows = []
    for qy in range(qh):
        y = qy * q + q / 2
        row = bytearray(qw * 3)
        for qx in range(qw):
            x = qx * q + q / 2
            r, g, b = bgr, bgg, bgb
            for rx, ry, cx, cy, col, alpha, end in grads:
                d = hypot((x - cx) / rx, (y - cy) / ry)
                if d < end:
                    a = alpha * (1 - d / end)
                    r = r + (col[0] - r) * a
                    g = g + (col[1] - g) * a
                    b = b + (col[2] - b) * a
            row[qx * 3:qx * 3 + 3] = bytes((round(r), round(g), round(b)))
        qrows.append(row)

    # expand quarter-res rows to full width once each
    expanded = []
    for row in qrows:
        full = bytearray(width * 3)
        for qx in range(qw):
            px = row[qx * 3:qx * 3 + 3]
            start = qx * q * 3
            full[start:start + q * 3] = px * q
        expanded.append(full[:width * 3])

    # per-tile-row sparse dot entries
    amap = dot_alpha_map(sc, mode)
    t = sc["tile"]
    by_row = {}
    for (x, y), a in amap.items():
        by_row.setdefault(y, []).append((x, a))
    dr, dg, db = m["dot"]

    rows = []
    for y in range(height):
        base = expanded[min(y // q, qh - 1)]
        entries = by_row.get(y % t)
        if not entries:
            rows.append(base)
            continue
        row = bytearray(base)
        for tx, a in entries:
            for x in range(tx, width, t):
                i = x * 3
                f = a / 255
                row[i] = round(row[i] + (dr - row[i]) * f)
                row[i + 1] = round(row[i + 1] + (dg - row[i + 1]) * f)
                row[i + 2] = round(row[i + 2] + (db - row[i + 2]) * f)
        rows.append(row)

    path = outdir / f"midori-{mode}-glow@{scale}.png"
    write_png(path, width, height, rows, rgba=False)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", choices=["1x", "2x"], required=True)
    ap.add_argument("--mode", choices=["paper", "night", "both"], default="both")
    ap.add_argument("--glow-size", metavar="WxH",
                    help="physical px of the target display (e.g. 3456x2234); "
                         "omit to skip the glow bake")
    ap.add_argument("--dot-cy", type=float,
                    help="override calibrated dot center y within the tile")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent
                                         / "ghostty" / "backgrounds"))
    args = ap.parse_args()

    if args.dot_cy is not None:
        SCALES[args.scale]["cy"] = args.dot_cy

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    modes = ["paper", "night"] if args.mode == "both" else [args.mode]

    for mode in modes:
        p = bake_dots(mode, args.scale, outdir)
        print(f"baked {p}")
        if args.glow_size:
            w, h = (int(v) for v in args.glow_size.lower().split("x"))
            p = bake_glow(mode, args.scale, w, h, outdir)
            print(f"baked {p}")

    print("Reminder: Ghostty re-reads images only on config reload (Cmd+Shift+,).")


if __name__ == "__main__":
    sys.exit(main())
