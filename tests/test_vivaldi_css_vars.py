#!/usr/bin/env python3
"""The Vivaldi UI mods now serve two design languages through variables.

WHY THIS FILE EXISTS. The mods under vivaldi/css-mods/ used to hardcode Midori's
colours and faces. They now declare them as --mcal-/--mmail-/--msurf-/--mstack-/
--mfont-/--msite- variables and reference those, and vivaldi/css-mods/lemonardo-palette.css
restates every one for the two Lemonardo themes. That buys one set of selectors
for both languages, and it buys exactly one new failure mode:

A VARIABLE THE MODS USE AND A PALETTE DOES NOT DECLARE. An undeclared custom
property is not an error in CSS. `color: var(--mmail-ink)` with no --mmail-ink
in scope makes the whole declaration invalid at computed-value time, so the
property falls back to its inherited or initial value and the text simply
renders in Vivaldi's own colour. Nothing logs, nothing throws, and the surface
looks approximately right -- a muted grey where a muted warm was intended. One
typo in one of 60-odd names is invisible until someone opens that pane in that
mode. So: collect every variable the mods REFERENCE, and require all four
scopes (Midori light, Midori dark, Lemonardo light, Lemonardo dark) to declare
it.

AND A SPECIFICITY TIE, which this repo has shipped before: a guard passed while
the rule it named lost a specificity contest and did nothing. Midori's defaults
sit on `#browser.theme-light` (one id, one class). Lemonardo's overrides must
OUTRANK that, not tie it -- a tie is settled by the order Vivaldi reads a
directory in, which is not a design decision. Check 3 computes both
specificities and requires Lemonardo's to be strictly greater.

AND AN ORPHANED PALETTE. The Lemonardo selectors name theme UUIDs. If an id in
vivaldi/themes.json is ever regenerated, the palette file still parses, still
loads, and matches nothing at all. Check 2 ties the two files together.

WHAT THIS CANNOT SEE. Whether the values look right -- that needs Vivaldi
running, and Vivaldi must be CLOSED to install into it, so there is no
rendered check here by construction. It also cannot see a variable declared in
all four scopes but used in the wrong role; the derivation comments in
lemonardo-palette.css are the record for that.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODS = ROOT / "vivaldi" / "css-mods"
LEM_FILE = MODS / "lemonardo-palette.css"
THEMES = ROOT / "vivaldi" / "themes.json"

# Only OUR variables. --colorBg*, --stackColorBg and --stackBgAlpha are
# Vivaldi's own and are declared by Vivaldi, not by anything in this directory.
OURS = re.compile(r"--m(?:cal|mail|surf|stack|font|site)-[a-z0-9-]+")
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")

FAIL = 0


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global FAIL
    print(f"  FAIL {msg}")
    FAIL = 1


def blocks(text):
    """(selector, body) for every top-level rule, comments stripped first.

    Comments are stripped BEFORE parsing because this file's own prose names
    variables (--mmail-label-dijon, --m-sage-soft) and a reader that counted
    those would find declarations that do not exist and pass a palette that is
    actually short a value.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.findall(r"([^{}]+)\{([^{}]*)\}", text)


def specificity(sel):
    """(ids, classes, elements) for a single compound selector."""
    sel = re.sub(r"::[a-z-]+", " ", sel)            # pseudo-ELEMENTS: not classes
    ids = len(re.findall(r"#[\w-]+", sel))
    classes = (len(re.findall(r"\.[\w-]+", sel))
               + len(re.findall(r"\[[^\]]*\]", sel))
               + len(re.findall(r":(?!:)[a-z-]+", sel)))
    elements = len(re.findall(r"(?:^|[\s>+~])([a-z][\w-]*)", sel))
    return (ids, classes, elements)


