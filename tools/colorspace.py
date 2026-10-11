#!/usr/bin/env python3
"""sRGB <-> Oklab/OKLCH <-> CIELAB, WCAG contrast, CIEDE2000. No dependencies.

WHY THIS EXISTS RATHER THAN A PIP PACKAGE. Every colour claim in this repo is
supposed to be a measurement, and a measurement nobody can re-run is a claim.
The repo's tests run with the system python3 and no virtualenv, so a colour
library would make the gates unrunnable on a clean checkout -- which is how
tests/lint.sh traversed zero files for two days. 120 lines of published matrix
arithmetic is cheaper than that failure mode.

Sources for the constants, so they can be checked rather than trusted:
  - Oklab forward/inverse matrices: Bjoern Ottosson, "A perceptual color space
    for image processing" (2020), the published M1/M2 and their inverses.
  - sRGB transfer function and D65 white: IEC 61966-2-1.
  - WCAG 2.x relative luminance and contrast ratio: WCAG 2.1 definitions.
  - CIEDE2000: Sharma, Wu & Dalal (2005), "The CIEDE2000 Color-Difference
    Formula", including the rotation term and the G factor. Verified below
    against four of that paper's own test pairs -- see selftest(). One of the
    four is from the quartet published to catch a wrong hue-mean branch.

WHICH DIFFERENCE METRIC TO USE WHERE. Oklab euclidean distance is the right
tool for CHOOSING colours (it is smooth and has no hue-angle discontinuity, so
it behaves under optimisation). CIEDE2000 is the right tool for REPORTING how
different two finished colours are, because it is the metric everyone else's
numbers are in. This module provides both and the callers say which they mean.
"""
import math

D65 = (0.95047, 1.00000, 1.08883)


# --------------------------------------------------------------------------
# sRGB
# --------------------------------------------------------------------------
def _to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_gamma(c):
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


def in_gamut(rgb, eps=1e-6):
    return all(-eps <= c <= 1 + eps for c in rgb)


# --------------------------------------------------------------------------
# Oklab / OKLCH
# --------------------------------------------------------------------------
def rgb_to_oklab(rgb):
    r, g, b = (_to_linear(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def oklab_to_rgb(lab):
    L, A, B = lab
    l_ = L + 0.3963377774 * A + 0.2158037573 * B
    m_ = L - 0.1055613458 * A - 0.0638541728 * B
    s_ = L - 0.0894841775 * A - 1.2914855480 * B
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return (_to_gamma(r), _to_gamma(g), _to_gamma(b))


def oklab_to_oklch(lab):
    L, A, B = lab
    return (L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360)


def oklch_to_oklab(lch):
    L, C, H = lch
    t = math.radians(H)
    return (L, C * math.cos(t), C * math.sin(t))


def hex_to_oklch(h):
    return oklab_to_oklch(rgb_to_oklab(hex_to_rgb(h)))


def oklch_to_hex_clamped(L, C, H, tol=1e-4):
    """The sRGB hex for (L, C, H), reducing C until it fits the gamut.

    THE CLAMP IS ON CHROMA ALONE, DELIBERATELY. Clamping the RGB channels
    instead -- the obvious shortcut -- moves hue and lightness by whatever
    the clip happens to do, which silently breaks the uniform-lightness
    property the whole palette is built on. Reducing C holds both.
    Returns (hex, achieved_C).
    """
    if in_gamut(oklab_to_rgb(oklch_to_oklab((L, C, H)))):
        return rgb_to_hex(oklab_to_rgb(oklch_to_oklab((L, C, H)))), C
    lo, hi = 0.0, C
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if in_gamut(oklab_to_rgb(oklch_to_oklab((L, mid, H)))):
            lo = mid
        else:
            hi = mid
    return rgb_to_hex(oklab_to_rgb(oklch_to_oklab((L, lo, H)))), lo


def d_oklab(h1, h2):
    a, b = rgb_to_oklab(hex_to_rgb(h1)), rgb_to_oklab(hex_to_rgb(h2))
    return math.dist(a, b)


# --------------------------------------------------------------------------
# CIELAB + CIEDE2000
# --------------------------------------------------------------------------
def hex_to_cielab(h):
    r, g, b = (_to_linear(c) for c in hex_to_rgb(h))
    X = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    Y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    Z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29
    fx, fy, fz = f(X / D65[0]), f(Y / D65[1]), f(Z / D65[2])
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def ciede2000(h1, h2):
    L1, a1, b1 = hex_to_cielab(h1)
    L2, a2, b2 = hex_to_cielab(h2)
    kL = kC = kH = 1.0
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7))) if Cb else 0.5
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0

    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)

    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbp = (h1p + h2p + 360) / 2
    else:
        hbp = (h1p + h2p - 360) / 2

    T = (1 - 0.17 * math.cos(math.radians(hbp - 30))
         + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6))
         - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dTheta = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) if Cbp else 0.0
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dTheta)) * Rc

    return math.sqrt((dLp / (kL * Sl)) ** 2 + (dCp / (kC * Sc)) ** 2
                     + (dHp / (kH * Sh)) ** 2
                     + Rt * (dCp / (kC * Sc)) * (dHp / (kH * Sh)))


