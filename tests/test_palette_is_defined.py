#!/usr/bin/env python3
"""Every colour used across 4+ files must be declared -- in palette.json
or in the themes/*.json a target's palette block is generated from.

THE DRIFT THIS CATCHES IS SILENT BY CONSTRUCTION. Sage is hand-copied into 18
files across seven targets and nothing links the copies. Change one and the
others keep the old value, looking correct in isolation; the only symptom is
that two apps stop matching, which nobody notices until they are side by side.
Measured before this guard existed: 40 values sat within 8/255 per channel of
a core colour without equalling it, 9 of them within 3/255 -- invisible, so a
stale copy or a typo rather than a design choice.

Threshold is 4+ files, matching tests/measure_palette_drift.py. Below it a hex
is one target's local shade; at or above it the value is being hand-copied
between targets and needs a home.

This does NOT check that the copies agree with palette.json -- only that the
value is declared. Reconciling copies to a single source is a later item.
"""
import collections
import json
import pathlib
import re
import subprocess
import sys

SKIP_SUFFIX = (".ttf", ".woff2", ".png", ".pdf", ".vsix", ".ico")
# Files that QUOTE colours in order to discuss them. Counting the write-up
# inflates every value by one and lists the write-up as a usage site.
SKIP_FILES = {"docs/cleanup-queue.md", "palette.json",
              "tests/measure_palette_drift.py",
              "docs/superpowers/specs/2026-08-19-palette-generation-scope.md",
              "t3/README.md",
              # Quotes colours to check colour arithmetic against published
              # CIEDE2000 and WCAG values. Counting a test fixture as a usage
              # site pushed four pigment reference hexes over the threshold
              # and demanded that #ff4000 have a palette role, which it must
              # not: it is a citation, not a colour this repo ships.
              "tools/colorspace.py",
              # SAME REASON AS colorspace.py, and it is a GENERATOR besides.
              # It names #ffffff and #000000 as the WCAG reference white and
              # black that every contrast() call measures against, and as the
              # two lamps the material layer's alphas are solved for. Neither
              # is a colour this repo ships. Counting it pushed #ffffff from
              # three files to four and demanded a palette role for white.
              # Its own Lemonardo values are not lost by skipping it: they are
              # declared in themes/lemonardo.json, and `make-lemonardo-palette
              # .py --check` (in lint) holds the generated CSS to them.
              "vivaldi/make-lemonardo-palette.py",
              # Quotes one tmux line verbatim in a docstring, to explain a
              # filter bug that hid exactly that line from the guard. Counting
              # a write-up as a usage site is what SKIP_FILES is for, and this
              # one pushed #44484e from three files to four.
              "tests/test_lemonardo_twins.py",
              # A FROZEN COPY, not a usage site. watcher/midori-tokens-*.json
              # was extracted from the two heredocs that used to live in
              # watcher/midori-claude-theme.sh, and exists for one purpose:
              # tests/test_claude_themes.py holds watcher/themes/midori-*.json
              # byte-equal to it, which is the only evidence that moving the
              # maps out of the watcher did not restyle Claude Code. Every
              # value in it also appears in the live map beside it, so counting
              # both doubled three Midori mix colours (#2c2b26, #e4e0d6,
              # #ebe8e0) from three files to four and demanded palette roles
              # for values that are derived, not declared.
              "watcher/midori-tokens-light.json",
              "watcher/midori-tokens-dark.json",
              # Quotes the Lemonardo Paintpot accent and the value a
              # SCREENSHOT of it reads back as, to record that
              # Page.captureScreenshot does not return sRGB. Both are
              # citations: the accent's home is themes/lemonardo.json and
              # vivaldi/themes.json, and #d6882c is not a colour this repo
              # ships at all -- it is what a display did to one that it does.
              # Counting the write-up pushed #dc931e from three files to five
              # and #ffffff from three to four.
              "tests/check_vivaldi_tab_material.py",
              # Same reason, one level up: CLAUDE.md states the screenshot
              # finding with its two measured hexes so the next person does
              # not re-derive it, and was promptly listed as a usage site for
              # the accent.
              "CLAUDE.md",
              # AND THIS FILE ITSELF, which it did not do until the comment
              # above named those three hexes and promptly became their fourth
              # usage site -- the same failure, with the same three values,
              # reported one run later against the explanation for it. Every
              # entry in SKIP_FILES is a file that quotes colours in order to
              # discuss them, and the list is now one of those files.
              "tests/test_palette_is_defined.py"}
