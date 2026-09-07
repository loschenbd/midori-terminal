# Changelog

## 1.22.0 — Python reads like Python

Python is coloured by the language server, not by the TextMate grammar: on a
real FastAPI file, 40 tokens carry no scope past `source.python`, so semantic
tokens do all the work and *override* every rule below them. Six new
`:python`-scoped rules give back the roles that override was flattening. Nothing
outside Python changes — re-resolving the same 252 tokens as `typescript`
changes 0 of them.

- **Module names step back.** `namespace` was the same wine as the class beside
  it, so `from pydantic import BaseModel` had no tiers. Modules now take the
  parameter neutral, upright.
- **Builtins are italic.** `dict`, `str`, `len` and `.values()` were
  indistinguishable from your own classes and functions. They keep their hue and
  gain italic — the ladder had no free rung to spend (a search over all eight
  hues × L 43–56 × C 0.5–20 found no candidate below C 14.5, above this theme's
  C 12.0 ceiling), and italic already means "provided, not declared" here.
- **Module constants are terracotta again.** `MAX_RETRIES` and `_ITEMS` matched
  `constant.other.caps` and still rendered as plain ink, because the semantic
  type `variable.readonly` resolved onto a scope this theme's `variable` rule
  caught first.
- **Enum members are terracotta.** `Color.RED` was rendering as an ordinary
  variable.
- The `variable.language` caption said "this / self"; Python's `self` is a
  `selfParameter` with `superType: parameter` and lands on the parameter rule
  instead. Left as-is — it reads better — and the caption now says so.

## 1.21.0 — first public release

Midori Paper and Midori Night, plus a matching file icon set, workbench
product icons, and a styled markdown preview.

**Themes**

- **Midori Paper** — light, cream `#f3f1eb` on ink `#2a2825`.
- **Midori Night** — dark, warm charcoal `#1a1917` on bone `#ebe8e2`.
- Five accents — indigo, olive, wine, ochre, sage — deliberately held at low
  chroma, separated by an OKLCh lightness ladder rather than by saturation.
- Contrast laddered against the 90th-percentile *rendered* pixel at 1x rather
  than the nominal WCAG ratio, so body tokens sit at 5–8:1 instead of a bare
  4.5. On a non-retina display almost every glyph pixel is an antialiased
  blend toward the background, which makes nominal ratios overstate what is
  actually legible.
- Control flow is split from storage and declarations — `if`/`return` no
  longer share a colour with `const`/`class` — separated on lightness, chroma
  and weight at once.
- Bold marks where a name is *introduced*: functions, methods, classes,
  interfaces, enums, types, namespaces, and control flow. Not call sites, and
  not variables.
- Markup hierarchy for tags, attributes and brackets, following the
  convention the large majority of established themes share.
- Bracket-pair guide colours and the active indent rail, both wired up by the
  installer's settings snippet.

**Syntax**

- A TextMate grammar injection colours HTML inside TypeScript and JavaScript
  template literals. TypeScript's own grammar gives a template literal one
  scope end to end, so `` `<div class="muted">` `` normally has no tags or
  attributes for any theme to colour.

**Icons**

- File icons recoloured from Material Symbols Rounded (Apache-2.0).
- Workbench product icons built from Phosphor (MIT).
- Both credited in `CREDITS.md`, with full licence texts in `licenses/`.

**Markdown preview**

- Spectral headings, M PLUS body, themed code blocks laddered against the
  rendered surface rather than the token.
- A small shell lexer for ```` ```bash ```` blocks, which highlight.js
  otherwise leaves almost entirely unstyled.

### Note on the version number

Versions 1.0.0 through 1.20.0 were local development builds and were never
published. This is the first release available anywhere.
