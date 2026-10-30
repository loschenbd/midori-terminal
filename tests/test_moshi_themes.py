#!/usr/bin/env python3
"""The committed Moshi themes must still match the Ghostty themes they derive
from — and every artifact that embeds their values must match too.

This is a DRIFT guard, not a unit test of the generator: it re-derives in
memory and compares against what is on disk. It deliberately writes nothing,
so it is safe in lint/CI and cannot touch iCloud.

The failure it exists to catch: someone edits ghostty/themes/midori-* and
doesn't re-run moshi/build-moshi-themes.py. Everything still opens and still
imports a theme — just the previous one.
"""
import base64
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MOSHI = REPO / "moshi"

spec = importlib.util.spec_from_file_location(
    "build_moshi_themes", MOSHI / "build-moshi-themes.py"
)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

FAIL = 0


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    global FAIL
    print(f"  FAIL {msg}")
    FAIL = 1


def main():
    print("== moshi themes match the ghostty source ==")
    built = {}
    # gen.THEMES became gen.SETS when a second design language arrived: each set
    # has its own themes, its own fonts and its own folder on the phone. Flatten
    # back to (slug, name, mode) here so this test covers EVERY set rather than
    # the first one -- a loop over one set would have gone green while the other
    # set's JSON drifted.
    for slug, name, mode in [t for spec in gen.SETS.values() for t in spec["themes"]]:
        want = gen.build(slug, name, mode)
        built[slug] = want

        path = MOSHI / f"{slug}.json"
        got = json.loads(path.read_text())
        if got == want:
            ok(f"{path.name} matches {slug}")
        else:
            diff = [k for k in want["colors"] if got.get("colors", {}).get(k) != want["colors"][k]]
            bad(f"{path.name} is stale (differs at: {', '.join(diff) or 'top level'}) "
                f"— re-run moshi/build-moshi-themes.py")

        # The non-colour cursor (cell-background; formerly a background-hex
        # sentinel) must not survive into a Moshi theme. Assert on the
        # SOURCE as well as the output: checking only the output is vacuous,
        # since the generator always substitutes. This way, deleting the
        # substitution fails the test, and Ghostty moving to a real colour tells
        # us the substitution is no longer needed rather than silently passing.
        _, named = gen.parse_ghostty(gen.GHOSTTY / slug)
        src_cursor, src_bg = named.get("cursor-color"), named["background"]
        out_cursor, out_bg = want["colors"]["cursor"], want["colors"]["background"]
        if not (src_cursor == src_bg or (src_cursor or "").startswith("cell-")):
            bad(f"{slug}: ghostty's cursor-color is now a real colour ({src_cursor}); "
                f"the substitution in the generator may be obsolete")
        elif out_cursor == out_bg or out_cursor.startswith("cell-"):
            bad(f"{slug}: sentinel leaked through — the ported cursor is invisible")
        elif out_cursor != want["colors"]["blue"]:
            bad(f"{slug}: cursor is {out_cursor}, expected the indigo ink "
                f"{want['colors']['blue']} the shader draws")
        else:
            ok(f"{slug} non-colour cursor ({src_cursor}) replaced with the indigo ink ({out_cursor})")

        url = (MOSHI / f"{slug}.url").read_text().strip()
        if url == gen.deep_link(want):
            ok(f"{slug}.url matches the theme")
        else:
            bad(f"{slug}.url is stale — re-run moshi/build-moshi-themes.py")

    # ONE import PAGE PER SET, so this loops the sets. The page used to be a
    # single moshi/import.html; with a second design language there is one per
    # set and a test that read only the old filename would have crashed (it did)
    # or, worse, passed while a set's page went stale.
    print("== each set's import page carries the current payloads ==")
    pages = 0
    for set_id, spec in sorted(gen.SETS.items()):
        page = MOSHI / f"import-{set_id}.html"
        if not page.exists():
            bad(f"import-{set_id}.html is missing — re-run moshi/build-moshi-themes.py")
            continue
        pages += 1
        html = page.read_text()
        links = re.findall(r"moshi://theme\?d=([A-Za-z0-9+/]+)", html)
        if len(links) == len(spec["themes"]):
            ok(f"import-{set_id}.html: {len(links)} deep link(s) present")
        else:
            bad(f"import-{set_id}.html: expected {len(spec['themes'])} deep links, "
                f"found {len(links)}")

        decoded = []
        for b in links:
            try:
                decoded.append(json.loads(base64.b64decode(b + "=" * (-len(b) % 4))))
            except Exception as e:                              # noqa: BLE001
                bad(f"a deep link in import-{set_id}.html does not decode: {e}")
        for theme in decoded:
            slug = next((sl for sl, t in built.items()
                         if t["name"] == theme["name"]), None)
            if slug is None:
                bad(f"import-{set_id}.html carries an unknown theme: "
                    f"{theme.get('name')!r}")
            elif theme == built[slug]:
                ok(f"import-{set_id}.html payload for {theme['name']} is current")
            else:
                bad(f"import-{set_id}.html payload for {theme['name']} is STALE — "
                    f"the page still imports the previous palette")

    # Fail on an empty input set. A drift check that examined no themes is this
    # repo's documented failure mode, not a pass.
    total = sum(len(spec["themes"]) for spec in gen.SETS.values())
    if total == 0 or pages == 0:
        bad(f"examined {total} theme(s) across {pages} page(s) — nothing was checked")
    print(f"\nmoshi drift check: {'all green' if not FAIL else 'failures above'} "
          f"({total} themes across {len(gen.SETS)} set(s), {pages} import page(s))")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