def main():
    if not MODS.is_dir():
        bad(f"{MODS} is not a directory")
        return 1
    files = sorted(MODS.glob("*.css"))
    if not files:
        bad("no .css files in vivaldi/css-mods -- the glob matched nothing, "
            "so every check below would pass against an empty input set")
        return 1
    if not LEM_FILE.exists():
        bad("vivaldi/css-mods/lemonardo-palette.css is missing")
        return 1

    # ---- gather references and declarations -------------------------------
    referenced = {}          # var -> set(files that use it)
    declared = {}            # scope -> set(vars)
    scopes_seen = {}         # scope -> selector text
    for p in files:
        text = p.read_text()
        body_only = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        for v in OURS.findall(" ".join(re.findall(r"var\(\s*(--[\w-]+)", body_only))):
            referenced.setdefault(v, set()).add(p.name)
        for sel, body in blocks(text):
            sel = " ".join(sel.split())
            # A declaration is `--x:` at the start of a statement; a
            # reference is inside var(). Strip the var() calls first, so a
            # rule that only USES a variable is never counted as declaring it.
            stmt = re.sub(r"var\([^)]*\)", "", body)
            names = set(OURS.findall(" ".join(
                re.findall(r"(--m(?:cal|mail|surf|stack|font|site)-[a-z0-9-]+)\s*:", stmt))))
            if not names:
                continue
            declared.setdefault(sel, set()).update(names)
            scopes_seen[sel] = sel

    if not referenced:
        bad("no --m* variable is referenced anywhere -- the reader is broken, "
            "not the files")
        return 1

    # A variable that does not vary by mode is declared ONCE, on the bare
    # #browser, rather than copied into both mode blocks -- the font faces are
    # like this. So a language satisfies a variable either from its
    # mode-independent scope or from BOTH of its mode scopes. Requiring all
    # four mode scopes unconditionally was this checker's first version, and it
    # failed the three --mfont-* names that were correctly declared once.
    mid_base = declared.get("#browser", set())
    mid_scopes = {s: v for s, v in declared.items()
                  if re.fullmatch(r"#browser\.theme-(light|dark)", s)}
    lem_scopes = {s: v for s, v in declared.items() if "theme-id-" in s}
    if len(mid_scopes) != 2:
        bad(f"expected 2 Midori default scopes (#browser.theme-light and "
            f"-dark), found {len(mid_scopes)}: {sorted(mid_scopes)}")
        return 1
    if len(lem_scopes) != 2:
        bad(f"expected 2 Lemonardo scopes, found {len(lem_scopes)}: "
            f"{sorted(lem_scopes)}")
        return 1
    ok(f"{len(files)} css mod(s); {len(referenced)} variable(s) referenced; "
       f"4 declaring scopes ({len(mid_scopes)} Midori, {len(lem_scopes)} Lemonardo)")

    # ---- 1. every reference is declared in all four scopes ----------------
    missing = []
    per_mode = both = 0
    for var, users in sorted(referenced.items()):
        mid_ok = var in mid_base or all(var in n for n in mid_scopes.values())
        lem_ok = all(var in n for n in lem_scopes.values())
        if var in mid_base:
            both += 1
        else:
            per_mode += 1
        for lang, good in (("midori", mid_ok), ("lemonardo", lem_ok)):
            if not good:
                missing.append((var, lang, sorted(users)))
    if missing:
        for var, lang, users in missing[:20]:
            bad(f"{var} is used by {', '.join(users)} but {lang} declares it "
                f"in neither its mode-independent scope nor both of its mode "
                f"scopes -- that pane renders in Vivaldi's colour, silently")
        if len(missing) > 20:
            bad(f"... and {len(missing) - 20} more")
    else:
        ok(f"all {len(referenced)} referenced variable(s) resolve in both "
           f"languages ({per_mode} declared per mode, {both} mode-independent)")

    # ---- 2. the Lemonardo selectors name ids themes.json actually has -----
    pkg = json.loads(THEMES.read_text())
    real_ids = {t["id"]: t["name"] for t in pkg["themes"]}
    lem_ids = {t["id"] for t in pkg["themes"] if t["name"].startswith("Lemonardo")}
    css_ids = set(re.findall(r"theme-id-([0-9a-f-]{36})", LEM_FILE.read_text()))
    if not css_ids:
        bad("lemonardo-palette.css names no theme id at all")
    elif css_ids != lem_ids:
        bad(f"palette targets {sorted(css_ids)} but themes.json's Lemonardo "
            f"themes are {sorted(lem_ids)} -- the palette matches nothing")
    else:
        ok(f"palette targets exactly the {len(lem_ids)} Lemonardo theme id(s) "
           f"in themes.json: {sorted(real_ids[i] for i in lem_ids)}")

    # ---- 3. Lemonardo must OUTRANK the Midori defaults, not tie them ------
    worst_mid = max(specificity(s) for s in mid_scopes)
    ties = []
    for sel in lem_scopes:
        spec = specificity(sel)
        if spec <= worst_mid:
            ties.append((sel, spec))
    if ties:
        for sel, spec in ties:
            bad(f"{sel} has specificity {spec}, which does not beat the Midori "
                f"default's {worst_mid} -- load order would decide, so this "
                f"override may do nothing")
    else:
        ok(f"every Lemonardo scope outranks the Midori default "
           f"({[specificity(s) for s in lem_scopes][0]} > {worst_mid})")

    # ---- 4. no Midori-only colour left in the Lemonardo palette -----------
    def palette_hexes(stem):
        d = json.loads((ROOT / "themes" / f"{stem}.json").read_text())
        out = {h.lower() for h in HEX.findall(json.dumps(d["palette"]))}
        for t in (ROOT / "ghostty" / "themes").glob(f"{stem}-*"):
            out |= {h.lower() for h in HEX.findall(t.read_text())}
        return out

    mid_hex, lem_hex = palette_hexes("midori"), palette_hexes("lemonardo")
    if not mid_hex or not lem_hex:
        bad(f"read {len(mid_hex)} Midori and {len(lem_hex)} Lemonardo colours "
            f"-- the palette reader is broken")
    else:
        midori_only = mid_hex - lem_hex
        live = "\n".join(l for l in LEM_FILE.read_text().splitlines()
                         if not l.lstrip().startswith(("/*", "*", "//")))
        found = {h.lower() for h in HEX.findall(live)}
        leaked = sorted(h for h in found if h in midori_only)
        if leaked:
            bad(f"lemonardo-palette.css carries Midori-only colour(s) "
                f"{', '.join(leaked)} -- a value was missed")
        else:
            ok(f"lemonardo-palette.css: {len(found)} hex(es), none of the "
               f"{len(midori_only)} Midori-only colours")

    # ---- 5. themes.json: schedule points at themes that exist -------------
    langs = {k: v for k, v in pkg["scheduleOS"].items() if not k.startswith("_")}
    if not langs:
        bad("themes.json scheduleOS names no language")
    else:
        for lang, pair in sorted(langs.items()):
            unknown = [i for i in pair.values() if i not in real_ids]
            if sorted(pair) != ["dark", "light"]:
                bad(f"scheduleOS[{lang}] has keys {sorted(pair)}, want light+dark")
            elif unknown:
                bad(f"scheduleOS[{lang}] names unknown theme id(s) {unknown}")
            else:
                ok(f"scheduleOS[{lang}] -> "
                   f"{real_ids[pair['light']]} / {real_ids[pair['dark']]}")
        ok(f"{len(pkg['themes'])} theme(s) defined, {len(langs)} language(s) scheduled")

    print("vivaldi css vars: all green" if not FAIL
          else "vivaldi css vars: failures above")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
