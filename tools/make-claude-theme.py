#!/usr/bin/env python3
"""Generate a Claude Code theme (~/.claude/themes/<name>.json) for a design
language, from that language's own palette.

WHY THIS EXISTS AS A GENERATOR. The Midori token map was written by hand into
watcher/midori-claude-theme.sh, 48 tokens x 2 modes, and it is correct. Copying
it for Lemonardo would have meant hand-translating 96 values, which is exactly
the job that produced ten Lemonardo ANSI slots sitting within dE 10 of Midori's
before tools/make-lemonardo-ansi.py replaced the hand map. So the SOURCE of
each token is written down once, here, and both languages are built from it.

THREE KINDS OF TOKEN, and the third is the interesting one.

  ANSI       the token is a terminal slot: `error` is ANSI 1, `success` ANSI 2.
             Mechanical, and the right answer for both languages, because the
             slot already means that thing in each palette.

  ROLE       the token is a named palette role: `claude` is terracotta in light
             and clay in dark. Also mechanical, and note the role differs per
             mode in the Midori map -- that asymmetry is deliberate and is
             carried over rather than normalised away.

  MIX        the token is a surface or a wash that exists in no palette: a diff
             band, a message background, the rate-limit trough. These were
             chosen by eye for Midori and have no name. Rather than invent
             Lemonardo equivalents by eye in turn, each is SOLVED against the
             Midori map: find the (role, alpha) whose composite over Midori's
             ground best reproduces Midori's value, then replay that same
             (role, alpha) over Lemonardo's ground. What ports is the DISTANCE
             the surface sits from the page, which is the design decision;
             the pigment comes from whichever palette is being built.

             The solve is checked, not assumed: --report prints the dE2000 of
             each reproduction against the Midori value it is fitting, and a
             fit worse than FIT_CEILING fails the build rather than shipping a
             surface whose rule nobody can state.
"""
import argparse
import importlib.util
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cs = _load("tools/colorspace.py", "colorspace")

# A fit worse than this means the (role, alpha) model does not describe the
# Midori value, so replaying it on Lemonardo would be replaying nothing. 2.0
# dE2000 is about the just-noticeable threshold for large flat areas.
FIT_CEILING = 2.0

# token -> ("ansi", n) | ("role", name) | ("role2", light_name, dark_name)
#        | ("mix",) meaning "solve it"
# Taken from watcher/midori-claude-theme.sh by tracing each hex to the Midori
# palette; tools/make-claude-theme.py --verify re-derives that trace and fails
# if a token's Midori value stops matching the source named here.
SOURCE = {
    "text": ("fg",), "inverseText": ("ansi15", "bg"),
    "suggestion": ("ansi", 4), "planMode": ("ansi", 4),
    "permission": ("ansi", 4), "professionalBlue": ("ansi", 4),
    "claudeBlue_FOR_SYSTEM_SPINNER": ("ansi", 4),
    "permissionShimmer": ("ansi", 12),
    "claudeBlueShimmer_FOR_SYSTEM_SPINNER": ("ansi", 12),
    "error": ("ansi", 1), "warning": ("ansi", 3), "autoAccept": ("ansi", 3),
    "chromeYellow": ("ansi", 3), "warningShimmer": ("ansi", 11),
    "autoAcceptShimmer": ("ansi", 11), "success": ("ansi", 2),
    "briefLabelYou": ("ansi", 2), "rate_limit_fill": ("ansi", 2),
    "remember": ("ansi", 5), "effortUltra": ("ansi", 5),
    "ide": ("ansi", 6), "selectionBg": ("sel",),
    "fastMode": ("role2", "terracotta", "clay"),
    "claude": ("role2", "terracotta", "clay"),
    "briefLabelClaude": ("role2", "terracotta", "clay"),
    "fastModeShimmer": ("role2", "clay", "terracotta"),
    "claudeShimmer": ("role2", "clay", "terracotta"),
    "clawd_body": ("role", "clay"),
    "clawd_background": ("role", "warm-wash"),
    "subtle": ("mix",), "inactive": ("mix",), "inactiveShimmer": ("mix",),
    "merged": ("tint",), "skill": ("tint",), "bashBorder": ("mix",),
    "bashMessageBackgroundColor": ("mix",), "memoryBackgroundColor": ("mix",),
    "userMessageBackground": ("mix",), "userMessageBackgroundHover": ("mix",),
    "promptBorder": ("mix",), "promptBorderShimmer": ("mix",),
    "rate_limit_empty": ("mix",),
    "diffAdded": ("wash",), "diffAddedDimmed": ("wash",),
    "diffAddedWord": ("wash",), "diffRemoved": ("wash",),
    "diffRemovedDimmed": ("wash",), "diffRemovedWord": ("wash",),
}

