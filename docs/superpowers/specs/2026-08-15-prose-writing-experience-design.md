# The prose writing experience

**Date:** 2026-08-15
**Status:** design, awaiting review
**Builds on:** `2026-08-15-prose-typography-evidence.md` (what the evidence
supports) and `../plans/2026-08-15-prose-writing-surface.md` (the typography
plan this corrects)

## What this is

The goal was "an amazing prose writing experience, for myself and others." Four
areas were considered and two survived. The record of what was cut is part of
the design, because each was cut for a reason that should not need rediscovering.

| Area | Verdict |
|---|---|
| The page at rest — type, spacing, colour, caret | **In.** Already planned; this corrects the plan against the real vault. |
| A writing mode you enter | **In.** Consolidated into the repo; behaviour unchanged in kind. |
| Revision and look-back | **Out**, not chosen. The one solid composition finding — look-back fires at sentence boundaries — remains undesigned-for, deliberately. |
| Around the note — starting, phone, export | **Out.** "The seams are fine." |

Two further cuts inside the surviving areas: the mode changes **nothing about
the page** (no typewriter scrolling, no dimming, no type change on entering),
and it takes away **nothing more** than it does today (the status bar, the
sidebars and the toggle dot all stay).

## Discovery that forced the design

Read out of the live vault at
`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Mud & Silicon/.obsidian/`,
not assumed:

- **`baseFontSize: 14`**, against a theme that documents itself as assuming
  15–16px. Every number in the typography plan was computed at 16.
- **`showViewHeader: false`** and **`showRibbon: false`** — most of what a zen
  mode normally removes is already gone at the app level.
- **`pretty-paragraphs` is enabled**, so the real writing surface already has
  novel-style first-line indents and no paragraph spacing.
- **The writing mode lives in three places**: a `zen-toggle` plugin authored
  here but kept outside this repo, a `zen-mode.css` snippet in the vault, and
  ~40 lines in `theme.css`. Only the third ships to anyone.

## Part 1 — The writing mode, consolidated

### The boundary

**The plugin owns what it creates. The theme owns how the app's chrome reacts.**
This is the split `midori-timer` already uses, and it is chosen against the
failure this repo keeps hitting: one constant living in two files.

| Artifact | Owns |
|---|---|
| `obsidian/plugins/zen-toggle/` (moved in) | The corner dot element, the styles for that element only, the `body.zen-mode` class, the command. |
| `obsidian/theme.css` | Every rule describing how the tab strip, view header and canvas respond to `body.zen-mode`. These manipulate the dot-grid phase and `--header-height`, which are theme-owned constants. |
| `obsidian/install-obsidian.sh` | Fans the plugin out with the others, and renames the now-duplicated `zen-mode.css` aside **once** (to `zen-mode.css.superseded`) so there is exactly one live home. It never deletes a snippet it did not write — see Risks. |

