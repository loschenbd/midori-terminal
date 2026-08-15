# midori-terminal

A complete terminal theme system built on the Midori design language from
[benjaminloschen.com](https://benjaminloschen.com) — warm paper neutrals and a
sage accent, taking their cue from Japanese MD-style notebook stock. It covers
Ghostty, Claude Code, tmux, herdr, fzf, oh-my-posh, Vivaldi, Cursor/VS Code,
Obsidian and Antinote, all switching light/dark together with macOS appearance.

**Midori Paper** (light) · **Midori Night** (dark)

## Quick start (new machine)

```sh
git clone https://github.com/loschenbd/midori-terminal.git
cd midori-terminal
./install.sh
```

Then restart Ghostty. Vivaldi is set up by `install.sh` too (themes, CSS mods,
and the canonical keyboard shortcuts from `vivaldi/keyboard.json`) — but only if
Vivaldi is closed, since it rewrites its config on exit. To choose which
profile(s) get the treatment, quit Vivaldi and run `./vivaldi/install-vivaldi.sh`
for an interactive profile picker (`--profile "Artisan Studios"` / `--profile all`
to skip the prompt). After tweaking hotkeys in Vivaldi's UI, re-export them with
`./vivaldi/export-keyboard.sh` so the repo stays the source of truth. For Cursor/VS Code: `./vscode/install-vscode.sh`
(it prints the settings snippet to wire up auto light/dark + icons). For
Obsidian: `./obsidian/install-obsidian.sh`. For Antinote:
`./antinote/install-antinote.sh`, then Settings → Visuals → "Reload Custom
Themes". herdr is handled by `install.sh` too (skipped when it isn't installed) —
see `herdr/README.md`, which explains why herdr is the one component with no
`midori-paper`/`midori-night` theme files.

Safe to re-run `./install.sh` any time (it's idempotent) — that's also the
update path: `git pull && ./install.sh`.

## How it works — two layers

**Layer 1 — infrastructure (theme-agnostic).** The seam is ANSI-16: the
Ghostty theme pair (`theme = light:midori-paper,dark:midori-night`) is the
single source of truth for color. Everything downstream — the oh-my-posh
prompt, fzf, tmux status — speaks ANSI color names/indices, so it retints
automatically when macOS appearance flips. Two things can't ride that seam
and get a helper daemon (`watcher/midori-claude-theme.sh`, launchd):

- **Claude Code** needs its custom theme's `base` flipped between
  `light`/`dark` (written to `~/.claude/themes/midori.json` with the full
  Midori token overrides, diff washes included).
- **tmux pane borders** need per-mode hexes — no single ANSI slot reads as a
  subtle hairline in both modes.

The watcher also checks the main display's scale (~30 s) and flips the
background symlinks between `@1x`/`@2x` assets (see below).

**Layer 2 — the Midori theme pack.** Ghostty themes with baked backgrounds,
the Claude Code token map, tmux border hexes, and the Vivaldi themes. Swap
this layer to re-skin everything without touching the infrastructure.

## The accent palette

Every surface here draws from one named set, mirrored from
`benjaminloschen.com`'s `app/globals.css` (which is the source of truth):

| Token | Light | Dark | Role |
|---|---|---|---|
| `--midori-indigo` | `#3a5572` | `#6c87a4` | links, `function` |
| `--midori-olive` | `#6c7d52` | `#9eaf85` | `string` |
| `--midori-wine` | `#7a4a4a` | `#b8868a` | ANSI red, `operator` |
| `--midori-ochre` | `#b88a3a` | `#d8b06a` | ANSI yellow, `value` |
| `--midori-sage` | `#5f6f5e` | `#9aab97` | the UI accent |
| `--midori-purple` | `#653f7f` | `#a079be` | ANSI magenta, `keyword` |
| `--midori-mint` | `#548373` | `#9ebfb4` | ANSI cyan, `property` |

plus a warm ramp (wash → light → clay → terracotta → deep) and
`--midori-mythic` for unresolved/faint text.

**Purple is new (Aug 2026), and the old one was broken.** The site had no
purple token, so this repo derived a plum (`#664f63` / `#a48ba3`) for the ANSI
magenta slot; it spread to seven surfaces and drifted to `#7f5a74` in one.
Measured in OKLCh it sat **0.6 lightness and 2.2 chroma from wine** — well
under the C 12 mark where hue stops doing any work at body size, so `keyword`
and `operator` read as a single colour in a code fence. The replacement is not
a chroma *lift above* the palette but a lift *up to* it: C 10.9, where ochre is
11.1 and terracotta 9.9 and the old plum was the outlier at 4.3. Hue 310 clears
wine by ~70° and indigo by ~59°, the two neighbours it has to beat.

Dark is L 64, not the 65 a straight mirror of light would give: on the charcoal
ground terracotta rises to L 70, and *every* close neighbour sits above purple,
so dropping a point widens all four gaps at once. It still reads 5.00:1.

Two surfaces deliberately don't follow:

- **Obsidian dark** uses the dot-grid mint `#9ebfb4` as `property` ink rather
  than `--midori-mint`. The site's dark mint lands at L 71.2 / C 5.7 and
  indigo-lift at L 70.6 / C 6.3 — 0.6 apart on both axes. Light has no such
  problem and uses the real mint.
- **Antinote** keeps its own 331° purple — see `antinote/README.md` for the
  measurements. It is the one palette here that separates on hue rather than
  lightness, and 310° would move it *toward* its blue.

### The palette is closed

Purple was the last slot. Don't add an eighth accent without re-reading this —
the instinct is to look for an empty hue, and hue is not the constraint.

**The ANSI-16 seam has six chromatic slots and all six are filled**: red=wine
20°, green=olive 144°, yellow=ochre 78°, blue=indigo 251°, magenta=purple
310°, cyan=mint 171°. A new hue has nowhere to live downstream — every surface
here speaks through that seam.

**Lightness, not hue, is what ran out.** VS Code Paper packs 15 distinct syntax
colours into L 27.8–54.1 — 26 points of range at a mean gap of **1.9**. Night
packs 16 into L 62.6–93.2 at a mean gap of **2.0**. Neither has one rung
10 points wide. Below C 12 hue does almost no work at body size, so an eighth
accent would have to share a rung with an existing role and would read as a
duplicate of it no matter how far apart their hues are.

Four hue gaps ≥40° do exist (102°, 211°, 280°, 345°) and none is usable. The
two widest are also the worst real estate: hue 211° has a ceiling of only
**C 7.8** at L 45, the muddiest region of the wheel. Two candidates in these
gaps were already priced and rejected — see the 289° and 212° note under
"Cursor / VS Code notes".

**If a future role genuinely needs its own colour**, the lever is not a new hue.
It is the one control flow already used: take an *extreme* lightness rung and
buy separation with chroma. That is how `#175a98` got in at C 12.0 / L 46.1
without colliding with anything.

## What's in the box

| Path | What |
|---|---|
| `ghostty/` | Main config, `midori-paper`/`midori-night` themes, background PNGs, rounded-cursor shader |
| `watcher/` | Appearance/display watcher script + launchd plist template |
| `prompt/midori.omp.json` | Manuscript-style oh-my-posh prompt (ANSI names only, no powerline blocks) |
| `shell/zshrc.midori` | omp init, fzf ANSI palette, eza aliases, zoxide, zsh autosuggestions/highlighting, cursor-color reset (sourced from `.zshrc`) |
| `tmux/midori.tmux.conf` | Pane borders, status/message styles (sourced from `.tmux.conf`) |
| `vivaldi/` | Midori Paper/Night browser themes, typography CSS mods, installer |
| `vscode/` | Cursor/VS Code extension: Midori Paper/Night color themes, file icons recolored from Material Symbols Rounded (Apache-2.0), workbench-chrome product icons built from Phosphor (MIT) — see `midori-theme/CREDITS.md`; `build-icons.py` / `build-product-icons.py` regenerate — plus installer |
| `antinote/` | Midori Paper/Night Antinote themes (24-key JSON), installer, and a transcription of Antinote's undocumented theme schema |
| `obsidian/` | "Midori" Obsidian theme (palette, dot grid, page glow, embedded metric-normalised fonts), the `midori-caret`, `midori-confetti` and `midori-timer` companion plugins, installer for iCloud vaults; `build-fonts.py` regenerates the embedded faces |
| `moshi/` | Midori Paper/Night for [Moshi](https://getmoshi.app) (the phone terminal for agents) — **generated** from the Ghostty themes by `build-moshi-themes.py`, which also publishes them to iCloud for the phone |
| `fonts/` | M PLUS 1 Code (terminal), M PLUS 1p + Spectral (UI) — SIL OFL 1.1 |
| `tools/bake-backgrounds.py` | Regenerates dot tiles + glow washes for new displays |

Fonts follow the site's semantic split: **Spectral** is the naming voice
(titles, headers), **M PLUS** is the working voice (text you read and type).

**Spectral was re-examined in Aug 2026 and retained.** Twenty-seven libre
serifs were measured against M PLUS straight out of the font binaries, and on
metrics Spectral loses: its x-height is 454 against M PLUS's 520, so at the
same font-size a title reads about 13% smaller than the body beneath it, and
no variable font exists or is coming — fourteen discrete statics, no `wght`
axis. Literata at a low optical size wins that comparison outright (x-height
within 2% of M PLUS at *every* opsz, stem 53 vs 50).

It was kept anyway, for two reasons a metrics table cannot see. Spectral's
−10° italic carries the sublines and Literata's is −2°, near-upright by
design. And **this repo is pixel-tuned to Spectral specifically**: the caret
and selection band constants in `obsidian/theme.css` are derived from
Spectral's measured ink at the title size (19.41px above the baseline, 6.21px
below at 25.888px, giving the `0.83em / 0.30em` offsets), the h1–h4 line-box
struts come from Spectral's *natural* boxes, and `midori-caret` shares those
numbers. Swapping the face invalidates all of it, because a natural line box
comes from the font's own ascent and descent. The general rule, since it will
recur: before replacing any component, grep for constants derived from the
incumbent — a comparison that only looks at the candidates understates the
cost of moving.

If a title ever reads too small, headings can absorb a size bump: the 48px
line box has headroom over their ~24.5–27.5px natural boxes. The note title is
the one to leave alone; its 24px box is tight.

## How the dot grid stays aligned (Ghostty)

**The dots are drawn by the cursor shader, not the background image.**
`ghostty/shaders/rounded-cursor.glsl` anchors the lattice to the live cell
geometry Ghostty reports via `iCurrentCursor`: pitch = cell height, rows = the
text baseline. Dots therefore track the text rows *by construction* on any
display, at any cell height — there is no phase to calibrate. The baked
`*-glow` images carry only the low-frequency washes
(`tools/bake-backgrounds.py --without-dots`); the `*-dots` tiles are retired.

Glow images still render at **physical pixels** (`fit = none`), so the watcher
flips `@2x`/`@1x` symlinks when the main display class changes — Ghostty only
re-reads images on config reload, so hit **Cmd+Shift+,** after
docking/undocking.

Residual gotchas:

- `adjust-cell-height` nudges the row pitch toward the 24 pt rhythm, but
  Ghostty integer-izes the *base* cell height before applying the percentage
  (35 px × 1.37 → 48, not 34.585 × 1.37) and applies it **at app startup
  only**. An off-by-one no longer breaks alignment — the shader follows
  whatever the cell is — it only nudges the rhythm off 24 pt. Coupled to
  font size.
- The font family must be exactly `"M PLUS 1 Code"` — a wrong name silently
  falls back to JetBrains Mono and changes the cell metrics.
- Dots disappear in full-screen TUIs that hide the cursor (no cursor uniform,
  no anchor) — a known trade-off.
- Box-drawing rules (TUI separators) render at cell *center* and can never
  share the baseline lattice — expected, not a bug.
- The themes set `cursor-color` to the exact background hex **on purpose**:
  the native cursor composites after the shader and the hollow unfocused one
  ignores `cursor-opacity`, so bg-on-bg hides every native draw and the
  shader substitutes the indigo ink when it sees that sentinel. Don't "fix"
  the cursor color in the theme files.

## How the dot grid stays aligned (Obsidian)

Nothing like the Ghostty story: there is no shader and no cell geometry to
anchor to, so the grid is a CSS background and the phase **is** calibrated.

**`background-attachment: local` on `.cm-scroller`** is what makes it work. A
background on a scroll container defaults to `scroll`, which pins it to the
viewport and lets text slide over stationary dots. Painting on `.cm-sizer`
scrolls correctly but is clipped to `readable-line-width`, so the texture stops
at the prose edges. `local` re-anchors to the scrolled *content*: the dots
travel with the text **and** fill the pane edge to edge.

**`background-origin: content-box`** is what makes one phase serve every
device, and it answers a different question from `local`. The default origin,
`padding-box`, sits above the element's own `padding-top` — and Obsidian puts
`padding-top: var(--view-top-spacing-markdown)` on exactly the elements the
grid is painted on, resolving through `env(safe-area-inset-top)`: 59px on a
Dynamic Island iPhone, 47px with a notch, 20px on an SE, 0 in landscape. Those
differ mod 24, so with the default origin the phase is a function of which
phone and which way up. `content-box` moves the origin with the padding and the
term cancels, which is why `--dotgrid-offset-y` is one number rather than a
per-device table. It is measured from rendered pixels, not computed: where a
baseline falls inside a 24px row depends on half-leading, which no CSS length
exposes. Desktop and iOS both measure 0.00px off across every line.

**Symmetric font metrics** are what removed the per-heading magic numbers. A
line box seats its baseline at `L/2 + F*(A-D)/2`, and that second term — a
per-font constant times the font size — *was* the ladder of per-level constants
this theme used to carry. `build-fonts.py` emits each family twice: stock, for
interface chrome, and a `Midori …` alias with `A = D = 45%` for prose. The term
vanishes at every size, every baseline lands at exactly `L/2`, and every margin
becomes a plain multiple of 24.

Residual gotchas:

- **The metrics are rewritten in the font BINARY, not declared in CSS.**
  `ascent-override` / `descent-override` / `line-gap-override` are honoured by
  Chromium and **ignored outright by WebKit**, so descriptors alone are correct
  on desktop and silently wrong on every phone. Measured on iOS: setting the
  aliases to `ascent-override: 0%; descent-override: 100%` — which should have
  thrown every baseline half a row — changed nothing at all. `build-fonts.py`
  patches hhea, OS/2 sTypo and OS/2 usWin (all three; which one an engine reads
  is not a theme's choice) so there is no descriptor left for a UA to skip.
- **The alias faces carry no `local()`; the stock faces do.** `local()` on an
  alias hands desktop the Homebrew binary, whose metrics are the stock ones,
  quietly reinstating the descriptor dependency above. The cost is CJK prose
  falling through to the next family in the stack, as it always did on iOS.
- **Fonts are embedded** as base64 Latin subsets at the foot of `theme.css`.
  iOS cannot install fonts, and Obsidian injects theme CSS into a `<style>`
  element rather than `<link>`ing it, so relative `url()` resolves against the
  app document and loose `.woff2` files 404.
- **The caret and the selection band need a plugin** —
  `obsidian/plugins/midori-caret`, fanned out by the installer alongside the
  theme. Obsidian's editor is a plain contenteditable, so both are the
  *browser's*, and the browser derives both from the font's content area —
  which the symmetric metrics centre on the baseline. The caret came out a
  short tick sitting low; the selection band came out a full 24px slab with the
  ink crowded into its top half (1.5px of colour above the ascenders against
  12.25px below the baseline). Neither is reachable from CSS: `caret-color`
  only sets colour, and `::selection` accepts colour properties **only**, never
  height or offset. The plugin hides all four natives and draws replacements
  the theme can size — editor caret, editor band, and the same pair again for
  the note title, which is its own contenteditable outside CodeMirror and so
  misses every rule scoped to `.cm-content`. Uninstall it and the natives come
  back: each replacement is gated on a body class the plugin sets.
- **On iOS the band is drawn under a native one, and shaped to match it.** Both
  replacements work by painting the native out and drawing over it, and on iOS
  only one of the two natives can be painted out. Measured in the Simulator
  rather than assumed: with `::selection { background-color: transparent }`
  applied and computing to `rgba(0,0,0,0)`, iOS still drew its full band with
  handles — the highlight is UIKit's text-interaction UI drawn *above* the web
  content, not a background CSS can reach, on static text as much as in an
  editable. `caret-color: transparent`, by contrast, is honoured (the native
  caret blinked across 4 of 8 frames without it and 0 of 8 with it) because the
  caret is WebKit's own editing code.
- **Confetti fires on the crossing, not the value** —
  `obsidian/plugins/midori-confetti`, also fanned out by the installer, throws
  a burst when a note passes a word target you set. The obvious test, `words >=
  target`, is wrong in a way that only shows up in use: a finished note is
  above its target forever, so opening one and typing a single character would
  set it off. It instead remembers the previous count per note and fires only
  on the transition `prev < target <= now`, seeding `prev` on file-open so an
  already-finished note stays quiet. Particle colours are read from the theme's
  own CSS variables rather than hardcoded, so the burst follows Paper and Night
  without the plugin knowing either exists. Nothing in the community registry
  did this — of 6,478 plugins, Writing Goals draws a progress bar and stops,
  Target Word Count *blocks editing* until you hit your number, and the one
  confetti plugin fires on every keystroke.
- **The timer stores a deadline, not a remaining count** —
  `obsidian/plugins/midori-timer`, a countdown you set either for a length or
  until a clock time, on drums or by typing `25m`, `1h30`, `90s`, `1:30` or
  `1:30pm` into a window a hotkey can open. The obvious
  implementation keeps a `remaining` number and subtracts one per tick, and it
  runs slow by minutes: Chromium — which is what Obsidian is — clamps
  background timers to roughly one wake per minute once a window is hidden, and
  suspends them while the machine sleeps. The bug hides while you watch it,
  because watching it is what keeps the window in front. So the only stored
  quantity is an absolute `endsAt`, and every tick recomputes `endsAt -
  Date.now()`; ticks are then free to be late, coalesced or skipped, including
  across a lid close, and persisting that value is also what lets a restart
  resume the same countdown instead of losing it. The readout uses tabular
  figures *and* reserves the width of the longest form the run will produce,
  because a proportional countdown changes its own width twice a second and
  drags every status item to its left along with it. Finishing *resets*: the
  session clears and the bar returns to its idle clock in the same frame,
  because the end is announced by things that announce themselves and then stop
  — a Notice, the chime, the optional OS banner — and a readout parked at 0:00
  wearing a bell until you click it is a chore, and a lie by the time you come
  back to the desk.
- **The duration window is a drum you flick, reading out on a split-flap clock.**
  Two implementation notes, both learned the hard way. The drum is a *real
  scroll container* — `overflow: scroll` plus `scroll-snap-type: mandatory` —
  which buys momentum, rubber-banding, wheel support, trackpad inertia and touch
  flinging from the platform; the only hand-written part is pointer-drag,
  because a mouse press does not scroll a div, and that drag has to switch
  `scroll-snap-type` off while it runs or every `scrollTop` it sets is yanked
  back to the nearest snap point and the drum judders. And **position and value
  are pure arithmetic in both directions, never measured.** The obvious
  `item.offsetTop - (scroller.clientHeight - item.offsetHeight) / 2` is wrong
  here in a way that hides: `clientHeight` *includes padding*, and this scroller
  is mostly padding — 68px top and bottom so the first and last values can reach
  the centre band. Under content-box sizing `clientHeight` came back 306 instead
  of 170, every scroll landed two items short, and because the drum's scroll
  handler writes what it finds back into state, the window quietly rewrote its
  own default from 25m to 23m on open. A measurement bug in a control that feeds
  itself does not look like a measurement bug — it looks like the setting not
  sticking. Centring item *i* is `scrollTop = 34i`; the inverse is one division.
- **A surface colour that must differ from a ground has to be *derived* from
  it, not named.** The bar's flip cards took three attempts. First
  `--background-modifier-form-field`, which the setting window's cards use —
  invisible, because a status bar is `--background-secondary` and the two sit a
  hair apart, so all that survived was the seam: a hairline through the middle
  of every digit, reading as a strikethrough. Then `--background-primary`,
  which fixed the harness and not the app, because this theme sets
  `.status-bar { background-color: transparent }` and the bar therefore shows
  the *page* ground — exactly `--background-primary`. Same bug, other colour.
  There is no named surface that is reliably distinct from a ground a theme is
  free to redefine, so the card is derived from the ground — lifted off it, the
  way a card sits on the desk it is lying on. That needs *two amounts and one
  direction*, and the second table is unavoidable rather than lazy: "lighter"
  is a single instruction, but the room to obey it is not symmetric. Paper's
  `#f3f1eb` has twelve points of headroom below white; Night's `#1a1917` has
  almost the whole range. One percentage toward white is either invisible on
  paper or a floodlight at night. Measured after: `#f3f1eb → #fdfdfc` and
  `#1a1917 → #282724`, ~1.1:1 either way — a card, not a panel. It is stated as
  a custom property rather than as two background rules, so the theme branch
  and the `is-sep` exception cannot end up tied on specificity and settled by
  document order. **The middle attempt is the interesting one:**
  the harness stubbed the status bar as `--background-secondary`, the way
  Obsidian paints it by default, so it was checking contrast against a colour
  that never appears in this theme. A harness that models the host's chrome has
  to model *this* host's chrome.
- **A component moved to a new home is sized against its new neighbours, not
  its old ones.** The readout's card metrics and icon were tuned for a status
  bar — 12px labels, a 14px `--icon-xs` clock — and putting the same element in
  a phone's note header, a row of 26px touch targets, made it read as something
  dropped in from another screen rather than as one of the header's own
  controls. Not smaller-and-restrained: smaller-and-wrong. It is now
  `--font-ui-medium` with `--icon-s` and the heavier stroke Obsidian draws
  header icons at, and the cards grew *taller in proportion* rather than merely
  bigger, because a flip card is a portrait object — wider than it is tall it
  stops reading as a card and starts reading as a key. Measured against a mock
  built to the screenshot's real dimensions: card 20.7px in a 30px pill (69%),
  0.8 of the button box, 1.72:1 portrait. The four card metrics are custom
  properties for exactly this reason — a second home is one block of values
  rather than six overrides hunted through the sheet.
- **`:empty` never matches an element that has children, however little it is
  showing.** The readout is emptied when it has nothing to say, and Obsidian's
  own `.status-bar-item:empty { display: none }` was expected to take it out of
  the bar — it never did, because the item still contains its icon and readout
  spans. Emptied but present, it is an invisible item still holding a gap
  between two real ones, which nobody noticed in a status bar and is a hole in
  a phone header's tight row of touch targets. The plugin now says `is-blank`
  outright rather than hoping a selector notices.
- **A software keyboard does not resize the layout viewport**, so no media
  query, no `resize` listener and nothing in CSS knows it is there — the window
  stays serenely centred on a screen half of which is now covered. What the
  keyboard *does* resize is the **visual** viewport, so the fix is
  `visualViewport` and its `resize`/`scroll` events, lifting the window by
  exactly the overlap and no further, clamped to the distance to the top of the
  screen (a window pushed off the top is not an improvement on one pushed off
  the bottom). The other half of the fix is not summoning it at all: the
  duration field is autofocused on desktop, where the premise is a duration you
  type into a window a hotkey opened, and *not* on a phone, where the same line
  hides the drums behind a keyboard nobody asked for.
- **A width reserve that was invisible in text is a visible hole beside
  objects.** The status-bar readout reserved the widest form the run would
  produce, so the item would not shrink from `1:00:00` to `59:59` and drag its
  neighbours across. That was right for a proportional countdown, which changes
  width twice a second. It stopped being right the moment the digits became
  fixed-width cards: the board's width now changes only when a *cell* is
  dropped — twice in a whole session — and the reserved emptiness that nobody
  could see in a run of text is perfectly obvious as a gap beside a row of
  cards. Two rare one-cell shifts is the cheaper of the two. Removing a
  mechanism is the same kind of decision as adding one, and it is worth
  checking whether the condition that justified it still holds.
- **A mouse gets no momentum for free, and the throw has to outlive the drag.**
  A trackpad and a finger both hand the platform a release velocity and get
  inertia from it; a mouse button hands it nothing, so a flicked drum stopped
  dead the instant the button came up — which is what makes a dial feel like a
  list of rows rather than a wheel. Three things make the hand-written version
  behave. Velocity is an *exponential average* over the moves, not the last
  move's distance, or the same gesture flies or dies depending on whether the
  final event happened to carry 14px or 1px. Snap-off has to persist through
  the whole glide, not just the drag, or the first frame of coasting is hauled
  back to the nearest row. And the glide can afford a long tail — 0.96 a frame,
  about twelve rows from a firm flick — precisely because a press anywhere in
  the window kills it, so overshooting costs a tap rather than a second gesture
  in the opposite direction. That press is captured at the window, before the
  drum's own handler, and each drum it actually stops is marked so the same
  press does not also select the row it was passing.
- **Two ways to say the same thing, and one value underneath.** A session is
  held in the head either as *for 25 minutes* or as *until 1pm*, and neither is
  a special case of the other, so the window offers both: a segmented control,
  drums for hours/minutes/seconds on one side and hour/minute/meridiem on the
  other, and one typed field that parses whichever the current mode expects.
  Only `seconds` is state — until-mode works out the exact remainder and hands
  that to the same machinery — so switching modes carries the value across
  rather than resetting it, and everything downstream stayed untouched. The
  12-hour column is asked of `Intl.DateTimeFormat().resolvedOptions()` rather
  than guessed from the language, and the deadline is recomputed at the moment
  Start is pressed, because "until 1pm" means 1pm and the seconds spent
  choosing it are part of what has to come off.
- **Seeding a drum from typed text has to be instant, not smooth.** A smooth
  programmatic scroll passes through every intermediate row, each firing a
  scroll event, and a control that reads its own scroll position back as a
  value will read every one of those as a choice the human never made —
  overwriting the field mid-keystroke. Landing on the row in one step means the
  only event that arrives already reads the value just written, and the drum's
  own index check swallows it. The other half of that fix is knowing *who*
  moved a drum: the drums report `pointerdown`/`wheel`/`touchstart` separately
  from any value change, so the window can tell a scroll it caused from a
  scroll the reader caused, and never rewrites text under a live cursor.
- **The same split-flap board reads the countdown in the status bar, and
  turning the flip off cannot be done in CSS.** The obvious way to honour
  Reduce Motion — or a "don't flip" setting — is to hide the two animated
  halves and let the static ones change. That leaves a real defect: the lower
  static half is *deliberately late*, because it must not change until the fold
  has covered it, so with nothing covering it the top of the glyph shows the
  new digit and the bottom shows the old one for 90ms. A torn character, once a
  second. The suppression has to set both halves in the same frame, which is
  JS.
- **A split-flap that only flips what changed, and cancels rather than queues.**
  Scrolling the drum changes the value many times a second. Re-rendering every
  cell flips the unchanged ones too, so the whole board flaps when only the
  minutes moved, which reads as noise instead of a mechanism; and queued flips
  fall behind a fast scroll and keep flapping after the drum has stopped. So an
  unchanged glyph is left completely alone, and a new flip cancels the one in
  flight — which is also what produces the cascade while you scroll. Each cell's
  two timers are tracked and cleared, rather than trusting `setTimeout` ordering
  to make the last write win: that happens to be true today and is an argument
  rather than a guarantee.
- **Parsing is not loading, and a truncated plugin parses fine.** An edit that
  replaced a range of `main.js` swallowed everything after it — the `Plugin`
  class, the settings tab, `module.exports` — and the file that came out was
  still perfectly valid JavaScript. `node --check` passed, the stylesheet guard
  passed, and the browser harness passed too, because the harness lifts the
  modal out of the file and never asks the file as a whole to be a plugin. The
  only symptom was Obsidian saying *Failed to load plugin* with no line number.
  `tests/check_plugin_loads.js` now `require()`s each plugin the way Obsidian
  does, with `obsidian` and `@codemirror/*` stubbed, and insists the export is
  a class extending `Plugin` with an `onload`. Every check a repo has can be
  green on a file that does not work; the fix is to run the thing, not to read
  it more carefully.
- **Seven designs, and the first six were the same mistake.** The timer's
  display went through a dotted rail inside the note's edge, the same rail as a
  solid gradient, a warming page-wide glow, a tinted dot grid, a corner bloom,
  and discrete marks at session breakpoints. Every rejection was read as a
  tuning problem and answered with a better-tuned version of the same idea. The
  constraint that explains all six only arrived at the end — *nothing may enter
  the visual field unbidden* — and it leaves exactly two legal moves: change a
  property of something already on screen, or reveal something that was asked
  for. All six were new matter on the page. So the display is now the **caret**,
  which drifts from its resting indigo through sage and ochre to wine: already
  there, already the theme's, and the only thing in *foveal* vision while
  writing, which is where colour discrimination is best and where none of the
  six were. That is why 1.5px of it is enough. It also deleted a fixed element,
  a live measurement of the note's scroller and a list of floating chrome to
  dodge — the mobile placement problem was not solved, it stopped existing.
  Written up in `docs/superpowers/specs/2026-08-15-timer-caret-design.md`.
- **A rectangular colour space cuts the corner between two hues, and the corner
  is where the grey is.** The drift interpolates in `oklch`, and the usual
  argument for it is wrong at this scale: measured off a render of this exact
  ramp, sRGB and oklab differ by at most ΔE 0.029 — a JND on a big swatch,
  nothing on a 1.5px caret. The real defect is that indigo and sage sit on
  opposite sides of neutral, so a straight line between them passes *nearer the
  achromatic axis than either endpoint*. Chroma measured 0.058 → 0.042 → 0.029
  → **0.024** → 0.033, bottoming a third of the way in, below sage's own 0.033:
  the caret would have gone grey mid-session, reading as a caret that lost its
  colour rather than as time passing. `oklch` interpolates hue angle and chroma
  separately, rounds the corner, and stays monotonic into sage. A unit test can
  only assert which space was *asked for*; the rendered check is what caught it.
- **Notices and tooltips are Obsidian's dark toast, and the text colour is not
  a variable.** `.notice`, `.tooltip`, `.cm-completionInfo` and
  `.cm-tooltip-docstring` all take their background from
  `--background-modifier-message`, which app.css sets to `rgba(0, 0, 0, 0.9)`
  on `body` everywhere except `.is-mobile.theme-dark` — so a paper theme always
  got a near-black slab, full-width at the top of a phone. All four also
  hardcode `color: #FAFAFA`, so retargeting only the background paints
  near-white text on cream: unreadable, and worse than the slab. The fix has to
  move the *variable*, not the elements, because the tooltip arrows are CSS
  triangles coloured by `border-<side>: solid var(--same-var)` — style the
  elements and the bodies go light while the arrows stay black, pointing at
  them. Moving the variable then inherits app.css's specificity problem:
  `.is-mobile.theme-dark` redefines it at (0,2,0) and beats a bare `body`
  regardless of source order, hence the second selector. A notice's
  `<progress>` needed a third fix for the same root cause — Obsidian themes it
  correctly at (0,1,1) but a `.theme-light` hardcode of `#262626` at (0,2,1)
  beats that, so light mode alone got a black track. Measured after: text at
  10.89:1 on Paper and 13.17:1 on Night, with the card only 1.07:1 against the
  page — which is why the border is explicit, since Obsidian drops the
  box-shadow entirely on phone.

  The first response was to withhold the band on mobile, because drawing under
  an unremovable native one read as a doubled highlight. That blamed the
  drawing for a fault in the shape. Sampling a dark-mode iPhone screenshot,
  the selected region is every underlying pixel times 0.8 — including the
  **glyphs**, 234,232,227 → 187,185,181, which a selection *background* sits
  behind and could not dim. So it is a translucent scrim on top: unrecolourable,
  but see-through, and a band underneath returns at 80%. Matching its shape is
  the whole job — the line box rather than the ink, middle rows squared off to
  the content edges (which turned out not to be an iOS matter at all: a row the
  selection continues past should reach the edge of the column on every
  platform, and scoping the squaring here left desktop with a notch bitten out
  of every soft-wrap point), and, in the prose, a box leaning above the baseline by
  `fontSize × (A−D)/2` for the **system** font, since UIKit lays the rect out
  without ever resolving the webfont. That lean scales with font size, so the
  slot is written as half the line box ± `--midori-scrim-lean`.

  **The title takes the same rule with different numbers, and extrapolating the
  prose's was the bug.** Measured against the title's baseline on the phone: the
  scrim sits at `[−11.0, +11.0]` — symmetric to a third of a pixel, which is
  what a centred line box on a symmetric face looks like — while the prose lean
  carried over put our band at `[−20.0, +4.0]`. So the title's lean is 0. Its
  height is measured too: a scrim 11px either side of the baseline *is* a 22px
  line box, against the 24px that `--inline-title-line-height` says, so the
  plugin measures the element (content height ÷ visual rows) and hands the
  answer in as `--midori-title-line-box` rather than trusting the variable.
  Both surfaces are now `line box / 2 ± lean` with both terms measured per
  surface. Note the pair must be *declared on the band*: a `var()` inside a
  custom property is substituted at the element the declaration sits on, so
  declaring it on `body` would resolve the measurement against `body`, where it
  does not exist. (`em` is the opposite — it is not resolved until substituted
  into a real property, which is why the `0.83em` slots can live on `body`.)

  Gated on **iOS, not mobile**: Android is Chrome, honours `::selection`, and
  so has no scrim left to match — it takes the desktop ink slot. `is-ios` /
  `Platform.isIosApp`, both of which Obsidian ships.
- **The caret and the band share one "slot", deliberately.** They answer the
  same question — where the text on this line lives — so `--midori-slot-rise` /
  `--midori-slot-drop` (14px / 5px) size both, and the title's
  `--midori-title-slot-*` pair (0.83em / 0.30em) does the same job for the
  title. Letting them drift is a real bug: put the caret on a character, select
  that character, and the highlight would sit 5px lower than the caret did.
  The caret's bottom therefore hangs 5px **below** the baseline rather than
  landing on a baseline dot — which is both the measured browser convention
  (across five real faces, 17–22% of a native caret sits below the baseline and
  its bottom edge tracks the descender depth to within 0.6px) and the only way
  it can enclose the descenders it sits beside. Text hangs from the bottom of
  its cell, so nothing sized to the ink can also be dot-aligned.
- **px in the editor, em in the title, and the distinction is load-bearing.**
  `.cm-line` has an absolute `line-height: 24px` that does *not* move with
  Appearance → Font size, so anything sized against the ROW is px. The title
  has no fixed row and its size *is* a user setting, so its slot is em. The
  plugin makes that expressible by copying the title's font size onto the
  elements it draws, which live outside `.inline-title`.
- **The properties widget opts out, onto its own paper.** Its rows are flex
  boxes full of inputs, icons and pills whose heights Obsidian derives from
  content the theme never sees. The block's *outer* box is a whole number of
  rows so prose below is unaffected, and an opaque fill hides the dots behind
  it so the interior only has to agree with itself. Inside it, text uses the
  *stock* face on purpose: a baseline at `L/2` centres the line box, not the
  ink, which leaves lowercase floating above every icon beside it.
- **Prose is the sans face and the interface is the serif one.** Not a
  transposition — titles are Spectral against M PLUS 1p body copy. Per-vault
  font settings in `appearance.json` will mask a mistake here until someone
  clears them.
- Elements with arbitrary heights (images, Mermaid diagrams, embeds) knock
  following lines off-register — inherent to baseline grids.

## Cursor / VS Code notes

- **Judge syntax contrast at 1x, never on the retina display.** Decomposing a
  non-retina screenshot into per-pixel ink coverage: across every token colour
  only **8–11% of glyph pixels reach ≥90% coverage**, and the median glyph
  pixel sits at 0.13–0.27. A WCAG ratio describes that ~9% core only — the rest
  of the letterform is partial-coverage pixels much nearer the background. So
  the nominal number overstates legibility, and it does so worst where you can
  least afford it. Measured at the 90th-percentile pixel: ink `#2a2825` held
  13.01 → 8.73:1, keywords 6.83 → 5.10:1, but functions at `#b88a3a` went
  2.76 → **2.42:1**, with a median glyph pixel of 1.13:1 — essentially no pixel
  in the glyph was legible. Retina has the subpixels to hold the true colour
  and hides all of this, which is why it only ever gets reported on the
  external monitor. Compensate with headroom: aim ~5–8:1 nominal for 12–13px
  body text, not a bare 4.5.
- **Lightness is the lever; chroma is not.** Raising saturation was tried first
  and made things *worse* — the accents rely on chroma *tiers* to stay apart
  when they share a line, and lifting everything collapsed those tiers,
  reintroducing collisions and clipping sRGB. Paper's 11 syntax roles are now
  an OKLCh lightness ladder (L 27.8 → 54) with hues unchanged; the pairwise
  `ΔL<6 and ΔC<3` check goes 5 flagged pairs → 0, min contrast 2.76 → 4.46:1.
  Night had no contrast problem (everything ≥5.7:1) but 9 collisions from
  stacking all 11 roles into L 59–78; same re-laddering, now 0 and ≥4.93:1.
- **Two tiers, on purpose.** Code-surface keys (`tokenColors`,
  `semanticTokenColors`, `editorBracketHighlight.*`, `symbolIcon.*`) take the
  full ladder value. Diagnostics, git decorations, testing and charts take a
  separate *status* value per hue fixed only to clear 4.5:1 — so a warning
  still reads as ochre instead of inheriting the ladder's much darker rung.
- **`terminal.ansi*` is deliberately untouched.** Those 16 keys mirror
  `ghostty/themes/midori-*` and are consumed by the shell, tmux and fzf
  fragments; changing them here alone would drift the palette across tools.
  They still carry the old light values (`ansiYellow` `#b88a3a` is 2.76:1 on
  paper), so the integrated terminal is the one surface this pass did not fix.
- **Coloured nesting guides need a setting the theme can't supply, and turning
  it on silently disables another one.** `editorBracketPairGuide.background1-6`
  / `activeBackground1-6` only render when `editor.guides.bracketPairs` is on
  (it defaults to `false`), so the theme half is inert on its own. The trap is
  the second step: `editor.guides.highlightActiveIndentation` defaults to
  `true`, which means *"highlight the active indent guide **unless bracket pair
  guides are enabled**"* — so switching on `bracketPairs` silently kills the
  active-indentation rail. Set it to `"always"` to get both. Verified by
  sampling guide columns out of a screenshot: every indent rail came back at
  the idle `#d6d0c6` with no active one drawn anywhere.
- **Bracket guides will never track JSX elements.** Bracket-pair colorization
  only knows `()`, `[]`, `{}`; `<span>`/`</span>` are tags, so the active pair
  for a caret inside JSX is whatever paren or brace encloses the whole block —
  often several screens up. The thing that follows JSX nesting is the plain
  indentation guide, which is why `editorIndentGuide.activeBackground1` is
  pitched to match the active bracket guides (2.4:1 paper / 3.0:1 night)
  instead of the near-invisible one-step-off-idle value it started at.
- **The markdown preview is a separate stylesheet, and in Cursor it is not what
  opens by default.** `markdown/midori-markdown.css` ships as a
  `markdown.previewStyles` contribution (not the `markdown.styles` *setting* —
  the preview webview's `localResourceRoots` only ever holds the open workspace
  folders, so a global path into this repo would 404 in every other project;
  an extension's own directory is always a resource root). It carries the
  Spectral/M PLUS split, the `hljs-*` remap, and the surface fixes. Two traps:
  `markdown.css` and `highlight.css` are themselves `previewStyles`
  contributions, so they are *peers* in `<head>` and their order is just
  extension enumeration order — every selector here is one step more specific
  than it needs to be (`html body`, `body.vscode-light .hljs-keyword`) so the
  cascade is decided by specificity, not luck. And Cursor's default `.md`
  editor is its own native ProseMirror component (`markdown-editor-react`, the
  `Preview | Markdown` toggle in the breadcrumb row), which is not a webview
  and loads no contributed CSS at all. Use `Markdown: Open Preview` (⌘⇧V) to
  see any of this.
- **That `Preview` chip is a trap, and it is stickier than it looks.** It is
  `markdownEditor.toggleMode`, which swaps the *native* editor between rich and
  raw — `RAW → Ny.id` (plain text), `RICH → V9.EditorID`
  (`workbench.editor.markdown`). Neither position is the webview. Worse, it
  calls `replaceEditors` with an explicit `options.override`, so it walks
  straight past `workbench.editorAssociations`, and it writes the choice to
  `markdownEditorModePreferences` keyed by URI — one click re-pins that file to
  the native editor for good. Two more reasons the association looks broken:
  `MarkdownEditorInput` has an editor serializer whose `deserialize()` builds
  the input straight from JSON, so *restored* tabs never consult the resolver
  at all; and eligibility is `endsWith('.md') && !endsWith('.plan.md')` minus a
  hardcoded dot-dir list — `['.cursor', '.claude', '.codex']` — so markdown
  under exactly those three opens normally and everything else does not. There
  is no setting to disable the native editor (nothing registers under
  `markdownEditor.*`), but the chip only mounts when it finds a live
  breadcrumbs control, so `"breadcrumbs.enabled": false` removes it entirely.
  Default mode is RAW (`kXu(uri) => isMermaid(uri) ? RICH : RAW`), so a file
  showing the rich render has a stored preference; closing and reopening the
  tab is the only way to clear it short of the state DB.
- **Fenced code in the preview is not themed by the theme.** `highlight.css`
  hardcodes highlight.js' VS2015 palette with no reference to the active
  colour theme, and its `.vscode-light` override block misses
  `.hljs-selector-class`, `.hljs-selector-id` and `.hljs-bullet` — which keep
  the *dark* theme's tan `#D7BA7D` on cream. The whole class set is remapped
  per theme. Measure those against `textCodeBlock.background`, not
  `editor.background`: the code block sits a rung darker, and three paper roles
  tuned on the editor surface slipped under 4.5:1 there.
- **Cursor's native markdown editor colours its code blocks from
  `symbolIcon.*` and `debugTokenExpression.*`, of all things.** Its
  `.code-highlight-*` classes map straight onto those keys —
  `comment → debugTokenExpression.name`, `string → debugTokenExpression.string`,
  `keyword → symbolIcon.keywordForeground`, `function →
  symbolIcon.functionForeground`, and so on — so that surface *is* themeable
  even though no contributed CSS reaches it. What is **not** themeable is the
  block background: measured `#e3e1dc`, which is the page `#f3f1eb` under a
  uniform 6.5% black (`243 × 0.935` on every channel), one of Cursor's own
  `color-mix` design tokens rather than `textCodeBlock.background`. It sits a
  full rung below anything the theme controls, so those two key families are
  laddered against that measured surface — `#e3e1dc` on paper and `#2b2a27` on
  night (the editor background under a uniform +17 white, ~7.4%) — rather than
  against `editor.background`. Five paper values dropped 1.6–4 OKLCh points and
  three night values lifted ~2, all at unchanged hue and chroma, which costs
  nothing on the lighter surfaces these keys normally land on (min 5.27:1 paper
  / 5.59:1 night on the editor). Measure both modes: night's overlay is not the
  mirror of paper's, and estimating it left three values short at 4.39–4.42. A
  fence with no language tag gets no tokens at all and renders as flat ink.
  That block also sets `font-size: 12px`, below the body text around it, and at
  12px the 1x coverage problem above bites hard: sampling the olive token, the
  *thickest* pixel in any glyph reaches 98% coverage and the p90 pixel 92%, so
  a nominal 4.56:1 renders at 3.91:1 and there is no pure-ink pixel anywhere in
  the block. These keys are therefore laddered so the **p90 pixel** clears
  4.5:1, not the nominal value — which lands them at 5.0–5.4:1 nominal, the
  same headroom rule as the first bullet.
- **Shell code blocks needed a lexer, not more CSS.** highlight.js' Bash
  grammar only emits classes for a fixed built-in list (`cd`, `echo`, `whoami`,
  the coreutils names), quotes, comments and `$vars` — a command name in command
  position is simply not a token in that model. Measured on a real block: 2 of
  ~20 words carried a class, and `git`, `npm`, `node` and every argument came
  out as plain ink. No stylesheet can colour a span that was never created,
  which is why `midori-theme/extension.js` exists at all. It contributes
  `markdown.markdownItPlugins` and re-sets markdown-it's `highlight` for shell
  fences only, emitting the same `hljs-*` names the stylesheet already maps:
  command → `built_in`, bare-word arguments → `title`, `-flags` → `meta`,
  `$var` → `subst`, quotes and `#` comments as themselves. Everything that is
  not a shell fence falls through to highlight.js untouched. Two ordering facts
  make it work: `MarkdownItEngine` applies contributed plugins *after* it sets
  its own `highlight` option, so ours wins; and it normalises aliases first, so
  `shell` arrives as `sh`.
- **HTML inside a template literal is one scope, so it was one colour.** The
  TypeScript grammar gives a template body `contentName: "string.template.ts"`
  and exactly two sub-patterns — `#template-substitution-element` and
  `#string-character-escape`. Nothing else. So every character of
  `<div class="muted">` carried a single scope, and a theme cannot split one
  scope into three colours; the `entity.name.tag` and
  `entity.other.attribute-name` values were already defined and simply never
  fired. `syntaxes/midori-html-in-template.tmLanguage.json` injects into
  `source.ts`/`.tsx`/`.js`/`.js.jsx` with selector
  `L:string.template -comment -meta.template.expression` and emits those same
  scopes, so no new palette values were needed. Three things it has to get
  right: the selector must subtract `meta.template.expression`, because `${…}`
  inherits `string.template` from the enclosing literal and the rules would
  otherwise fire on real code inside interpolations; the tag span must
  `include: source.ts#template-substitution-element` or it shadows the base
  grammar and kills `${…}` highlighting inside tags; and quoted attribute
  values need an explicit rule so a value like `"a=b"` can't produce a phantom
  attribute name. Tag *brackets* take the punctuation neutral rather than the
  tag indigo — `entity.name.tag` is the same value as `keyword`, and `return`
  sits on the same line as `` `<div ``, which is exactly the co-occurrence the
  Antinote notes warn about. Attribute names stay ochre, which is also the
  function colour, but attributes are italic and functions are not.
- **`if`/`return`/`for`/`catch` sharing a colour is standard; `const` joining
  them is not.** Same tokenising survey, 39 schemes with all five keyword roles
  resolved: **82%** give the four control-flow roles one colour, but **62%**
  give `storage.type` (`const`, `let`, `var`, `function`) a *different* colour
  from `keyword.control`. Only 38% collapse all five, which is what Midori did.
  The interesting precedent is Nightfox and Nordfox: they split by **lightness
  at one hue** (`const #9D79D6` vs `if #BAA1E2`) rather than by inventing a
  second accent — which is the only split a low-chroma palette can afford, and
  the same lever the bullet above describes. Control flow now takes the extreme
  rung and storage stays at the resting one: night `#5f8dbe` → `#77a6d8`
  (L 63 → 71, 6.89:1), paper `#264464` → `#112f4e` (L 37.9 → 30, 12.07:1), hue
  and chroma unchanged in both. The reasoning is that `const` opens most lines
  and carries almost no information, while `if`/`return`/`for` are the shape of
  the function. Paper flags nothing. Night flags one pair — control vs number,
  ΔL 2.0 and ΔC 1.5 — which is accepted rather than fixed: the two are **166°
  apart in hue**, near-complementary blue against orange, and the `ΔL<6 and
  ΔC<3` heuristic is calibrated for *near-hue* pairs (its worked example is an
  80° step at C 6). Every alternative lightness was worse — L ≥ 79 collides
  with the function ochre and the mint, L ≤ 67 collides with storage itself,
  which is the pair being separated. Control flow is then separated on two
  further channels that cost no hue: chroma (C 9 → 12 in both) and **real
  weight**. Final values: night `#65a6ea` bold at 6.86:1, paper `#175a98` bold
  at 6.30:1, separated from storage by ΔL 8.0 + ΔC 3.0 and ΔL 8.1 + ΔC 5.4,
  plus 250 units of font weight. The rule is the same in both themes: control
  flow is the **lighter, more chromatic** blue and storage is the deeper,
  quieter one.
- **On a light background, "more contrast" and "more visible" are not the same
  thing.** Paper's control flow first shipped at `#002e5b`, mirroring night's
  *direction* — night raises control from 5.05:1 to 6.86:1, so paper raised it
  from 8.88:1 to 12.06:1. That was wrong, and reported as "I'm not sure it's in
  the light theme?". Sampling the reported screenshot proved the theme *was*
  applied — `#002c58` at 198 px alongside storage's `#244460`, with the
  previous value absent — so the failure was perceptual, not mechanical. Night
  had headroom because its storage sits at 5.05:1; paper's already sat at
  8.88:1, and past roughly 8:1 on cream both values simply read as near-black
  and further darkening buys nothing. The fix was to mirror night's *effect*
  instead: move control **lighter** and much more chromatic, so a medium blue
  sits against a deep navy. Searching every (L, C) at the indigo hue for slots
  with no flagged pair showed paper's L 42–54 band is only passable at C ≥ 9.6
  — below that the comment, purple, string, mint and number rungs block it — which
  is why the answer needed chroma and lightness together.
- **`fontStyle: bold` is a real axis here; `fontStyle: italic` is not.**
  `MPLUS1Code[wght].ttf` is a variable font carrying Thin → Bold, so bold is an
  actual instance rather than a synthetic smear — and because heavier strokes
  raise the share of full-coverage pixels, it is the one differentiator that
  *helps* the 1x problem in the first bullet instead of trading against it.
  Neither M PLUS face ships an italic, so every italic in these themes
  (comments, `variable.parameter`, `variable.language`,
  `entity.other.attribute-name`) is a synthesized oblique. That still reads,
  but it is a reason not to keep spending italic: it is a skew, not a face, and
  four roles already claim it. Style is the rare channel among the surveyed
  themes — only 5% italicise storage and 8% control — so it is worth spending
  where colour has run out rather than as a first move.
- **Weight is spent on declarations, and that is a Midori decision rather than
  a convention.** The survey is nearly silent here: of 44 theme files, bold
  goes to `markup.bold` (93%) and `markup.heading` (84%), and the 82% figure
  for `entity.name` is almost entirely `entity.name.section` — markdown
  headings again. In actual code the field barely uses it: `entity.name.type`
  2%, `entity.name.function` 2%, `keyword.control` 5%. So there is no consensus
  to adopt, only a lever nobody is using. Midori spends it on **where a name is
  introduced**, which is the same split the fonts already state — Spectral is
  the naming voice, M PLUS the working voice — applied inside the working
  voice. That requires the semantic layer, because TextMate cannot tell a
  definition from a call: `entity.name.function` fires on both, so bolding it
  would bold every call site. `semanticHighlighting` was already true here, so
  seven rules carry it: `function.declaration`, `method.declaration`, and
  `class`/`interface`/`enum`/`type`/`namespace.declaration`. Foregrounds are
  restated explicitly in each rather than left to fall through specificity —
  and note this is the one change in this section that the tokenising harness
  **cannot** verify, since it resolves TextMate only and semantic tokens come
  from the language server. Variables are deliberately excluded: `*.declaration`
  would bold every `const`, which is most lines.
- **Bold is already at the ceiling, and `editor.fontWeight: 450` is exactly
  right — both measured, neither guessed.** `MPLUS1Code[wght].ttf` declares
  `wght` **100–700** (`fvar`), and `fontStyle: bold` renders 700, so bold sits
  on the axis maximum with nowhere left to go. There is no `editor.fontWeightBold`
  either — VS Code exposes that only for the terminal — so the base weight is
  the sole remaining lever, and it should not move. Rendering the real font at
  the real `editor.fontSize: 14` and tracking the ochre function colour (the
  tightest regular-weight token, 4.54:1 nominal) against `#f3f1eb`:

  | base `wght` | p90 ink coverage | p90 rendered contrast |
  |---|---|---|
  | 300 | 0.757 | 2.97:1 |
  | 350 | 0.910 | 3.86:1 |
  | 400 | 0.984 | **4.41:1** |
  | **450** | **1.000** | **4.54:1** |
  | 500 | 1.000 | 4.54:1 |

  450 is precisely the lowest weight at which coverage saturates: one step down
  to 400 and the ochre falls to 4.41:1, under the floor this whole section
  exists to hold. Widening the bold gap would buy weight contrast by spending
  the 1x contrast in the first bullet.

  **Measure weight as total ink, not stem width.** A first pass ran horizontal
  run-lengths over a screenshot and reported bold at only 1.166× — misleading,
  because at 14 px a run-length threshold misassigns the antialiased edges
  between two colours as close as `#264464` and `#002e5b`, and it degenerates
  badly (base 600 measured a 3.00 px "stem", above bold's own). Summed coverage
  is stable and gives the real figure: **bold carries 1.48× the ink of base
  450**, a 48% increase. That is a strong signal — it reads as weak only when
  one lone role carries it, which is why weight is spent across declarations
  and control flow rather than on a single scope.
- **Midori cannot afford a hue for every role, and that is the palette
  working as designed.** Tokenising one line of HTML through every installed
  theme and deduping by colour signature gives 40 distinct schemes, and they
  agree: brackets dim from the tag name (82%), the attribute name is its own
  accent rather than a neutral (95%, only 15% near-neutral), the tag is the
  most chromatic of the three (48%, best mean rank) and the value is the
  loudest by lightness (38%, best mean rank). Midori now matches all four. The
  one convention it does not is that its attribute name doubles as the function
  ochre, which only 12% of themes do. That is not fixable by adding a colour.
  Those 41 themes carry **14.0 distinct accents across 7.9 of 12 hue bins at
  mean chroma 12.3**; Midori Night carries 10 accents over 7 bins at **8.3**,
  Paper 8 over 6 at **8.5**. Below roughly C 12 hue does almost no work at body
  size, so the field's 12.3 is exactly what buys them a spare hue slot. An 11th
  Midori accent dropped into the gap at 289° would sit at C 8 and read as
  another muddy mid-tone — every candidate priced (the then-plum at 327°, cyan
  212°) still flagged `ΔL<6 and ΔC<3` against `function`, because at this
  chroma separation has to come from lightness and night's L 73–86 band already
  holds function, number, value, mint and plain. Raising chroma to open the
  slot is the experiment in the second bullet that already failed. The role is separated on
  an orthogonal channel instead: `entity.other.attribute-name` is italic and
  `entity.name.function` is not — verified in the tokeniser, not assumed —
  which is what 18% of the surveyed themes do deliberately.
- **Verify a grammar change by tokenising, not by looking.** Cursor ships
  `vscode-textmate` and `vscode-oniguruma` in `Contents/Resources/app/node_modules`,
  so a ~60-line script can load the real grammars *and* the real theme through
  `Registry({theme})`, run `tokenizeLine2`, and resolve `getColorMap()` — the
  same tokenizer the editor runs, reporting the actual hex per token. That is
  how the keyword collision above was caught before shipping, and how the
  no-false-positive cases were confirmed: `` `SELECT … WHERE a = "b" AND x < y` ``
  and `` `total = ${a > b ? "hi" : 'lo'}` `` both tokenise identically with the
  injection on and off.
- Reinstall with `./vscode/install-vscode.sh` — it repackages the `.vsix` and
  force-installs into both editors. Symlinking into `~/.cursor/extensions`
  does not work; see the header of that script.

## Antinote notes

Two themes (`antinote/midori-paper.json`, `antinote/midori-night.json`), flat
24-key JSON, no nesting. Antinote publishes no schema — the role of each key was
transcribed out of the theme-maker's Svelte route chunk and lives in
`antinote/README.md`, so a colour can be picked for its job instead of by
nudging sliders.

- **Turn translucency off before judging any colour.** `translucentWindow: true`
  with `translucentAmount: 0.6` composites the whole note against the desktop:
  measured `#E5E4E2` against the theme's `#F3F1EB` on paper and `#636464`
  against `#1A1917` on night — 29 points of lightness gone, dragging
  `typeLight` down to **1.08:1**. Every "these colours look washed out" report
  traced back to this and not to the palette.
- **The `math` block is what constrains the palette.** Everywhere else in Midori
  roles are separated by *position*; the math block puts four roles on one line
  in one monospace weight (`deducted: income * taxes = 459.20` — assignment,
  use, use, total). In OKLCh every Midori accent sits at chroma 4–7, and below
  roughly C 12 hue barely registers at 13px, so separation has to come from
  lightness — and the first cut had four roles stacked at L 53–57. The fix was
  to give the *total* the extreme rung (darkest on paper, lightest on night;
  ΔL against variable-use went 0.7 → 16.1) and lift chroma ~1.7× across every
  accent. This is why the Antinote files diverge from `obsidian/theme.css`
  rather than copying it.
- **No font setting exists.** Antinote exposes `fontSize` / `doubleFontSize`
  only; `availableFontFamilies` is an AppKit call, and "Reset Font & Offsets to
  Defaults" belongs to the Non-English Typography beta. Custom faces are not a
  theme's lever.
- **`sync.sh` does not round-trip these** — nothing edits them on the machine,
  so the repo is the only copy. Edit the JSON, re-run
  `./antinote/install-antinote.sh`, hit "Reload Custom Themes"; no restart.

## Moshi notes

[Moshi](https://getmoshi.app) is the phone terminal for driving agents over
SSH/Mosh, and it restyles its whole UI from the imported scheme — not just the
terminal grid. `moshi/build-moshi-themes.py` derives both themes from
`ghostty/themes/midori-*`, emits the JSON, deep links, QR codes and
`import.html`, and publishes all of it to
`iCloud Drive/Dev/midori-moshi-theme` so the phone copies can't fall behind the
repo. Full format notes — the schema is undocumented — are in `moshi/README.md`.

Two things worth carrying to any future port:

- **A sentinel value is not a colour.** Both Ghostty themes set `cursor-color`
  to the exact background hex on purpose: Ghostty composites the native cursor
  *after* the custom shader and `cursor-opacity=0` doesn't hide the hollow
  unfocused cursor, so bg-on-bg is how they kill it and the shader draws the
  indigo instead. Ported verbatim to a renderer with no shader, that is simply
  an invisible cursor. The generator detects `cursor == background` and
  substitutes palette 4 — the indigo the shader was drawing. Before copying a
  theme value anywhere, check whether it's a colour or a hack exploiting one
  renderer's quirk.
- **ANSI 7/15 are reverse-video on a light theme**, so they belong *near* the
  background and their low contrast is correct, not a defect. Midori Paper
  lands 8/18 under 4.5:1, the same as Piatto Light, against Atom One Light's 11
  and Belafonte Day's 14. The generator prints the contrast table on every
  build so a palette edit that hurts phone legibility is visible immediately.

## Claude Code notes

- The installer sets `"theme": "custom:midori"` in `~/.claude/settings.json`.
  If Claude Code ever looks stock/wrong, check that setting first — picking a
  stock preset in `/theme` silently overwrites it.
- The watcher owns `~/.claude/themes/midori.json`; don't hand-edit it (edits
  are clobbered on the next appearance flip). Change the token maps in
  `watcher/midori-claude-theme.sh` instead, then re-run `./install.sh`.
- **Inside tmux, diffs need two env vars or they render muddy.** Claude Code
  deliberately clamps its colour depth to 256 whenever `$TMUX` is set (upstream
  issue #35148, verified in the 2.1.210 binary: `if(env.TMUX && chalk.level>2)
  chalk.level=2`), which collapses the Midori washes to their nearest 256-color
  cube entry (terracotta `#ddc7b7` → `#d7af87`). The fix is two exports, both in
  `shell/zshrc.midori` (and pinned in the tmux configs): `COLORTERM=truecolor`
  (raises chalk to 24-bit) **and** `CLAUDE_CODE_TMUX_TRUECOLOR=1` (the
  undocumented escape hatch that disables the clamp). Either alone still renders
  256-color — you need both, exported from the shell (the clamp reads them at
  module load). Ghostty-direct is unaffected (no `$TMUX`, no clamp).
- **Some colours are a binary patch, not a theme token.** Three render paths
  bypass `~/.claude/themes` entirely, so a value you set there silently does
  nothing and the binary is the only lever (upstream issues #66937/#69445):
  (1) **diff bands** — hardcoded RGB triples since ~2.1.186; (2) **inline code**
  (`` `codespan` ``) and (3) **the `suggestion` token** (tips, ghost-text — e.g.
  the blue `ultracode` keyword) both go through a helper that resolves via
  `UX(mode)`, which switches on the base-mode *name* and **discards custom
  overrides**, so your `permission`/`suggestion` values never apply and stock
  ansi-blue/periwinkle shows. `tools/apply-claude-midori-patch.sh` unpacks the
  binary (via `tweakcc`), and `tools/patch-claude-diffs.py` rewrites the eight
  diff-band constants to the Midori washes *and* injects per-mode `#`-literals
  into the codespan + suggestion call sites (a `#`-prefixed value bypasses the
  broken `UX` lookup), then repacks + re-signs it — so diffs, inline code, and
  tips all stay Midori *with syntax highlighting on*. Needs
  node/npx/python3. **Any** Claude Code update reverts it — the native installer's
  updater (`~/.local/share/claude/versions/<v>`, the default now) or a
  `brew upgrade` on older brew-cask installs — because it restores the stock
  binary. The `claude` shell wrapper in `shell/zshrc.midori` self-heals on next
  launch, re-patching whenever the resolved binary path changes (works for both
  update mechanisms). Opt out with `MIDORI_SKIP_CC_PATCH`; restore stock by
  copying back the per-version backup under `~/.config/midori/claude-backup/`
  (or `brew reinstall claude-code` if you're on the brew cask).
- **The self-heal wrapper must use `whence -p`, not `command -v`.** Inside a
  zsh function *named* `claude`, `command -v claude` resolves the function and
  returns the bare word `claude`; `readlink` of that is empty, the guard
  short-circuits, and the patch silently never runs. That bug shipped three
  unpatched Claude Code updates before anyone noticed, and it was caught by
  measuring a screenshot's pixels (inline code at hue 233° — Midori's blue is
  211° and its purple 274°, so it was neither), not by the tooling. If Midori
  colours ever quietly revert, check this first.
- **Currently blocked upstream: 2.1.229+ cannot be unpacked.** `tweakcc` 4.3.1
  and 4.3.2 both fail to extract the embedded JS from 2.1.229 and 2.1.231,
  while the same tool handles 2.1.226–228 cleanly — the binary packaging
  changed (it also grew 279 MB → 295 MB). The patch script records the specific
  binary path in `~/.config/midori/claude-unpatchable` and skips it silently,
  so the wrapper doesn't retry-and-fail on every launch; a new Claude Code
  version lifts the block by itself, and a successful patch clears it. Until
  tweakcc catches up, **inline code and tips render stock blue** — everything
  else in the theme is unaffected. Delete that file to force a retry.

## Shell & tmux fragments are additive

The shell and tmux pieces install as **fragments** that your own rc files
`source` — the installer never overwrites `~/.zshrc` or `~/.tmux.conf`, it just
appends one `source` line (detected by the exact fragment path, so it's
idempotent). Everything midori-specific lives in the fragment
(`shell/zshrc.midori`, `tmux/midori.tmux.conf`); your personal config stays
yours. That means the fragment is the single source of truth: edit it in the
repo, run `./install.sh`, and the change reaches every machine that sources it.

Corollary for the Claude Code self-heal: the `claude` wrapper that re-patches the
binary after updates lives **in the shell fragment**. If your `~/.zshrc` inlines
midori bits instead of sourcing the fragment, that wrapper never loads and
updates silently revert to stock diffs — so keep the `source` line, don't inline.

## Tests

Most of the repo is declarative (themes, fragments, shaders) and validated by
eye. The one piece with real, fragile logic — `tools/patch-claude-diffs.py`,
which silently breaks when Claude Code's minified binary changes — has unit
tests:

```sh
python3 tests/test_patch_claude_diffs.py   # patcher logic (idempotency, fail-loud, name-capture)
sh tests/lint.sh                           # + shellcheck, py_compile, zsh/tmux fragment parse
```

CI (`.github/workflows/ci.yml`) runs the portable subset (unit tests, py_compile,
shellcheck) on every push. The patcher tests build their fixtures from the
module's own `TRIPLE_PATCHES`, so they track palette changes instead of going
stale.

## Keeping machines in sync

On the machine where the theme evolves:

```sh
./sync.sh        # live files -> repo (paths de-personalized)
git diff         # review
git commit -am "..." && git push
```

On other machines: `git pull && ./install.sh`.

### Vivaldi theme maintenance across profiles

Two layers propagate differently:

- **CSS mods** (`vivaldi/css-mods/*.css`) are **shared across every profile** — all
  profiles point their `css_ui_mods_directory` at one folder, and Vivaldi has no
  per-profile CSS layer. Edit once, restart Vivaldi, done for all profiles.
- **Theme palette, light/dark schedule, and keyboard shortcuts** live in each
  profile's `Preferences`. They do **not** propagate — quit Vivaldi and re-run
  `./vivaldi/install-vivaldi.sh --profile all` to push changes into every profile.

On this machine the live `CSSMods` folder is a **symlink to `vivaldi/css-mods/`**,
so the repo *is* what Vivaldi serves — no copy step, drift impossible. `install.sh`
and `sync.sh` both detect this and skip their copy. To revert to a managed copy:
`rm "$HOME/Library/Application Support/Vivaldi/CSSMods" && ./vivaldi/install-vivaldi.sh`.

### Marketplace icon

`vscode/midori-theme/media/icon.png` is four stadium bars — ink, slate, ochre,
sage — on cream, their left edges stepping in, in, then back out one level, so
the block reads as nested code rather than a ragged stack. It follows the brand
guide that
lives in the sibling repos (`benjaminloschen/docs/brand-images.md` and
`tokentrail/docs/brand-images.md`), not this one, which is worth knowing before
regenerating it. Two of its rules shape how it was built:

- **The model never draws the background.** It generates the mark on flat
  cream; the base is then snapped to exactly `#f3f1eb` and the mint `#9ebfb4`
  dot grid composited through a background mask. That is what keeps the
  background pixel-identical across every image in the set regardless of model
  drift.
- **Sage is punctuation, not paint.** It gets one bar, not the whole mark. The
  cool accent is Color-Dot slate `#3a5572` rather than the theme's own syntax
  indigo, which sits outside the brand palette.

`media/finish_icon.py` is the post-processing step and `media/icon-raw.png` the
untouched generation, both kept in git and both excluded from the `.vsix`, so
the icon can be rebuilt without another round of generation. The bars snapped
to exact palette hexes at 99.6% coverage; the remaining 0.4% is antialiased
edges, left alone deliberately.

**The indentation is measured, not eyeballed** — `media/measure_bars.py` asserts
the staircase (bar 1 alone at the outer margin, bar 3 the most indented, bars 2
and 4 level). The first generation failed all of it while looking plausible at a
glance. Two traps make that measurement harder than it sounds, and both bit:

- Matching bar colours by nearest-palette-distance is not enough. The
  ink-to-cream antialiasing ramp passes through mid-greys that land almost
  exactly on sage `#5f6f5e`, so sage's bounding box swallowed the whole image.
  Filtering to pixels inside a horizontal run of 50+ separates a real bar
  (hundreds of px wide) from a ramp (~3px).
- The model does not honour absolute coordinates, but it does honour
  *relationships*. Asking for pixel positions produced a group shifted ~25px
  right with a 72px indent step instead of 96 — while the staircase pattern
  itself came out exact. Specify the relationships and check those.

The grid pitch is the one place the guide is knowingly departed from: the brand
draws dots at ~1/50 of the frame width, which on a small icon would be 2.5px
and disappear, so it is scaled up to 8 columns.

**It ships at 256×256**, set by surveying the field rather than guessing: the
top 100 themes on the Marketplace were pulled by install count and their icons
measured. 59% ship ≥256px on the long edge and only 18% are exactly 128 — 128
is the documented minimum, not the target.

That survey also mapped the genre. 70% of the 87 colour themes use a disc or
rounded mark on transparency (41% strongly circular); only 23% are full-bleed
squares. Of those with opaque backgrounds, 50% are dark against 17% light. The
three archetypes are coloured palette-dots on a dark disc, a mascot (the
largest group — vampire, owl, bear, cat, panda, penguin), and a wordmark.
Midori is deliberately none of them: it is the only light, flat, mascot-free,
full-bleed icon in the top 40, and it sits at the 13th percentile for
saturation against a field median of 0.38.

**It has no border, and that is a decision rather than an oversight.** Cream
`#f3f1eb` against VS Code's light list background `#f3f3f3` is 1.02:1, so on
light chrome the square has no visible boundary and the mark reads as four
bars floating free. A 4px ink-muted rule was built and measured — it fixes the
edge outright at 7.54:1 — but it frames the paper and turns a sheet into a
card. Being edge-to-edge paper matters more than having a silhouette.

One measurement that looks like a contradiction: the icon reads as flat but
scores 58 quantised colours, dead on the field median of 56. The 1024 master
holds exactly five hexes; the mint dot grid plus downsampling generates the
rest. Low saturation is what makes it read flat, not a small palette — so
judge that quality by saturation, not by colour count.

### Publishing the VS Code extension

Release is automated — `.github/workflows/release-vscode.yml` packages and
publishes on a `vscode-v*` tag — but it cannot run until four one-time,
account-level things exist. As of Aug 2026 none of them do, so the extension
is packaged and installable locally but **not published**.

1. **Two README screenshots**, `vscode/midori-theme/media/paper.png` and
   `media/night.png`. `media/SCREENSHOTS.md` is the brief: same file and
   scroll position in both themes, 1800px captured then halved to 900, with
   the explorer strip and a tab visible. `media/screenshot-sample.tsx` is the
   file to shoot — it is arranged to exercise control-flow vs declaration
   colour, bold-on-introduction, and accents on a single line. Until these are
   committed the Marketplace listing renders two broken images, because the
   README links them by absolute raw URL (see below).
2. **A publisher named `benjaminloschen`**, created once at
   <https://marketplace.visualstudio.com/manage>.
3. **An Azure DevOps PAT** with *Marketplace → Manage* scope and
   *All accessible organizations* — the org dropdown defaults to a single org
   and a PAT scoped that way fails at publish time with an unhelpful error.
   Then `gh secret set VSCE_PAT`. `OVSX_PAT` is optional; the Open VSX step
   skips cleanly without it.
4. **Tag `vscode-v1.21.0`** to trigger the workflow.

The version numbering starts at 1.21.0 deliberately: 1.0.0–1.20.0 were local
builds that were never published, and a Marketplace version number can never
be reused, so restarting the count would collide. `CHANGELOG.md` says so.

**Why the README uses absolute raw URLs for images.** vsce rewrites relative
links assuming the extension sits at the *repo root*, so `media/paper.png` in
this subdirectory package becomes `.../blob/HEAD/media/paper.png` and 404s.
Verified by unzipping the built `.vsix` and curling both forms. The
alternatives are `--baseContentUrl` / `--baseImagesUrl` or
`--no-rewrite-relative-links`; absolute URLs were chosen because they are
correct regardless of which tool builds the package. Full write-up in the
`vsce-readme-links-rewritten-relative-to-repo-root` skill.

Local installs are a different path and do **not** go through any of this —
see the Cursor/VS Code notes above: a folder drop is silently ignored, only a
`.vsix` installed through each editor's own CLI registers in
`extensions.json`.

## A note on the name

Midori is an independent project. It is not affiliated with, endorsed by, or
sponsored by Designphil Inc. or any other company. "Midori" is used here in its
ordinary sense — 緑, the Japanese word for green — which is also why the theme's
accent is sage.
