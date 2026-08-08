# midori-terminal

A complete terminal theme system based on [benjaminloschen.com](https://benjaminloschen.com)'s
"Midori MD Paper" design language — Ghostty, Claude Code, tmux, fzf, oh-my-posh,
Vivaldi, Cursor/VS Code, Obsidian, and Antinote, all switching light/dark
together with macOS appearance.

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
Themes".

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
| `obsidian/` | "Midori" Obsidian theme (palette, dot grid, page glow, embedded metric-normalised fonts), the `midori-caret` companion plugin, installer for iCloud vaults; `build-fonts.py` regenerates the embedded faces |
| `fonts/` | M PLUS 1 Code (terminal), M PLUS 1p + Spectral (UI) — SIL OFL 1.1 |
| `tools/bake-backgrounds.py` | Regenerates dot tiles + glow washes for new displays |

Fonts follow the site's semantic split: **Spectral** is the naming voice
(titles, headers), **M PLUS** is the working voice (text you read and type).

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
