# Midori Timer: the caret carries the session

**Date:** 2026-08-15
**Status:** design, awaiting review
**Replaces:** the edge rail (`display: 'rail'`), shipped in `7dcdd64`

## The problem

Six visual treatments have been built and rejected:

1. A dotted rail inside the note's edge.
2. The same rail as a solid gradient line.
3. A warming page-wide atmosphere glow.
4. Tinting the dot grid itself.
5. A corner bloom.
6. Discrete marks appearing at session breakpoints.

Each rejection was read as a tuning problem and answered with a better-tuned
version of the same idea. That was wrong six times, which means the category was
wrong, not the tuning.

## What the rejections actually share

The decisive constraint arrived last and explains all six:

> "I don't want to pull the writer out of the zone. 'New' things appearing on
> screen as the timer goes that are not prompted by the writer are an issue."

Nothing may enter the visual field unbidden. That leaves exactly two legal
categories:

- a **property change to something already on screen**, or
- a **reveal the writer asked for**.

Every rejected design was new matter on the page, persisting for the whole
session. Design 6 was worse on this axis, not better: it removed the persistence
but added an actual event.

The earlier stated goal — "ambient presence, I should never have to read it" —
was a correct description of the *job* and a misleading guide to the *form*. It
was read as licence to paint something quiet. The constraint above is the real
requirement, and it forbids painting anything at all.

## Evidence

A deep-research pass returned 25 candidate claims; adversarial verification
killed 72 of 75 verdicts. The recurring verdict was "NUMBERS CHECK OUT,
INFERENCE DOES NOT" — sources were downloaded and quotes checked
character-for-character, so the *facts* held and the *design inferences* bolted
onto them did not. Treat the below as constraints, not as a mandate; the design
leap is ours.

**McCrickard, Catrambone & Stasko, INTERACT '01** (N=70, N=91), peripheral
display types measured against a primary task:

| Type | Mechanism | Monitoring cost |
|---|---|---|
| blast | appears in place | 88.85s |
| fade | fades in place | 117.41s |
| ticker | continuous motion | 192.93s |

F(2,52)=17.24, p<.001. Continuous motion costs 2.2x an in-place mark. Ticker won
on hit rate (F(2,96)=3.87, p=.03) with no false-alarm penalty (p=.58).

**The caveat, which survived peer review into IJHCS 58(5), 2003:** that result
holds for *browsing* primary tasks. Maglio & Campbell (2000) found all animated
peripheral displays distracting to the primary task of **document editing** —
"though the start-and-stop display was the least distracting." Cutrell et al.
(2001) corroborates that disruption rises with primary-task cognitive intensity.

Writing essays is the document-editing case. This retired the "slow breath"
proposal, which was the ticker condition in the one task class where animated
peripheral displays are known to be disruptive.

**Janaka et al., CHI '22** — paracentral and near-peripheral placement for
attention-maintaining secondary information — survived verification and is the
reason placement, not styling, was the thing to change.

## The design

**The caret carries the session. Nothing else on screen changes.**

- **Idle:** byte-identical to today. Indigo caret, no timer artifacts anywhere.
- **Running:** the caret's colour drifts indigo → sage → ochre → wine across the
  session, by continuous interpolation. There is no step, no event and no moment
  at which a change is visible *happening*. The caret is simply a different
  colour than when it was last registered.
- **Paused:** the colour holds. A pause is the absence of change, which is what
  a pause is.
- **Finished:** the session clears and the caret returns to indigo, alongside the
  existing Notice and chime.

Nothing enters the field at any point, because the caret was already there — the
writer summoned it by placing the cursor.

### Why the caret specifically

- **It is the one thing in foveal vision.** Every prior design was peripheral,
  which is where colour discrimination is worst. The caret is where the eye
  demonstrably rests while writing, so a change legible at 1.5px there would be
  invisible anywhere else on the page.
- **It adds nothing.** `midori-caret` already draws it as a real, stylable
  element. This is a property change to existing matter — the first legal
  category above.
- **It self-limits.** The caret exists only while the editor has focus. Reading
  in preview, or working in another app, it is not there at all, so it cannot
  distract when the writer is not writing.
