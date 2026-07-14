#!/usr/bin/env python3
"""Generate the Midori file-icon theme from Material Symbols Rounded icons.

Fetches Material Symbols "rounded" style, fill variant SVGs (Apache-2.0)
from unpkg — soft rounded corners, solid fills — recolors them per the
Midori Color Dot palette, and emits light + dark variants plus the
icon-theme JSON into midori-theme/icons/. One icon theme serves both modes
via the "light" override block that VS Code file icon themes support.
(The workbench-chrome icons stay Phosphor — see build-product-icons.py.)

Run from anywhere:  python3 vscode/build-icons.py
Then repackage/reinstall via install-vscode.sh.
"""

import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
ICONS = ROOT / "midori-theme" / "icons"
CACHE = ROOT / ".icon-cache"

# role -> (light hex, dark hex) — from the ghostty midori-paper/midori-night themes
ROLES = {
    "sage":   ("#5f6f5e", "#9aab97"),  # folders — accent as punctuation
    "muted":  ("#8c8578", "#837d72"),  # default files — recede like comments
    "indigo": ("#3a5572", "#6c87a4"),  # code
    "wine":   ("#7a4a4a", "#b8868a"),  # markup, tests
    "olive":  ("#6c7d52", "#9eaf85"),  # shell, spreadsheets
    "ochre":  ("#b88a3a", "#d8b06a"),  # data, config, package
    "plum":   ("#664f63", "#a48ba3"),  # styles, databases
    "mint":   ("#548373", "#9ebfb4"),  # images
    "warm":   ("#b06d4a", "#d4a07a"),  # env, git
    "faint":  ("#a29f98", "#5d574e"),  # locks, vendored dirs
}

# definition name -> (material symbol candidates in preference order, role).
# The "-fill" variant suffix is appended automatically.
DEFS = {
    "folder":       (["folder"], "sage"),
    "folder-open":  (["folder_open"], "sage"),
    "folder-git":   (["folder_data", "folder"], "warm"),
    "folder-quiet": (["folder_managed", "rule_folder", "folder"], "faint"),
    "file":         (["draft", "description"], "muted"),
    "code":         (["code_blocks", "code"], "indigo"),
    "markup":       (["html", "code"], "wine"),
    "style":        (["css", "palette"], "plum"),
    "data":         (["data_object"], "ochre"),
    "text":         (["article", "description"], "muted"),
    "image":        (["image"], "mint"),
    "shell":        (["terminal"], "olive"),
    "lock":         (["lock"], "faint"),
    "env":          (["key"], "warm"),
    "config":       (["settings"], "ochre"),
    "test":         (["science"], "wine"),
    "package":      (["package_2", "deployed_code", "inventory_2"], "ochre"),
    "db":           (["database"], "plum"),
    "sheet":        (["csv", "table"], "olive"),
    "git":          (["account_tree", "merge"], "warm"),
}

EXT = {
    "code":   ["ts", "tsx", "js", "jsx", "mjs", "cjs", "py", "go", "rs", "rb",
               "php", "swift", "java", "kt", "c", "h", "cc", "cpp", "hpp",
               "m", "mm", "lua", "zig"],
    "markup": ["html", "htm", "xml", "vue", "svelte", "astro", "erb", "ejs"],
    "style":  ["css", "scss", "sass", "less", "styl"],
    "data":   ["json", "jsonc", "json5", "yaml", "yml", "toml", "ini", "plist"],
    "text":   ["md", "mdx", "txt", "rst", "log"],
    "image":  ["png", "jpg", "jpeg", "gif", "webp", "avif", "svg", "ico",
               "icns", "bmp", "tiff"],
    "shell":  ["sh", "zsh", "bash", "fish", "ps1", "bat", "cmd"],
    "lock":   ["lock"],
    "env":    ["env"],
    "test":   ["test.ts", "test.tsx", "test.js", "test.jsx",
               "spec.ts", "spec.tsx", "spec.js", "spec.jsx"],
    "db":     ["sql", "sqlite", "db", "db3"],
    "sheet":  ["csv", "tsv"],
    "config": ["conf", "config"],
}

