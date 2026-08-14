#!/usr/bin/env python3
"""Wrap dumbzone's status line to the pane width instead of letting it be cut.

dumbzone (https://github.com/jbruns — installed at ~/.local/bin/dumbzone) writes
one long line. Claude Code truncates the status line to the pane and marks the
cut with a single ellipsis, so on a narrow pane everything past ~50 columns is
simply gone. Measured on the phone (Moshi at ~50 columns) against the real
binary, output width by context level:

    fresh     42        working   78        warm      95        critical  106

The advice sentences are what blow it out, and they are the part you never read:
they only appear once the line is long enough to be truncated. No combination of
DZ_SEGMENT_* switches fixes it — with every optional segment off the worst case
still measured 69 columns, because the rate-limit prose is not behind
DZ_SEGMENT_ADVICE at all.

Two changes, in this order. Drop the sentences and keep the tier labels, which
are the actual signal (see ADVICE below). Then pack whatever is left onto as
many lines as the pane needs — Claude Code renders a multi-line status line
as-is, so nothing is dropped at any width. After both:

    pane   fresh   working   warm   critical
     94      1        1       1        1       lines (93 columns at the worst)
     50      2        2       2        3

Reading the width is the one non-obvious part, and the obvious answer is wrong.
Claude Code gives the command its JSON on stdin and takes stdout, so neither is
a terminal; the natural move is to open /dev/tty and ask that. Measured from
inside a real status-line invocation, that fails:

    tty_cols   : ERR [Errno 6] Device not configured: '/dev/tty'
    COLUMNS    : 94
    width_used : 94

Claude Code spawns the command with no controlling terminal, and exports a live
COLUMNS instead — 94 matched the pane it was rendering into. So COLUMNS is the
authority here and /dev/tty is only a fallback for other hosts. Getting this
backwards fails silently: you land on the 80-column default and the line is
still cut on a phone, just less obviously.
"""

import os
import re
import shutil
import subprocess
import sys

# dumbzone's own separator, byte for byte. Splitting on this keeps each segment's
# colours attached to it, which a plain text split would not.
SEP = "\x1b[2m | \x1b[0m"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

# The tier LABEL is the signal; the sentence after it is not. DZ_SEGMENT_ADVICE
# turns that sentence off for the context zone — but only there. Swept 0-100,
# the rate-limit tiers are:
#
#     <50   (nothing)          75-89  HOT switch to small tasks
#     50-74 pace yourself      90+    WALL
#
# and no switch reaches them. Strip by STYLE rather than by phrase: dumbzone sets
# the advice dim+italic and the label bold, so this keeps HOT and WALL and drops
# the prose whatever it says — including strings added by a future version.
ADVICE = re.compile(r"\s*\x1b\[2m\x1b\[3m[^\x1b]*\x1b\[0m")

# Applied only when the user has not set them. Two deliberate changes:
#   PROJECT off — herdr already prints the workspace name directly above this
#                 line, in BOTH layouts (mobile header and desktop sidebar), so
#                 the segment is a duplicate. The git branch is NOT in herdr's
#                 mobile header, so DZ_SEGMENT_GIT stays on.
#   WEEKLY  on  — the 7-day limit. Off by default, and with the old single line
#                 it would have sat past the cut anyway; wrapping makes it free.
#   ADVICE  off — keep the zone label (WARM / DUMB / STUPID / COOKED), drop the
#                 sentence after it. See the ADVICE regex above for the half of
#                 this that the switch does not reach.
DEFAULTS = {
    "DZ_SEGMENT_PROJECT": "0",
    "DZ_SEGMENT_WEEKLY": "1",
    "DZ_SEGMENT_ADVICE": "0",
}


def width(default=80):
    try:
        cols = int(os.environ["COLUMNS"])
        if cols > 0:
            return cols
    except (KeyError, ValueError):
        pass
    try:
        with open("/dev/tty") as tty:
            cols = os.get_terminal_size(tty.fileno()).columns
            if cols > 0:
                return cols
    except Exception:                                            # noqa: BLE001
        pass
    return default


def cells(s):
    return len(ANSI.sub("", s))


def wrap_long(seg, w):
    """A single segment wider than the pane — break it on spaces, never mid-word
    and never mid-escape."""
    out, line = [], ""
    for word in seg.split(" "):
        cand = word if not line else line + " " + word
        if cells(cand) > w and line:
            out.append(line)
            line = word
        else:
            line = cand
    if line:
        out.append(line)
    return out


def pack(segments, w):
    lines, line = [], ""
    for seg in segments:
        cand = seg if not line else line + SEP + seg
        if cells(cand) <= w:
            line = cand
            continue
        if line:
            lines.append(line)
        if cells(seg) <= w:
            line = seg
        else:
            chunks = wrap_long(seg, w)
            lines.extend(chunks[:-1])
            line = chunks[-1]
    if line:
        lines.append(line)
    return lines


def main():
    raw = sys.stdin.read()
    binary = os.environ.get("DUMBZONE_BIN") or os.path.expanduser("~/.local/bin/dumbzone")
    if not os.path.exists(binary):
        binary = shutil.which("dumbzone")
    if not binary:
        return 0                       # no status line beats a broken one

    env = dict(os.environ)
    for k, v in DEFAULTS.items():
        env.setdefault(k, v)
    try:
        out = subprocess.run(
            [binary], input=raw, capture_output=True, text=True, env=env, timeout=5
        ).stdout.rstrip("\n")
    except (OSError, subprocess.SubprocessError):
        return 0
    if not out.strip():
        return 0

    w = width()
    for line in out.split("\n"):
        segments = [ADVICE.sub("", s) for s in line.split(SEP)]
        line = SEP.join(segments)
        if cells(line) <= w:
            print(line)
        else:
            for packed in pack(segments, w):
                print(packed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
