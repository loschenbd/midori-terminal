#!/usr/bin/env python3
"""Regenerate the embedded @font-face block at the foot of theme.css.

iOS has no font installer, so the theme carries its own Latin subsets of
Spectral and M PLUS 1p as base64 data URIs. Obsidian injects theme.css into a
<style> element rather than <link>ing it, so relative url() would resolve
against the app document — data URIs are the only route that works.

Run after changing FAMILIES; it rewrites everything from the FONT_FENCE marker
to the end of theme.css and leaves the rest of the file untouched.

    ./obsidian/build-fonts.py && ./obsidian/install-obsidian.sh

Needs fontTools and brotli to rewrite the alias faces' metric tables. macOS
ships a PEP-668 "externally managed" Python that refuses `pip install`, so if
the imports are missing this script builds itself a venv in obsidian/.fontenv
and re-execs into it. Nothing to do by hand.
"""
import base64
import io
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEME = HERE / "theme.css"
FONT_FENCE = "/* ==========================================================================\n   Embedded webfonts"


def ensure_fonttools():
    try:
        import fontTools  # noqa: F401
        import brotli     # noqa: F401  (woff2 compression)
        return
    except ImportError:
        pass
    venv = HERE / ".fontenv"
    py = venv / "bin" / "python3"
    if not py.exists():
        print(f"provisioning {venv} (fonttools, brotli)…", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run([str(py), "-m", "pip", "install", "-q", "fonttools", "brotli"],
                       check=True)
    os.execv(str(py), [str(py), str(Path(__file__).resolve()), *sys.argv[1:]])


ensure_fonttools()
from fontTools.ttLib import TTFont  # noqa: E402

# Google Fonts serves a different (smaller, woff2) payload to modern browsers.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Covers all three --font-*-theme families the theme declares. Leaving one out
# means that role alone falls back to a system face on iOS, which is the exact
# failure this file exists to prevent.
CSS2 = ("https://fonts.googleapis.com/css2"
        "?family=M+PLUS+1p:wght@400;500;700"
        "&family=M+PLUS+1+Code:wght@400;700"
        "&family=Spectral:ital,wght@0,400;0,500;0,600;1,400"
        "&display=swap")

# Only the Latin subset ships. The full CJK coverage of M PLUS 1p would be
# megabytes; desktop still gets it through the local() sources below.
LATIN = "U+0000-00FF"

# family, weight, style -> local() names to try before the embedded copy, so
# machines with the Homebrew casks keep using the complete installed families.
LOCALS = {
    ("M PLUS 1p", "400", "normal"): ["M PLUS 1p", "MPLUS1p-Regular"],
    ("M PLUS 1p", "500", "normal"): ["M PLUS 1p Medium", "MPLUS1p-Medium"],
    ("M PLUS 1p", "700", "normal"): ["M PLUS 1p Bold", "MPLUS1p-Bold"],
    ("M PLUS 1 Code", "400", "normal"): ["M PLUS 1 Code", "MPLUS1Code-Regular"],
    ("M PLUS 1 Code", "700", "normal"): ["M PLUS 1 Code Bold", "MPLUS1Code-Bold"],
    ("Spectral", "400", "normal"): ["Spectral", "Spectral-Regular"],
    ("Spectral", "500", "normal"): ["Spectral Medium", "Spectral-Medium"],
    ("Spectral", "600", "normal"): ["Spectral SemiBold", "Spectral-SemiBold"],
    ("Spectral", "400", "italic"): ["Spectral Italic", "Spectral-Italic"],
}

# Metric-normalised aliases. Each source family is emitted TWICE: once stock,
# for interface chrome, and once under the alias below with symmetric ascent and
# descent, for prose.
#
# WHY. A single-line box seats its baseline at L/2 + F*(A-D)/2, where A and D
# are the font's ascent and descent as fractions of the em and F is the font
# size. With the real metrics that second term is a per-font constant times the
# font size — Spectral 0.2980, M PLUS 1p 0.3775 — which is precisely the ladder
# of per-heading-level magic numbers this theme used to carry. Setting A = D
# makes the term vanish for EVERY font size, so every baseline sits at exactly
# L/2 and every margin becomes a plain multiple of the row.
#
# WHY ALIASES AND NOT AN OVERRIDE IN PLACE. Normalising the real Spectral would
# move its baseline up by 0.298 * font-size — about 4px at interface size —
# inside every button, menu and file-tree row, which centre their text on the
# line box. Prose gets the normalised metrics; the UI keeps the font as drawn.
#
# WHY 45%. Content-area height becomes (A + D) * F, and `line-height: 24px`
# only governs while that stays under 24px (a line box is max(strut, content)).
# The largest prose text is h1 at --h1-size 1.618em, so the ceiling is
# A <= 12 / (1.618 * baseFontSize): 0.53 at base 14, 0.46 at base 16. 45% holds
# up to roughly base 16.5. Above that h1 needs a 48px box and the half-row
# margin rule comes back.
ALIAS = {
    "M PLUS 1p": "Midori Text",
    "Spectral": "Midori Display",
    "M PLUS 1 Code": "Midori Mono",
}
ASCENT = DESCENT = 0.45
LINE_GAP = 0.0


def normalise(woff2, ascent=ASCENT, descent=DESCENT, line_gap=LINE_GAP):
    """Rewrite a face's vertical metrics in the BINARY, and return new woff2.

    THE DESCRIPTORS ALONE ARE NOT ENOUGH — this is not belt-and-braces. CSS
    `ascent-override` / `descent-override` / `line-gap-override` are honoured by
    Blink, so desktop Obsidian (Electron) was correct with descriptors only, but
    WebKit ignores them outright. Measured on iOS 26 / Obsidian mobile: setting
    the alias faces to `ascent-override: 0%; descent-override: 100%` — which
    would have thrown every baseline half a row — produced screenshots identical
    to the bit, and prose sat 5.29px low, exactly M PLUS 1p's own 0.3775 * 14.
    Baking the numbers into the font makes the fix engine-independent: there is
    no descriptor left for a UA to skip.

    All three metric sources are set to the same values, because which one an
    engine reads is not something a theme gets to choose: Blink prefers hhea on
    macOS and usWin on Windows, WebKit goes through Core Text, and OS/2's
    USE_TYPO_METRICS bit (set here) redirects both to sTypo. Setting one and
    leaving the others is how a font ends up with a different line box per
    platform.

    usWinAscent/usWinDescent are deliberately tightened to 0.45em even though
    that is smaller than the ink. They are a clipping hint on Windows and a line
    metric in some engines; a value that disagreed with hhea would reintroduce
    exactly the per-platform divergence this exists to remove. The theme has
    always drawn glyphs outside their declared box — that is what makes 45%
    work at h1 — so this changes nothing that was not already true.
    """
    font = TTFont(io.BytesIO(woff2))
    upm = font["head"].unitsPerEm
    a, d, g = round(ascent * upm), round(descent * upm), round(line_gap * upm)

    hhea = font["hhea"]
    hhea.ascent, hhea.descent, hhea.lineGap = a, -d, g

    os2 = font["OS/2"]
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = a, -d, g
    os2.usWinAscent, os2.usWinDescent = a, d
    if os2.version >= 4:
        # Bit 7 is USE_TYPO_METRICS, and it is only defined from version 4.
        # Do not bump an older table to reach it: versions below 4 lack
        # sxHeight/sCapHeight/usDefaultChar/usBreakChar/usMaxContext entirely,
        # so raising the number means inventing five fields. The bit is
        # decoration here anyway — sTypo, hhea and usWin now all say the same
        # thing, so there is nothing left for it to disambiguate.
        os2.fsSelection |= 1 << 7

    out = io.BytesIO()
    font.flavor = "woff2"
    font.save(out)
    return out.getvalue()

HEADER = """/* ==========================================================================
   Embedded webfonts — Latin subsets, base64 data URIs. Generated by
   build-fonts.py; do not hand-edit below this line.

   Each family appears twice: stock, and again as a "Midori …" alias carrying
   symmetric ascent/descent overrides. The aliases are what prose uses; the
   stock copies are what the interface uses. See ALIAS in build-fonts.py for
   why the two cannot be the same face.

   WHY THIS IS HERE. Spectral and M PLUS 1p install on the Mac via Homebrew
   casks, but iOS offers no way to install a font, so on iPhone/iPad the stack
   fell through to a system serif. A different typeface seats its baseline
   elsewhere inside the same 24px line box — which is precisely what knocked
   the dot grid out of register on mobile.

   WHY DATA URIs AND NOT FILES NEXT TO theme.css. Obsidian does not <link> a
   theme; it reads theme.css and injects the text into a <style> element
   (app.js: this.styleEl.setText). Relative url() therefore resolves against
   the app document, not the theme folder, so loose .woff2 files alongside
   would silently 404. Data URIs also ride along with the single theme.css
   that install-obsidian.sh already fans out to every vault.

   local() IS LISTED FIRST on the STOCK faces on purpose: desktop keeps the
   full installed families, including the CJK coverage these Latin subsets
   drop. The alias faces carry NO local() — see normalise() in build-fonts.py.

   Source: Google Fonts (SIL Open Font License 1.1).
   ========================================================================== */"""


def fetch(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA})).read()


