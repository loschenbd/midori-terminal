#!/usr/bin/env python3
"""Render real prose in the real theme, at several measures, for a look.

Loads obsidian/theme.css itself rather than a copy, so what is judged is what
ships. Writes to the path given as argv[1] (default ./prose.html) and expects
to be served over http, not opened as file:// — Chrome blocks font loading and
some CSS on file URLs.

    python3 tests/prose_harness.py /tmp/prose.html
    python3 -m http.server 8777 --directory /tmp
"""

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CSS = (REPO / "obsidian" / "theme.css").read_text()

PROSE = """<p>The question of how long a line of text should be is older than the
screen, and most of the answers in circulation were never measured at all. A
writer revising a paragraph moves through it differently than a reader meeting
it once: the eye returns to the line just finished, hops back to the start of
the sentence, and leaves again. Whether that pattern wants a shorter measure
than reading does is, as far as the literature goes, an open question.</p>
<p>What is not open is that the same stylesheet is a different size on every
panel it lands on. An angle is not a length, and a length is not a size until
something says how far away the reader is sitting.</p>"""

WIDTHS = ("calc(var(--font-text-size) * 32)",   # 66 cpl
          "calc(var(--font-text-size) * 34)",   # 70 cpl
          "calc(var(--font-text-size) * 36)",   # 75 cpl
          "700px")                             # today, ~91 cpl

def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "prose.html")
    blocks = "\n".join(
        f'<section><h3>{w}</h3>'
        f'<div class="markdown-preview-view" style="--file-line-width:{w}">'
        f'<div class="markdown-preview-sizer">{PROSE}</div></div></section>'
        for w in WIDTHS
    )
    out.write_text(f"""<!doctype html><meta charset=utf-8><title>Measure</title>
<style>{CSS}
body {{ font-family: "Midori Text", system-ui, sans-serif; }}
section {{ margin: 0 0 48px; }}
section h3 {{ font: 12px ui-monospace, Menlo, monospace; color: #888; margin: 0 0 8px; }}
.markdown-preview-sizer {{ max-width: var(--file-line-width); }}
</style>
<button onclick="document.body.classList.toggle('theme-dark');
                 document.body.classList.toggle('theme-light')">night</button>
{blocks}
<script>document.body.classList.add('theme-light');</script>
""")
    print("wrote", out)

if __name__ == "__main__":
    main()
