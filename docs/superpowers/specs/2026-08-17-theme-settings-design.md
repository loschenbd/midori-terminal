# Midori theme settings

**Date:** 2026-08-17
**Status:** design — approved in conversation, not yet planned
**Goal:** Let a reader adjust the Midori Obsidian theme's stated preferences —
the measure, the paragraph rhythm, the dot grid, the accent — without being
able to break the baseline grid the theme exists to hold.

## The problem

Every design decision in `obsidian/theme.css` is a literal or a derived `calc`
in 3080 lines. There is no settings surface at all: no `@settings` block, and
the Style Settings plugin is not installed in any vault here. Changing the
paragraph indent means editing the stylesheet.

That is tolerable for one person and disqualifying for a theme that ships to
other writers.

## The principle

**Expose what the project has already admitted is preference. Derive what it
has established as evidence.**

The theme's own documentation already draws this line. On paragraph indents the
README says: *"The evidence review found nothing either way on
indent-versus-blank-line. This is a stated preference."* That is a setting
waiting to happen. By contrast `x 1.1556` is Spectral's x-height (0.450em)
divided by M PLUS 1p's (0.520em) — not a matter of taste, and meaningless as a
slider.

A second rule, decided explicitly: **no setting may put the note off the dot
grid.** Values that cannot affect vertical rhythm move freely. Values that can
are quantised in CSS, so no input reaches a rule without passing a `round()`.

## Mechanism: a Style Settings block

A `/* @settings */` YAML comment in `theme.css`. The Style Settings plugin
reads it and generates the UI — sliders, selects, colour controls, class
toggles. No JavaScript to write or maintain, and it is what Obsidian theme
users already expect.

**It is not a hard dependency.** The block is a CSS comment. With the plugin
absent it is inert and the theme behaves exactly as it does today. This
distinguishes it from the `pretty-paragraphs` situation, where a third-party
plugin silently overrode the theme's own rules.

Rejected alternatives:

- **A first-party settings plugin.** Full control, no third-party anything, and
  the repo already ships four plugins. Rejected because it reimplements a
  solved problem and adds a fifth artifact to maintain, for a UI the ecosystem
  already standardised.
- **Documented override points.** A variable list plus a snippet template. No
  dependency, but it is documentation rather than settings and does nothing for
  the "ships to others" half of the goal.

## The inventory

### Tier 1 — preferences, free to move

Horizontal, colour, or on/off. No input can touch the lattice.

| setting | variable / class | default | control | range |
|---|---|---|---|---|
| Paragraph rhythm | `midori-rhythm-*` on `body` | Indent | class-select | Indent / Space between / Both |
| Indent size | `--midori-set-indent` | `2` (em) | slider | 0–4, step 0.5 |
| Measure | `--midori-set-measure` | `70` (characters) | slider | 40–100, step 1 |
| Dot grid opacity | `--midori-set-dot-alpha` | `1` (x shipped) | slider | 0–1.5, step 0.05 |
| Accent | `--midori-set-accent` | sage | select | sage, mint, olive, ochre, clay, wine, indigo, purple |

Notes:

- **The measure is exposed in characters, and the stylesheet holds em.** The
  shipped `calc(var(--font-text-size) * 34)` is **34 em, which is 70.6 cpl** —
  cpl = em / 0.4818, where 0.4818 is M PLUS 1p's average advance measured from
  the outlines over a prose sample. So the setting needs a conversion the
  current variable does not have:

  ```css
  --midori-avg-advance: 0.4818;   /* M PLUS 1p, BoundsPen over prose */
  --midori-set-measure: 70;       /* characters per line */
  --file-line-width: calc(var(--font-text-size)
                          * var(--midori-set-measure)
                          * var(--midori-avg-advance));
  ```

  It stays a multiple of `--font-text-size`, so it keeps following the reader's
  text-size slider, and it stays numeric rather than `em` — an `em` here
  resolves against `.cm-line`'s own font-size, which is also the heading
  element, giving headings an 880px column against a body line's 544px.

  The advance constant is font-specific and only valid because the body font is
  fixed (see Out of scope). If fonts are ever exposed, this must be measured
  from the chosen face.