- **It is already the theme's.** Resting colour is `--midori-indigo`
  (`#3a5572` Paper, `#6c87a4` Night) via `--color-blue`, so the drift departs
  from a real baseline rather than nudging within one.

### Colour

Stops, as fractions of the session elapsed:

| t | colour | variable |
|---|---|---|
| 0.00 | indigo | `--color-blue` |
| 0.40 | sage | `--interactive-accent` |
| 0.80 | ochre | `--color-yellow` |
| 1.00 | wine | `--color-red` |

Interpolated with `color-mix(in oklch, …)` between the two bracketing stops.

**oklch, and not for the usual reason.** The design originally specified oklab on
the standard argument that sRGB is not perceptually uniform. Measured off a
render of this exact ramp, that argument does not apply at this scale: sRGB and
oklab differ by at most ΔE 0.029 across all twelve samples — about a JND on a
large swatch, nothing on a 1.5px caret.

The defect the render did find is different. Indigo and sage sit on opposite
sides of neutral in the a–b plane, so a straight line between them — in sRGB or
oklab alike, both rectangular — passes *nearer the achromatic axis than either
endpoint*:

| t | 0 | 0.10 | 0.20 | 0.30 | 0.40 |
|---|---|---|---|---|---|
| oklab chroma | 0.058 | 0.042 | 0.029 | **0.024** | 0.033 |
| oklch chroma | 0.054 | 0.049 | 0.043 | 0.036 | 0.032 |

The oklab minimum falls *below* sage's own 0.033. About a third into a session
the caret would go grey — which reads as the caret losing its colour, not as
time passing. oklch interpolates hue angle and chroma separately, rounding the
corner instead of cutting across it, and stays monotonic into sage. Same result
in Night (min 0.025 → 0.033).

A unit test can only assert which space was *asked for*; the rendered check is
what caught this.

**Theme variables, not hex:** `color-mix` accepts `var()`, so the drift resolves
per-theme and follows Paper and Night for free, with no second table of
dark-mode colours to keep in sync.

### The CSS hook

The timer owns the caret's colour without touching `theme.css` or
`midori-caret`:

```css
body.midori-drawn.midori-timer-running .midori-cursor::before,
body.midori-drawn.midori-timer-running .midori-title-caret {
  background: var(--midori-timer-caret);
}
```

Specificity (0,3,2) beats the theme's own (0,2,2) rule, and document order is
not relied on — which matters, because Obsidian hot-reloads theme CSS but not
plugin code, so the two can be out of step for a reload cycle. The rule is gated
on a class only the timer sets, so it is inert whenever no timer is running.
`--midori-timer-caret` is set on `body` by the plugin.

The title caret inherits the treatment at no extra cost, since
`.midori-title-caret` takes its colour from the same declaration.

**And the same display without `midori-caret`, or under another theme.** As
first shipped this was a hard dependency: `midori-drawn` is set only when the
Midori stylesheet is loaded *and* `midori-caret` is enabled, so under any other
theme the caret display was silently inert. That was a misreading of what
`midori-caret`'s own gate is for. It gates itself because it replaces caret
**geometry**, and the constants it uses are `theme.css`'s. Colour is not
geometry: the native caret has taken `caret-color` since forever. A second rule
paints it directly wherever the drawn one is absent:

```css
body:not(.midori-drawn).midori-timer-running .markdown-source-view .cm-content,
body:not(.midori-drawn).midori-timer-running .inline-title {
  caret-color: var(--midori-timer-caret, var(--caret-color));
}
```

`:not(.midori-drawn)` makes the two branches mutually exclusive, which matters
because `theme.css` paints the native caret transparent wherever the drawn one
is present. Specificity is (0,4,1) and (0,3,1) against Obsidian's own (0,3,0);
a theme with a heavier opinion about the caret still wins, which is correct.
The plugin already writes `--midori-timer-caret` to `body` unconditionally, so
nothing in the JavaScript changes.

### Update cadence

