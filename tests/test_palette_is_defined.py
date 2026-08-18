#!/usr/bin/env python3
"""Every colour used across 4+ files must be declared in palette.json.

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
SKIP_FILES = {"docs/cleanup-queue.md", "palette.json"}
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
    files = subprocess.run(["git", "-C", str(root), "ls-files"],
                           capture_output=True, text=True).stdout.split()
    out = collections.defaultdict(set)
    for f in files:
        if f.endswith(SKIP_SUFFIX) or f in SKIP_FILES:
            continue
        try:
            text = (root / f).read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for h in re.findall(r"#[0-9a-fA-F]{6}\b", text):
            out[h.lower()].add(f)
    return out


def declared(root):
    path = root / "palette.json"
    if not path.exists():
        bad("palette.json is missing -- the palette has no definition")
        return None
    doc = json.loads(path.read_text())
    out = {}
    for name, role in doc.get("roles", {}).items():
        for mode, value in role.items():
            if mode == "source":
                continue
            out.setdefault(value.lower(), []).append(f"{name}.{mode}")
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
    ok(f"palette.json declares {len(have)} colours across "
       f"{len(json.loads((ROOT / 'palette.json').read_text())['roles'])} roles")

    missing = sorted(h for h in shared if h not in have)
    for h in missing:
        where = sorted(shared[h])
        bad(f"{h} is used in {len(where)} files but is not in palette.json "
            f"({', '.join(where[:3])}{'...' if len(where) > 3 else ''})")
    if not missing:
        ok(f"all {len(shared)} shared colours are declared")

    print("palette: all green" if not FAIL else "palette: failures above")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
