# Credits and third-party licences

The Midori extension's own source (colour themes, build scripts, theme JSON)
is MIT, © Benjamin Loschen. The icon artwork is derived from two third-party
sets, each under its own licence and each **modified**. Both are listed below
as required by those licences.

Regenerate either set with `vscode/build-icons.py` /
`vscode/build-product-icons.py`.

---

## Material Symbols — file icons ("Midori Icons")

- **Upstream:** Material Symbols, Rounded style, fill variant — Google
- **Source:** <https://github.com/google/material-design-icons>
- **Licence:** Apache License 2.0 — <https://www.apache.org/licenses/LICENSE-2.0>
- **Used in:** `icons/light/*.svg`, `icons/dark/*.svg` (20 glyphs × 2 modes)

**Modifications made:** the SVGs were fetched from unpkg unaltered in geometry,
then recoloured — a `fill` attribute in one of ten Midori palette roles (sage,
muted, indigo, wine, olive, ochre, plum, mint, warm, faint) was applied, and a
separate light and dark variant of each glyph was emitted. No path data was
changed. See `vscode/build-icons.py` for the exact glyph → role mapping.

---

## Phosphor — workbench chrome icons ("Midori Product Icons")

- **Upstream:** Phosphor Icons, regular weight
- **Source:** <https://github.com/phosphor-icons/core>
- **Licence:** MIT
- **Used in:** `product-icons/midori-product.woff`

**Modifications made:** the regular-weight SVGs were renamed after the VS Code
codicon ids they override and compiled into a single WOFF via `fantasticon`;
the glyph outlines are unchanged. VS Code product icon themes require a font
rather than SVGs, which is why the outlines are embedded rather than shipped
as files. See `vscode/build-product-icons.py` for the codicon → glyph mapping.

MIT licence text, reproduced as required:

```
MIT License

Copyright (c) 2023 Phosphor Icons

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Fonts

The editor/terminal fonts are not shipped in this extension — they live in
`fonts/` at the repo root with their own OFL licences
(`OFL-MPLUS.txt`, `OFL-Spectral.txt`) and are installed separately.