- **Characters is a UI unit, not a scientific claim.** The evidence review
  refuted 0–3 the claim that *characters* rather than visual angle is the
  critical variable, and lists the question as genuinely open. Characters is
  what a writer thinks in and what the research is *reported* in; it is not
  established as the thing the eye responds to. The setting's description
  should not imply otherwise.

- **The range spans the two horns of the only surviving finding.** The
  speed/preference split is confirmed 3–0: longer lines are read faster,
  moderate lines are preferred, and subjective ratings do not track measured
  performance. So there is no single optimum to centre a slider on — there are
  two defensible ends, and which one a reader wants is exactly the preference a
  setting should carry.

  - **Bottom, 40 cpl.** Below the floor of every proposed preference band
    (45–75). The only hard lower bound in the literature is Atilgan, Xiong &
    Legge (PNAS 2020): ~13 characters to reach 80% of maximum reading speed —
    so low it never binds. 40 gives headroom under the band without being
    absurd for prose.
  - **Top, 100 cpl.** Where the speed literature peaks: reading speed and
    efficiency are reported highest around 95 cpl, and 100-character lines are
    read faster than 25-character ones with comprehension unchanged. Obsidian's
    own 700px default is ~91 cpl at 16px, so this also lets a reader keep stock
    behaviour.
  - **Default 70**, the shipped value — the top of the preference band, which
    is where "erring large is much cheaper than erring small" lands it.

  Provenance caveat, carried from the review: the line-length literature is
  CRT-era with mixed tasks and is the weakest evidence in the set. The 95-cpl
  speed peak comes from the same body of work whose 55-cpl *comprehension*
  optimum was refuted 0–3. Only the speed half survived, and only the speed
  half is used here.
- **The accent is a select, not a colour picker.** "The palette is closed" is a
  documented decision with a stated argument (the ANSI-16 seam has six
  chromatic slots and all six are filled; lightness, not hue, is what ran out).
  A free picker would quietly reopen it.
- **Dot opacity 0 turns the grid off.** This is the single largest lever for
  other users: many will want the typography without visible dots. It is a
  multiplier on the shipped per-mode values rather than a flat alpha, so light
  and dark keep their separately-tuned relationship — `0.46` light against
  `0.1748` dark is not an accident, and one flat slider would flatten it.

  `--dotgrid-dot` is currently a whole `rgba()` literal, so this requires
  splitting it into channel and alpha parts first — the same split the theme
  already uses for `--color-blue-rgb` and friends:

  ```css
  --dotgrid-dot-rgb: 158, 191, 180;     /* per mode */
  --dotgrid-dot-alpha: 0.46;            /* per mode, the shipped value */
  --dotgrid-dot: rgba(var(--dotgrid-dot-rgb),
                      calc(var(--dotgrid-dot-alpha) * var(--midori-set-dot-alpha)));
  ```

  Both mode blocks must be split, or dark silently keeps a literal and stops
  responding to the setting.

### Tier 2 — exposed, but snapped

| setting | variable | default | how it is made safe |
|---|---|---|---|
| Leading | `--midori-set-leading` | `1.5` | `round(up, max(24px, fs x mult), 2px)` — always an even pixel, never below 24 |
| Heading scale | `--midori-set-heading-scale` | `1` | multiplies the ladder only; the x-height compensation and the one-row line box stay automatic |

**Rounding is to 2px, not 1px.** `--dotgrid-offset-y` adds *half* the row's
growth, so an odd row puts the baseline 0.50px off. Measured at every base in
the 10–30 clamp: exact at even rows, -0.50px at odd ones.

### Tier 3 — not exposed

- The `x 1.1556` x-height compensation. Derived from two font metrics.
- `--dotgrid-offset-y`. Derived; a wrong value is invisible and fatal.
- The 2px rounding itself. Mechanism, not preference.

## Architecture

**The setting and the value the theme uses are never the same variable.**
Style Settings writes an input; the theme consumes a derived value.

