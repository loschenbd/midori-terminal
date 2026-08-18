#!/usr/bin/env python3
"""Report where Midori's palette is duplicated across targets, and where it drifted.

REPORTING TOOL, NOT A GUARD. It asserts nothing and never fails a build. It
exists so the numbers quoted in docs/cleanup-queue.md can be re-derived instead
of trusted -- a measurement nobody can reproduce becomes an invented claim the
first time someone reads it, which has already happened in this repo once.

The real guard (every 4+-file hex must appear in a canonical palette file) is a
queue item, deliberately not written here.

    python3 tests/measure_palette_drift.py
"""
import collections
import pathlib
import re
import subprocess
import sys

SKIP_SUFFIX = (".ttf", ".woff2", ".png", ".pdf", ".vsix", ".ico")
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")

# EXCLUDE THE DOCUMENT THAT REPORTS ON THIS. docs/cleanup-queue.md quotes the
# drifted values in order to discuss them, which makes every one of them appear
# in one more file and lists the queue itself as a drift site. A measurement
# that counts its own write-up is measuring the wrong thing.
SKIP_FILES = {"docs/cleanup-queue.md"}

# A colour in this many files is palette, not a one-off. 4 is the knee: below
# it a value is usually one theme's local shade, above it the value is being
# hand-copied between targets.
SHARED_AT = 4
# "Core" is the subset stable enough to measure drift AGAINST.
CORE_AT = 8
# Max per-channel delta below which two colours are indistinguishable in use.
# 3 is conservative -- a 1-3 step is invisible on any display, so a value that
# close to a core colour is a stale copy or a typo, never a design choice.
INVISIBLE = 3
# Above INVISIBLE but still suspiciously close: worth a human look, not a fix.
SUSPICIOUS = 8


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def delta(a, b):
    return max(abs(x - y) for x, y in zip(rgb(a), rgb(b)))


def collect(root):
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
        for h in HEX.findall(text):
            out[h.lower()].add(f)
    return out


def main():
    root = pathlib.Path(__file__).resolve().parent.parent
    hf = collect(root)
    if not hf:
        sys.exit("no hex values found at all -- the collector is broken, "
                 "not the repo")
    n_files = len({f for v in hf.values() for f in v})
    shared = {h: fs for h, fs in hf.items() if len(fs) >= SHARED_AT}
    core = {h for h, fs in hf.items() if len(fs) >= CORE_AT}

    print(f"{len(hf)} distinct hex values across {n_files} files")
    print(f"{len(shared)} appear in {SHARED_AT}+ files (the de-facto shared "
          f"palette); {len(core)} in {CORE_AT}+ (core)\n")

    print(f"{'hex':>9}  {'files':>5}  areas")
    for h, fs in sorted(shared.items(), key=lambda kv: -len(kv[1]))[:12]:
        areas = sorted({f.split("/")[0] for f in fs})
        print(f"{h:>9}  {len(fs):>5}  {', '.join(areas[:6])}")

    invisible, suspicious = [], []
    for h in sorted(set(hf) - core):
        near = min(((delta(h, c), c) for c in core), default=None)
        if not near:
            continue
        d, c = near
        if 0 < d <= INVISIBLE:
            invisible.append((h, c, d))
        elif d <= SUSPICIOUS:
            suspicious.append((h, c, d))

    print(f"\nDRIFT -- within {INVISIBLE}/255 of a core colour, i.e. invisible, "
          f"so a stale copy or a typo ({len(invisible)}):")
    for h, c, d in invisible:
        print(f"  {h} vs {c} (d={d})  {', '.join(sorted(hf[h])[:2])}")

    print(f"\nSUSPICIOUS -- {INVISIBLE + 1}..{SUSPICIOUS}/255 away, visible, so "
          f"possibly deliberate ({len(suspicious)}): report, do not fix")
    for h, c, d in suspicious[:10]:
        print(f"  {h} vs {c} (d={d})  {', '.join(sorted(hf[h])[:2])}")
    if len(suspicious) > 10:
        print(f"  ... and {len(suspicious) - 10} more")


if __name__ == "__main__":
    main()
