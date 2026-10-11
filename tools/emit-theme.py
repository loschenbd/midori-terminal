#!/usr/bin/env python3
"""Write a theme's raw palette into a target stylesheet, between sentinels.

    tools/emit-theme.py --target silverbullet --theme midori
    tools/emit-theme.py --target silverbullet --theme midori --check
    tools/emit-theme.py --target silverbullet --theme lemonardo --out FILE

WHAT THIS DOES NOT DO, which is the whole design.

It does not generate stylesheets. obsidian/theme.css is 3,397 lines of which
~2,093 are comments recording what was measured, on what hardware, what was
tried and failed. silverbullet/midori.css carries the same kind of record.
Regenerating either would destroy the thing this repo exists to keep.

So a theme owns exactly ONE region per file: the raw palette declarations,
fenced by sentinel comments. Everything else -- every rule, every mapping from
a palette role to an app token, every comment -- is hand-written and is never
read, rewritten or reordered by this script. The two layers were already
separate before this existed; silverbullet/midori.css declares 24 raw roles
and then maps 98 app tokens off them by hand. This only formalises the seam.

WHY ANNOTATIONS LIVE HERE AND NOT IN THE THEME FILE. The trailing comments on
these declarations ("background-primary", "the accent") say what the role
means TO THIS APP. That is per-target knowledge, not per-theme: it is true of
SilverBullet whichever palette is loaded. Keeping them in the adapter means a
new theme inherits them for free and cannot silently drop them.

VERIFICATION. --check exits non-zero if the committed file does not match what
this script would write, and the round-trip is asserted in lint: emitting
midori must reproduce the committed block byte for byte. That is what makes
this safe to point at a file whose comments matter -- if the emitter were
lossy, the round-trip would say so before anything shipped.

THE ROUND-TRIP HAD NEVER ACTUALLY RUN. For as long as this file existed, no
target carried the sentinels, so --check could not reach a single file and lint
never invoked it. The gate above was aspirational. Wiring the first target
found that the adapter did NOT reproduce its file: it dropped both RAW TOKENS
banners and the whole MODE-VARYING SCALARS section, nine comment lines in all.
It also carried a correction the committed file lacked -- the note claiming
"indigo and wine" both take their lifted variants, when wine is declared at
wine's own dark value and wine-lift is unused. That correction had been written
here and never shipped, because nothing ran. A guard that cannot reach its
subject is not a weak guard, it is no guard.

MEASUREMENTS IN NOTES ARE COMPUTED, NOT TYPED. A note may write {ratio:a,b} and
the emitter substitutes the measured contrast of role a on role b in the mode
being emitted. This is not convenience. The committed block said "Paper text on
sage is 4.71:1" (it is 4.74) and "7.4:1 against night sage" (it is 7.23), and
both numbers would have become straightforwardly false for any second theme
while reading as authoritative. A per-target adapter cannot hold a per-theme
measurement as text. The available substitutions are:

    {ratio:a,b}   contrast of role a on role b, this mode, 2 decimals
    {hex:role}    role's value in this mode
    {hex:role.light} / {hex:role.dark}   a named mode, for an arrow like
                  "faint goes DARKER in night mode (#8a847b -> #6e685f)"
    {rgb:role}    role's value as "r, g, b", for building an rgba()

Anything a note states that is NOT one of these is a claim about the target,
true whichever palette is loaded. If you find yourself wanting to write a
number by hand, that number belongs to the theme, not to the adapter.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
THEMES = ROOT / "themes"

BEGIN = "/* >>> theme palette: generated from themes/{id}.json -- see tools/emit-theme.py */"
END = "/* <<< end theme palette -- everything below is hand-written */"
# Matches either sentinel pair regardless of which theme id is named inside,
# so re-emitting a DIFFERENT theme into a file still finds the region.
BEGIN_RE = re.compile(r"^/\* >>> theme palette:.*\*/$", re.M)
END_RE = re.compile(r"^/\* <<< end theme palette.*\*/$", re.M)

# A SECOND REGION, for type and for the constants derived from it. Colour is not
# the only thing a theme owns. silverbullet/midori.css declares --editor-width as
# 647px, which is 70 characters at M PLUS 1p's average advance of 0.4818em plus
# the border-box padding -- a number that is correct for exactly one body font.
# Lemonardo's body font measures 0.4527, so the same 70-character line is 610px.
# Left hand-written, that constant would have been copied into the second theme
# and silently set its measure 37px too wide, with the arithmetic above it still
# reading as a derivation. So the expression is emitted, not the result: see
# {calc:} below.
BEGIN_T = ("/* >>> theme type: generated from themes/{id}.json"
           " -- see tools/emit-theme.py */")
END_T = "/* <<< end theme type -- everything below is hand-written */"
BEGIN_T_RE = re.compile(r"^/\* >>> theme type:.*\*/$", re.M)
END_T_RE = re.compile(r"^/\* <<< end theme type.*\*/$", re.M)

# --- target adapters --------------------------------------------------------
# banners: the block comment above each mode's selector, per mode. These carry
# the specificity warning that makes the file work, so they are emitted rather
# than left outside the region -- a sentinel placed below them would have put
# them beyond the emitter's reach and invited the next edit to drop them.
#
# slots: one entry per emitted declaration, in order.
#   ("", ...)                      a blank line
#   ("#", key, None)               a standalone comment block from notes[key],
#                                  attached to no declaration (section headers)
#   ("@slot", ...)                 a literal from extra[], not a palette role
#   (slot, light_role, dark_role)  the token --midori-<slot> takes light_role's
#                                  light value and dark_role's dark value
# The two roles are usually the same, and the cases where they are NOT are the
# reason this is a mapping rather than a list of names. SilverBullet takes
# indigo's LIFTED variant on dark ground and uses page-dot where mint would go;
# those are decisions about this app's code surface, not about the palette, so
# they belong here and travel to every theme automatically.
#
# A 1:1 adapter would have silently rewritten three values the first time it
# ran. The round-trip check is what caught that, and it is why --check exists.
TARGETS = {
    "silverbullet": {
        # LAYOUT METRICS THIS TARGET OVERRIDES. The theme's measure_chars is 70,
        # which is also the default of the midori-set-measure slider in
        # obsidian/theme.css -- and there it is a DEFAULT the reader can move
        # between 40 and 100. SilverBullet exposes no such control and the body
        # font is fixed, so its measure is whatever this file says and nothing
        # else. The two numbers are different kinds of value and are not made to
        # agree: one is a starting point, one is the setting.
        #
        # 80 characters, up from 70. The slider's own description records the
        # finding -- "longer lines are read faster; moderate lines are preferred;
        # 70 is the preference end, 95 the speed peak" -- so this moves toward
        # the speed end without abandoning the middle.
        #
        # THE CEILING IS 87 CHARACTERS, and it is font-specific. --editor-width
        # is a border-box max-width, so the total is chars * advance * 18px plus
        # 40px of padding, and SilverBullet's stock --editor-width is 800px. At M
        # PLUS 1p's 0.4818em that puts 87 characters at 794.5px and 88 at 803.2,
        # past stock. Going past is not broken, but the note on @editor-width
        # reasons about the top bar staying where SilverBullet put it, and that
        # argument assumes the theme is no wider than stock. 80 leaves seven
        # characters of headroom. A theme with a narrower face has more: at
        # Instrument Sans's 0.4527em the same ceiling is 93.
        "metrics": {"measure_chars": 80, "topbar_font_px": 28},
        # One file per theme. Everything outside the palette region -- the
        # header prose, the semantic mapping, the long notes -- is hand-written
        # per (target, theme) and is never generated; only the region between
        # the sentinels belongs to the emitter.
        "files": {
            "midori": "silverbullet/midori.css",
            # "lemonardo": "silverbullet/lemonardo.css" -- NOT YET, and the
            # reason is recorded rather than worked around. The type region
            # quotes the advance of "0" in the body font, which is what the CSS
            # ch unit resolves to, and derives the indent grid and blockquote
            # pitch from it. Midori has that measurement (0.620em, M PLUS 1p).
            # Lemonardo's body font is Instrument Sans, which this repo does not
            # vendor in fonts/, so the number does not exist and the emitter
            # exits rather than carrying M PLUS 1p's across. Vendor the face,
            # measure U+0030, add metrics.ch_advance_em with its provenance, and
            # this line becomes a one-line change.
        },
        "slots": [
            ("ink", "ink", "ink"),
            ("text", "text", "text"),
            ("muted", "muted", "muted"),
            ("faint", "faint", "faint"),
            ("", None, None),
            ("paper", "paper", "paper"),
            ("card", "card", "card"),
            ("secondary", "secondary", "secondary"),
            ("@border", None, None),
            ("", None, None),
            ("sage", "sage", "sage"),
            ("indigo", "indigo", "indigo-lift"),
            ("olive", "olive", "olive"),
            ("wine", "wine", "wine"),
            ("ochre", "ochre", "ochre"),
            ("purple", "purple", "purple"),
            ("mint", "mint", "page-dot"),
            ("clay", "clay", "clay"),
            ("mythic", "mythic", "mythic"),
            ("", None, None),
            ("code-normal", "code-normal", "code-normal"),
            ("code-comment", "code-comment", "code-comment"),
            ("code-punctuation", "code-punctuation", "code-punctuation"),

            ("", None, None),
            ("#", "scalars", None),
            ("", "light", None),
            ("@on-accent", None, None),
            ("", "light", None),
            ("@selection-alpha", None, None),
            ("", "light", None),
            ("@wash-base", None, None),
            ("@comment-alpha", None, None),
        ],
        # Trailing comment on a declaration. PER TARGET, not per theme: these
        # say what the role means to SilverBullet, which is true whichever
        # palette is loaded. Keyed (slot, mode) when it differs by mode.
        "annotations": {
            ("paper", "light"): "background-primary",
            ("card", "light"): "background-primary-alt, code-background",
            ("secondary", "light"): "background-secondary",
            ("sage", "light"): "the accent",
            ("indigo", "dark"): "midori-indigo-lift",
            ("mint", "dark"): "midori-page-dot",
            # Computed, not typed. This read "7.4:1 against night sage" in the
            # committed file and measures 7.23 for Midori -- and would have been
            # wrong by a different amount for every later theme.
            ("@on-accent", "dark"): "{ratio:on-accent,sage}:1 against night sage",
        },
        # The block comment above each mode's selector. These are emitted, not
        # left above the sentinel, because the night banner states the one fact
        # that makes this file work at all.
        "banners": {
            "light": [
                "/* ====================================================================== *",
                " * RAW TOKENS, PAPER.",
                " * The Midori palette, copied from obsidian/theme.css via palette.json under",
                " * the names those values already carry. Nothing here is invented for",
                " * SilverBullet. The palette is CLOSED: all six chromatic slots are spoken",
                " * for, and a new hue is a palette decision, not a theme decision.",
                " * ====================================================================== */",
            ],
            "dark": [
                "/* ====================================================================== *",
                " * RAW TOKENS, NIGHT. Same element, higher specificity, so these replace the",
                " * paper values above for every semantic property that reads them.",
                " * ====================================================================== */",
            ],
        },
        # Block comments carried into the generated region, so the reasoning
        # for a non-obvious slot mapping is not lost when the region is
        # rewritten. Emitted immediately ABOVE the named slot, in that mode.
        "notes": {
            ("indigo", "dark"): [
                "Indigo takes its LIFTED variant on dark ground. That is a separate palette",
                "entry (indigo-lift), not an ad-hoc lightening: {hex:indigo} is indigo's own",
                "dark value and sits too close to the ground for code, which is what -lift",
                "exists for.",
                "",
                "CORRECTED. This note used to say \"indigo and wine\" take their lifted",
                "variants. Wine does not, and never did here -- it is declared below at",
                "{hex:wine}, which is wine's own dark value; wine-lift is {hex:wine-lift} and is",
                "unused in this file. The claim was plausible because the two roles are",
                "adjacent in the palette and both have a -lift entry, so one sentence",
                "covered both and only one half was ever checked.",
            ],
            ("mint", "dark"): [
                "Mint has no dark entry in palette.json; page-dot is the value",
                "obsidian/theme.css uses in its place on dark ground.",
            ],
            ("scalars", "light"): [
                "MODE-VARYING SCALARS, so the semantic block below can stay mode-free.",
                "Each of these differs between paper and night for a reason that is not a",
                "hue change, and putting them here is what keeps the mapping single.",
            ],
            ("@on-accent", "light"): [
                "Text ON the accent. Paper text on sage is {ratio:on-accent,sage}:1, clearing AA for body",
                "and AAA for large. On night ground the accent is light, so this inverts;",
                "see the night block.",
                "",
                "CORRECTED, and now computed. This said 4.71:1 on paper and 7.4:1 on night;",
                "the palette measures 4.74 and 7.23. Neither was far enough off to notice by",
                "eye, which is the point -- they were typed once, correct to roughly a",
                "rounding, and then outlived the values they described. Both numbers now",
                "come from a computed substitution and cannot say anything the palette does not.",
            ],
            ("@selection-alpha", "light"): [
                "The selection needs more alpha on dark ground to register at all: sage at",
                "25% over {hex:paper.light} is a visible tint, the same 25% over {hex:paper.dark} is nearly",
                "nothing. marktext/midori.css landed on the same pair for the same reason.",
            ],
            ("@wash-base", "light"): [
                "The neutral a general-purpose wash is mixed from. Faint on paper, muted on",
                "night: faint goes DARKER in night mode ({hex:faint.light} -> {hex:faint.dark}) because it is",
                "a de-emphasis colour against light ground, so a wash built from it would",
                "disappear.",
            ],
        },
        # Target facts that are not palette roles. The border is this app's own
        # hairline over its own ground; the alpha is the target's, the colour it
        # tints is the theme's, so it is built from the palette rather than typed.
        # --- the TYPE region. Mode-independent: SilverBullet declares the fonts
        # and the measure once, in the shared mapping rule. Every value here is a
        # computed expression, because each is a property of the typeface or of
        # the layout, never of the palette. --editor-width is the reason this
        # region exists: 647px is 70 characters at M PLUS 1p's 0.4818em advance,
        # and copying it into a second theme would have set that theme's measure
        # 37px too wide with the arithmetic above it still reading as a derivation.
        "type_slots": [
            ("#", "divider", None),
            ("", None, None),
            ("@ui-font", None, None),
            ("", None, None),
            ("@editor-font", None, None),
            ("", None, None),
            ("@editor-width", None, None),
        ],
        "type_notes": {
            ("divider", "only"): [
                "---------------- type ----------------",
            ],
            ("@ui-font", "only"): [
                "{font_name:ui} for chrome, matching --font-interface-theme in",
                "obsidian/theme.css. --ui-font drives #sb-root, every button, input, select",
                "and tab, the page-name field in the top bar, and the nav sidebar.",
            ],
            ("@editor-font", "only"): [
                "{font_name:body} for the writing surface. This is the one real departure from",
                "stock: SilverBullet is monospace end to end by design (iA-Mono), and",
                "--editor-font is the ONLY font-family the editor sets \u2014 there is no",
                "separate family for code anywhere in its stylesheet, so switching this to",
                "a proportional face takes fenced code with it. The tail of this file puts",
                "a monospace family back on code, which is a rule SilverBullet does not",
                "need and this theme does.",
                "",
                "WHAT THE ch-BASED GEOMETRY DOES WHEN THE FONT CHANGES, measured rather",
                "than assumed. `#sb-main .cm-editor .cm-content` declares",
                "`--editor-column: 1ch` and `--blockquote-step: 2ch`; the first indents",
                "inline comments by 3 columns, the second sets the repeating-gradient pitch",
                "that draws nested blockquote bars. `ch` is the advance of \"0\":",
                "",
                "    iA-Mono    0.600em  ->  10.80px at the 18px editor size",
                "    {font_name:body}  {metric:ch_advance_em:3}em  ->  {calc_raw:ch_advance * editor_font_px}px",
                "",
                "so the indent grid moves +{calc_raw:(ch_advance - 0.600) * editor_font_px}px per column, +{calc_raw:(ch_advance - 0.600) * 3 * editor_font_px}px on a 3-column inline",
                "comment, and the blockquote pitch goes 21.60px -> {calc_raw:ch_advance * 2 * editor_font_px}px. Left alone",
                "deliberately. Pinning it would mean re-declaring --editor-column on",
                "`.cm-content`, which needs a selector at least as specific as",
                "`#sb-main .cm-editor .cm-content` (1,2,0) \u2014 a high-specificity rule",
                "reaching into SilverBullet's layout to buy back a third of a pixel.",
            ],
            ("@editor-width", "only"): [
                "THE MEASURE, IN ABSOLUTE PX, AND IT MUST BE ABSOLUTE.",
                "",
                "Midori's line length is a setting in characters held through one measured",
                "constant: {metric:measure_chars} characters at {font_name:body}'s average advance of",
                "{metric:avg_advance_em}em, taken with a BoundsPen over a prose sample. See the long",
                "note at --midori-set-measure in obsidian/theme.css; the constant is",
                "font-specific and is only valid because the body font is fixed, which it",
                "is here too.",
                "",
                "80 CHARACTERS, UP FROM 70, and the ceiling here is 87. --editor-width is a",
                "border-box max-width and SilverBullet's stock value is 800px; at this",
                "font 87 characters land at 794.5px and 88 at 803.2, past stock. The note",
                "below reasons about the top bar staying where SilverBullet put it, and",
                "that argument assumes the theme is no wider than stock, so the headroom",
                "matters. The number itself lives in tools/emit-theme.py as this target's",
                "metrics override, not in the theme: obsidian/theme.css offers 70 as a",
                "DEFAULT the reader can move between 40 and 100, and SilverBullet has no",
                "such control, so one is a starting point and the other is the setting.",
                "",
                "SilverBullet applies --editor-width as max-width on `.cm-content`, which",
                "is `box-sizing: border-box` with `padding: 5px 20px`, at font-size 18px:",
                "",
                "    {metric:measure_chars} * {metric:avg_advance_em} * {metric:editor_font_px}px  =  {calc_raw:measure_chars * avg_advance * editor_font_px}px of text",
                "                 + 40px     the two 20px paddings, inside the border box",
                "    ------------------",
                "                  {calc:measure_chars * avg_advance * editor_font_px + editor_padding_px}",
                "",
                "NOT em, for the same class of reason obsidian/theme.css records, in a",
                "different element. There the hazard is that `.cm-line` is also the heading",
                "element, so an em measure hands an h1 an 880px column against a body",
                "line's 544px. SilverBullet is safe from THAT one \u2014 max-width sits on the",
                "shared `.cm-content` parent, and h1 and p lines both measure 760px at the",
                "stock 800px, verified. But --editor-width has four consumers, and one of",
                "them is `#sb-top .main .inner`, the page-title row, at `font-size: 28px`.",
                "An em value resolves against each consumer's own font-size: {calc_raw:measure_chars * avg_advance}em is",
                "{calc:measure_chars * avg_advance * editor_font_px} in the text column but {calc:measure_chars * avg_advance * topbar_font_px} in the top bar, pulling the",
                "title out of alignment with the text it names. The px form leaves the top",
                "bar where SilverBullet put it; the rendered check asserts the resulting",
                "text column at {calc_raw:measure_chars * avg_advance * editor_font_px}px to 0.6px.",
            ],
        },
        "type_extra": {
            "@ui-font": "\"{font_name:ui}\", ui-serif, Georgia, serif",
            "@editor-font": "{font:body}",
            "@editor-width": "{calc:measure_chars * avg_advance * editor_font_px + editor_padding_px}",
        },
        "extra": {
            "@border": {"light": "rgba({rgb:border-base.light}, 0.1)",
                        "dark": "rgba({rgb:border-base.dark}, 0.12)"},
            "@on-accent": {"light": "var(--midori-paper)", "dark": "{hex:on-accent}"},
            "@selection-alpha": {"light": "25%", "dark": "38%"},
            "@wash-base": {"light": "var(--midori-faint)", "dark": "var(--midori-muted)"},
            "@comment-alpha": {"light": "10%", "dark": "14%"},
        },
    },
}


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hexv):
    h = hexv.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


SUBST_RE = re.compile(r"\{(ratio|hex|rgb|font|font_name|metric|calc|calc_raw):([^}]+)\}")


def _calc(expr, theme):
    """Evaluate a small arithmetic expression over the theme's own metrics.

    Only the names below resolve, and only arithmetic runs: no builtins, no
    attribute access, no calls. The point is that a derived constant ships as
    its derivation, so a second theme cannot inherit the first theme's number.
    """
    met = theme.get("metrics", {})
    typ = theme.get("type", {})
    # The advances live under "type" because they are properties of a typeface;
    # the measure terms live under "metrics" because they are properties of the
    # layout. themes/midori.json already records the formula in
    # metrics._comment: measure_chars * avg_advance_em * editor_font_px +
    # editor_padding_px, border-box. This resolves both halves.
    names = {
        "avg_advance": typ.get("avg_advance_em"),
        "mono_advance": typ.get("mono_advance_em"),
        "ch_advance": met.get("ch_advance_em"),
        "measure_chars": met.get("measure_chars"),
        "topbar_font_px": met.get("topbar_font_px"),
        "editor_font_px": met.get("editor_font_px"),
        "editor_padding_px": met.get("editor_padding_px"),
    }
    missing = [k for k, v in names.items() if v is None]
    tree = compile(expr, "<calc>", "eval")
    for n in tree.co_names:
        if n not in names:
            sys.exit(f"emit-theme.py: {{calc:}} may use "
                     f"{', '.join(sorted(names))}, not {n!r}")
        if n in missing:
            sys.exit(f"emit-theme.py: theme {theme['id']!r} has no "
                     f"metric {n!r}, which {expr!r} needs")
    return eval(tree, {"__builtins__": {}}, dict(names))


def interpolate(text, pal, mode, theme=None):
    """Fill {ratio:a,b}, {hex:role[.mode]} and {rgb:role} from the palette.

    A note that quotes a number must get it from here, so that the number is
    the one this theme actually measures. See the docstring: the two numbers
    this replaced were both wrong for the theme they described.
    """
    def one(m):
        kind, arg = m.group(1), m.group(2)

        def value(spec):
            if "." in spec:
                role, which = spec.rsplit(".", 1)
            else:
                role, which = spec, mode
            if role not in pal:
                sys.exit(f"emit-theme.py: note references unknown role {role!r}")
            if which not in ("light", "dark"):
                sys.exit(f"emit-theme.py: note references unknown mode {which!r}")
            return pal[role][which]

        if kind == "ratio":
            parts = [x.strip() for x in arg.split(",")]
            if len(parts) != 2:
                sys.exit(f"emit-theme.py: {{ratio:}} wants two roles, got {arg!r}")
            return f"{contrast(value(parts[0]), value(parts[1])):.2f}"
        if kind == "hex":
            return value(arg.strip())
        if kind == "font":
            return theme["type"][arg.strip()]
        if kind == "font_name":
            # The family's own name, without the fallback stack -- for prose
            # that names the face ("M PLUS 1p for the writing surface").
            return theme["type"][arg.strip()].split(",")[0].strip().strip('"')
        if kind == "metric":
            # Looks in "metrics" then "type": the advances are properties of a
            # typeface and live under type, the measure terms live under metrics.
            # "name" or "name:N" -- N forces N decimal places. A measured
            # advance of 0.620em has three significant decimals and JSON stores
            # it as 0.62, so the precision has to be stated where it is used.
            key = arg.strip()
            places = None
            if ":" in key:
                key, p_ = key.rsplit(":", 1)
                places = int(p_)
            for section in ("metrics", "type"):
                if key in theme.get(section, {}):
                    v = theme[section][key]
                    return f"{v:.{places}f}" if places is not None else str(v)
            sys.exit(f"emit-theme.py: theme {theme['id']!r} has no metric "
                     f"{key!r} in metrics or type")
        if kind == "calc":
            # px, rounded. The arithmetic is in the comment above the slot;
            # this is the one place the result is produced.
            return f"{round(_calc(arg.strip(), theme))}px"
        if kind == "calc_raw":
            # Two decimals, no unit, for prose that quotes the unrounded
            # intermediate ("607.07px of text").
            return f"{_calc(arg.strip(), theme):.2f}"
        h = value(arg.strip()).lstrip("#")
        return ", ".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))

    return SUBST_RE.sub(one, text)


def load_theme(theme_id):
    p = THEMES / f"{theme_id}.json"
    if not p.is_file():
        sys.exit(f"emit-theme.py: no theme at {p}")
    return json.loads(p.read_text())


def render(theme, target):
    """The generated region, as text. Both mode blocks, nothing else."""
    pal = theme["palette"]
    ann, notes = target["annotations"], target.get("notes", {})
    extra = target.get("extra", {})
    banners = target.get("banners", {})
    out = [BEGIN.format(id=theme["id"])]

    def block_comment(lines, mode, indent="  "):
        """A /* ... */ comment, interpolated, at the given indent."""
        body = [interpolate(l, pal, mode, theme) for l in lines]
        rendered = []
        for i, line in enumerate(body):
            if i == 0:
                rendered.append(f"{indent}/* {line}".rstrip())
            elif line:
                rendered.append(f"{indent}   {line}")
            else:
                rendered.append("")
        rendered[-1] = rendered[-1] + " */"
        return rendered

    for mode, selector in (("light", "html {"), ("dark", 'html[data-theme="dark"] {')):
        for line in banners.get(mode, []):
            out.append(interpolate(line, pal, mode))
        out.append(selector)

        for slot, light_role, dark_role in target["slots"]:
            if slot == "":
                # A blank row may be scoped to one mode. The light block spaces
                # its scalars out with their comments; the dark block has no
                # comments there and runs the four declarations together.
                if light_role in (None, mode):
                    out.append("")
                continue

            # a comment attached to no declaration -- a section header
            if slot == "#":
                key = (light_role, mode)
                if key in notes:
                    out.extend(block_comment(notes[key], mode))
                continue

            if (slot, mode) in notes:
                out.extend(block_comment(notes[(slot, mode)], mode))

            if slot.startswith("@"):
                value = interpolate(extra[slot][mode], pal, mode, theme)
                name = slot[1:]
            else:
                role = light_role if mode == "light" else dark_role
                if role not in pal:
                    sys.exit(f"emit-theme.py: theme {theme['id']!r} "
                             f"has no role {role!r} (slot {slot!r}, {mode})")
                value, name = pal[role][mode], slot
            decl = f"  --midori-{name}: {value};"
            note = ann.get((slot, mode)) or ann.get((slot, None))
            if note:
                note = interpolate(note, pal, mode, theme)
                decl = f"{decl:<36}/* {note} */"
            out.append(decl)
        out.append("}")
        if mode == "light":
            out.append("")

    out.append(END)
    return "\n".join(out)


def extract(text):
    """The sentinel region's lines, for reporting a mismatch."""
    b, e = BEGIN_RE.search(text), END_RE.search(text)
    if not b or not e:
        return []
    return text[b.start():e.end()].split("\n")