```css
body {
  /* Inputs. Style Settings writes these. */
  --midori-set-measure: 34;
  --midori-set-leading: 1.5;
  --midori-set-indent: 2;

  /* Derived. The theme consumes only these. */
  --file-line-width: calc(var(--font-text-size) * var(--midori-set-measure));
  --midori-indent:   calc(var(--midori-set-indent) * 1em);
  --midori-row: 24px;          /* the plain fallback, OUTSIDE the query */
}
@supports (line-height: round(up, 25px, 2px)) {
  body {
    --midori-row: round(up, max(24px, var(--font-text-size) * var(--midori-set-leading)), 2px);
  }
}
```

This is what makes the no-broken-grid rule enforceable rather than
aspirational: there is no path from a user value to a rule that does not pass
through a `round()`. It is also directly testable — **no theme rule may
reference a `--midori-set-*` variable.**

**Every snapped variable needs the `@supports` pair.** A custom property parses
as an arbitrary token stream, so `--x: 24px; --x: round(...)` hands the second
declaration to every consumer regardless of support, and the failure lands at
each use site as invalid-at-computed-value-time. `var(--x, 24px)` does not
rescue it — var()'s fallback is for an *undefined* property. The existing
`test_row_has_a_plain_fallback` guard must generalise to every new snapped
variable.

**Defaults live in the CSS.** Style Settings persists only deviations, so a
user who never opens settings sees exactly the shipped design, and uninstalling
the plugin restores it rather than orphaning state.

## Testing

**Static** — extends `tests/test_prose_typography.py`, stdlib only as before:

1. The `@settings` YAML parses.
2. Every `id` in the block maps to a variable or class the stylesheet defines.
3. No theme rule consumes a `--midori-set-*` directly.
4. Every snapped variable has a plain declaration outside its `@supports`.

**`test_measure` changes subject.** It currently asserts the shipped value is
between 55 and 75 cpl, and parses `calc(var(--font-text-size) * N)` with a
regex that the new three-factor expression will not match. Once the measure is
a setting, "the value" is whatever the reader chose, so the test can no longer
assert it. It must assert instead:

- the **default** is inside 55–75, and
- the **slider bounds** in the `@settings` block are inside 40–100, and
- the conversion still resolves numerically rather than in `em`.

This is the general pattern for every knob: a guard over a constant becomes a
guard over a default plus a range. Losing that distinction would silently
delete the band check rather than widen it.

Each new guard must be proven non-vacuous by sabotage: break the property on a
scratch copy and require the test to fail naming it. A guard accepted on
reading alone has already passed here while the thing it named was broken.

**Rendered** — the instrument this repo does not yet have, and the reason two
real defects survived nine tasks and a whole-plan review:

5. A matrix sweep in a browser over leading {1.5, 1.6, 1.75} x base {10..30} —
   63 combinations — asserting the row is always even and >= 24, and every line
   box is a whole number of rows.

Drive it over the Chrome DevTools Protocol against a running Obsidian
(`open -a Obsidian --args --remote-debugging-port=9222`), reading computed
styles and element boxes rather than inferring them from pixels. A harness that
rebuilds the theme's DOM does not rebuild CodeMirror's, and CodeMirror's own
furniture is where the last two defects lived.

## Out of scope

- **Body font.** Changing the face breaks both the x-height compensation and
  the iOS metric normalisation (WebKit ignores `@font-face` metric overrides,
  so normalisation is rewritten into the woff2 binary and does not generalise
  to an arbitrary user font). Decided explicitly: Spectral and M PLUS stay
  fixed. Font support is a separate project with its own spec if it is ever
  wanted.
- **Reopening the palette.** The accent select offers the eight existing
  tokens. Adding a ninth hue is governed by the closed-palette argument in the
  README.
- **Settings for the companion plugins** (`midori-caret`, `midori-timer`,
  `midori-confetti`, `zen-toggle`). They have their own settings tabs already.

## Risks

- **Style Settings is third-party.** Mitigated by the block being inert without
  it, but the plugin could change its YAML schema. The contract is the
  `--midori-set-*` variables, not the block; a different front end could write
  the same variables.
- **The heading-scale knob interacts with a known defect.** An h1's line box in
  Live Preview already floors at 25px against a 24px row, because 1.870em is
  29.92px and the glyph box is 26. Raising the heading scale makes that worse.
  The slider's upper bound should be chosen with that measured, not guessed.