# Directories that DEFINE colours rather than use them. themes/*.json is the
# source a target's palette block is generated FROM, so counting it as a usage
# site double-counts every value: adding themes/midori.json alone pushed seven
# colours from three files to four and tripped SHARED_AT, while nothing about
# how the repo actually uses them had changed.
# This is the same reason palette.json is skipped above, one level stronger:
# palette.json mirrors the values, themes/ declares them.
SKIP_PREFIX = ("themes/",)
SHARED_AT = 4

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAIL = False


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global FAIL
    print(f"  FAIL {msg}")
    FAIL = True


def used_hexes(root):
    # --others --exclude-standard so a file that is NEW but not yet committed
    # counts. Plain `ls-files` sees only tracked paths, which meant lint went
    # green on the very commit that introduced a violation and failed on the
    # NEXT one -- the new file was invisible while it was still untracked.
    # That is exactly how docs/superpowers/specs/2026-08-19-palette-generation
    # -scope.md pushed two values over the threshold unnoticed. gitignored
    # scratch stays excluded, so this widens the scan without dragging in
    # build output.
    files = subprocess.run(["git", "-C", str(root), "ls-files",
                            "--cached", "--others", "--exclude-standard"],
                           capture_output=True, text=True).stdout.split()
    out = collections.defaultdict(set)
    for f in files:
        if (f.endswith(SKIP_SUFFIX) or f in SKIP_FILES
                or f.startswith(SKIP_PREFIX)):
            continue
        try:
            text = (root / f).read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for h in re.findall(r"#[0-9a-fA-F]{6}\b", text):
            out[h.lower()].add(f)
    return out