def render_type(theme, target):
    """The type region, as text. One block, no selectors, no mode split.

    Returns None for a target that declares no type_slots -- most targets have
    no metric-derived constant and should not be given an empty region.
    """
    rows = target.get("type_slots")
    if not rows:
        return None
    pal = theme["palette"]
    notes = target.get("type_notes", {})
    vals = target.get("type_extra", {})
    out = [BEGIN_T.format(id=theme["id"])]

    for slot, key, _ in rows:
        if slot == "":
            out.append("")
            continue
        if slot == "#":
            body = [interpolate(l, pal, "light", theme)
                    for l in notes.get((key, "only"), [])]
            if body:
                out.append(f"  /* {body[0]} */")
            continue
        body = notes.get((slot, "only"))
        if body:
            rendered = []
            for i, line in enumerate(interpolate(l, pal, "light", theme)
                                     for l in body):
                if i == 0:
                    rendered.append(f"  /* {line}".rstrip())
                elif line:
                    rendered.append(f"     {line}")
                else:
                    rendered.append("")
            rendered[-1] = rendered[-1] + " */"
            out.extend(rendered)
        value = interpolate(vals[slot], pal, "light", theme)
        out.append(f"  --{slot[1:]}: {value};")

    out.append(END_T)
    return "\n".join(out)


