#!/usr/bin/env python3
"""Contrast-check every theme in themes/ against the grounds it is read on.

WHY THIS EXISTS. Midori is low-chroma and was tuned by eye over a year, and it
works. A SECOND design language gets no such grace period: Lemonardo's hues
come from a poster palette built for fills and large display type, and "it
looks right on the site" says nothing about a 15px syntax token on a cream
editor ground. Lifting brand colour into a code editor is exactly where a
palette quietly stops being readable.

HOW THE FLOORS WERE SET -- and a correction that is the whole point of this
file. The first version used WCAG bands straight from the standard: 7.0 AAA
for prose, 4.5 AA for syntax. MIDORI FAILED TWELVE OF THEM. Its own shipped
ochre measures 2.76 against paper and clay 2.40. A check that fails the
reference implementation is measuring the wrong thing, so the thresholds were
wrong and the palette was fine.

The second version overcorrected: it set each floor to the reference's weakest
value in that band and mode. That fails Midori's dark prose at 13.17 as a bar
for Lemonardo's 9.83 -- which is comfortably past AAA and perfectly readable.
Parity between two different design languages is not a goal; both being
readable is.

So the floors below are the MEASURED MINIMA OF THE SHIPPED MIDORI THEME,
rounded down, with the measurement recorded beside each one. They are checked
in rather than computed so that changing the bar is a visible edit, and
tests/test_theme_floors.py re-derives them from themes/midori.json so they
cannot drift from it silently.

  band        floor   Midori   Lemonardo   note
  prose        7.0     9.54       8.63      AAA; body text read for hours
  secondary    3.5     3.56       5.05      Midori's own code-comment is 3.56
  recessive    3.0     3.19       3.08      rules, placeholders, disabled
  syntax       2.4     2.40       2.46      see below -- deliberately low
  on-accent    4.5     4.74       4.97      text on an accent fill

SYNTAX AT 2.4 IS A DELIBERATE AESTHETIC, NOT AN OVERSIGHT. Midori's warm hues
on a cream ground do not reach WCAG AA and never have; clay sits at 2.40 and
has been read daily for a year. Recording it here stops the next reader
"fixing" it into a brighter palette that is no longer Midori. If that tradeoff
is ever revisited it should be revisited on purpose, for both themes at once.

THE SECOND GATE catches what a floor cannot: one bad token in a palette that
is otherwise fine. A hue more than REGRESSION_TOLERANCE worse than the
reference's same hue fails -- but only when it lands below DANGER_ZONE, so a
drop from 13.17 to 9.83 is correctly ignored while 6.83 to 4.21 is not. That
second case is real: it is what the first Lemonardo draft did to indigo.

    python3 tests/check_theme_contrast.py            # all themes
    python3 tests/check_theme_contrast.py lemonardo # one theme
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
THEMES = ROOT / "themes"
REFERENCE = "midori"

# THE RULE, in one line:
#     floor = min(WCAG standard for the band, Midori's measured minimum)
# Hold a theme to the standard, except where the shipped reference proves this
# design language does not work that way -- then hold it to the reference.
# Both halves matter. Using the standard alone fails Midori (version one of
# this file); using the reference alone fails Lemonardo's softer dark mode
# for being 9.83 against Midori's 13.17 (version two).
STANDARD = {"prose": 7.0,        # WCAG AAA, normal text
            "secondary": 4.5,    # WCAG AA, normal text
            "recessive": 3.0,    # WCAG AA, large text / UI
            "syntax": 4.5,       # a syntax token is small continuous text
            "on-accent": 4.5}
# Midori's measured minimum per band, across both modes, from themes/midori.json.
REFERENCE_MIN = {"prose": 9.54, "secondary": 3.56, "recessive": 3.19,
                 "syntax": 2.40, "on-accent": 4.74}
FLOORS = {b: int(min(STANDARD[b], REFERENCE_MIN[b]) * 10) / 10.0 for b in STANDARD}

# A hue may be this much worse than the reference before it fails, but only
# if it also lands below DANGER_ZONE. Wide enough that a different brand's
# hue family is not punished for being a different colour; tight enough to
# have caught Lemonardo's first indigo at 4.21 against Midori's 6.83.
REGRESSION_TOLERANCE = 1.5
DANGER_ZONE = 5.0

CHECKS = [
    ("text",             ["paper", "card", "secondary"], "prose"),
    ("ink",              ["paper", "card"],              "prose"),
    ("code-normal",      ["card"],                       "prose"),
    ("muted",            ["paper", "card"],              "secondary"),
    ("code-comment",     ["card"],                       "secondary"),
    ("code-punctuation", ["card"],                       "secondary"),
    ("faint",            ["paper"],                      "recessive"),
]
# The hues that carry meaning in each target's code mapping. Each has to be
# readable as small text on both grounds it can land on.
HUES = ["sage", "indigo", "olive", "wine", "ochre",
        "purple", "mint", "clay", "mythic", "terracotta"]

# Guide colours are the INVERSE assertion, and they are the rule most likely to
# be "fixed" by someone being helpful. A drafting guide -- non-photo blue, a rule
# line, a peg-bar shadow -- is doing its job only while it CANNOT be read: col-erase
# blue existed because the rostrum camera could not see it, so an animator drafted
# in it and inked straight over without erasing. Darkening one until it passes an
# ordinary contrast check destroys the thing the check was meant to protect. So
# these are held BELOW a ceiling. A theme with no guide roles is not failed for it,
# but the count is printed either way -- a guard that silently examined nothing is
# this repo's documented failure mode, not a pass.
GUIDES = ["guide", "guide-pale", "peg"]
GUIDE_CEILING = 2.0

# A theme MAY carry a "syntax" map naming which palette role each code token
# takes, per mode. It holds role names, never colours, so the tone it resolves
# to is already covered by the HUES loop above; what this gate catches is a
# token pointing at a role that does not exist, or at one whose hue lands in a
# band too weak to carry small continuous text. It exists because a sweep of the
# mockup boards found 106 hex literals belonging to no role -- syntax colours
# were being invented per board, so no two surfaces agreed and nothing could be
# emitted. A theme with no syntax map is not failed for it; the count prints
# either way, because a guard that silently examined nothing is this repo's
# documented failure mode, not a pass.
SYNTAX_GROUND = "card"


def srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def pairs():
    """Every (role, ground, band) asserted here. One definition, used for both
    the reference and the theme under test, so the two cannot drift."""
    out = [(role, ground, band)
           for role, grounds, band in CHECKS for ground in grounds]
    out += [(hue, ground, "syntax") for hue in HUES for ground in ("paper", "card")]
    out.append(("on-accent", "sage", "on-accent"))
    return out


def measure(pal, mode):
    return {(r, g): ratio(pal[r][mode], pal[g][mode])
            for r, g, _ in pairs() if r in pal and g in pal}


def check_theme(path, ref_pal):
    theme = json.loads(path.read_text())
    pal, name = theme["palette"], theme["name"]
    is_ref = theme["id"] == REFERENCE
    print(f"\n=== {name}  ({path.name}){'   [reference]' if is_ref else ''}")

    checked = failures = 0
    worst = {}
    for mode in ("light", "dark"):
        ref = measure(ref_pal, mode)
        for role, ground, band in pairs():
            if role not in pal or ground not in pal:
                print(f"  FAIL {mode}/{role} on {ground}: role missing from palette")
                failures += 1
                continue
            r = ratio(pal[role][mode], pal[ground][mode])
            checked += 1
            worst[band] = min(worst.get(band, 99.0), r)

            floor = FLOORS[band]
            if r < floor:
                failures += 1
                print(f"  FAIL {mode:<5} {band:<10} {role:>17} on {ground:<10} "
                      f"{r:5.2f}  below the {band} floor {floor}")
                continue

            if not is_ref and r < DANGER_ZONE:
                rv = ref.get((role, ground))
                if rv is not None and rv - r > REGRESSION_TOLERANCE:
                    failures += 1
                    print(f"  FAIL {mode:<5} {band:<10} {role:>17} on {ground:<10} "
                          f"{r:5.2f}  vs {REFERENCE} {rv:5.2f} "
                          f"(regression {rv - r:.2f} in the danger zone)")

    guides = 0
    for mode in ("light", "dark"):
        for role in GUIDES:
            if role not in pal or "paper" not in pal:
                continue
            r = ratio(pal[role][mode], pal["paper"][mode])
            guides += 1
            if r > GUIDE_CEILING:
                failures += 1
                print(f"  FAIL {mode:<5} {'guide':<10} {role:>17} on paper      "
                      f"{r:5.2f}  ABOVE the guide ceiling {GUIDE_CEILING} -- "
                      "a guide that reads as text is not a guide")

    tokens = resolved = 0
    for token, by_mode in (theme.get("syntax") or {}).items():
        for mode in ("light", "dark"):
            role = by_mode.get(mode)
            tokens += 1
            if role not in pal:
                failures += 1
                print(f"  FAIL {mode:<5} {'syntax':<10} {token:>17} names role "
                      f"{role!r}, which is not in the palette")
                continue
            resolved += 1
            if SYNTAX_GROUND not in pal:
                continue
            r = ratio(pal[role][mode], pal[SYNTAX_GROUND][mode])
            if r < FLOORS["syntax"]:
                failures += 1
                print(f"  FAIL {mode:<5} {'syntax':<10} {token:>17} -> {role} on "
                      f"{SYNTAX_GROUND:<6} {r:5.2f}  below the syntax floor "
                      f"{FLOORS['syntax']}")

    bands = "  ".join(f"{b} {worst[b]:.2f}" for b in sorted(worst))
    print(f"  {checked} pair(s) checked, {failures} failure(s)")
    print(f"  weakest per band: {bands}")
    print(f"  {guides} guide(s) checked against the {GUIDE_CEILING} ceiling"
          if guides else "  no guide roles in this theme")
    # Attempted AND resolved, never just one number: an earlier version printed
    # "18 resolved" while one token named a role that did not exist, which is the
    # confident-but-vacuous count this file exists to prevent.
    print(f"  {resolved} of {tokens} syntax token-mode(s) resolved to a palette role"
          if tokens else "  no syntax map in this theme")
    if checked == 0:
        print("  FAIL this theme produced no checks at all -- that is not a pass")
        return 1
    return 1 if failures else 0


def main():
    if not THEMES.is_dir():
        print(f"FAIL no themes/ directory at {THEMES}")
        return 1
    ref_path = THEMES / f"{REFERENCE}.json"
    if not ref_path.is_file():
        print(f"FAIL the reference theme {ref_path} is missing; "
              "every floor here is calibrated against it")
        return 1
    ref_pal = json.loads(ref_path.read_text())["palette"]

    files = sorted(THEMES.glob("*.json"))
    if len(sys.argv) > 1:
        files = [f for f in files if f.stem == sys.argv[1]]
    if not files:
        # An empty input set is a failure, never a silent pass. This repo has
        # shipped a linter that traversed zero files for two days.
        print("FAIL no theme files matched -- nothing was checked")
        return 1

    print(f"contrast: {len(files)} theme file(s), floors calibrated on {REFERENCE}")
    bad = sum(check_theme(f, ref_pal) for f in files)
    print(f"\n{'CONTRAST: all green' if not bad else f'CONTRAST: {bad} theme(s) failed'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
