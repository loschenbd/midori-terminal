# Midori for T3 Code

[T3 Code](https://github.com/pingdotgg/t3code) is a web GUI for coding agents.
It ships a full theme system that **its documentation does not mention** — as
of `t3@0.0.33` the docs site has no theming page at all, while the app carries
a theme editor, a theme library, and a strict file importer.

Everything below was recovered from the shipped bundle
(`package/dist/client/assets/index-*.js`) and re-derived by the validator in
`build-t3-theme.py`. It is a transcription of someone else's undocumented
schema, exactly like `antinote/`'s, so treat it as accurate for 0.0.33 and
re-check it after a t3 upgrade.

## Install

```sh
./t3/build-t3-theme.py          # regenerate midori-t3.json
./t3/build-t3-theme.py --check  # verify it matches its source (runs in lint)
```

Then in T3 Code: **Settings → Appearance → Add a theme**, and give it
`t3/midori-t3.json`. One file installs both modes — Paper is the base
appearance and Night rides along as a variant, so the theme follows
light/dark rather than needing two entries.

There is no installer script here on purpose. Every other target in this repo
writes to a file on disk; t3 keeps installed themes in the browser's
`localStorage`, which nothing outside the app should be reaching into.

## The schema

```jsonc
{
  "version": 1,              // must be exactly 1
  "id": "midori",            // optional; /^[a-z0-9](?:[a-z0-9-]{0,47})$/
  "name": "Midori",          // 1-48 chars after trim
  "appearance": "light",     // exactly "light" or "dark"
  "colors":   { "canvas": "#f3f1eb", ... },   // >= 1 role
  "variants": { "dark": { ... } },            // optional; the OTHER mode
  "sidebarArtwork": true     // optional
}
```

- **57 colour roles.** The full list is `ROLES` in `build-t3-theme.py`, taken
  from the bundle's own default palettes and cross-checked against both the
  light and dark defaults (identical key sets, 57 each).
- **Hex only.** Values must match
  `/^#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})$/i`. `rgb()`,
  `oklch()` and named colours are rejected. This matters here: several Midori
  tokens are authored as `rgba()` in `obsidian/theme.css` and cannot be
  copied across without conversion.
- **Reserved ids**: `system`, `light`, `dark`, `t3-chat`, `t3-grove`,
  `t3-ocean`, `t3-ember`, `t3-iris`.
- **A variant may not repeat the base appearance.** `appearance: "light"` with
  a `variants.light` is an error, not an override.
- Roles you omit fall back to t3's built-in default for that mode, so a
  partial theme silently mixes Midori with t3-chat. This file sets all 57 in
  both modes for that reason.

## Two import paths, different strictness

This is the part worth knowing before debugging anything.

Importing a **file** validates strictly and throws a named error — an unknown
role gives `"sidebarGlow" is not a supported theme color role.`

Writing a theme **straight into `localStorage["t3code:themes:v1"]`** goes
through a different validator that **silently drops** unknown keys and
malformed values, substituting the built-in default. The same typo is a loud
error through one door and an invisible no-op through the other. Import the
file.

## What a theme file cannot reach

The 57 roles map **only** to `--app-theme-*` variables — verified against the
bundle's own role-to-variable table, where none of the 57 points anywhere
else. Two visible things therefore sit outside a theme's reach in 0.0.33:

**The terminal's 16 ANSI colours.** There is no ansi role and no `--ansi-*`
CSS variable, and t3 hardcodes two palettes, both bright-on-dark. Against a
4.5:1 floor on paper `#f3f1eb`: the VGA palette medians 2.33 with 11 of 16
failing, the VS Code one medians 2.48 with 13 of 15 failing. A shell prompt
painting with ANSI names is therefore unreadable in Paper, and no choice of
`terminalForeground` fixes it, because the prompt never uses that value.

**The way out is truecolor.** t3's SGR parser returns the literal rgb for
`38;2;R;G;B` and only falls back to the hardcoded table for named and
256-colour codes, so a 24-bit colour renders exactly as named. That is why
`prompt/midori.omp.json` now pins hex instead of `green`/`cyan`/`yellow`/
`red`/`lightGreen`/`darkGray`. Verified from the rendered escape sequence, not
assumed: `oh-my-posh print primary` emits 5 truecolor codes and **0** legacy
ANSI colour codes.

The cost is that one pinned value must serve both the cream and the night
ground, and **no colour clears 4.5:1 on both** — a light ground needs dark ink
and a dark ground needs light ink. So the prompt no longer adapts between
ghostty Paper and Night; each value is chosen for the best worst-case:

| role | Midori token | on cream | on night |
|---|---|---|---|
| path, prompt arrow | olive `#6c7d52` | 3.96 | 3.93 |
| git clean | mint `#548373` | 3.82 | 4.08 |
| ahead | sage `#5f6f5e` | 4.74 | 3.28 |
| conflict, error | terracotta `#b06d4a` | 3.62 | 4.29 |
| separator | faint `#8a847b` | 3.28 | 4.74 |
| dirty, behind | ochre `#b88a3a` | **2.96** | 5.63 |

**Ochre is the known-weak one and is deliberate.** It is Midori's real ANSI
yellow, and nothing darker exists in the palette; inventing one would put a
colour in the prompt that appears nowhere else. It carries the highest chroma
in the set (C 11.1 in OKLCh, against 1.5–7.8 for the rest), so it reads as
*coloured* rather than as faint — the standard trade when a token has no
lightness room left. It is also the state you see most often, so if it grates,
the honest fix is a darker ochre added to the palette proper.

Anything that is not the prompt still emits ANSI — `ls`, `git` output, compiler
diagnostics — and those remain at the mercy of t3's hardcoded palette.

**Status labels.** "Working", "Awaiting Input", "Plan Ready" and friends are
Tailwind utilities baked into the components — `text-sky-600
dark:text-sky-400`, `text-indigo-600`, `text-violet-600`. They resolve to
`var(--color-sky-600)` and similar, which a theme file has no way to set, and
0.0.33 exposes no custom-CSS hook. Recolouring "Working" to Midori indigo is
not possible from a theme; it needs either an upstream change mapping those
labels onto theme roles, or a CSS injection mechanism that does not exist yet.

## Two things that would have shipped wrong

**The terminal cursor is not `cursor-color`.** In `ghostty/themes/*` that key
is not a colour: `cell-background` now, and when this was written *the exact
background hex as a sentinel*. Either way the shader draws the indigo ink
itself. Copying it here would have produced an invisible cursor that looked
perfectly faithful to the source. The real ink is used
instead: `#6c87a4`, the lifted indigo, in **both** modes.

> That last sentence read "`#3a5572` on paper and `#6c87a4` on night" until
> the paper terminal moved onto the night ground. It was true when written and
> false immediately after — `#3a5572` is the indigo tuned for a cream bed and
> is the wrong ink on `#1a1917`. Both modes now share one terminal, so both
> share one cursor.

**Paper's ink is `#2a2825`, not `--text-normal` `#3d3933`.** The first cut
used `#3d3933` and read washed out. Sampling a retina screenshot showed the
token rendering exactly as set — ground `#f3f1ec`, darkest glyph `#3d3934` —
so nothing was broken; the value was simply the wrong one to borrow.
`theme.css` calls `#3d3933` "`--foreground` lifted a step": it is Obsidian's
*body* text, softened on purpose for long-form reading. t3 is a UI at ~15px,
not a writing surface, and that lift reads as faint. It was also an asymmetry
— Night had taken ghostty's un-lifted ink `#ebe8e2` while Paper took the
lifted body value. Both now take the ghostty foreground for their ground:
Paper 13.01:1 (was 10.15:1), Night 14.37:1 (unchanged).

**Three roles are derived, not Midori tokens.** `errorSurface`,
`warningSurface` and `updateSurface` are washes, and Midori has no hand-tuned
value for them. Rather than invent three hexes and let them read as part of
the palette, `mix()` computes each as its status colour at 14% over the
canvas. They are the only values in this file that are not already shipped
somewhere else in this repo.

## Requires Node >= 22.16

`t3@0.0.33` declares `engines: { node: "^22.16 || ^23.11 || >=24.10" }`, and
every published version requires Node 22 or newer. npm treats `engines` as
advisory by default, so `npx t3` on an older Node installs and then fails at
runtime rather than refusing up front.