def splice_type(text, region):
    b, e = BEGIN_T_RE.search(text), END_T_RE.search(text)
    if not b or not e:
        return None
    return text[:b.start()] + region + text[e.end():]


def extract_type(text):
    b, e = BEGIN_T_RE.search(text), END_T_RE.search(text)
    if not b or not e:
        return []
    return text[b.start():e.end()].split("\n")


def splice(text, region):
    b, e = BEGIN_RE.search(text), END_RE.search(text)
    if not b or not e:
        return None
    return text[:b.start()] + region + text[e.end():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=sorted(TARGETS))
    ap.add_argument("--theme", required=True)
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the file does not already match")
    ap.add_argument("--out", help="write here instead of in place")
    a = ap.parse_args()

    theme = load_theme(a.theme)
    target = TARGETS[a.target]
    if a.theme not in target["files"]:
        sys.exit(f"emit-theme.py: target {a.target!r} ships no file for theme "
                 f"{a.theme!r}. It declares: {', '.join(sorted(target['files']))}")
    rel = target["files"][a.theme]
    path = ROOT / rel
    if not path.is_file():
        sys.exit(f"emit-theme.py: no target file at {path}")

    # A target may override layout metrics (not colour). Merged here so that
    # every substitution downstream -- the note's arithmetic and the declaration
    # it produces -- sees exactly one value and cannot disagree with itself.
    if target.get("metrics"):
        theme = dict(theme, metrics={**theme.get("metrics", {}),
                                     **target["metrics"]})

    region = render(theme, target)
    text = path.read_text()
    new = splice(text, region)

    # The TYPE region, where the target has one. A target that declares
    # type_slots and whose file has no type sentinels is an error, not a
    # silent skip: that combination is exactly how the palette gate spent
    # its whole life passing without reaching anything.
    type_region = render_type(theme, target)
    if type_region is not None:
        if new is None:
            new = text
        spliced = splice_type(new, type_region)
        if spliced is None:
            sys.exit(f"emit-theme.py: {rel} declares type_slots but has no "
                     f"theme-type sentinels.\n  Add these two lines around the "
                     f"font and measure declarations:\n    "
                     f"{BEGIN_T.format(id=a.theme)}\n    {END_T}\n"
                     f"  Nothing was written.")
        new = spliced
    if new is None:
        sys.exit(f"emit-theme.py: {rel} has no theme-palette sentinels.\n"
                 f"  Add these two lines around the raw palette declarations:\n"
                 f"    {BEGIN.format(id=a.theme)}\n    {END}\n"
                 f"  Nothing was written.")

    if a.check:
        if new == text:
            n = len([s for s, _, _ in target["slots"] if s and s != "#"])
            t = len([s for s, _, _ in target.get("type_slots", [])
                     if s and s != "#"])
            extra = f" + {t} type" if t else ""
            print(f"  ok   {rel} matches themes/{a.theme}.json "
                  f"({n} declarations x 2 modes{extra})")
            return 0
        # Name what broke. A guard that says only "does not match" sends the
        # reader back to a diff they have to construct themselves, and this
        # repo's history is of green-but-vacuous checks -- a red one that
        # cannot say why is the same problem with the sign flipped.
        print(f"  FAIL {rel} does not match themes/{a.theme}.json")
        import difflib
        cur = extract(text) + extract_type(text)
        want = extract(new) + extract_type(new)
        shown = 0
        for line in difflib.unified_diff(cur, want, "committed", "emitted",
                                         lineterm="", n=0):
            if line.startswith(("---", "+++")):
                continue
            print(f"       {line}")
            shown += 1
            if shown >= 12:
                print("       ... (truncated)")
                break
        print("       run: tools/emit-theme.py "
              f"--target {a.target} --theme {a.theme}")
        return 1

    dest = pathlib.Path(a.out) if a.out else path
    dest.write_text(new)
    n = len([s for s, _, _ in target["slots"] if s])
    print(f"wrote {dest} <- themes/{a.theme}.json ({n} roles x 2 modes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