The existing 250ms tick drives the readout. The caret colour is recomputed on
the same tick but **written only when the mix percentage within the current
segment changes by at least 1 point** — 100 writes per segment, 300 across a
session, against 6000 ticks: about one style write every 5 seconds on the two
10-minute segments and every 3 on the final 5-minute one, with no perceptible
difference. Nothing here is animated in CSS;
there is no transition, because a transition would be the thing the design
exists to avoid.

## What is removed

- `display: 'rail'` and every rail setting (`railEdge`, `railThickness`,
  `railTrack`, `railInset`).
- `clipToChrome`, `positionRail`, `scrollerEl`, `CHROME`, `CHROME_GAP` and the
  rail's CSS block — roughly 150 lines, including all the mobile placement
  machinery, which stops being a problem rather than being solved.
- The `display` setting becomes `caret` | `statusbar` | `both`.

## What is kept

- The absolute-deadline timekeeping. Untouched, and still the load-bearing part.
- The typed-duration modal and every command.

## Addendum, same day: the setting window

The window that *sets* the session was redesigned alongside this, and none of it
touches the display above — it produces a number of seconds and hands it to the
same machinery.

- **Drums, not a text field with a dial bolted on.** A row of scroll containers
  with `scroll-snap-type: y mandatory`, so momentum, rubber-banding, wheel,
  trackpad inertia and touch flinging are the platform's. Hours, minutes and
  seconds, which makes everything under a day reachable by dragging.
- **Split-flap readout**, flipping only the cells whose glyph changed — the
  same board, at one seventh the size, now also reads the countdown in the
  status bar. That is a deliberate exception to the no-motion argument above
  and is scoped to it: the status bar is opt-in, it is outside the note, and
  the flip is a setting that is off under Reduce Motion. The writing surface is
  still untouched.

  **A phone gets none of it, and that was tested rather than assumed.**
  Obsidian hides the status bar on mobile, so the readout was homed in the
  note's own header instead — existing chrome, not the writing surface, and
  therefore inside the rules above on paper. In use it was removed on sight.
  The header is where the eye goes to *leave* the note; a countdown parked
  there is a persistent thing to look at that nobody asked to see, which is the
  same objection that retired the six painted designs. The tell was in the
  building: four rounds of geometry and specificity fights to make it sit in a
  row it did not belong in. On a phone the caret is the whole display.
- **Two modes: *for* a length, or *until* a clock time.** Both are how a session
  is actually held in the head, and neither is a sub-mode of the other, so it is
  a segmented control with two sets of drums. Until-mode carries hour, minute
  and — where `Intl` says the locale is 12-hour — a meridiem column; it works
  out the exact hours, minutes and seconds remaining, and the flaps show that
  *duration* in both modes, so spinning a target time visibly assembles the
  countdown. The deadline is recomputed when Start is pressed, not when the
  target was picked.
- **One value underneath.** `seconds` is the only state; the mode decides how it
  is arrived at and described. Switching modes seeds the other set of drums from
  the current value, so the switch is a change of framing, not a reset.
- **Typing remains first-class**, and now parses per mode: `parseDuration` for
  *for*, `parseClockTime` for *until*.
- The status-bar readout, as the on-demand number.
- Self-reset on finish, and the Notice, chime and optional system banner.

## Open question for review

**Should the ending be silent too?** The finish Notice is, strictly, something
appearing on screen unprompted. It is also the event the timer was set for, and
it has never been objected to. Kept as-is unless told otherwise.

## Testing

- Unit: the stop table and interpolation — bracketing stop selection at
  t = 0, 0.39, 0.40, 0.41, 0.80, 1.0 and outside [0,1]; the 1%-threshold write
  suppressor; `parseDuration`/`formatClock` round-trips as today.
- Rendered: caret colour sampled from a real screenshot at several t, in Paper
  and Night, confirming the drift is monotonic in the intended direction and that
  no intermediate value goes muddy. This is the check that catches an sRGB
  regression, which unit tests cannot see.
- Manual: idle state byte-identical to a pre-change screenshot; caret returns to
  indigo on finish; nothing appears anywhere at any point in a full session.
