#!/usr/bin/env python3
"""Generate vivaldi/css-mods/lemonardo-palette.css.

WHY THIS FILE IS GENERATED AND THE MIDORI MODS ARE NOT. The Midori mods are
hand-written and their comments are the design record for Vivaldi's own quirks
-- which selector Vivaldi paints, why !important is needed against an inline
style attribute, which hooks were found over CDP. None of that is per-language
and none of it should be duplicated. This file is only the VALUES, and every
value here is derived from themes/lemonardo.json and the pigment anchors in
tools/make-lemonardo-ansi.py, so it is generated and the derivation is checked
on every run.

THE FIRST VERSION OF THIS FILE WAS WRONG, AND THE WAY IT WAS WRONG MATTERS.
Every value in it was ported as a measured delta from the corresponding MIDORI
value -- same lightness step from the ground, same chroma step, at Lemonardo's
hue. Each individual number was defensible and the whole was not: a method that
preserves Midori's relationships produces a Midori-shaped theme wearing
different paint. Shipped, it read as "Midori but beige", and the giveaway was
the active tab, a muted sage-green pill that was literally Midori's accent
relationship re-landed on cream.

Porting a delta is the right tool when the QUESTION is "how loud should this
be" -- a tab bar is a large persistent surface whichever language paints it,
and that is a fact about tab bars, not about Midori. It is the wrong tool for
"what colour is this", because the answer to that has to come from the
language's own material vocabulary or it is not a different language.

So the values below are split by which question they answer:

  IDENTITY -- from Lemonardo's own pigments, no reference to Midori:
    the chrome accent, the selection, the nine tab-stack colours.
  LOUDNESS -- still measured against Midori, deliberately:
    the wash alphas, because "how strongly should a today-column tint the
    page" is a question about reading, not about brand.

THE MOTIF. Lemonardo is an animation studio at the end of the hand-drawn era.
Its pipeline is the design: a drawing is roughed in NON-PHOTO BLUE (#a4dded,
the drafting blue the graphic-arts camera could not see, so it needed no
erasing), construction lines go down in VERMILION, the committed clean-up line
is inked in COBALT, and the cel is painted in Paris green, chrome yellow and
verdigris.

THE TWO MODES ARE TWO BENCHES, NOT ONE HUE AT TWO LIGHTNESSES. The first pass
put vermilion in both and dimmed it for dark mode, which made Inkwell read as
Paintpot at night -- the same mistake as porting Midori's deltas, one level
down. They are named for different objects and the themes' own subtitles say
so: Paintpot is "ink and paint by day", Inkwell is "the night shift at the
light table".

  PAINTPOT -- the paint bench by day. The accent is CHROME YELLOW, which the
  anchor table calls "the paint-pot yellow of the period": wet, opaque cel
  paint in the pot. The selection is NON-PHOTO BLUE, the rough still showing
  through under the paint.

  INKWELL -- the night shift at the light table. The accent is VERDIGRIS, the
  blue-green of aged copper and of the inks ground from it: the metal of the
  well itself, not the ink in it (ink is the ground here, and a ground cannot
  also be the accent). The selection is the WARM GLOW of the light table
  leaking out from under the page.

So each bench carries one warm element and one cool one, and they are swapped:
warm paint over a cool rough by day, cool copper over a warm lamp by night.
That is what makes them two places instead of one place at two exposures.

NOT VERMILION, THOUGH IT IS STILL EVERYWHERE. The construction-line red did
not lose an argument; it moved to where a line colour belongs. It is slot 3 of
the tab stacks and the `clay` mail label, both of which are marks on a page.
An accent here fills a tab, and a filled tab is a surface -- paint, or metal.

THE MATERIAL LAYER: ONE SURFACE, LIT FROM OPPOSITE SIDES. The active tab is
the one place either bench shows its accent as a filled SURFACE rather than as
a mark, so it is the only place a material reading is available. Paintpot gets
wet paint under a window: a crisp specular line along the top rim, and the
colour deepening as it runs down into the pot. Inkwell is the same surface
turned over -- a light table lights from BELOW, so the rim's own shadow falls
across the top and the glass glints along the bottom edge.

Inkwell's gradient is therefore Paintpot's flipped vertically, the same stops
read `to top` instead of `to bottom`, and the two alphas are gated EQUAL. The
asymmetry that carries the motif is where the light is, not how much of it
there is; if one bench were also brighter, the difference would read as one of
them being wrong rather than as two rooms. Equal loudness, swapped position --
the same structure as the warm/cool swap above.

WHY THE PSEUDO-ELEMENT HANGS OFF .tab-header AND NOT .tab. Measured over CDP
against a live 8.2.4133.84: `.tab.active::before` and `::after` are BOTH
already Vivaldi's, carrying the concave corner joins that tie the active tab
into the toolbar (`mask-image: radial-gradient(circle at 0 0, transparent 70%,
#000 73%)`) plus 64ms `leftfade`/`rightfade` animations. They compute to
`content: none` in this configuration, which makes them look free and is a
trap: setting `content: ""` would switch Vivaldi's own geometry back on under
our colours. `.tab.active .tab-header` has no author ::before/::after rule at
all, so that is where the layer lives.

Z-INDEX -1 PUTS THE LAYER UNDER THE LABEL. .tab-header is position: relative
with a transparent background, so a negative-z-index child paints above the
accent fill on .tab and below .tab-header's own text. Without it the veil also
crosses the glyphs -- the specular line would lighten the top pixel of the
title and the field would wash the black label -- which is a different and
worse effect than light falling on the paint behind it.
"""
import importlib.util
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import colorspace as cs  # noqa: E402

