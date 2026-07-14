# midori-terminal

A complete terminal theme system based on [benjaminloschen.com](https://benjaminloschen.com)'s
"Midori MD Paper" design language — Ghostty, Claude Code, tmux, fzf, oh-my-posh,
and Vivaldi, all switching light/dark together with macOS appearance.

**Midori Paper** (light) · **Midori Night** (dark)

## Quick start (new machine)

```sh
git clone https://github.com/loschenbd/midori-terminal.git
cd midori-terminal
./install.sh
```

Then restart Ghostty. For the Vivaldi themes: quit Vivaldi and run
`./vivaldi/install-vivaldi.sh`.

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
| `shell/zshrc.midori` | omp init + fzf ANSI palette (sourced from `.zshrc`) |
| `tmux/midori.tmux.conf` | Pane borders, status/message styles (sourced from `.tmux.conf`) |
| `vivaldi/` | Midori Paper/Night browser themes, typography CSS mods, installer |
| `fonts/` | M PLUS 1 Code (terminal), M PLUS 1p + Spectral (UI) — SIL OFL 1.1 |
| `tools/bake-backgrounds.py` | Regenerates dot tiles + glow washes for new displays |

Fonts follow the site's semantic split: **Spectral** is the naming voice
(titles, headers), **M PLUS** is the working voice (text you read and type).

## Display gotchas (read before fighting the dot grid)

Ghostty draws background images at **physical pixels** (`fit = none`), so the
dot grid needs `@2x` assets on retina and `@1x` on 1x externals. The watcher
flips symlinks when the main display class changes — but Ghostty only re-reads
images on config reload, so hit **Cmd+Shift+,** after docking/undocking.

**Baseline lock:** text rows land on the 24 pt dot grid because
`adjust-cell-height` stretches the cell to exactly one grid step. It is
**coupled to font size**: 14 pt → 38.9 %, 15 pt → 29.7 %, 16 pt → 21.6 %.
Change one, change both. And the font family must be exactly `"M PLUS 1 Code"`
— a wrong name silently falls back to JetBrains Mono and breaks the lock.

### Calibrating the dot phase on a new display

The vertical dot offset does **not** scale cleanly between displays — measure
it, don't derive it:

1. Screenshot a terminal with a prompt underline visible (`screencapture -x`).
2. Measure the y-pixel of a dot row and of the underline/text baseline
   (any pixel tool; `sips -s format bmp` + a few lines of python works).
3. The difference mod the tile size is your phase error. Adjust and rebake:
   `tools/bake-backgrounds.py --scale 1x --glow-size <WxH> --dot-cy <new>`
4. Reload Ghostty, re-measure, repeat until dots sit on baselines.

Known-good values: `cy 11.5` @2x (16" MacBook Pro), `cy 10.75` @1x
(LG ultrawide). Box-drawing rules (TUI separators) render at cell *center*
and can never share the baseline lattice — that's expected, not a bug.

## Claude Code notes

- The installer sets `"theme": "custom:midori"` in `~/.claude/settings.json`.
  If Claude Code ever looks stock/wrong, check that setting first — picking a
  stock preset in `/theme` silently overwrites it.
- The watcher owns `~/.claude/themes/midori.json`; don't hand-edit it (edits
  are clobbered on the next appearance flip). Change the token maps in
  `watcher/midori-claude-theme.sh` instead, then re-run `./install.sh`.

## Keeping machines in sync

On the machine where the theme evolves:

```sh
./sync.sh        # live files -> repo (paths de-personalized)
git diff         # review
git commit -am "..." && git push
```

On other machines: `git pull && ./install.sh`.