# WASH and TINT, the two kinds that are stated in OKLCh rather than fitted.
# Both exist because the MIX model could not express them, and in both cases
# the reason turned out to be that they were never composites.
#
# WASH -- the six diff bands. watcher/midori-claude-theme.sh says in its own
# header that they are "highlighter washes (olive/terracotta seeds from
# tokentrail feature-colors chroma)", and the numbers agree. Solved as mixes
# they left five tokens above the fit ceiling, worst dE 3.61, every one of them
# on the NIGHT ground -- because on a dark page a wash is a LIFT, and
# compositing an accent toward a near-black ground cannot produce one.
#
# The rule: each band is its ground's lightness offset by a fixed amount,
# carrying a fixed chroma, at its family seed's hue. Three strengths, two
# families. The offsets below are measured from the Midori map and are the
# design decision that ports -- how loud a band reads against its own page.
# The HUE is not in the table: it comes from whichever language is being built,
# so Lemonardo's bands are its own pigments rather than Midori's.
#
# dL is signed: paper darkens, night lifts, and the two are near mirrors.
WASH = {
    "diffAddedDimmed":   ("added",   -0.0450, 0.0134, 0.0638, 0.0187),
    "diffAdded":         ("added",   -0.1157, 0.0264, 0.1314, 0.0296),
    "diffAddedWord":     ("added",   -0.2112, 0.0374, 0.2191, 0.0443),
    "diffRemovedDimmed": ("removed", -0.0428, 0.0163, 0.0643, 0.0186),
    "diffRemoved":       ("removed", -0.1143, 0.0331, 0.1242, 0.0367),
    "diffRemovedWord":   ("removed", -0.1980, 0.0543, 0.2401, 0.0647),
}

# The seed each family takes its hue from, as a palette role in
# themes/<language>.json -- the two the watcher's header names.
#
# AND BOTH MODES READ THE `light` VARIANT, which looks like a bug and is the
# measurement. Each role has a light and a dark value; taking each mode's own
# variant reproduces Midori's twelve bands to worst dE 4.04, while taking the
# light variant for BOTH reproduces them to worst 2.62 -- and three of the six
# night bands come back byte-identical, which a wrong hue does not do. Midori's
# night bands measure hue 47.7-52.7 against terracotta.light at 47.8 and
# terracotta.dark at 59.5. One base hue per family, lifted or darkened per
# mode, is what the original script did.
WASH_SEED = {"added": "olive", "removed": "terracotta"}

# THE OFFSETS PORT; THE HEADROOM DOES NOT. A band is written under body text,
# so the number that has to hold is text-on-band contrast, and that depends on
# how far each language's ink already sits from its page. Midori's ink is
# #2a2825 on #f3f1eb and its own six bands clear 6.13:1 at worst -- the table
# above was measured where this constraint was never close. Lemonardo's ink is
# #3a4048 on #f3eee2, a lighter ink on a warmer page, and the SAME offsets land
# its two word-level bands at 4.58:1 (light) and 4.38:1 (dark). The dark one
# misses the 4.5:1 floor this surface holds elsewhere (prompt/lemonardo.omp.json
# measures every slot against it) by 0.12.
#
# So the offset is a target and this is its floor: pull |dL| back, in 0.001
# steps, until text-on-band clears 4.5:1. It is the smallest correction that
# keeps the rule stated rather than per-language, and for Midori it never
# binds -- which is checkable, and --check would report it if it ever did.
WASH_FLOOR = 4.5


def clip_wash(ground_L, dl, c, hue, ink):
    """Walk |dl| back until text-on-band clears WASH_FLOOR. Returns (hex, dl)."""
    step = -0.001 if dl > 0 else 0.001
    while abs(dl) > 0.001:
        v, _ = cs.oklch_to_hex_clamped(ground_L + dl, c, hue)
        if cs.contrast(ink, v) >= WASH_FLOOR:
            return v, dl
        dl += step
    v, _ = cs.oklch_to_hex_clamped(ground_L + dl, c, hue)
    return v, dl