Rejected alternatives: the plugin shipping the chrome CSS (it would need the
theme's grid constants — the same split-knowledge bug in a new place), and a
theme-only version with no plugin (a theme cannot flip a class).

### The defect to fix

Every zen rule that depends on the view header currently fires whether or not
the header exists. app.css hides it outright when the setting is off:

```css
body:not(.show-view-header):not(.is-phone) .view-header { display: none; }
```

So with `showViewHeader: false`, `body.zen-mode … .cm-sizer { padding-top:
var(--header-height) }` and its matching `background-position` phase shift add a
header's worth of empty space above the note, and move the dot grid to match,
for a header that is not displayed. The fix is to gate on the class app.css
itself keys off:

```css
body.zen-mode.show-view-header .markdown-source-view.mod-cm6 .cm-sizer {
  padding-top: var(--header-height);
}
```

That makes the mode correct under both settings rather than under one.

### Invariant

Every `body.zen-mode` rule that mentions `--header-height` must also require
`.show-view-header`. Statically checkable; see Testing.

## Part 2 — The page at rest, corrected

### Base size

`baseFontSize: 14` is the real setting, so the plan's numbers were computed at
the wrong base. Nothing in the mechanism changes — both fixes were already
written to follow the reader rather than assume:

| | at base 14 | at base 16 |
|---|---|---|
| measure today (700px) | ~104 cpl | ~91 cpl |
| measure as `calc(var(--font-text-size) * 34)` | 70 cpl | 70 cpl |
| grid `round(up, max(24px, base × 1.5), 1px)` | 24px = 1.71 | 24px = 1.50 |

The theme's own comment claiming it assumes 15–16px is corrected to state the
range it actually supports, which is the app's whole 10–30px clamp.

**One number that is the writer's to act on, not the theme's.** At base 14 on
the 81 ppi ultrawide (800 × 340 mm panel, 2560 × 1080, 1×), M PLUS 1p's x-height
subtends 0.217° at 60cm and **0.186° at 70cm**, against a 0.2° critical-print-size
floor below which reading speed falls sharply. 15 or 16 is better supported than
14 by the strongest part of this literature. The theme follows the slider either
way and does not argue with it.

### Paragraphs: the theme adopts the indents

`pretty-paragraphs` is doing something the theme should own, for one reason
above preference: **its blank-line handling is grid-hostile, and only the owner
of the grid can fix it.**

The plugin's mechanism, and what is wrong with it:

| Plugin rule | Effect | Defect |
|---|---|---|
| `.cm-line:has(> br:only-child) { line-height: 0 }` | Collapses the blank line between paragraphs, matching Reading view's lack of paragraph margin | None — 0 is a multiple of any row |
| `.cm-active:has(> br:only-child) { line-height: normal }` | Re-expands the blank line the caret is on, so the cursor is visible | **`normal` is ~16.8px at base 14 — not a multiple of 24.** Every time the caret rests on an empty line, everything below it steps off the dot grid |
| `.cm-line:has(> br:only-child) + .cm-line { text-indent: 2em }` | Indents the line after a blank | Does not exclude headings, so **a heading following a blank line is indented 2em** |

The theme's version keeps the mechanism and fixes both:

- the active blank line takes `line-height: var(--midori-row)` — one full grid
  row, so the caret is visible *and* the lattice holds;
- the indent excludes every non-prose line — headings, list lines, code, quotes,
  tables, callouts;
- Reading view keeps `text-indent` with `margin-block: 0`, which suits the grid
  better than the 24px paragraph gap it replaces, since a paragraph break stops
  costing a row.

**Every paragraph is indented, including the first after a heading**, which
departs from the book convention on purpose. The exception is expressible in
Reading view (`h1 + p`) and not in Live Preview, where the blank line makes it
positional and fragile; the two panes matching matters more here than the
convention does, and this theme has paid for pane divergence before.

**This ships as a stated preference, not an optimum.** The evidence review found
nothing either way on indent-versus-blank-line. It is in the theme because it is
how these notes are actually written, and because the grid-correct version
cannot live anywhere else.

Once the theme owns this, `pretty-paragraphs` becomes redundant and should be
disabled — its `!important` margins would otherwise keep beating the theme's
paragraph rules. Its justify option is not carried over; nothing asked for it.

## Testing

- **Static (extends `tests/test_prose_typography.py`, stdlib only, runs in lint):**
  the zen/header invariant above; the measure in characters at every base in the
  app's 10–30 clamp; the leading ratio; no `line-height: normal` on any
  `.cm-line` rule.
- **Rendered, in a browser harness that loads the real `theme.css`:** with the
  caret simulated on a blank line, every following line's box top stays on a
  multiple of `--midori-row`. This is the check the plugin would have failed.
- **In the app, both settings:** zen on and off × `showViewHeader` on and off,
  confirming the note's first baseline does not move when the header is absent.

## Risks

- **`:has()` is load-bearing** in both the blank-line collapse and the tab-strip
  rule. Supported in Obsidian's Electron; it is a hard dependency worth naming.
- **Moving `zen-toggle` into the repo makes it a shipped artifact**, subject to
  `tests/check_plugin_loads.js` and the manifest conventions. That is the point,
  and it is also new maintenance.
- **Retiring the vault snippet is destructive.** The installer must not delete a
  `zen-mode.css` it did not write; the safe form is to rename it aside once and
  say so, not to remove it.
- **Class names carry no stability guarantee** — Obsidian publishes no
  deprecation policy, and `.cm-sizer` is an Obsidian-injected wrapper absent
  from upstream CodeMirror 6. `obsidian/dump-app-css.py` after an update is the
  whole mitigation.

## Deliberately not in this design

Revision and look-back support; typewriter scrolling; dimming or focus
highlighting; any page change on entering the mode; hiding the status bar or
sidebars in the mode; export and print styling; phone-specific work; paragraph
justification. Each was considered and declined above.
