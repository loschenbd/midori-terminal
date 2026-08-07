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
| `vscode/` | Cursor/VS Code extension: Midori Paper/Night color themes, Phosphor Duotone file icons, Phosphor product icons for the workbench chrome (`build-icons.py` / `build-product-icons.py` regenerate), installer |
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