# TINT -- `merged` and `skill`, the two accents that are neither a slot nor a
# composite: a palette role's HUE carried at its own lightness and chroma.
# Measured from the Midori map as (role, L light, C light, L dark, C dark).
#
#   merged  hue 310.7 / 310.4   purple role  310.0 / 309.5   <- the same hue
#   skill   hue 198.5 / 199.2   NO Midori role is within 25 degrees
#
# `merged` is simply purple held back: L 0.530 against the role's 0.440, C
# 0.077 against 0.109. Fitted as a mix it missed by dE 2.26 on night, because
# a composite toward ansi8 cannot raise lightness and drop chroma at once.
#
# `skill` HAS NO ANCESTOR IN THIS REPO, and that is the finding, not an
# omission on the way to one. Its hue is 199: Midori's mint is 171, its indigo
# 251, and nothing sits between. The watcher's header says the semantic colours
# came "from the site + tokentrail palette" -- sources this repo does not hold
# -- so the value arrived already mixed and the model can only approximate it.
# It is assigned the mint role here because teal is the family it belongs to,
# which moves Midori's own skill colour 28 degrees greener (dE 5.6 light / 4.5
# dark). THAT IS WHY THE MIDORI REPRODUCTION CHECK EXEMPTS IT BY NAME rather
# than the ceiling being raised to cover it: Midori's shipped file keeps its
# orphan, and only a language built fresh gets the mint-derived value.
TINT = {
    "merged": ("purple", 0.5300, 0.0770, 0.6780, 0.0580),
    "skill":  ("mint",   0.5000, 0.0370, 0.6660, 0.0300),
}


def ghostty(name):
    """Grounds, ink, selection and the 16 slots from a ghostty theme file."""
    txt = (ROOT / "ghostty" / "themes" / name).read_text()
    out = {}
    for key, k in (("background", "bg"), ("foreground", "fg"),
                   ("selection-background", "sel")):
        m = re.search(rf"^{key} = (#[0-9a-fA-F]{{6}})", txt, re.M)
        if m:
            out[k] = m.group(1).lower()
    for m in re.finditer(r"^palette = (\d+)=(#[0-9a-fA-F]{6})", txt, re.M):
        out[f"ansi{m.group(1)}"] = m.group(2).lower()
    return out


def palette(stem):
    doc = json.loads((ROOT / "themes" / f"{stem}.json").read_text())
    return doc.get("palette", {})


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def hexs(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(255 * x))) for x in c)


def mix(ground, ink, a):
    return tuple((1 - a) * g + a * i for g, i in zip(ground, ink))


def de(a, b):
    # ciede2000() in tools/colorspace.py takes HEX STRINGS, not Lab triples --
    # it converts internally. Passing it pre-converted Lab is the obvious
    # mistake and it raises rather than silently scoring nonsense, which is the
    # better of the two ways that could have gone.
    return cs.ciede2000(a, b)


def candidates(stem, mode, g):
    """Every named source a MIX may draw from, for one language and mode."""
    out = dict(g)
    for name, role in palette(stem).items():
        v = role.get(mode) if isinstance(role, dict) else role
        if isinstance(v, str) and v.startswith("#"):
            out[name] = v.lower()
    return out


# A surface is not always composited over the PAGE. A dark diff band sits over
# the code panel, a hover state over the resting state, a border over the
# chrome. Solving every mix against the ground alone left eight tokens above
# the fit ceiling -- worst dE 9.09, on `merged`, which is a muted purple that
# simply is not on the line between paper and any single purple role. So the
# base of the mix is searched too, over the neutral anchors a surface
# realistically sits on. It is NOT searched over all roles: that is 45x45x51
# per token, and more importantly a fit of one accent over another accent is a
# number rather than an explanation.
ANCHORS = ("bg", "fg", "ansi0", "ansi7", "ansi8", "ansi15")


def solve(target, ground, cand):
    """Best (base, source, alpha) whose composite reproduces target."""
    best = None
    for base in ANCHORS:
        if base not in cand:
            continue
        bv = rgb(cand[base])
        for name, v in cand.items():
            iv = rgb(v)
            for step in range(0, 51):
                a = step / 50
                d = de(hexs(mix(bv, iv, a)), target)
                if best is None or d < best[0]:
                    best = (d, base, name, a)
    return best


