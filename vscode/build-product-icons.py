#!/usr/bin/env python3
"""Generate the Midori product-icon theme (workbench chrome icons).

Product icon themes replace VS Code's codicons (activity bar, tree chevrons,
toolbars) and require an icon FONT, not SVGs. This script fetches Phosphor
regular-weight SVGs (MIT) — the same weight the Vivaldi start-page mod uses —
saves them named after the codicon ids they override, runs fantasticon (via
npx) to build a woff, and writes the product-icon-theme JSON with the
generated codepoints. Unmapped codicons fall back to the stock font.

Run from anywhere:  python3 vscode/build-product-icons.py
Then repackage/reinstall via install-vscode.sh.
"""

import json
import pathlib
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "midori-theme" / "product-icons"
CACHE = ROOT / ".icon-cache"
FONT_NAME = "midori-product"

# codicon id to override -> phosphor regular icon
ICONS = {
    # activity bar / views
    "files": "files",
    "search": "magnifying-glass",
    "source-control": "git-branch",
    "debug-alt": "bug",
    "extensions": "puzzle-piece",
    "settings-gear": "gear",
    "gear": "gear",
    "account": "user-circle",
    "remote": "plugs",
    "terminal": "terminal-window",
    # tree + editor chrome
    "chevron-right": "caret-right",
    "chevron-down": "caret-down",
    "chevron-left": "caret-left",
    "chevron-up": "caret-up",
    "close": "x",
    "add": "plus",
    "ellipsis": "dots-three",
    "refresh": "arrow-clockwise",
    "sync": "arrows-clockwise",
    "trash": "trash",
    "edit": "pencil-simple",
    "copy": "copy",
    "filter": "funnel",
    "link": "link",
    "globe": "globe",
    "home": "house",
    "history": "clock-counter-clockwise",
    "bookmark": "bookmark-simple",
    "folder": "folder",
    "folder-opened": "folder-open",
    "new-file": "file-plus",
    "new-folder": "folder-plus",
    "split-horizontal": "columns",
    "play": "play",
    "bell": "bell",
    "bell-dot": "bell-ringing",
    "check": "check",
    "error": "x-circle",
    "warning": "warning",
    "info": "info",
    "lightbulb": "lightbulb",
    "arrow-left": "arrow-left",
    "arrow-right": "arrow-right",
    "arrow-up": "arrow-up",
    "arrow-down": "arrow-down",
    "git-commit": "git-commit",
    "git-merge": "git-merge",
    "git-pull-request": "git-pull-request",
}


def fetch(icon: str) -> str:
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / f"{icon}-regular.svg"
    if cached.exists():
        return cached.read_text()
    url = f"https://unpkg.com/@phosphor-icons/core/assets/regular/{icon}.svg"
    with urllib.request.urlopen(url, timeout=20) as r:
        svg = r.read().decode()
    cached.write_text(svg)
    return svg


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        srcdir = pathlib.Path(td) / "svg"
        srcdir.mkdir()
        for codicon, phosphor in ICONS.items():
            (srcdir / f"{codicon}.svg").write_text(fetch(phosphor))

        subprocess.run(
            ["npx", "-y", "fantasticon", str(srcdir), "-o", td,
             "-n", FONT_NAME, "-t", "woff", "--asset-types", "json",
             "--normalize"],
            check=True,
        )
        shutil.copy(f"{td}/{FONT_NAME}.woff", OUT / f"{FONT_NAME}.woff")
        codepoints = json.loads(pathlib.Path(f"{td}/{FONT_NAME}.json").read_text())

    theme = {
        "fonts": [{
            "id": FONT_NAME,
            "src": [{"path": f"./{FONT_NAME}.woff", "format": "woff"}],
            "weight": "normal",
            "style": "normal",
        }],
        "iconDefinitions": {
            codicon: {"fontId": FONT_NAME, "fontCharacter": chr(cp)}
            for codicon, cp in sorted(codepoints.items())
        },
    }
    out = OUT / "midori-product-icon-theme.json"
    out.write_text(json.dumps(theme, indent=2) + "\n")
    print(f"wrote {out} ({len(codepoints)} icons)")


if __name__ == "__main__":
    main()
