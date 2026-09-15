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
    for slug, name, mode in gen.THEMES:
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

    print("== import.html carries the current payloads ==")
    html = (MOSHI / "import.html").read_text()
    links = re.findall(r"moshi://theme\?d=([A-Za-z0-9+/]+)", html)
    if len(links) == len(gen.THEMES):
        ok(f"{len(links)} deep links present")
    else:
        bad(f"expected {len(gen.THEMES)} deep links, found {len(links)}")

    decoded = []
    for b in links:
        try:
            decoded.append(json.loads(base64.b64decode(b + "=" * (-len(b) % 4))))
        except Exception as e:                                  # noqa: BLE001
            bad(f"a deep link in import.html does not decode: {e}")
    for theme in decoded:
        slug = next((s for s, t in built.items() if t["name"] == theme["name"]), None)
        if slug is None:
            bad(f"import.html carries an unknown theme: {theme.get('name')!r}")
        elif theme == built[slug]:
            ok(f"import.html payload for {theme['name']} is current")
        else:
            bad(f"import.html payload for {theme['name']} is STALE — the page still "
                f"imports the previous palette")

    total = sum(1 for _ in gen.THEMES)
    print(f"\nmoshi drift check: {'all green' if not FAIL else 'failures above'} "
          f"({total} themes)")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