def build(stem, modes, fit_from=None, report=False):
    """fit_from: (stem, modes) to solve MIX tokens against -- Midori, always."""
    out, fits, washes, clipped, worst = {}, [], [], [], 0.0
    for mode, tname in modes.items():
        g = ghostty(tname)
        pal = palette(stem)
        ov = {}
        for token, src in SOURCE.items():
            kind = src[0]
            if kind == "ansi":
                ov[token] = g[f"ansi{src[1]}"]
            elif kind in ("fg", "bg", "sel"):
                ov[token] = g[kind]
            elif kind == "ansi15":
                ov[token] = g["ansi15"] if mode == "light" else g["bg"]
            elif kind == "role":
                ov[token] = pal[src[1]][mode]
            elif kind == "role2":
                ov[token] = pal[src[1] if mode == "light" else src[2]][mode]
            elif kind == "wash":
                fam, dl_l, c_l, dl_d, c_d = WASH[token]
                dl, c = (dl_l, c_l) if mode == "light" else (dl_d, c_d)
                gL = cs.hex_to_oklch(g["bg"])[0]
                # .light for both modes -- see WASH_SEED.
                hue = cs.hex_to_oklch(pal[WASH_SEED[fam]]["light"])[2]
                ov[token], kept = clip_wash(gL, dl, c, hue, g["fg"])
                if abs(kept - dl) > 1e-9:
                    clipped.append((mode, token, dl, kept,
                                    cs.contrast(g["fg"], ov[token])))
                washes.append((mode, token, fam, gL + kept, c, hue, ov[token]))
            elif kind == "tint":
                role, l_l, c_l, l_d, c_d = TINT[token]
                L, c = (l_l, c_l) if mode == "light" else (l_d, c_d)
                hue = cs.hex_to_oklch(pal[role][mode])[2]
                ov[token], _ = cs.oklch_to_hex_clamped(L, c, hue)
                washes.append((mode, token, role, L, c, hue, ov[token]))
            elif kind == "mix":
                fg_stem, fg_modes = fit_from
                fg = ghostty(fg_modes[mode])
                # A KeyError here would be a crash with no subject. The
                # reference is a file on disk and can be truncated, emptied or
                # regenerated against a newer binary, so say which file lacks
                # what rather than raising from inside a dict lookup.
                rpath = ROOT / "watcher" / f"midori-tokens-{mode}.json"
                refmap = json.loads(rpath.read_text())
                if token not in refmap:
                    raise SystemExit(
                        f"ABORT: {rpath.name} lacks {token!r}, which the model "
                        f"fits against it -- {len(refmap)} token(s) present")
                ref = refmap[token].lower()
                d, base, name, a = solve(ref, fg["bg"],
                                         candidates(fg_stem, mode, fg))
                fits.append((mode, token, ref, base, name, a, d))
                worst = max(worst, d)
                here = candidates(stem, mode, g)
                for needed in (base, name):
                    if needed not in here:
                        raise SystemExit(
                            f"ABORT: {token} ({mode}) fits {base}/{name}, and "
                            f"{stem} does not declare {needed}")
                ov[token] = hexs(mix(rgb(here[base]), rgb(here[name]), a))
        out[mode] = ov
    if report:
        print(f"{'mode':6} {'token':28} {'midori':9} {'base':8} "
              f"{'+ source':16} {'alpha':>6} {'dE':>6}")
        for mode, token, ref, base, name, a, d in fits:
            flag = "  <-- ABOVE THE FIT CEILING" if d > FIT_CEILING else ""
            print(f"{mode:6} {token:28} {ref:9} {base:8} {name:16} "
                  f"{a:6.2f} {d:6.2f}{flag}")
        print(f"\n{len(fits)} mix token(s) solved, worst dE {worst:.2f} "
              f"(ceiling {FIT_CEILING})")
    if report and washes:
        print(f"\n{'mode':6} {'token':20} {'L':>7} {'C':>7} {'hue':>7}  hex")
        for mode, token, fam, L, c, hue, v in washes:
            print(f"{mode:6} {token:20} {L:7.3f} {c:7.3f} {hue:7.1f}  {v}")
        print(f"{len(washes)} wash(es) built in OKLCh")
        if clipped:
            print(f"\n{len(clipped)} band(s) pulled back to clear "
                  f"{WASH_FLOOR}:1 text-on-band:")
            for mode, token, dl, kept, ratio in clipped:
                print(f"   {mode:6} {token:20} dL {dl:+.4f} -> {kept:+.4f}"
                      f"   {ratio:.2f}:1")
        else:
            print(f"no band needed pulling back; all clear "
                  f"{WASH_FLOOR}:1 text-on-band")
    if not fits:
        raise SystemExit("ABORT: 0 mix tokens solved -- the model fitted "
                         "nothing, so nothing was checked")
    want = 2 * (len(WASH) + len(TINT))
    if len(washes) != want:
        raise SystemExit(f"ABORT: {len(washes)} OKLCh token(s) built, expected "
                         f"{want} -- a band or tint was skipped")
    if worst > FIT_CEILING:
        raise SystemExit(
            f"ABORT: worst mix fit is dE {worst:.2f}, above {FIT_CEILING}. "
            f"A surface whose rule cannot be stated must not ship; run "
            f"--report to see which.")
    return out