def declared(root):
    """Every place a colour can legitimately HAVE A HOME.

    palette.json was the only one when Midori was the only design language.
    Lemonardo's values live in themes/lemonardo.json, which is the file its
    palette blocks are GENERATED from -- a stronger definition than
    palette.json's mirror, not a weaker one. Reading only palette.json made
    this test demand that Lemonardo's card (#fbf8f0) be hand-copied into a
    file whose own header reads "The Midori palette": a second, unlinked copy
    of a generated value, which is precisely the drift this test exists to
    catch. So themes/*.json counts as a declaration site.

    Note the asymmetry with SKIP_PREFIX above, which is deliberate and is the
    same fact twice: themes/ does not count as a USAGE site (it would
    double-count every value) and does count as a DECLARATION site.
    """
    out, sites = {}, []

    path = root / "palette.json"
    if not path.exists():
        bad("palette.json is missing -- the palette has no definition")
        return None
    doc = json.loads(path.read_text())
    for name, role in doc.get("roles", {}).items():
        for mode, value in role.items():
            if mode == "source":
                continue
            out.setdefault(value.lower(), []).append(f"palette:{name}.{mode}")
    sites.append(f"palette.json ({len(doc.get('roles', {}))} roles)")

    # The Lemonardo ANSI palette is not stored anywhere -- it is DERIVED, by
    # tools/make-lemonardo-ansi.py, from pigment hues and a handful of rules.
    # So the generator is the declaration site for both halves of it: the
    # reference hexes its anchor table names (with a source and a strength per
    # entry, which is more provenance than palette.json carries) and the 32
    # slots those rules produce. Asking a human to copy either into
    # palette.json would create exactly the unlinked second copy this test
    # exists to detect.
    gen_path = root / "tools" / "make-lemonardo-ansi.py"
    if gen_path.exists():
        import importlib.util
        gspec = importlib.util.spec_from_file_location("mla", gen_path)
        gen = importlib.util.module_from_spec(gspec)
        gspec.loader.exec_module(gen)
        n_anchor = 0
        for fam, entry in list(gen.ANCHORS.items()) + [
                ("selection", gen.SELECTION_ANCHOR)]:
            out.setdefault(entry[0].lower(), []).append(f"anchor:{fam}")
            n_anchor += 1
        theme = json.loads((root / "themes" / "lemonardo.json").read_text())
        n_slot = 0
        for mode_id in sorted(gen.MODES):
            built = gen.build(mode_id, theme)
            for slot, value in built["slots"].items():
                out.setdefault(value.lower(), []).append(
                    f"{built['id']}:{slot}")
                n_slot += 1
            # divider and split_fill joined this list on 2026-10-11, when
            # herdr and tmux started painting with the divider tone and it
            # crossed the 4-file threshold while being declared nowhere. They
            # were derived inside the generator's emit() rather than build(),
            # so this reader could not see them; the generator now returns them.
            for key in ("bg", "fg", "selection", "divider", "split_fill"):
                out.setdefault(built[key].lower(), []).append(
                    f"{built['id']}:{key}")
        if n_anchor == 0 or n_slot == 0:
            bad("the lemonardo ANSI generator declared 0 anchors or 0 slots "
                "-- it was imported but produced nothing")
        sites.append(f"make-lemonardo-ansi.py ({n_anchor} anchors, "
                     f"{n_slot} derived slots)")

    for tpath in sorted((root / "themes").glob("*.json")):
        tdoc = json.loads(tpath.read_text())
        pal = tdoc.get("palette", {})
        for name, role in pal.items():
            # A role is EITHER a {light, dark} map or a single hex: page-dot is
            # one value in both modes by design, so it is stored as a bare
            # string. Assuming the map shape crashed here on exactly that role.
            modes = role.items() if isinstance(role, dict) else [(None, role)]
            for mode, value in modes:
                if not (isinstance(value, str) and value.startswith("#")):
                    continue
                label = name if mode is None else f"{name}.{mode}"
                out.setdefault(value.lower(), []).append(
                    f"{tpath.stem}:{label}")
        sites.append(f"{tpath.name} ({len(pal)} roles)")

    # A declaration reader that found no files reads as "nothing is missing".
    if not sites or not out:
        bad("no declaration site yielded any colour -- the reader is broken")
        return None
    ok("declaration sites: " + ", ".join(sites))
    return out


def main():
    hf = used_hexes(ROOT)
    if not hf:
        # A GUARD THAT SCANNED NOTHING LOOKS EXACTLY LIKE A GUARD THAT PASSED.
        bad("found 0 hex values in the whole repo -- the collector is broken, "
            "not the repo")
        print("palette: failures above")
        sys.exit(1)

    shared = {h: fs for h, fs in hf.items() if len(fs) >= SHARED_AT}
    ok(f"scanned {len({f for v in hf.values() for f in v})} files, "
       f"{len(hf)} distinct colours, {len(shared)} used in {SHARED_AT}+")

    have = declared(ROOT)
    if have is None:
        print("palette: failures above")
        sys.exit(1)
    if not have:
        bad("palette.json declares no colours at all")
        print("palette: failures above")
        sys.exit(1)
    ok(f"{len(have)} distinct colours declared across those sites")

    missing = sorted(h for h in shared if h not in have)
    for h in missing:
        where = sorted(shared[h])
        bad(f"{h} is used in {len(where)} files but is declared nowhere "
            f"({', '.join(where[:3])}{'...' if len(where) > 3 else ''})")
    if not missing:
        ok(f"all {len(shared)} shared colours are declared")

    print("palette: all green" if not FAIL else "palette: failures above")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
