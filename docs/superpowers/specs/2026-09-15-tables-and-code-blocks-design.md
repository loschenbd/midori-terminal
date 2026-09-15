# Midori tables and code blocks

**Date:** 2026-09-15
**Status:** design — approved in conversation, not yet planned
**Goal:** Tables that are readable and hand the grid back intact, and code
blocks whose text never runs into the edge of its own background. Both in live
preview and reading view.

Everything below marked *measured* was taken from the running app (Obsidian
1.13.7, Mud & Silicon vault, `Midori Block Reference.md` in live preview, base
16px, row 24px, measure setting 85 = a 655px column in a 1428px pane) over CDP.
Mockups were rendered in that app, on the note's own lattice, from clones of
the note's own table widget; the note and the theme were not modified.

## The problem

### Tables are off the grid

*Measured:* the reference note's five-row table is **122px**, not 120. A dense
four-column table is 410px, not 408. Everything below a table sits 2px off the
dots for the rest of the note. The header row and the last row are 24.5px each,
and cell text sits 1px off.

The cause is four Obsidian variables, all `1px` in 1.13.7:
`--table-header-border-width`, `--table-row-last-border-width`,
`--table-column-first-border-width`, `--table-column-last-border-width`. The
app.css rules that consume them (`thead tr > th`, `tbody tr:last-child > td`,
`td:first-child`, `td:last-child`) out-specify the theme's
`.markdown-rendered td { border-width: 0 }`, so a 1px top border on the header
and a 1px bottom border on the last row come back. In a collapsed-border table
each adds half its width to its row and half to the table.

*Measured:* setting the four variables to `0px` gives exactly 120px in live
preview (on the real widget, then reverted) and in reading view (an offscreen
`.markdown-rendered` table).

The comment above the table rules in `theme.css` ends *"Verified: the widget
went 7.042 -> 8.000 rows."* That does not hold on 1.13.7. Whether it held when
written and Obsidian added these variables since, or whether it never did, is
not established; the correction must say which is known.

### Tables are hard to read

- Cells have no vertical padding and 8px horizontal; the rules are
  `rgba(60,58,54,0.1)`, nearly invisible, and the horizontal ones fall between
  dot rows. The dots show through every cell. The header differs only by
  weight.
- The tables actually written in these vaults are prose tables. *Measured
  across all vaults:* 93 notes contain tables; the densest have cells of
  300–460 characters and up to 7 columns (CFA, job-search). Obsidian's automatic
  column sizing squeezes such a table into the 655px column at 90 / 247 / 162 /
  155px per column: about 30 characters per line, and one cell ran 8 lines.
- Blank lines between paragraphs render at `line-height: 0` (the paragraph-
  indent rhythm), so a table sits directly against the heading or paragraph on
  either side.

### Code text runs into the edge

Code does not overflow sideways; it wraps in both views. *Measured in live
preview:*

- Code lines have `padding-left: 16px` and `padding-right: 0`. Wrapped text
  ended as close as **2.2px** from the right edge of the background.
- A wrapped line continues flush left (wrap indent 0), even when the source
  line was indented, so a continuation reads as a new line.
- Long tokens break anywhere (`overflow-wrap: anywhere`); a path broke as
  `...memberships.sq` / `l`.
- The language label (`.code-block-flair`, absolutely positioned 6px from the
  top with 4px vertical padding) is **32px** tall inside the 24px fence row and
  overlapped the end of a long first line.

*Measured in reading view* (offscreen `pre`): `white-space: pre-wrap` and
`overflow-wrap: break-word`, so content never exceeded the `pre`'s width. The
`pre` already pads both sides. The hover copy button (6px margin + 6px padding,
absolutely positioned) sits over the first code line the same way the flair
does.

*Measured across all vaults:* 43 notes have fenced lines over 70 characters,
up to 332.

## Decisions

### Tables: the ruled grid, fixed (treatment C)

Chosen from three treatments rendered side by side in the app:

- **A, book rules:** horizontal rules only, a blank row between records, small-
  caps headers, cell text on the dots.
- **B, banded rows:** no rules, alternating tinted bands with a half-row bleed,
  cell text on the dots.
- **C, ruled grid, fixed:** chosen.

**Width, decided before the treatments:** tables may break out wider than the
text column (prose keeps its measure). Rejected: staying inside the column
(dense tables stay eight lines deep) and scrolling sideways at a minimum column
width.

The design:

1. **Grid.** The four border variables above are set to `0px`; that is the
   2px fix. The theme comment is corrected as described.