MODES = {
    "midori": {"light": "midori-paper", "dark": "midori-night"},
    "lemonardo": {"light": "lemonardo-paintpot", "dark": "lemonardo-inkwell"},
}
TITLE = {"midori": "Midori", "lemonardo": "Lemonardo"}


# Tokens the model is NOT expected to reproduce, each with the reason. A name
# in here is a documented orphan, not a tolerance: see TINT for `skill`.
CHECK_EXEMPT = {
    "skill": "hue 199 has no ancestor in this repo (see TINT)",
}
CHECK_CEILING = 3.0  # dE; the light bands carry C <= 0.033, where OKLCh hue
# is ill-conditioned, so they land 1.1-2.6 off a hue that reproduces the night
# bands exactly. Raising this to cover `skill` instead would have hidden it.


def check():
    """Rebuild Midori from the model and diff it against the shipped map.

    This is the only test of the rules above that is not circular: the
    reference is watcher/midori-claude-theme.sh's own output, extracted to
    watcher/midori-tokens-*.json before any of this existed. If a rule is
    edited and Midori still comes back, the rule describes the design; if
    Midori moves, the rule is an invention that happens to fit.
    """
    # The DECOY coupling: watcher/midori-claude-theme.sh's header and
    # tests/test_patch_claude_binary.py both require these to equal palette 4.
    for token in ("suggestion", "permission"):
        if SOURCE.get(token) != ("ansi", 4):
            raise SystemExit(f"ABORT: {token} must be ANSI 4 -- the binary "
                             f"patch points the stock preset at palette 4 and "
                             f"tests/test_patch_claude_binary.py fails if they "
                             f"drift (watcher header, DECOY TOKENS)")

    built = build("midori", MODES["midori"], fit_from=("midori", MODES["midori"]))
    checked = exempt = bad = 0
    worst, worst_at = 0.0, None
    for mode in ("light", "dark"):
        ref = json.loads(
            (ROOT / "watcher" / f"midori-tokens-{mode}.json").read_text())
        missing = set(SOURCE) - set(ref)
        if missing:
            raise SystemExit(f"ABORT: {mode} reference lacks {sorted(missing)} "
                             f"-- the model names tokens the shipped map does "
                             f"not, so they were never checked")
        for token, want in ref.items():
            if token not in SOURCE:
                raise SystemExit(f"ABORT: the shipped map has {token!r} and the "
                                 f"model has no rule for it -- Lemonardo would "
                                 f"ship one token short")
            if token in CHECK_EXEMPT:
                exempt += 1
                continue
            checked += 1
            d = de(want.lower(), built[mode][token])
            if d > worst:
                worst, worst_at = d, f"{mode} {token} "\
                                      f"want {want} got {built[mode][token]}"
            if d > CHECK_CEILING:
                bad += 1
                print(f"  OFF  {mode:5} {token:28} want {want} "
                      f"got {built[mode][token]}  dE {d:.2f}")
    if checked == 0:
        raise SystemExit("ABORT: 0 tokens checked -- an empty reference proves "
                         "nothing")
    print(f"{checked} token(s) checked against the shipped Midori map, "
          f"{exempt} exempt by name, {bad} over dE {CHECK_CEILING}")
    print(f"worst: {worst_at} dE {worst:.2f}")
    for token, why in CHECK_EXEMPT.items():
        print(f"exempt: {token} -- {why}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="lemonardo", choices=sorted(MODES))
    ap.add_argument("--mode", choices=("light", "dark"))
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="rebuild Midori and diff it against the shipped map")
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.check:
        return check()

    built = build(a.theme, MODES[a.theme],
                  fit_from=("midori", MODES["midori"]), report=a.report)
    if a.report and not a.mode:
        return 0
    doc = {"name": TITLE[a.theme], "base": a.mode,
           "overrides": built[a.mode]}
    text = json.dumps(doc, indent=2) + "\n"
    if a.out:
        pathlib.Path(a.out).write_text(text)
        print(f"wrote {a.out} ({len(doc['overrides'])} overrides)")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