FILENAMES = {
    "package":  ["package.json"],
    "lock":     ["package-lock.json", "pnpm-lock.yaml", "yarn.lock",
                 "bun.lockb", "Cargo.lock"],
    "env":      [".env", ".env.local", ".env.development", ".env.production",
                 ".env.example"],
    "git":      [".gitignore", ".gitattributes", ".gitmodules"],
    "config":   ["Dockerfile", "docker-compose.yml", "compose.yml", "Makefile",
                 "tsconfig.json", "jsconfig.json", ".editorconfig",
                 "next.config.js", "next.config.ts", "next.config.mjs",
                 "vite.config.ts", "vite.config.js",
                 "tailwind.config.js", "tailwind.config.ts",
                 "postcss.config.js", "postcss.config.mjs",
                 "eslint.config.js", ".eslintrc", ".eslintrc.json",
                 ".prettierrc", "prettier.config.js"],
}

FOLDERNAMES = {
    "folder-git":   [".git"],
    "folder-quiet": ["node_modules", "dist", "build", ".next", "out",
                     ".turbo", ".cache"],
}


def fetch(candidates: list) -> str:
    CACHE.mkdir(exist_ok=True)
    for icon in candidates:
        cached = CACHE / f"{icon}-fill.svg"
        if cached.exists():
            return cached.read_text()
        url = f"https://unpkg.com/@material-symbols/svg-400/rounded/{icon}-fill.svg"
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                svg = r.read().decode()
            cached.write_text(svg)
            if icon != candidates[0]:
                print(f"  note: {candidates[0]} -> fallback {icon}")
            return svg
        except Exception:
            continue
    raise SystemExit(f"could not fetch material symbol (tried {candidates})")


def recolor(svg: str, color: str) -> str:
    # Material Symbols SVGs carry no fill attribute (default black); set the
    # color on the root so the path inherits it.
    assert svg.startswith("<svg ") and "fill=" not in svg.split(">", 1)[0], \
        "unexpected material symbols svg format"
    return svg.replace("<svg ", f'<svg fill="{color}" ', 1)


def main() -> None:
    defs = {}
    for name, (candidates, role) in DEFS.items():
        svg = fetch(candidates)
        for mode_idx, mode in enumerate(["light", "dark"]):
            (ICONS / mode).mkdir(parents=True, exist_ok=True)
            color = ROLES[role][mode_idx]
            (ICONS / mode / f"{name}.svg").write_text(recolor(svg, color))
            defs[f"{mode[0]}_{name}"] = {"iconPath": f"./{mode}/{name}.svg"}

    def block(prefix: str) -> dict:
        return {
            "folder": f"{prefix}_folder",
            "folderExpanded": f"{prefix}_folder-open",
            "rootFolder": f"{prefix}_folder",
            "rootFolderExpanded": f"{prefix}_folder-open",
            "file": f"{prefix}_file",
            "fileExtensions": {e: f"{prefix}_{d}" for d, exts in EXT.items() for e in exts},
            "fileNames": {n: f"{prefix}_{d}" for d, names in FILENAMES.items() for n in names},
            "folderNames": {n: f"{prefix}_{d}" for d, names in FOLDERNAMES.items() for n in names},
            "folderNamesExpanded": {n: f"{prefix}_{d}" for d, names in FOLDERNAMES.items() for n in names},
        }

    theme = {"iconDefinitions": defs, **block("d"), "light": block("l"),
             "hidesExplorerArrows": False}
    out = ICONS / "midori-icon-theme.json"
    out.write_text(json.dumps(theme, indent=2) + "\n")
    print(f"wrote {out} ({len(defs)} icon definitions)")


if __name__ == "__main__":
    main()
