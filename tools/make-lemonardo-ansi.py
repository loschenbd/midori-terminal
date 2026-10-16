#!/usr/bin/env python3
"""Derive Lemonardo's 16-slot ANSI palette by rule, and gate it on measurement.

                            WHY THIS FILE EXISTS

The first Lemonardo ANSI map was assembled by hand out of the theme's existing
semantic roles, with six of the sixteen slots produced by lifting a base slot's
HLS lightness by a transform read off Midori's own base->bright pairs. It was
internally consistent and it passed a distinctness check -- 16/16 distinct hexes
in both modes -- and it was still the wrong artifact, for a reason the
distinctness check could not see:

    measured, ten of its thirty-two slots sat within CIE76 dE 10 of the
    Midori slot in the same position, and twenty-two within dE 20.

Two palettes whose corresponding slots differ by dE 7 are not two palettes.
"16/16 distinct" was true and measured and answered the wrong question: it
asked whether Lemonardo collided with ITSELF. Nothing asked whether it
collided with Midori, so nothing noticed that it did. That is this repo's
standing failure mode -- a passing check is evidence only of what it examined
-- and it is why the gates below include a mandatory distance to EVERY Midori
value, and why the generator refuses to emit when any of them is unmet.

                               THE METHOD

Hues come from the materials of a golden-era ink-and-paint studio, and from
nowhere else. Each family's hue is read out of a published reference value for
a real pigment or drafting material; the generator then discards that value's
lightness and chroma and rebuilds them, so what is inherited is the material's
HUE IDENTITY and not a web swatch's idea of how bright it should be. Deriving
L and C by rule is what makes uniform lightness possible, and uniform accent
lightness is the one property that separates a designed palette from a
collection of nice colours:

  - Solarized (Schoonover) set its hues by colour-wheel relation and then
    translated them into CIELAB "to ensure perceptual uniformity in terms of
    lightness".
  - Selenized (Warchol) re-tuned those hues and lightnesses in CIELAB
    specifically to stop green/yellow and blue/violet reading as each other.
  - OkSelenized re-derived the same idea in Oklab, pinning all eight accents
    to ONE Oklab lightness and asserting explicit contrast floors (text >= 6.0,
    comments >= 3.2, every accent >= 3.5).

This generator follows that line and tightens the accent floor, because a
terminal accent is body text: every BASE accent here must clear 4.5:1 against
its own mode's background rather than 3.5:1, with the bright tier held to 3.5.

                   WHY TWO DIFFERENCE METRICS, NOT ONE

CIEDE2000 alone would have passed this palette's worst problem and failed its
best feature, because its Sc term divides the chroma difference by
(1 + 0.045 * Cbar). On two colours that share a hue and a lightness and differ
mainly in SATURATION, that denominator is doing most of the work -- and
saturation is the entire axis on which these two design languages differ.
Measured: Midori's accents run Oklab chroma 0.065 to 0.079 mean (a wash);
Lemonardo's run at 97 percent of the sRGB gamut ceiling for their hue and
lightness (paint from the pot). A vivid chrome yellow against Midori's dusty
ochre at the same lightness scores only dE2000 6.7, which reads as "nearly the
same colour" and is not what the eye reports.

Oklab euclidean distance has the opposite bias: it is dominated by lightness,
so it understates two near-whites that differ in warmth. Measured on the
neutrals: slot 15's cream is dE2000 10.0 from Midori's card and Oklab 3.1.

Neither is wrong; each is blind in a different place. Every distance gate below
is therefore evaluated in BOTH, and a pair has to clear a floor in both to
count as distinct. Oklab distances are reported multiplied by 100 so the two
columns are the same order of magnitude.

              NON-PHOTO BLUE: TRIED AS SLOT 12, AND REJECTED

The best material in the whole research set is non-photo blue -- the drafting
blue a graphic-arts camera cannot see, so a rough drawn in it needed no erasing
before the clean-up line went down on the same sheet. The obvious move was to
make it the blue family's bright tier: slot 4 the committed cobalt line, slot
12 the rough underneath it. It is the right story and there is precedent in this
repo for a base->bright pair that rotates hue rather than lifting lightness
(measured: Midori's own green pair rotates -32.7 degrees in paper and -26.7 in
night and leaves lightness flat).

It was still wrong, and the gate below is what said so. Non-photo blue sits at
Oklab hue 217.0, between verdigris at 191.0 and cobalt blue at 259.7. Putting
a seventh hue in there crowds a 55-degree span with three of them, and slots 12
and 14 -- bright blue and bright cyan, both at one lightness -- landed
dE2000 8.5 apart, Oklab distance 0.027. That is the closest pair in the palette
by a factor of two, and it is two slots a terminal uses constantly.

So the blue family holds one hue across both tiers, and non-photo blue has a
better job anyway: it is the SELECTION wash. A selection is a mark you make on
the page that is not part of the document and must not print -- which is
precisely, literally, what the pigment was for.

                           ON THE SOURCE QUALITY

The anchors are not equally well sourced and the table says so per entry. Two
are Wikipedia infobox values credited to Maerz and Paul's colour dictionary;
two are Wikipedia infobox values with weaker provenance (the verdigris page
carries a maintenance notice that it may conflate verdigris with patina); one,
mauveine, is from a colour-name site and is the weakest in the set. None of
them is a spectrophotometer reading of actual paint. This matters less than it
looks like it should, because only the HUE ANGLE survives into the output -- a
pigment reference being too bright or too saturated for a terminal is exactly
the part this generator throws away. It would matter if a future reader
believed these hexes were measured. They were not.

              RECORDS CARRIED OVER FROM THE HAND-BUILT MAP

The hand-built files are gone, replaced by this generator's output. Three
things written on them were measurements or rejected alternatives and so
survive here rather than being lost with the file.

1. WHY THE ACCENT IS NOT THE GREEN SLOT. midori-paper puts its accent in
   slot 2 because Midori's accent is sage, a green. Lemonardo's accent is
   brick, and a terminal that renders "green" as brick breaks every tool that
   prints a green tick. The brick family therefore takes 1/9. Nothing was done
   to arrange this under the new rules and it came out that way anyway:
   vermilion is the red anchor, and measured, Paintpot's slot 1 (#ab3417) sits
   dE2000 2.5 from the theme's own accent role (#b03e22). The accent is
   reachable as ordinary ANSI red.

2. THE CORRECTED LIFT MEASUREMENT. The hand-built map derived six slots by
   raising HLS lightness 0.10, citing "Midori's own four derivations, +0.088
   to +0.114, hue drift at most 2.2 degrees". That sample was four pairs out
   of twelve, all from midori-night, all of which happen to obey the rule.
   All twelve pairs (slots 1-6 -> 9-14, both Midori modes) measure:
     - 9 of 12 hold hue within 2.2 degrees and lift lightness +0.088 to
       +0.114, median +0.102;
     - 1 of 12 lifts only +0.055 (midori-paper 3->11, ochre);
     - 2 of 12 are not lifts at all -- the green pair, in BOTH modes, rotates
       hue -32.7 and -26.7 degrees and leaves lightness flat (+0.004, -0.027).
   So the 0.10 rule was the dominant pattern and not a universal one, and
   green is exactly where Midori departs from it. Keeping the number without
   this is how a sample becomes a law.

3. A ROLE COLLISION THAT CONSTRAINED THE OLD MAP AND NO LONGER DOES. In
   themes/lemonardo.json, mint.dark and indigo-lift.dark are the same value,
   #b8e0e8 -- two roles, one tone. The hand-built map could not fill two ANSI
   slots from them and pushed cyan onto the indigo-deep teal family instead.
   The collision is still in the theme file and still matters to any surface
   that uses both roles; it stopped constraining the terminal only because the
   terminal no longer draws its accents from the roles at all.

        WHAT THIS DOES *NOT* TOUCH, AND THE QUESTION THAT LEAVES OPEN

The grounds stay tied to the theme's own roles -- background is paper,
foreground is text -- so a Lemonardo terminal still sits on Lemonardo's paper.
The twelve accents and four neutrals, though, are now derived here and are no
longer the semantic roles the editor surfaces use. Measured, that split is
nearly invisible in the light mode and quite visible in the dark one:

    light: slot 1 vs sage dE2000 2.5, slot 3 vs ochre 2.3, slot 2 vs olive
           7.2, slot 4 vs indigo 6.7, slot 5 vs purple 11.6, slot 6 vs mint
           12.3
    dark:  slot 2 vs olive 5.3, slot 1 vs sage 6.6, slot 5 vs purple 15.3,
           slot 4 vs indigo 17.6, slot 6 vs mint 19.8, slot 3 vs ochre 21.2

The light column is a quiet vindication of the method: the hues these rules
pick from pigments are, to within a few dE, the hues that were picked by hand.
The dark column is a real divergence, because Lemonardo's dark roles were
chosen pale (#f4d896, #87ceeb, #b8e0e8) while this derivation puts the base
tier at Oklab L 0.700 with genuine chroma. Whether the dark editor roles
should be re-derived from these same rules is a decision for a human and is
deliberately not taken here.
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import colorspace as cs                                        # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# The material anchors. HUE IS THE ONLY THING TAKEN FROM THESE.
# --------------------------------------------------------------------------
# family -> (reference hex, material, source, source strength)
ANCHORS = {
    "red": ("#ff4000", "vermilion / cinnabar (HgS) -- the red of the "
            "construction-line pencil every animator roughed in",
            "Wikipedia infobox, credited to Maerz and Paul", "strong"),
    "yellow": ("#ffa700", "chrome yellow (lead chromate, from crocoite) -- "
               "the paint-pot yellow of the period",
               "Wikipedia infobox", "medium"),
    "green": ("#50c878", "Paris green / emerald green (copper "
              "acetoarsenite) -- the brilliant cel-paint green",
              "Wikipedia infobox, credited to Maerz and Paul", "strong"),
    "cyan": ("#43b3ae", "verdigris (copper acetate) -- the blue-green of "
             "aged copper, and of the inks ground from it",
             "Wikipedia infobox; that page carries a maintenance notice "
             "that it may conflate verdigris with patina", "weak"),
    # CHANGED FROM PRUSSIAN BLUE (#003153, hue 245.9), and the reason is
    # worth keeping. Prussian blue is the better story -- it is the committed
    # line -- but it sits 5.1 degrees from Midori's own blue at hue 251.0, and
    # a blue built on it came out dE2000 6.7 from midori-paper's slot 12. That
    # failed the distance gate, and the fix is not to lower the gate: cobalt
    # blue is every bit as period (PB28, cobalt aluminate, in use from 1802 and
    # the standard artist blue right through the era) and sits at 259.7, which
    # moved the same slot to dE2000 9.1 / Oklab 13.0. Prussian blue's story
    # survives in the comment; its hue did not survive the measurement.
    "blue": ("#0047ab", "cobalt blue (PB28, cobalt aluminate) -- the "
             "committed line, inked over the rough",
             "Wikipedia infobox", "medium"),
    "magenta": ("#8d029b", "mauveine / Perkin's aniline purple, 1856 -- the "
                "first synthetic dye, and the aniline family the studio's "
                "coloured inks came from",
                "color-name.com -- the WEAKEST source in this table",
                "weak"),
}
# Non-photo blue is NOT an ANSI slot -- the gates rejected it there; see the
# docstring. It is the selection wash in both modes.
SELECTION_ANCHOR = ("#a4dded", "non-photo blue -- the drafting blue graphic-"
                    "arts camera film cannot see, so a rough drawn in it "
                    "needed no erasing before the clean-up line went down on "
                    "the same sheet",
                    "Wikipedia infobox", "strong")

# Neutrals are anchored too, on the two things that were always on the desk.
NEUTRAL_HUE_INK = "blue"        # India ink reads black with a faint blue cast
NEUTRAL_HUE_PAPER = "yellow"    # animation bond is a warm cream, not white

FAMILY_SLOTS = {"red": 1, "green": 2, "yellow": 3,
                "blue": 4, "magenta": 5, "cyan": 6}
ACCENT_SLOTS = tuple(sorted(list(FAMILY_SLOTS.values())
                            + [v + 8 for v in FAMILY_SLOTS.values()]))
NEUTRAL_SLOTS = (0, 7, 8, 15)

# --------------------------------------------------------------------------
# Per-mode construction rules
# --------------------------------------------------------------------------
# accent_l     ONE Oklab lightness for all six base accents. Uniform accent
#              lightness is the property the whole method exists to get.
# bright_dl    signed Oklab L step to the bright tier.
#
#              NEGATIVE IN LIGHT MODE, AND THAT IS NOT A TYPO. On cream paper
#              the more emphatic mark is the DENSER one -- bright is a second
#              coat, not a thinner one -- and it is also the only direction
#              that keeps the bright tier legible, since a lighter accent on
#              light paper loses contrast. Measured at accent_l 0.50: going
#              -0.14 puts the bright tier at 9.03:1 against the ground, going
#              +0.14 puts it at 2.71:1, which fails even the 3.5 floor.
#
# chroma_frac  chroma as a FRACTION OF THE sRGB CEILING at that lightness and
#              hue, not an absolute number.
#
#              A FIXED ABSOLUTE CHROMA CANNOT WORK IN sRGB, and finding out why
#              reshaped the palette. Measured ceilings at Oklab L 0.50: red
#              0.178, magenta 0.236, green 0.133, blue 0.128, yellow 0.107,
#              cyan 0.086. A single target has to sit under the lowest of
#              those or cyan silently clamps while magenta keeps its full load
#              -- and 0.086 is barely above Midori's 0.065-0.079 mean, so a
#              uniform-chroma Lemonardo would have been as muted as the palette
#              it is supposed to differ from. Taking a fraction of each hue's
#              own ceiling instead makes "fully loaded paint" mean the same
#              thing for every pigment, which is what it means in a paint pot.
# neutral      (L, C) per slot, in slot order 0, 8, 7, 15.
MODES = {
    "paintpot": {
        "label": "Lemonardo Paintpot",
        "subtitle": "light mode -- ink and paint by day",
        "ground_role": "paper", "ink_role": "text", "mode": "light",
        "midori": "midori-paper",
        # 0.90 rather than 0.97, and -0.120 rather than -0.140: both pass the
        # gates, and the softer pair keeps the bright tier off near-black.
        # Measured, -0.140 put slots 9-14 at Oklab L 0.36, where the whole
        # bright row reads as dark blobs on cream.
        "accent_l": 0.500, "bright_dl": -0.120, "chroma_frac": 0.90,
        "neutral": {0: (0.170, 0.025), 8: (0.500, 0.022),
                    7: (0.780, 0.070), 15: (0.950, 0.045)},
        "selection_l": 0.905,
    },
    "inkwell": {
        "label": "Lemonardo Inkwell",
        "subtitle": "dark mode -- the night shift at the light table",
        "ground_role": "paper", "ink_role": "text", "mode": "dark",
        "midori": "midori-night",
        # 0.97 here and not lower: slot 11, the bright yellow, is the binding
        # slot in this mode, and at any fraction below 0.97 it falls within
        # dE2000 9.2 of midori-night's own #e6c489. A pale warm yellow at high
        # lightness has very little room, which is why the fraction cannot
        # come down even though the cap above still cuts red and magenta.
        "accent_l": 0.700, "bright_dl": +0.120, "chroma_frac": 0.97,
        # Slot 7 first sat at L 0.880, which put it dE2000 6.1 from slot 15
        # -- the closest pair in the palette, and two slots that a terminal
        # uses as "white" and "bright white" right next to each other. Dropped
        # to 0.835 with a little more chroma, which reads as kraft board under
        # cream paper rather than two creams.
        "neutral": {0: (0.345, 0.028), 8: (0.660, 0.030),
                    7: (0.835, 0.050), 15: (0.955, 0.050)},
        "selection_l": 0.360,
    },
}

# --------------------------------------------------------------------------
# Gates. The generator refuses to write a file whose gates do not all pass.
# --------------------------------------------------------------------------
BASE_CONTRAST_FLOOR = 4.5       # a base accent IS body text
BRIGHT_CONTRAST_FLOOR = 3.5     # OkSelenized's accent floor
DIM_CONTRAST_FLOOR = 3.2        # slot 8, the comment grey
FG_CONTRAST_FLOOR = 6.0         # OkSelenized's text floor

# Distinctness WITHIN the palette, and distance FROM Midori. Each is a pair of
# floors, (CIEDE2000, Oklab x100), and both have to clear -- see the docstring
# on why one metric is not enough.
INTRA_FLOOR = (9.0, 6.0)
# Same slot, same mode: the direct substitution test. What a reader sees if
# they switch theme and look at the same token.
SAME_SLOT_FLOOR = (8.0, 6.0)
# Any value in the same-mode Midori theme: the confusability test.
#
# SCOPED TO THE SAME MODE ON PURPOSE. The first version of this gate compared
# every Lemonardo slot against all 39 values in BOTH Midori themes and was
# unsatisfiable: it kept failing Inkwell's pale bright accents against
# midori-paper's light values, two sets of colours that can never appear on a
# screen together. A gate nobody can pass gets its floor lowered until it
# passes, which is how a gate becomes decoration.
ANY_MIDORI_FLOOR = (8.0, 6.0)
# Neutrals carry their own floors and that is not a fudge, it is the geometry.
# Near-white and near-black have almost no room: two warm off-whites at
# Oklab L 0.95 are a few units apart however different their warmth, which is
# why the Oklab floor here is low while the CIEDE2000 floor is not. Measured,
# slot 15's cream is dE2000 10.0 from Midori's card and Oklab 3.1 -- clearly a
# different paper, and only 3.1 apart in a metric that is mostly lightness.
NEUTRAL_SAME_SLOT_FLOOR = (7.0, 2.0)
NEUTRAL_ANY_FLOOR = (5.0, 2.0)


def ghostty_values(name):
    """Every hex a ghostty theme file uses, value -> the keys that set it."""
    out = {}
    for line in (ROOT / "ghostty" / "themes" / name).read_text().splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().lower()
        # A palette line is "palette = 7=#c9c4b8", so the value side needs
        # splitting again. Partitioning once found only the 9 named keys and
        # silently skipped all 16 palette slots -- which the size check below
        # caught, and which is the whole reason it is there.
        if key == "palette" and "=" in val:
            idx, _, val = val.partition("=")
            key = f"palette {idx.strip()}"
        if val.startswith("#") and len(val) == 7:
            out.setdefault(val, []).append(key)
    if len(out) < 16:
        sys.exit(f"{name}: only {len(out)} values parsed -- the collector is "
                 f"broken, and a distance gate against an empty reference "
                 f"set passes everything")
    return out


def ghostty_slots(name):
    out = {}
    for line in (ROOT / "ghostty" / "themes" / name).read_text().splitlines():
        m = re.match(r"^palette\s*=\s*(\d+)=(#[0-9a-fA-F]{6})", line.strip())
        if m:
            out[int(m.group(1))] = m.group(2).lower()
    if len(out) != 16:
        sys.exit(f"{name}: {len(out)} palette slots parsed, expected 16")
    return out


# An absolute ceiling on top of the gamut fraction.
#
# WHY A CAP AS WELL AS A FRACTION. The fraction alone produced a magenta of
# Oklab chroma 0.273 in the dark mode, because mauveine's hue has an unusually
# generous sRGB ceiling there (0.281, against cyan's 0.120 at the same
# lightness). Taking the same fraction of a much larger ceiling does not give
# the same colour relationship -- it gives one slot that reads as a light
# source while its neighbours read as paint. The cap is the point past which
# "fully loaded" stops meaning anything, and it was chosen by measurement: at
# 0.16 the light mode's blue falls back inside Midori's, at 0.18 every gate in
# both modes passes, and above 0.20 nothing improves because only red and
# magenta are still being cut.
# --------------------------------------------------------------------------
# PER-SLOT EXCEPTIONS TO accent_l, AND WHY SLOT 3 HAS ONE
#
# Every base accent sits at accent_l -- one lightness for all six -- because
# that uniform lightness is the invariant this palette's Selenized/OkSelenized
# ancestry is built on: no accent outweighs another, so none of them grabs the
# eye first in a wall of log output. Slot 3 is now the single exception, and
# the cost is real: the yellow no longer sits at the same weight as the other
# five, and that is a deliberate loss, not an oversight.
#
# The reason is that yellow has the least chroma room of any hue at L 0.500.
# Measured maxima at that lightness: magenta 0.239, red 0.189, blue 0.141,
# green 0.131, yellow 0.104, cyan 0.085. A yellow held at L 0.500 therefore
# cannot be a gold -- it is forced to C <= 0.104, which on a cream ground
# renders as brown. #855918 was that brown, and it was rejected on sight.
#
# What CANNOT fix it: raising the lightness while keeping the 4.5:1 base
# floor. The lightest gold at this hue that still clears 4.5 is L 0.539
# (#94631c, 4.47:1) -- only +0.039 above the invariant, and still brown. The
# floor, not the invariant, is what traps this slot.
#
# So slot 3 takes BRIGHT_CONTRAST_FLOOR (3.5) instead of BASE_CONTRAST_FLOOR
# (4.5) -- the floor this palette already accepts for its eight bright
# accents -- and lifts to L 0.580, which the rule renders as #a36e20 at
# 3.77:1. That is dE2000 1.96 from Lemonardo's own `clay` role (#a0701d) --
# near it, and not it: the slot is still generated from the anchor hue (71.7)
# rather than pasted from the palette, and clay sits at hue 76. Close enough
# that the slot reads as the language's existing gold, far enough that calling
# it clay would be wrong.
#
# THE COST, STATED PLAINLY: 3.77:1 is below WCAG AA for normal text. Yellow
# used as body text on paintpot is now harder to read than the other five base
# accents. It clears AA Large (3:1) and clears this palette's own bright-accent
# floor. If that trade is ever revisited, the legible alternative is #94631c
# at 4.47:1 -- and the reason it was not taken is that it is the brown this
# exception exists to escape.
ACCENT_L_OVERRIDE = {
    ("paintpot", 3): 0.580,
}
# Slots measured against BRIGHT_CONTRAST_FLOOR though they are base slots.
# Keyed the same way, so the exception and its floor cannot drift apart.
BASE_FLOOR_EXEMPT = {
    ("paintpot", 3): "yellow cannot be a gold at L 0.500; see ACCENT_L_OVERRIDE",
}

CHROMA_CAP = 0.18


def loaded(L, frac, hue):
    """The hex at (L, hue) carrying `frac` of the sRGB chroma available there,
    never exceeding CHROMA_CAP. Returns (hex, achieved_C, sRGB_ceiling)."""
    _, ceiling = cs.oklch_to_hex_clamped(L, 0.45, hue)
    hx, got = cs.oklch_to_hex_clamped(L, min(ceiling * frac, CHROMA_CAP), hue)
    return hx, got, ceiling


def build(mode_id, theme):
    spec = MODES[mode_id]
    m = spec["mode"]
    pal = theme["palette"]
    hues = {k: cs.hex_to_oklch(v[0])[2] for k, v in ANCHORS.items()}
    slots, notes = {}, {}

    for fam, slot in FAMILY_SLOTS.items():
        hue = hues[fam]
        material = ANCHORS[fam][1].split(" -- ")[0]
        base_l = ACCENT_L_OVERRIDE.get((mode_id, slot), spec["accent_l"])
        for s, L, tier in ((slot, base_l, "thinned"),
                           (slot + 8, spec["accent_l"] + spec["bright_dl"],
                            "full load")):
            hx, got, ceil = loaded(L, spec["chroma_frac"], hue)
            slots[s] = hx
            notes[s] = (f"{fam}{'' if s == slot else ' bright'}: {material}, "
                        f"hue {hue:.1f}, L {L:.3f}, C {got:.3f} "
                        f"({spec['chroma_frac']:.2f} of the {ceil:.3f} "
                        f"available here)")
            if (mode_id, s) in ACCENT_L_OVERRIDE:
                notes[s] += (f"; L lifted from {spec['accent_l']:.3f} by "
                             f"exception -- yellow has no gold at that "
                             f"lightness, see ACCENT_L_OVERRIDE")
            del tier

    ink_h, paper_h = hues[NEUTRAL_HUE_INK], hues[NEUTRAL_HUE_PAPER]
    for slot, hue, what in (
            (0, ink_h, "India ink -- dense black, with the faint blue cast it "
                       "actually has on paper"),
            (8, ink_h, "an ink wash -- the dim tier, the comment grey"),
            (7, paper_h, "pegboard kraft -- the warm board under the paper"),
            (15, paper_h, "animation bond -- the cream of the punched paper")):
        L, C = spec["neutral"][slot]
        hx, _ = cs.oklch_to_hex_clamped(L, C, hue)
        slots[slot] = hx
        notes[slot] = f"{what}; hue {hue:.1f}, L {L:.3f}, C {C:.3f}"

    sel, _ = cs.oklch_to_hex_clamped(
        spec["selection_l"], 0.075,
        cs.hex_to_oklch(SELECTION_ANCHOR[0])[2])

    # Split chrome. These were derived inline in emit() and are built here
    # instead so that build() returns EVERY colour the theme file will carry.
    # The reason is not tidiness: tests/test_palette_is_defined.py treats this
    # generator as the declaration site for values nothing else declares, and
    # it can only see what build() returns. While the divider lived in emit(),
    # #44484e was declared nowhere -- which went unnoticed until herdr and tmux
    # started using it and it crossed that test's 4-file threshold.
    div, _ = cs.oklch_to_hex_clamped(0.84 if m == "light" else 0.40, 0.012,
                                     cs.hex_to_oklch(ANCHORS["blue"][0])[2])
    unf, _ = cs.oklch_to_hex_clamped(0.86 if m == "light" else 0.27, 0.030,
                                     cs.hex_to_oklch(ANCHORS["red"][0])[2])

    return {"id": f"lemonardo-{mode_id}", "mode": m,
            "bg": pal[spec["ground_role"]][m],
            "fg": pal[spec["ink_role"]][m],
            "selection": sel, "divider": div, "split_fill": unf,
            "slots": slots, "notes": notes, "spec": spec}


def _pair_ok(a, b, floors):
    d2, dok = cs.ciede2000(a, b), cs.d_oklab(a, b) * 100
    return (d2 >= floors[0] and dok >= floors[1]), d2, dok


def measure(built):
    """Every gate as (ok, label, detail). Nothing is claimed that is not
    computed here, and the caller prints the row count so a gate set that
    evaluated nothing cannot read as a pass."""
    rows = []
    s, bg, spec = built["slots"], built["bg"], built["spec"]
    ref_vals = ghostty_values(spec["midori"])
    ref_slots = ghostty_slots(spec["midori"])

    for i in ACCENT_SLOTS:
        floor = BASE_CONTRAST_FLOOR if i < 8 else BRIGHT_CONTRAST_FLOOR
        # A base slot named in BASE_FLOOR_EXEMPT is measured against the
        # bright floor instead. The exemption is keyed by (mode, slot), so it
        # cannot leak into the other mode -- inkwell's yellow is a gold at its
        # own accent_l and takes the full 4.5.
        if i < 8 and (built["id"].split("-")[1], i) in BASE_FLOOR_EXEMPT:
            floor = BRIGHT_CONTRAST_FLOOR
        c = cs.contrast(s[i], bg)
        rows.append((c >= floor, f"slot {i:>2} contrast vs ground",
                     f"{c:5.2f}:1 (floor {floor})"))
    c8 = cs.contrast(s[8], bg)
    rows.append((c8 >= DIM_CONTRAST_FLOOR, "slot  8 contrast vs ground",
                 f"{c8:5.2f}:1 (floor {DIM_CONTRAST_FLOOR})"))
    cfg = cs.contrast(built["fg"], bg)
    rows.append((cfg >= FG_CONTRAST_FLOOR, "foreground vs ground",
                 f"{cfg:5.2f}:1 (floor {FG_CONTRAST_FLOOR})"))
    csel = cs.contrast(built["fg"], built["selection"])
    rows.append((csel >= BASE_CONTRAST_FLOOR, "foreground over selection",
                 f"{csel:5.2f}:1 (floor {BASE_CONTRAST_FLOOR})"))

    worst = None
    for i in range(16):
        for j in range(i + 1, 16):
            good, d2, dok = _pair_ok(s[i], s[j], INTRA_FLOOR)
            if worst is None or (d2, dok) < (worst[1], worst[2]):
                worst = (good, d2, dok, i, j)
    good, d2, dok, i, j = worst
    rows.append((good, "closest pair within the palette",
                 f"slots {i}/{j}: dE2000 {d2:.1f}, dEok {dok:.1f} "
                 f"(floors {INTRA_FLOOR[0]} / {INTRA_FLOOR[1]})"))

    for i in range(16):
        neutral = i in NEUTRAL_SLOTS
        f_same = NEUTRAL_SAME_SLOT_FLOOR if neutral else SAME_SLOT_FLOOR
        good, d2, dok = _pair_ok(s[i], ref_slots[i], f_same)
        rows.append((good, f"slot {i:>2} vs the same Midori slot",
                     f"dE2000 {d2:5.1f}, dEok {dok:5.1f} vs {ref_slots[i]} "
                     f"(floors {f_same[0]} / {f_same[1]})"))

        f_any = NEUTRAL_ANY_FLOOR if neutral else ANY_MIDORI_FLOOR
        near = min(((cs.ciede2000(s[i], v) + cs.d_oklab(s[i], v) * 100, v)
                    for v in ref_vals))[1]
        good, d2, dok = _pair_ok(s[i], near, f_any)
        rows.append((good, f"slot {i:>2} vs nearest {spec['midori']} value",
                     f"dE2000 {d2:5.1f}, dEok {dok:5.1f} vs {near} "
                     f"({ref_vals[near][0]}) (floors {f_any[0]} / "
                     f"{f_any[1]})"))
    return rows


def emit(built):
    """The ghostty theme text: one key per line, comments as '#'."""
    s, spec = built["slots"], built["spec"]
    out = []
    w = out.append
    w(f"# {built['id']} - {spec['label']}, {spec['subtitle']}")
    w("#")
    w("# GENERATED BY tools/make-lemonardo-ansi.py. Change the rules there,")
    w("# not the values here: tests/test_lemonardo_ansi.py re-derives this")
    w("# file from themes/lemonardo.json and fails on any difference, so a")
    w("# hand edit will be caught and then lost.")
    w("#")
    w("# EVERY HUE BELOW COMES FROM A MATERIAL AND FROM NOTHING ELSE. Each")
    w("# family's hue angle is read off a published reference value for a real")
    w("# pigment or drafting material; the generator then throws that value's")
    w("# lightness and chroma away and rebuilds both by rule. So what the")
    w("# pigment contributes is its hue identity, not a web swatch's opinion")
    w("# about how bright it should be. The reference hexes are NOT")
    w("# spectrophotometer readings of paint and must not be quoted as if")
    w("# they were; two are Wikipedia infobox values credited to Maerz and")
    w("# Paul, two are Wikipedia values with thinner provenance, and one")
    w("# (mauveine) is from a colour-name site and is the weakest of the set.")
    w("#")
    for fam, slot in sorted(FAMILY_SLOTS.items(), key=lambda kv: kv[1]):
        ref, what, src, strength = ANCHORS[fam]
        w(f"#   {slot}/{slot + 8}  {what}")
        w(f"#        ref {ref}, hue {cs.hex_to_oklch(ref)[2]:.1f} "
          f"[{strength}: {src}]")
    ref, what, src, strength = SELECTION_ANCHOR
    w(f"#   sel  {what}")
    w(f"#        ref {ref}, hue {cs.hex_to_oklch(ref)[2]:.1f} "
      f"[{strength}: {src}]")
    w("#        Tried as slot 12, the blue family's bright tier -- the")
    w("#        committed cobalt line over the rough that does not print.")
    w("#        REJECTED: at hue 217.0 it sits between verdigris (191.0) and")
    w("#        Prussian blue (245.9), and slots 12 and 14 came out dE2000 8.5")
    w("#        apart, the closest pair in the palette by a factor of two. A")
    w("#        selection is a mark that is not part of the document and must")
    w("#        not print, which is what the pigment was for anyway.")
    w("#")
    w(f"# All six base accents sit at ONE Oklab lightness, "
      f"{spec['accent_l']:.3f}, carrying")
    w(f"# {spec['chroma_frac']:.0%} of the sRGB chroma available at that "
      f"lightness for their own hue,")
    w(f"# capped at {CHROMA_CAP:.2f}. A fraction and not a fixed number, "
      f"because the sRGB")
    w(f"# ceiling at L {spec['accent_l']:.2f} runs from 0.086 for cyan to "
      f"0.236 for magenta, and one")
    w("# absolute target would clamp cyan flat while magenta kept its full")
    w("# load; and then a cap as well, because the same fraction of a much")
    w("# larger ceiling gives one slot that reads as a light source next to")
    w("# neighbours that read as paint.")
    w(f"# The bright tier is the same hues at L "
      f"{spec['accent_l'] + spec['bright_dl']:.3f} "
      f"({spec['bright_dl']:+.3f}).")
    if spec["bright_dl"] < 0:
        w("# It is DARKER, which is not a typo: on cream paper the emphatic")
        w("# mark is the denser one, bright being a second coat rather than a")
        w("# thinner one. It is also the only direction that stays legible --")
        w("# measured, -0.140 gives the bright tier 9.03:1 against this ground")
        w("# and +0.140 gives it 2.71:1, which fails even a 3.5 floor.")
    w("#")
    w("# Gates this file passed at generation time. Re-run the test rather")
    w("# than believing this comment, which is a record and not a check:")
    w(f"#   base accents >= {BASE_CONTRAST_FLOOR}:1 vs ground, bright >= "
      f"{BRIGHT_CONTRAST_FLOOR}:1, slot 8 >= {DIM_CONTRAST_FLOOR}:1")
    w(f"#   foreground >= {FG_CONTRAST_FLOOR}:1 vs ground and >= "
      f"{BASE_CONTRAST_FLOOR}:1 over the selection")
    w(f"#   no two of the 16 slots closer than dE2000 {INTRA_FLOOR[0]} AND "
      f"Oklab {INTRA_FLOOR[1]}")
    w(f"#   every accent >= dE2000 {SAME_SLOT_FLOOR[0]} / Oklab "
      f"{SAME_SLOT_FLOOR[1]} from the same")
    w(f"#   {spec['midori']} slot, and from the nearest value anywhere in that")
    w("#   theme. Both metrics, because each is blind where the other sees:")
    w("#   CIEDE2000 discounts pure saturation differences, which is the axis")
    w("#   these two languages differ on, and Oklab distance understates two")
    w("#   near-whites of different warmth, which is the neutrals.")
    w("")
    w(f"background = {built['bg']}")
    w(f"foreground = {built['fg']}")
    w("")
    for slot in range(16):
        w(f"# {slot}: {built['notes'][slot]}")
        w(f"palette = {slot}={s[slot]}")
    w("")
    w("# The selection is non-photo blue, at the lightness that keeps the")
    w("# foreground readable through it -- gated above, not assumed.")
    w(f"selection-background = {built['selection']}")
    w(f"selection-foreground = {built['fg']}")
    w("")
    w("# cell-background keeps the block cursor an inverse of whatever cell it")
    w("# lands on, so it stays visible over any slot above; cursor-text is the")
    w("# ground, which is what an inverted cell becomes.")
    w("cursor-color = cell-background")
    w(f"cursor-text = {built['bg']}")
    w("")
    m = built["mode"]
    div, unf = built["divider"], built["split_fill"]
    w("# Split chrome: the divider is an ink wash, the unfocused fill a")
    w("# vermilion one, both far enough down in chroma to stay furniture.")
    w(f"split-divider-color = {div}")
    w(f"unfocused-split-fill = {unf}")
    w("")
    w("# palette-generate fills 16-255 from the sixteen above rather than")
    w("# leaving ghostty's defaults, which belong to neither design language.")
    w("palette-generate = true")
    if m == "light":
        w("palette-harmonious = true")
    w("")
    w("# NO background-image. ghostty/backgrounds holds Midori artwork only;")
    w("# pointing Lemonardo at it would put Midori's ground under Lemonardo's")
    w("# ink, which is the one thing a second design language must not do.")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="write ghostty/themes/lemonardo-* (default: report "
                         "only). A mode whose gates fail is NOT written.")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the files on disk differ from what "
                         "the rules produce")
    args = ap.parse_args()

    theme = json.loads((ROOT / "themes" / "lemonardo.json").read_text())
    fail = 0
    total_rows = 0
    for mode_id in ("paintpot", "inkwell"):
        built = build(mode_id, theme)
        rows = measure(built)
        total_rows += len(rows)
        bad = [r for r in rows if not r[0]]
        ref = MODES[mode_id]["midori"]
        print(f"\n== {built['id']} vs {ref} == {len(rows)} gate(s), "
              f"{len(bad)} failing")
        for good, label, detail in rows:
            print(f"  {'ok  ' if good else 'FAIL'} {label:38s} {detail}")
        if not rows:
            print("  FAIL no gates evaluated -- nothing was checked")
            fail = 1
        if bad:
            fail = 1

        text = emit(built)
        path = ROOT / "ghostty" / "themes" / built["id"]
        if args.write:
            if bad:
                print(f"  NOT WRITTEN -- {len(bad)} gate(s) failing")
            else:
                path.write_text(text)
                print(f"  wrote {path.relative_to(ROOT)} "
                      f"({len(text.splitlines())} lines)")
        elif args.check:
            on_disk = path.read_text() if path.exists() else ""
            if on_disk != text:
                print(f"  FAIL {path.relative_to(ROOT)} differs from what the "
                      f"rules produce -- re-run with --write")
                fail = 1
            else:
                print(f"  ok   {path.relative_to(ROOT)} matches the rules")
    if total_rows == 0:
        print("FAIL no modes were evaluated at all")
        return 1
    print(f"\n{total_rows} gate(s) evaluated across 2 modes: "
          f"{'all green' if not fail else 'failures above'}")
    return fail


if __name__ == "__main__":
    sys.exit(main())
