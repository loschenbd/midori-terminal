# Midori

Two themes for people who read code on a laptop *and* on an external monitor.
**Midori Paper** is cream and ink; **Midori Night** is warm charcoal. They ship
with a matching file icon set, workbench icons, and a styled markdown preview.

<!--
  Absolute raw URLs on purpose. vsce rewrites relative links assuming the
  extension sits at the repo root, so `media/paper.png` in this subdirectory
  package becomes .../blob/HEAD/media/paper.png and 404s on the Marketplace.
  Verified: the rewritten CREDITS.md link returned 404, the absolute one 200.
-->
![Midori Paper](https://raw.githubusercontent.com/loschenbd/midori-terminal/main/vscode/midori-theme/media/paper.png)

![Midori Night](https://raw.githubusercontent.com/loschenbd/midori-terminal/main/vscode/midori-theme/media/night.png)

## Install

Search **Midori** in the Extensions view, or:

```
ext install benjaminloschen.midori-theme
```

Then pick *Midori Paper* or *Midori Night* from **Preferences: Color Theme**.

To follow the system appearance and get the icons and guides as intended, merge
this into `settings.json`:

```jsonc
"window.autoDetectColorScheme": true,
"workbench.preferredLightColorTheme": "Midori Paper",
"workbench.preferredDarkColorTheme": "Midori Night",
"workbench.iconTheme": "midori-icons",
"workbench.productIconTheme": "midori-product-icons",

// Both of these are required, and the second is not a typo.
// editor.guides.bracketPairs defaults to false, which leaves the theme's
// bracket-guide colours inert. And highlightActiveIndentation defaults to
// true, which actually means "highlight the active indent guide *unless*
// bracket pair guides are on" — so enabling the first silently kills the
// active indent rail, the only guide that follows JSX nesting.
// "always" keeps both.
"editor.guides.bracketPairs": true,
"editor.guides.highlightActiveIndentation": "always",
```

## What's in it

| | |
|---|---|
| **Midori Paper** | light — cream `#f3f1eb`, ink `#2a2825` |
| **Midori Night** | dark — warm charcoal `#1a1917`, bone `#ebe8e2` |
| **Midori Icons** | file icons, recoloured from Material Symbols |
| **Midori Product Icons** | workbench chrome, built from Phosphor |
| markdown preview | Spectral headings, M PLUS body, themed code blocks |

Syntax uses five accents — indigo, olive, wine, ochre, sage — kept at low
chroma on purpose.

## Why it looks the way it does

**Contrast is tuned for 1x, not for Retina.** On a non-retina display almost
every glyph pixel is an antialiased blend toward the background, so a nominal
WCAG ratio overstates what you can actually read — a 2.76:1 token measured
closer to 1.8:1 in practice. Every syntax colour here is laddered against the
90th-percentile rendered pixel rather than the nominal number, which is why
body tokens sit at 5–8:1 instead of a bare 4.5.

**Separation comes from lightness, not saturation.** Raising chroma was tried
first and made things worse: the accents rely on chroma *tiers* to stay apart
when four of them land on one line, and lifting everything collapsed those
tiers. The palette is an OKLCh lightness ladder with hues left alone.

**Weight means one thing.** Bold marks where a name is *introduced* —
functions, methods, classes, interfaces, enums, types, namespaces — and control
flow. Not call sites, and not variables.

**Markup inside template literals is coloured.** TypeScript's grammar gives a
template literal one scope end to end, so `<div class="muted">` normally has no
tags or attributes to colour. A grammar injection emits the missing scopes, and
a small shell lexer does the same for ```` ```bash ```` blocks in the preview,
which highlight.js otherwise leaves mostly bare.

## Companion themes

Part of [midori-terminal](https://github.com/loschenbd/midori-terminal), which
carries the same palette into Ghostty, tmux, fzf, oh-my-posh, Claude Code,
Obsidian and Antinote — all switching with macOS appearance together.

## Licence and credits

MIT. The icon artwork is derived from two third-party sets, both modified,
both credited in
[CREDITS.md](https://github.com/loschenbd/midori-terminal/blob/main/vscode/midori-theme/CREDITS.md)
with full licence texts in `licenses/`: **Material Symbols** (Google,
Apache-2.0) and **Phosphor Icons** (MIT).

*Midori is an independent project. It is not affiliated with, endorsed by, or
sponsored by Designphil Inc. or any other company. "Midori" is used here in its
ordinary sense — 緑, the Japanese word for green.*
