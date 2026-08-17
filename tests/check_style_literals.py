#!/usr/bin/env python3
"""Fail if a `const STYLE = ` template literal contains a stray backtick.

See the note in lint.sh. The failure mode this guards is nasty out of
proportion to its silliness: the string ends early, the CSS after it is parsed
as JavaScript, and the reported error is whatever identifier happens to sit at
the start of the next line — never the backtick that caused it.
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

sys.exit(fail)
