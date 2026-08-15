#!/usr/bin/env python3
"""Extract Obsidian's own app.css (and app.js) from the installed app.

WHY THIS EXISTS. This theme is a 2,700-line argument with a stylesheet nobody
here can read, and every time that argument has been lost it was lost to a rule
in app.css that did something other than what the docs imply — a selector one
class heavier than expected, a colour hardcoded where a variable was assumed, a
variable consumed on an element nobody would guess. Guessing costs a round
trip through the app; reading costs a second.

Obsidian ships app.css inside obsidian.asar. An asar is a pickle header
followed by a JSON index and one concatenated blob, so no npm tooling is
needed to read it — just the offsets.

    python3 obsidian/dump-app-css.py [outdir]

Nothing here is patched or written back. The app bundle is read-only to this
script, and the output is a scratch copy for grepping.
"""

import json
import pathlib
import struct
import sys

ASAR = pathlib.Path("/Applications/Obsidian.app/Contents/Resources/obsidian.asar")
WANT = ("app.css", "app.js")


def read_asar(path):
    """Yield (name, bytes) for the top-level files we care about."""
    blob = path.read_bytes()
    # Pickle header: u32 = 4, u32 payload size, u32 json size + padding,
    # u32 json size. The JSON index starts at byte 16.
    _, _, _, json_len = struct.unpack("<IIII", blob[:16])
    index = json.loads(blob[16:16 + json_len].decode("utf-8"))
    base = 16 + json_len
    base += (4 - base % 4) % 4          # the file blob is 4-byte aligned
    for name, entry in index["files"].items():
        if name in WANT and "offset" in entry:
            start = base + int(entry["offset"])
            yield name, blob[start:start + int(entry["size"])]


def main():
    if not ASAR.exists():
        print(f"not found: {ASAR}", file=sys.stderr)
        print("Obsidian is not installed at the default location.", file=sys.stderr)
        return 1
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "obsidian-app")
    out.mkdir(parents=True, exist_ok=True)
    for name, data in read_asar(ASAR):
        (out / name).write_bytes(data)
        print(f"wrote {out / name}  {len(data):,} bytes")
    print("\nUseful greps:")
    print(f"  grep -o -- '--h[1-6]-[a-z-]*: *[^;]*;' {out}/app.css | sort -u")
    print(f"  grep -o -- '[^{{}}]*var(--file-line-width)[^}}]*}}' {out}/app.css")
    return 0


if __name__ == "__main__":
    sys.exit(main())