# --------------------------------------------------------------------------
# WCAG
# --------------------------------------------------------------------------
def relative_luminance(h):
    r, g, b = (_to_linear(c) for c in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(h1, h2):
    a, b = relative_luminance(h1), relative_luminance(h2)
    lo, hi = min(a, b), max(a, b)
    return (hi + 0.05) / (lo + 0.05)


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
def selftest(verbose=True):
    """Prove the two formulas against published values before anyone trusts a
    number out of this module. A colour-difference function that is subtly
    wrong produces confident, plausible, wrong palettes -- the exact failure
    this repo keeps rediscovering. Pairs 1, 2, 17 and 25 of the Sharma/Wu/Dalal
    CIEDE2000 test set, converted to sRGB hex, so the tolerance is loose
    (0.35) to absorb the Lab->sRGB->Lab round trip; the formula itself is
    checked on the Lab values directly.
    """
    fails = 0

    # CIEDE2000 straight on the paper's Lab pairs (no sRGB round trip).
    # Pairs 1, 2, 17 and 24 of the published test set. Pair 17 is deliberately
    # included: it is one of the b2 = 0.0009 / 0.0010 / 0.0011 / 0.0012 quartet
    # that exists precisely to catch a wrong hue-mean branch, and its four
    # answers are 7.1792, 7.1792, 7.2195, 7.2195.
    #
    # CORRECTED. This list first asserted 7.1792 for b2 = 0.0012 and the check
    # went red. The formula was right and the EXPECTATION was wrong: 7.1792
    # belongs to b2 = 0.0009 and 0.0010, and 0.0011/0.0012 step up to 7.2195 --
    # which is exactly the discontinuity the quartet was published to expose.
    # Worth leaving written down, because the instinct on a red colour-maths
    # check is to go edit the formula, and that would have broken a correct one.
    cases = [((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
             ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
             ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0012), 7.2195),
             ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492)]
    import types
    for lab1, lab2, want in cases:
        # ciede2000() takes hex; call the formula on Lab by monkeypatching the
        # converter for the duration of the check. Converting these Lab values
        # to sRGB would clip them (several are outside the gamut), which is why
        # the published pairs cannot be checked through hex at all.
        g = globals()
        real = g["hex_to_cielab"]
        table = {"a": lab1, "b": lab2}
        g["hex_to_cielab"] = lambda k: table[k]
        try:
            got = ciede2000("a", "b")
        finally:
            g["hex_to_cielab"] = real
        if abs(got - want) > 1e-4:
            print(f"  FAIL ciede2000{lab1}{lab2} = {got:.4f}, published {want}")
            fails += 1
        elif verbose:
            print(f"  ok   ciede2000 published pair -> {got:.4f} (want {want})")
    assert isinstance(types, types.ModuleType)

    # Oklab round trip: every value must survive rgb -> oklab -> rgb.
    worst = 0.0
    for h in ("#000000", "#ffffff", "#ff4000", "#003153", "#50c878",
              "#a4dded", "#8d029b", "#f3eee2", "#2c2a28"):
        back = rgb_to_hex(oklab_to_rgb(rgb_to_oklab(hex_to_rgb(h))))
        worst = max(worst, max(abs(x - y) for x, y in
                               zip(hex_to_rgb(h), hex_to_rgb(back))))
        if back != h:
            print(f"  FAIL oklab round trip {h} -> {back}")
            fails += 1
    if verbose and not fails:
        print(f"  ok   oklab round trip exact for 9 values "
              f"(worst channel error {worst:.2e})")

    # WCAG against externally published anchors. #767676-on-white is the
    # canonical "just passes AA for body text" grey at 4.54:1 and #595959 is
    # the canonical AAA one at 7.00:1; both are quoted all over the WCAG
    # literature, which makes them a real external check rather than a value
    # read back out of this same function.
    #
    # CORRECTED. This block first asserted contrast("#777777", "#ffffff") ==
    # 4.47586 and failed by 0.002. The five-decimal expectation was invented:
    # #777777-on-white is 4.478, and the 4.5-ish figure everyone quotes is
    # #767676. A fabricated precision is worse than no check, because it makes
    # a correct implementation look broken.
    for a, b, want in (("#ffffff", "#000000", 21.0),
                       ("#767676", "#ffffff", 4.54222),
                       ("#595959", "#ffffff", 7.00473),
                       ("#ffffff", "#ffffff", 1.0)):
        got = contrast(a, b)
        if abs(got - want) > 5e-4:
            print(f"  FAIL contrast({a},{b}) = {got:.5f}, want {want}")
            fails += 1
        elif verbose:
            print(f"  ok   contrast({a},{b}) -> {got:.5f}")
        if abs(contrast(b, a) - got) > 1e-12:
            print(f"  FAIL contrast is not symmetric for {a}/{b}")
            fails += 1

    # Chroma clamp must land IN gamut and hold L and H.
    for L, H in ((0.52, 34.5), (0.72, 245.9), (0.80, 71.7), (0.45, 323.4)):
        hx, c = oklch_to_hex_clamped(L, 0.40, H)
        gl, gc, gh = hex_to_oklch(hx)
        dh = min(abs(gh - H), 360 - abs(gh - H))
        if not in_gamut(hex_to_rgb(hx), 0) or abs(gl - L) > 0.004 or dh > 0.6:
            print(f"  FAIL clamp(L={L},H={H}) -> {hx} "
                  f"(L={gl:.4f} dH={dh:.3f})")
            fails += 1
        elif verbose:
            print(f"  ok   clamp(L={L}, H={H}) -> {hx} C={c:.3f} "
                  f"(L off by {abs(gl - L):.4f}, H off by {dh:.3f}deg)")

    print(f"colorspace selftest: {'all green' if not fails else 'FAILURES'} "
          f"({len(cases)} ciede2000 + 9 round trips + 4 contrasts + 4 clamps)")
    return fails


if __name__ == "__main__":
    import sys
    sys.exit(1 if selftest() else 0)
