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

## Two things that would have shipped wrong

**The terminal cursor is not `cursor-color`.** In `ghostty/themes/*` that key
is set to the *exact background hex as a sentinel* — the shader detects it and
substitutes the indigo ink. Copying it here would have produced an invisible
cursor that looked perfectly faithful to the source. The real ink is
`#3a5572` on paper and `#6c87a4` on night, and that is what this theme uses.

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