OUT = ROOT / "vivaldi" / "css-mods" / "lemonardo-palette.css"
THEMES = ROOT / "vivaldi" / "themes.json"

GROUND = {"light": "#f3eee2", "dark": "#2c2a28"}
INK = {"light": "#3a4048", "dark": "#ede4d3"}
MUTED = {"light": "#5a616a", "dark": "#a49d93"}
CARD = {"light": "#fbf8f0", "dark": "#363330"}
INTENSER = {"light": "#fffcf5", "dark": "#3e3b38"}
# Both accents are derived at their anchor's hue, at full available chroma,
# at the lightness where the label Vivaldi derives clears 4.5:1 -- not taken
# from a palette role. The roles are text colours; these fill a tab.
#   light  chrome yellow (hue 71.7)  L 0.72  black label 8.24:1  dE 30.4
#   dark   verdigris     (hue 191.0) L 0.70  black label 8.30:1  dE 51.2
ACCENT = {"light": "#dc931e", "dark": "#22b5af"}
# Paintpot selects with the cool rough under the paint; Inkwell selects with
# the warm light-table glow under the page. #513e27 is that glow at L 0.38,
# C 0.045 -- dE 13.8 from the ground, so it recedes, with cream ink at 8.05:1.
SELECTION = {"light": "#a8d7ea", "dark": "#513e27"}

# Midori's wash, for the LOUDNESS comparison only.
MIDORI_ACCENT = {"light": "#5f6f5e", "dark": "#9aab97"}
MIDORI_GROUND = {"light": "#f3f1eb", "dark": "#1a1917"}
MIDORI_WASH = {("cal", "light"): 0.10, ("cal", "dark"): 0.12,
               ("mail", "light"): 0.12, ("mail", "dark"): 0.16}
# Line alphas port unchanged: a 1px signature rule is meant to be seen.
LINE_ALPHA = {("cal", "light"): 0.5, ("cal", "dark"): 0.55,
              ("mail", "light"): 0.55, ("mail", "dark"): 0.6}

LABELS = {
    "light": {"clay": "#b03e22", "ochre": "#8a5e14", "dijon": "#7d6d0c",
              "moss": "#1f6b4d", "slate": "#2e5c8a", "purple": "#6a4c7c",
              "taupe": "#5a616a"},
    "dark": {"clay": "#ff8a6a", "ochre": "#f4d896", "dijon": "#e9e99c",
             "moss": "#66bb6a", "slate": "#87ceeb", "purple": "#c9a9d8",
             "taupe": "#a49d93"},
}
THUMB = {"light": ("90 97 106", 0.35, 0.6), "dark": ("164 157 147", 0.4, 0.65)}

