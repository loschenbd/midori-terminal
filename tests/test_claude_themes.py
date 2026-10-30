#!/usr/bin/env python3
"""The four Claude Code token maps under watcher/themes/.

WHAT THIS EXISTS TO CATCH, in order of how badly it would hurt:

1. THE REFACTOR. watcher/midori-claude-theme.sh used to hold the two Midori
   maps as heredocs and now copies these files. Nothing proves that move was
   lossless except this test: watcher/midori-tokens-{light,dark}.json was
   extracted from those heredocs before they were deleted, and the Midori maps
   here must still equal it exactly -- not within a tolerance, exactly. If this
   ever fails, the live Claude Code UI has been restyled by accident.

2. A LANGUAGE SHORT A TOKEN. Claude Code's loader silently drops unknown keys
   and silently falls back to the stock preset for missing ones, so a map with
   47 of 48 tokens looks fine until someone opens the one pane that uses it.
   All four maps must carry the same token set.

3. THE DECOY COUPLING. `suggestion` and `permission` do nothing through these
   files -- Claude Code reads them from the stock preset -- and the binary
   patch points that preset at the terminal's ANSI 4 instead. The watcher's own
   header and tests/test_patch_claude_binary.py both require the value here to
   equal palette 4; this checks it per language and per mode, which neither of
   those does.

4. A BAND YOU CANNOT READ THROUGH. The diff bands sit under body text. The
   offsets were measured on Midori, whose ink clears its own bands by 6.13:1,
   and ported to Lemonardo, whose ink is lighter on a warmer page; the same
   offsets put its strongest band at 4.38:1 before tools/make-claude-theme.py
   clipped it. That clip is a rule in the generator, so this holds the result.

5. A MIDORI COLOUR LEFT IN A LEMONARDO MAP, the same check
   tests/test_lemonardo_twins.py makes of the other twins.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import colorspace as cs  # noqa: E402

THEMES = ROOT / "watcher" / "themes"
LANGS = {"midori": ("Midori", "midori-paper", "midori-night"),
         "lemonardo": ("Lemonardo", "lemonardo-paintpot", "lemonardo-inkwell")}
BANDS = ("diffAdded", "diffAddedDimmed", "diffAddedWord",
         "diffRemoved", "diffRemovedDimmed", "diffRemovedWord")
FLOOR = 4.5
fails = []


def fail(msg):
    fails.append(msg)
    print(f"  FAIL  {msg}")


def ghostty_palette4(theme):
    for ln in (ROOT / "ghostty" / "themes" / theme).read_text().splitlines():
        s = ln.strip()
        if s.startswith("palette") and "=" in s:
            parts = [p.strip() for p in s.split("=")]
            if len(parts) == 3 and parts[1] == "4":
                return parts[2].lower()
    return None


maps = {}
for lang, (title, lt, dt) in sorted(LANGS.items()):
    for mode in ("light", "dark"):
        p = THEMES / f"{lang}-{mode}.json"
        if not p.exists():
            fail(f"{p.name} does not exist -- {lang} has no {mode} map")
            continue
        try:
            doc = json.loads(p.read_text())
        except Exception as e:  # a map Claude Code cannot parse
            fail(f"{p.name} is not valid JSON: {e}")
            continue
        if doc.get("name") != title:
            fail(f"{p.name} name is {doc.get('name')!r}, expected {title!r}")
        if doc.get("base") != mode:
            fail(f"{p.name} base is {doc.get('base')!r}, expected {mode!r}")
        ov = doc.get("overrides") or {}
        if not ov:
            fail(f"{p.name} has no overrides -- an empty map is a stock theme")
            continue
        maps[(lang, mode)] = ov

if not maps:
    print("FAIL: no token maps read at all -- nothing was checked")
    sys.exit(1)

print(f"read {len(maps)} token map(s): "
      + ", ".join(f"{l}-{m} ({len(v)})" for (l, m), v in sorted(maps.items())))

# 1. The refactor.
frozen = 0
for mode in ("light", "dark"):
    ref_p = ROOT / "watcher" / f"midori-tokens-{mode}.json"
    if not ref_p.exists():
        fail(f"{ref_p.name} is missing -- the only evidence that removing the"
             f" heredocs did not restyle Claude Code")
        continue
    ref = json.loads(ref_p.read_text())
    got = maps.get(("midori", mode))
    if got is None:
        continue
    if got != ref:
        for k in sorted(set(ref) | set(got)):
            if ref.get(k) != got.get(k):
                fail(f"midori-{mode}: {k} is {got.get(k)} here and "
                     f"{ref.get(k)} in the frozen heredoc extraction")
    frozen += len(ref)
print(f"{frozen} Midori token(s) held byte-equal to the heredoc extraction")

# 2. One token set across every language.
sets = {k: set(v) for k, v in maps.items()}
base_key = ("midori", "light")
if base_key in sets:
    for k, s in sorted(sets.items()):
        for miss in sorted(sets[base_key] - s):
            fail(f"{k[0]}-{k[1]} is missing {miss!r} -- Claude Code would fall"
                 f" back to the stock preset for it")
        for extra in sorted(s - sets[base_key]):
            fail(f"{k[0]}-{k[1]} has {extra!r}, which midori-light does not")
print(f"{len(sets[base_key])} token(s) in the shared set")

# 3. The decoy coupling.
coupled = 0
for lang, (_, lt, dt) in sorted(LANGS.items()):
    for mode, theme in (("light", lt), ("dark", dt)):
        ov = maps.get((lang, mode))
        if ov is None:
            continue
        p4 = ghostty_palette4(theme)
        if p4 is None:
            fail(f"ghostty/themes/{theme} declares no palette = 4 -- the"
                 f" coupling cannot be checked, so treat it as broken")
            continue
        for token in ("suggestion", "permission"):
            if ov.get(token, "").lower() != p4:
                fail(f"{lang}-{mode}: {token} is {ov.get(token)} and "
                     f"{theme} palette 4 is {p4} -- the binary patch points "
                     f"the stock preset at palette 4 (see the watcher header, "
                     f"DECOY TOKENS, and tests/test_patch_claude_binary.py)")
            else:
                coupled += 1
print(f"{coupled} decoy token(s) equal to their theme's palette 4")

# 4. Text through every band.
checked = 0
worst = (99.0, None)
for (lang, mode), ov in sorted(maps.items()):
    ink = ov.get("text")
    if not ink:
        fail(f"{lang}-{mode} has no `text` token -- band legibility is "
             f"unmeasurable, so it is unproven")
        continue
    for band in BANDS:
        if band not in ov:
            continue  # already reported by the token-set check
        r = cs.contrast(ink, ov[band])
        checked += 1
        if r < worst[0]:
            worst = (r, f"{lang}-{mode} {band}")
        if r < FLOOR:
            fail(f"{lang}-{mode}: text {ink} on {band} {ov[band]} is "
                 f"{r:.2f}:1, under {FLOOR}:1 -- tools/make-claude-theme.py "
                 f"clips a band to this floor, so this means the clip is gone")
print(f"{checked} band(s) measured; worst {worst[1]} at {worst[0]:.2f}:1 "
      f"(floor {FLOOR}:1)")

# 5. No Midori colour inside a Lemonardo map.
mid = {v.lower() for mode in ("light", "dark")
       for v in maps.get(("midori", mode), {}).values()}
lem = {v.lower() for mode in ("light", "dark")
       for v in maps.get(("lemonardo", mode), {}).values()}
if not mid or not lem:
    fail("one language's colours came back empty -- the overlap check compared"
         " against nothing")
else:
    shared = mid & lem
    if shared:
        fail(f"Lemonardo's maps reuse Midori colour(s): {sorted(shared)}")
    print(f"{len(lem)} Lemonardo colour(s), none of Midori's {len(mid)}")

# 6. The watcher's launchd contract.
#
# This lives here rather than in a file of its own because it is the same
# delivery path: these maps only reach ~/.claude/themes if the job that copies
# them actually starts. Two ways it silently does not.
#
# A PLIST THAT DOES NOT PARSE. The template grew a comment explaining the log
# paths, that comment used "--" as a dash, and XML forbids "--" inside a
# comment -- so the file stopped being a plist. launchd would have refused it
# with a message about the file, not about the prose in it.
#
# LOG PATHS UNDER /tmp. /tmp is shared between accounts on a Mac. launchd
# creates the stdout/stderr file as whichever account starts the job first,
# mode 644, and a second account's job then cannot open it -- so launchd fails
# the SPAWN, before the script runs, with `last exit code = 78: EX_CONFIG` and
# an empty log, because the unwritable thing IS the log. On this machine that
# ran up runs = 6304 against files another account had owned since 7 Oct,
# while `launchctl list` showed the job present the whole time. A loaded job is
# not a running one.
import plistlib  # noqa: E402
import re  # noqa: E402

tpl = ROOT / "watcher" / "com.benjaminloschen.midori-claude-theme.plist.template"
if not tpl.exists():
    fail(f"{tpl.name} is missing -- the watcher has no launchd definition")
else:
    raw = tpl.read_text()
    rendered = raw.replace("__HOME__", "/Users/test").replace("__LANG__", "midori")
    try:
        d = plistlib.loads(rendered.encode())
    except Exception as e:
        d = None
        fail(f"{tpl.name} does not parse as a plist after substitution: {e}"
             + ('  (an XML comment may contain "--")'
                if any("--" in m for m in re.findall(r"<!--(.*?)-->", raw, re.S))
                else ""))
    if d is not None:
        for key in ("StandardOutPath", "StandardErrorPath"):
            v = d.get(key, "")
            if not v:
                fail(f"{tpl.name}: {key} is unset")
            elif v.startswith("/tmp/"):
                fail(f"{tpl.name}: {key} is {v} -- /tmp is shared between "
                     f"accounts, so the first account to start this job owns "
                     f"the file and every other account's job dies at spawn "
                     f"with EX_CONFIG (78) and an empty log")
            elif not v.startswith("/Users/test/"):
                fail(f"{tpl.name}: {key} is {v}, which is not per-user")
        env = d.get("EnvironmentVariables") or {}
        if env.get("MIDORI_LANG") != "midori":
            fail(f"{tpl.name}: MIDORI_LANG renders as "
                 f"{env.get('MIDORI_LANG')!r} -- install.sh substitutes "
                 f"__LANG__, and without it launchd runs the watcher's own "
                 f"midori default whatever the installer was told")
        print(f"launchd template parses; logs per-user "
              f"({d.get('StandardOutPath')}), MIDORI_LANG substitutes")

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