def faces():
    """Yield (family, weight, style, woff2 bytes) for the Latin subsets."""
    sheet = fetch(CSS2).decode()
    for block in re.findall(r"@font-face\s*{[^}]*}", sheet):
        get = lambda k: re.search(rf"{k}:\s*([^;]+);", block).group(1).strip()
        if LATIN not in get("unicode-range"):
            continue  # cyrillic / greek / vietnamese / CJK slices
        family = get("font-family").strip("\"'")
        url = re.search(r"url\(([^)]+)\)", block).group(1)
        yield family, get("font-weight"), get("font-style"), fetch(url)


def main():
    blocks = []
    for family, weight, style, data in sorted(faces(), key=lambda f: f[:3]):
        key = (family, weight, style)
        if key not in LOCALS:
            sys.exit(f"no local() names for {key} — add it to LOCALS")
        local = ",\n       ".join(f'local("{n}")' for n in LOCALS[key])
        b64 = base64.b64encode(data).decode()
        blocks.append(f"""@font-face {{
  font-family: "{family}";
  font-style: {style};
  font-weight: {weight};
  font-display: swap;
  src: {local},
       url(data:font/woff2;base64,{b64}) format("woff2");
}}""")
        # Metric-normalised twin, from a REWRITTEN binary — see normalise().
        #
        # NO local() HERE, and that is the point. local() would hand desktop the
        # Homebrew face, whose metrics are the stock ones, so the normalisation
        # would depend on the CSS descriptors below actually being honoured —
        # which is the WebKit assumption that broke mobile. Serving the patched
        # binary to every platform is what makes the two agree. The cost is CJK
        # prose on desktop, which now falls through to the next family in the
        # stack exactly as it already did on iOS; it would have been off-grid
        # under the installed face's metrics regardless.
        #
        # The descriptors are kept because they cost nothing and state the
        # intent at the point of use, but they are no longer load-bearing.
        b64a = base64.b64encode(normalise(data)).decode()
        blocks.append(f"""@font-face {{
  font-family: "{ALIAS[family]}";
  font-style: {style};
  font-weight: {weight};
  font-display: swap;
  ascent-override: {ASCENT:.0%};
  descent-override: {DESCENT:.0%};
  line-gap-override: {LINE_GAP:.0%};
  src: url(data:font/woff2;base64,{b64a}) format("woff2");
}}""")

    if len(blocks) != 2 * len(LOCALS):
        sys.exit(f"expected {2 * len(LOCALS)} faces, got {len(blocks)}")

    css = THEME.read_text()
    head = css.split(FONT_FENCE)[0].rstrip("\n")
    THEME.write_text(head + "\n\n" + HEADER + "\n\n" + "\n\n".join(blocks) + "\n")
    print(f"embedded {len(blocks)} faces -> {THEME} ({THEME.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