# The material layer on the active tab. Both numbers are composited dE2000
# against THIS bench's accent, not alphas: the same alpha over chrome yellow
# and over verdigris are not the same amount of light, because the two accents
# differ in chroma and lightness. Solved per bench, gated equal.
#
# 8.0 for the 1px edge and 3.5 for the soft field were chosen against the ink
# budget already set by the background tile: that grid runs dE 2.8 over 8.2% of
# its area (0.23 dE-weighted coverage), and a 1px line on a 30px tab inks 3.3%,
# so dE 8 there spends 0.27 -- the same order. The field is broad and must
# therefore be quiet; 3.5 is about a just-noticeable step on adjacent patches,
# which is what reads as depth rather than as a second colour.
MATERIAL_LIT_DE = 8.0      # the 1px rim: gloss on the paint / glint on glass
MATERIAL_SHADE_DE = 3.5    # the soft field, at its strongest end
MATERIAL_SHADE_START = 42  # %, where the field starts to build

# Built with %-formatting, not an f-string. This block is a multi-line CSS
# comment, and an f-string that needs a backslash escape is a SyntaxError in
# the Python this repo targets -- a rewrite of midori-tab-stacks.css silently
# did not run for exactly this reason and left 54 hexes unchanged while
# reporting success.
COMMENT = """/* %(theme)s: the accent read as a SURFACE -- lit from the %(lamp)s.
   Same stops in both benches, %(dirn)s: a 1px specular rim at the lit edge
   (dE %(lit)s composited on the accent) and the colour deepening
   %(where)s (dE %(shade)s at its strongest end). Inkwell is Paintpot
   flipped, because a light table lights from below; the alphas differ only
   because the same light over verdigris is not the same light over chrome
   yellow, and they are gated to land on equal dE.

   .tab-header, NOT .tab: both of .tab.active's own pseudo-elements already
   carry Vivaldi's corner joins (mask-image: radial-gradient) and 64ms fade
   animations, and they only LOOK free -- they compute to content: none in
   this configuration, so setting content there would switch Vivaldi's own
   geometry back on under our colours. Measured over CDP against 8.2.4133.84.

   z-index -1 keeps the layer under the label: .tab-header is position
   relative with a transparent background, so the veil lands on .tab's accent
   fill and the glyphs stay on top of it. Without it the specular line
   lightens the top pixel of the title. */"""

STACK_L = {"light": 0.500, "dark": 0.720}
STACK_FRAC = 0.90
SLOT_NAMES = ["gray", "blue", "red", "yellow", "green",
              "pink", "purple", "cyan", "orange"]