2. **Geometry.** Every cell gets half a row of padding on all four sides, so a
   row is `row × (lines + 1)` tall. Cell text therefore sits exactly half a row
   off the dots, which was seen and accepted in the mockup. Rules stay painted
   (inset box-shadows and an outline), not laid out. The table block gets one
   row of padding above and below, so it no longer touches its neighbours and
   still totals whole rows. Half a row is always a whole pixel because the
   theme already rounds the row to an even number (see "TWO PIXELS, NOT ONE"
   in `theme.css`).
3. **Look.** Rules are `color-mix(in srgb, var(--text-normal) 28%, transparent)`.
   The header band is `color-mix(in srgb, var(--text-normal) 9%,
   var(--background-primary))`. Cells take `var(--background-primary)`, so no
   dots show inside the table. The header keeps the body face at weight 600.
   Every colour derives from theme variables, so dark mode needs no separate
   values; it is still checked by eye.
4. **Width.** At least the text column. A table whose content needs more grows
   symmetrically about the column, to at most `min(1.6 × column, pane − 96px)`
   (1040px here). When that ceiling is below the column (a pane narrower than
   the column plus 96px) the column wins: the table never gets narrower than
   the prose beside it and never breaks out. Past the ceiling, Obsidian's
   existing sideways scroll inside the widget applies.

   *Measured feasibility (live preview):* widening the real widget to 1040px
   in a 1428px pane was not clipped (both edges hit-tested), did not make the
   editor scroll sideways (scroller 1428/1428), and did not change the widget's
   height. How CSS obtains the pane width, and the reading-view equivalent, are
   not yet proven. See "Open for the plan".

*Measured in the C mockup:* short table 288px = 12 rows, spanning the 655px
column; dense table 408px = 17 rows at 1040px; cell text +12px against the
lattice; the paragraph after each table 0px off.

### Code blocks

1. **Right padding (live preview).** Code lines get right padding equal to the
   left, so wrapped text never meets the edge. Reading view already has it.
2. **Wrapped continuations (live preview).** A wrapped line continues indented
   by two characters from its own start. Reading view renders a block as one
   run of text with no element per line (app.css has no per-line code
   selectors), so it keeps plain wrapping. Not attempted there.
3. **Label and copy button.** The live-preview language label and the reading-
   view copy button fit inside the empty row above the code and overlap no code
   text.
4. **Spacing.** One row above and below each code block, matching tables,
   still totalling whole rows.

**Not changing, and why:**

- **Wrapping stays.** In live preview every code line is its own editor line,
  so one block cannot get its own horizontal scroller.
- **Long tokens still break wherever they meet the edge.** CSS cannot prefer a
  break after `/`.

## Out of scope

- The visible HTML comments (`<!-- -->`) and the paragraph indent they pick up,
  seen in the cover-letter screenshot that opened this work.
- Style Settings controls for tables or code blocks.
- Treatments A and B.

## Open for the plan

These need a measurement before code is written, not a guess:

- **Pane width in CSS.** The candidates are container query units on an
  ancestor (container-type has layout side effects; a container query with no
  container silently does nothing) or viewport units less the sidebars. Prove
  the choice in both views before adopting it.
- **Reading-view breakout.** Whether `.markdown-preview-sizer` or its ancestors
  clip a table wider than the column.
- **Spacing around code in live preview.** CodeMirror lines cannot take
  margins. The row above and below has to come from padding on the fence lines
  without painting the code background into it, and the rounded corners have
  to survive.
- **Hanging indent mechanics** on `.HyperMD-codeblock` lines (padding plus a
  negative `text-indent`), and whether it disturbs caret placement or the
  fence lines.
- **Dark mode and a narrow pane**, checked in the app.

## Verification

This repo's checks have passed while examining nothing, so each new check must
fail when its target is deliberately broken, naming what was broken, before it
is trusted.

- **Static (in `tests/lint.sh`).** The four border variables are `0px`; cell
  padding is half a row. It must fail when either is removed.
- **Rendered (like `tests/check_rendered_grid.py`; not in lint, needs
  `--remote-debugging-port=9222`).**
  - Tables and code blocks total whole rows.
  - The paragraph after each is 0px off the lattice.
  - No wrapped code text comes within 16px of the right edge.
  - The label and copy button overlap no code text.
  - It selects the window by content, prints what it measured, and fails on an
    empty input set.
  - It must fail against a sabotaged stylesheet (border variables restored to
    `1px`; right padding removed).
- **By eye:** light and dark, wide and narrow pane, both views.

Installing into the vaults happens after the checks pass, through the
unchanged `install.sh` / `obsidian/install-obsidian.sh`.
