#!/usr/bin/env python3
"""Fail if a stylesheet this repo injects somewhere contains a stray backtick.

Two cases, the same silly character, two different nasty failures.

1. `const STYLE = ` template literals in the Obsidian plugins. The string ends
   early, the CSS after it is parsed as JavaScript, and the reported error is
   whatever identifier happens to sit at the start of the next line — never
   the backtick that caused it.

2. silverbullet/*.css, which gets wrapped twice over, by two different
   mechanisms, and has a forbidden sequence for each.

   a. `</style` — the headHtml route embeds the stylesheet inside a <style>
      element in the page head, and an HTML parser ends that element at the
      first `</style`, whatever follows it. The silverbullet-hub installer
      refuses CSS containing it outright, so this check exists to fail in the
      repo rather than at install time. A CSS comment mentioning the closing
      tag is the realistic way to trip it, and this file's own prose is proof
      that such comments get written.

   b. ``` — SilverBullet's documented install route wraps the whole
      stylesheet in a space-style fenced block, and a fence ends at the first
      line opening with a run of backticks at least as long as the opening one.
   Both are worse than case 1 because NOTHING errors: the page renders, the
   markup parses, the theme installs, and only the rules below the cut are
   missing. The backtick case has already happened here — a comment in
   midori.css that named the block type with a three-backtick fence truncated
   the installed stylesheet at line 33 of just over 400.

   silverbullet/wrap-midori.sh refuses to emit from such a file, but that only
   helps someone who uses it; this is the check that runs every commit. It
   matters more than it looks: a live SilverBullet install reads
   silverbullet/midori.css from its path at build time, so a bad commit here
   reaches real spaces the next time anyone runs sb-theme.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OPEN = re.compile(r"const\s+STYLE\s*=\s*`")

fail = 0
for js in sorted(ROOT.glob("obsidian/plugins/*/main.js")):
    src = js.read_text()
    rel = js.relative_to(ROOT)
    for m in OPEN.finditer(src):
        end = src.find("\n`;", m.end())
        body = src[m.end():end if end >= 0 else len(src)]
        if end < 0:
            print(f"  FAIL {rel}: STYLE literal is never closed with a lone `;")
            fail = 1
            continue
        if "`" in body:
            line = src[:m.end()].count("\n") + 1 + body[:body.index("`")].count("\n")
            print(f"  FAIL {rel}:{line}: backtick inside the STYLE literal")
            fail = 1
        else:
            print(f"  ok   {rel} STYLE literal is clean")

# The exact final line a complete silverbullet stylesheet must end with.
SENTINEL = "/* END midori.css -- if this line is missing, the file was truncated. */"

# Case 2: stylesheets that get wrapped for injection.
FENCED = sorted(ROOT.glob("silverbullet/*.css"))
if not FENCED:
    print("  FAIL no silverbullet/*.css found -- this check scanned nothing, "
          "which is not the same as finding nothing wrong")
    fail = 1
for css in FENCED:
    rel = css.relative_to(ROOT)
    lines = css.read_text().splitlines()
    clean = True
    for needle, why in (("```", "triple backtick would end a space-style fence"),
                        ("</style", "'</style' would end the headHtml <style> element")):
        for i, line in enumerate(lines, 1):
            if needle in line:
                print(f"  FAIL {rel}:{i}: {why} and truncate the theme here")
                fail = 1
                clean = False
    # COMPLETENESS, NOT PLAUSIBILITY. A minimum-length threshold is a guess;
    # a fixed final line is an exact answer. This is the one truncation an
    # empty-file check cannot catch: truncated-but-nonempty, where the
    # raw-token blocks survive, the semantic mapping does not, and the space
    # ends up half-themed with nothing logged.
    tail = [ln for ln in lines if ln.strip()]
    if not tail or tail[-1].strip() != SENTINEL:
        got = tail[-1].strip()[:60] if tail else "(file is empty)"
        print(f"  FAIL {rel}: last non-blank line is {got!r},")
        print(f"       expected the completeness sentinel {SENTINEL!r}")
        fail = 1
        clean = False

    if clean:
        print(f"  ok   {rel} has no fence-breaking backtick, no '</style', "
              f"and ends with its sentinel ({len(lines)} lines checked)")

sys.exit(fail)