def anchors():
    spec = importlib.util.spec_from_file_location(
        "lem_ansi", ROOT / "tools" / "make-lemonardo-ansi.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ANCHORS


def stack_spec(A):
    h = lambda k: cs.hex_to_oklch(A[k][0])[2]
    return [
        ("gray",   h("blue"),    0.10, "graphite, the pencil barely tinted"),
        ("blue",   h("blue"),    1.00, "cobalt PB28, the committed line"),
        ("red",    h("red"),     1.00, "vermilion/cinnabar, the construction line"),
        ("yellow", h("yellow"),  1.00, "chrome yellow, the paint pot"),
        ("green",  h("green"),   1.00, "Paris green, the cel paint"),
        ("pink",   345.0,        0.85, "rose madder; no anchor at this hue, placed"),
        ("purple", h("magenta"), 1.00, "mauveine, the first synthetic dye"),
        ("cyan",   h("cyan"),    1.00, "verdigris, aged copper"),
        ("orange", 50.0,         0.95, "red ochre, between vermilion and chrome"),
    ]


def over(fg, a, bg):
    f, b = cs.hex_to_rgb(fg), cs.hex_to_rgb(bg)
    return cs.rgb_to_hex(tuple(f[i] * a + b[i] * (1 - a) for i in range(3)))


def wash_alpha(surf, mode):
    """The alpha whose composite is as loud as Midori's, not the same alpha.

    Midori's sage is C 0.033; the vermilion accent is far more chromatic, so
    reusing the alpha unchanged would roughly double the wash.
    """
    want = cs.ciede2000(
        over(MIDORI_ACCENT[mode], MIDORI_WASH[(surf, mode)], MIDORI_GROUND[mode]),
        MIDORI_GROUND[mode])
    best = min(((abs(cs.ciede2000(over(ACCENT[mode], a / 1000, GROUND[mode]),
                                  GROUND[mode]) - want), a / 1000)
                for a in range(2, 300)))[1]
    got = cs.ciede2000(over(ACCENT[mode], best, GROUND[mode]), GROUND[mode])
    return best, want, got


def label_on(hx):
    """The label colour Vivaldi derives for a filled surface: whichever wins."""
    return ("#000000" if cs.contrast(hx, "#000000") >= cs.contrast(hx, "#ffffff")
            else "#ffffff")


def material(mode):
    """Lit-edge and soft-field alphas over this bench's accent.

    Returns (alpha, composite, dE) for each. White and black are used as the
    lamp and the shadow rather than a pigment on purpose: a specular highlight
    is light and an occlusion is the absence of it, so neither is paint. The
    paint is whatever --colorAccentBg holds, which is also why this layer still
    reads correctly if Vivaldi ever takes the accent from the page.
    """
    acc = ACCENT[mode]

    def solve(lamp, target):
        best = min(((abs(cs.ciede2000(over(lamp, a / 1000, acc), acc) - target),
                     a / 1000) for a in range(1, 500)))[1]
        comp = over(lamp, best, acc)
        return best, comp, cs.ciede2000(comp, acc)

    return solve("#ffffff", MATERIAL_LIT_DE), solve("#000000", MATERIAL_SHADE_DE)


def build_stacks(A):
    bg, fg, notes = {}, {}, {}
    for mode in ("light", "dark"):
        bg[mode], fg[mode], notes[mode] = [], [], []
        for name, hue, cfrac, why in stack_spec(A):
            _, ceil = cs.oklch_to_hex_clamped(STACK_L[mode], 0.45, hue)
            hx, got = cs.oklch_to_hex_clamped(
                STACK_L[mode], min(ceil * STACK_FRAC * cfrac, 0.18), hue)
            w, b = cs.contrast(hx, "#ffffff"), cs.contrast(hx, "#000000")
            bg[mode].append(hx)
            fg[mode].append("#fff" if w >= b else "#000")
            notes[mode].append(f"{name} -- {why}")
    return bg, fg, notes


def check(bg, fg):
    """Refuse to write a palette that is worse than the one it replaces."""
    MID = {"light": ["#524d46", "#3a5572", "#7a4a4a", "#b88a3a", "#6c7d52",
                     "#9c5f6b", "#6a5a78", "#4f7d75", "#c9916b"],
           "dark": ["#9c958a", "#6c87a4", "#b8868a", "#d8b06a", "#9eaf85",
                    "#c898a4", "#9a8cb0", "#85b0a8", "#d4a07a"]}
    bad = []
    for mode in ("light", "dark"):
        worst = lambda v: min(cs.ciede2000(a, b)
                              for a, b in itertools.combinations(v, 2))
        mine, theirs = worst(bg[mode]), worst(MID[mode])
        lo = min(cs.contrast(v, "#ffffff" if f == "#fff" else "#000000")
                 for v, f in zip(bg[mode], fg[mode]))
        far = sum(cs.ciede2000(a, b) for a, b in zip(bg[mode], MID[mode])) / 9
        print(f"  stacks {mode:5} closest pair dE {mine:5.2f} "
              f"(midori {theirs:5.2f})   worst label {lo:5.2f}:1   "
              f"mean dE from the Midori slot replaced {far:5.1f}")
        if mine < theirs * 0.8:
            bad.append(f"stack separation {mode}")
        if lo < 4.5:
            bad.append(f"stack label contrast {mode}")
        if far < 8.0:
            bad.append(f"stacks {mode} too close to Midori's -- that is the "
                       f"bug this rewrite exists to fix")
    a = ACCENT["light"]
    for mode in ("light", "dark"):
        v = ACCENT[mode]
        w, b = cs.contrast(v, "#ffffff"), cs.contrast(v, "#000000")
        print(f"  accent {mode:5} {v}  derived label {max(w, b):5.2f}:1   "
              f"dE from ground {cs.ciede2000(v, GROUND[mode]):5.1f}")
        if max(w, b) < 4.5:
            bad.append(f"accent {mode} label")
    del a
    return bad


def main():
    A = anchors()
    bg, fg, notes = build_stacks(A)
    print("Lemonardo Vivaldi palette -- gates:\n")
    bad = check(bg, fg)
    washes = {}
    for surf in ("cal", "mail"):
        for mode in ("light", "dark"):
            alpha, want, got = wash_alpha(surf, mode)
            washes[(surf, mode)] = alpha
            print(f"  wash   {surf:4} {mode:5} a {alpha:.3f} -> dE {got:5.2f} "
                  f"(midori {want:5.2f})")
            if got > want * 1.25:
                bad.append(f"wash {surf} {mode}")
    mats = {}
    for mode in ("light", "dark"):
        (la, lc, lde), (sa, sc, sde) = material(mode)
        mats[mode] = (la, sa)
        lab = label_on(ACCENT[mode])
        ct = cs.contrast(sc, lab)
        print(f"  tab    {mode:5} lit 1px a {la:.3f} -> {lc} dE {lde:5.2f}   "
              f"field a {sa:.3f} -> {sc} dE {sde:5.2f}   "
              f"label {lab} on the shaded end {ct:5.2f}:1")
        # The field DARKENS the surface the label sits on, so it can only lower
        # that contrast. Nothing else here can, which is why this is the one
        # contrast gate on the material layer.
        if ct < 4.5:
            bad.append(f"tab material {mode}: label falls to {ct:.2f}:1 at the "
                       f"shaded end")
    # Equal light in both benches, swapped position -- see the module
    # docstring. A future edit that retargets one bench and not the other is
    # exactly what this catches.
    for what, i in (("lit", 0), ("field", 1)):
        de = [material(m)[i][2] for m in ("light", "dark")]
        if abs(de[0] - de[1]) > 0.5:
            bad.append(f"tab material {what}: paintpot dE {de[0]:.2f} vs "
                       f"inkwell dE {de[1]:.2f} -- the two benches must carry "
                       f"the same amount of light, only in different places")
    if bad:
        sys.exit(f"\nrefusing to write: {bad}")
    print("\n  all gates pass")

    ids = {t["name"]: t["id"]
           for t in json.loads(THEMES.read_text())["themes"]}
    L = [__doc__.strip().replace("\n", "\n   ")]
    out = ["/* " + L[0] + "\n\n"
           "   GENERATED by vivaldi/make-lemonardo-palette.py -- edit that,\n"
           "   not this. Every number below is re-derived and gated on each\n"
           "   run; the gates are printed, including how far the tab stacks\n"
           "   sit from the Midori values they replace.\n\n"
           "   The selector repeats the class on purpose:\n"
           "   #browser.theme-id-X.theme-id-X is one id plus TWO classes, so\n"
           "   it outranks the Midori defaults on #browser.theme-light (one\n"
           "   id, one class) outright. A single .theme-id-X would merely tie\n"
           "   them, and a tie is settled by the order Vivaldi happens to read\n"
           "   the mods directory in -- not a design decision. */"]

    for mode, theme in (("light", "Lemonardo Paintpot"),
                        ("dark", "Lemonardo Inkwell")):
        tid = ids[theme]
        acc = ACCENT[mode]
        rgb = " ".join(str(c) for c in
                       (int(acc[1:3], 16), int(acc[3:5], 16), int(acc[5:7], 16)))
        out.append(f"\n/* ---- {theme}: ground {GROUND[mode]} ---- */")
        out.append(f"#browser.theme-id-{tid}.theme-id-{tid} {{")
        out.append("  /* typography: Besley names, Instrument Sans works "
                   "(themes/lemonardo.json `fonts`) */")
        out.append('  --mfont-working: "Instrument Sans", ui-sans-serif, '
                   'system-ui, sans-serif;')
        out.append("  --mfont-naming: Besley, ui-serif, Georgia, serif;")
        out.append("  --mfont-naming-weight: 600;")
        out.append("")
        out.append(f"  /* calendar -- accent is the vermilion construction line */")
        out.append(f"  --mcal-sage: {acc};")
        out.append(f"  --mcal-sage-soft: rgb({rgb} / {washes[('cal', mode)]:.3f});")
        out.append(f"  --mcal-sage-line: rgb({rgb} / {LINE_ALPHA[('cal', mode)]});")
        out.append(f"  --mcal-ink: {INK[mode]};")
        out.append(f"  --mcal-muted: {MUTED[mode]};")
        out.append("")
        out.append("  /* mail */")
        out.append(f"  --mmail-sage: {acc};")
        out.append(f"  --mmail-sage-soft: rgb({rgb} / {washes[('mail', mode)]:.3f});")
        out.append(f"  --mmail-sage-line: rgb({rgb} / {LINE_ALPHA[('mail', mode)]});")
        out.append(f"  --mmail-ink: {INK[mode]};")
        out.append(f"  --mmail-muted: {MUTED[mode]};")
        out.append(f"  --mmail-card: {CARD[mode]};")
        for role, v in LABELS[mode].items():
            out.append(f"  --mmail-label-{role}: {v};")
        out.append("")
        out.append("  /* surfaces -- !important to beat Vivaldi's inline style "
                   "on #browser */")
        out.append(f"  --colorBgIntense: {CARD[mode]} !important;")
        out.append(f"  --colorBgIntenser: {INTENSER[mode]} !important;")
        out.append(f"  --colorBgLight: {CARD[mode]} !important;")
        trgb, ta, tb = THUMB[mode]
        out.append(f"  --msurf-thumb: rgb({trgb} / {ta});")
        out.append(f"  --msurf-thumb-strong: rgb({trgb} / {tb});")
        out.append("")
        out.append("  /* start page ink (midori-site-match.css). Ink and muted are "
                   "this language's\n     own anchors; eyebrow = muted because "
                   "Lemonardo has no --accent-mythic and\n     deriving one as a "
                   "delta from Midori is the mistake the header describes. */")
        out.append(f"  --msite-ink: {INK[mode]};")
        out.append(f"  --msite-muted: {MUTED[mode]};")
        out.append(f"  --msite-eyebrow: {MUTED[mode]};")
        out.append("")
        out.append("  /* tab stacks -- the studio's pigments, at this mode's "
                   "one accent lightness */")
        for i in range(9):
            hx, f_ = bg[mode][i], fg[mode][i]
            r = " ".join(str(int(hx[j:j + 2], 16)) for j in (1, 3, 5))
            out.append(f"  --mstack-{i+1}: {hx}; --mstack-{i+1}-rgb: {r};"
                       f" --mstack-{i+1}-fg: {f_};   /* {notes[mode][i]} */")
        out.append("}")

        # --- the material layer on the active tab --------------------------
        lit_a, field_a = mats[mode]
        dirn, lamp, where = (("to bottom", "window above", "down into the pot")
                             if mode == "light" else
                             ("to top", "light table below",
                              "up the sheet from the glass"))
        out.append("")
        out.append(COMMENT % {"theme": theme, "lamp": lamp, "dirn": dirn,
                              "where": where, "lit": MATERIAL_LIT_DE,
                              "shade": MATERIAL_SHADE_DE})
        out.append(f"#browser.theme-id-{tid}.theme-id-{tid} "
                   f".tab.active .tab-header::after {{")
        out.append('  content: "";')
        out.append("  position: absolute;")
        out.append("  inset: 0;")
        out.append("  z-index: -1;")
        out.append("  pointer-events: none;")
        out.append(f"  background:")
        out.append(f"    linear-gradient({dirn}, rgb(255 255 255 / "
                   f"{lit_a:.3f}) 0 1px, rgb(255 255 255 / 0) 1px),")
        out.append(f"    linear-gradient({dirn}, rgb(0 0 0 / 0) "
                   f"{MATERIAL_SHADE_START}%, rgb(0 0 0 / {field_a:.3f}));")
        out.append("}")

    text = "\n".join(out) + "\n"
    # --check IS WHAT MAKES THE GATES ABOVE BINDING. Without it the gates only
    # run when someone chooses to regenerate, and every number in the shipped
    # CSS can be hand-edited past them -- the live check in
    # tests/check_vivaldi_tab_material.py would not notice, because it reads
    # the alphas out of this file and would faithfully confirm that whatever is
    # written there is what reaches the screen. So lint runs this with --check:
    # the design gates and the shipped file are then the same claim.
    if "--check" in sys.argv:
        have = OUT.read_text() if OUT.exists() else ""
        if have == text:
            print(f"  {OUT.relative_to(ROOT)} is up to date with this "
                  f"generator ({len(text.splitlines())} lines)")
            return
        n = sum(1 for a, b in itertools.zip_longest(
            have.splitlines(), text.splitlines()) if a != b)
        sys.exit(f"\n{OUT.relative_to(ROOT)} does not match this generator "
                 f"({n} line(s) differ). It is generated; run\n"
                 f"    python3 vivaldi/make-lemonardo-palette.py\n"
                 f"and commit the result. A hand edit here is not checked by "
                 f"anything else: the gates above are the only thing that "
                 f"knows what these numbers are supposed to be.")

    OUT.write_text(text)
    print(f"  wrote {OUT.relative_to(ROOT)} "
          f"({len(OUT.read_text().splitlines())} lines)")
    print(f"  selection is set in themes.json, not here: "
          f"{SELECTION['light']} non-photo blue (the rough) / "
          f"{SELECTION['dark']} light-table glow")


if __name__ == "__main__":
    main()
