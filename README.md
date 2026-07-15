# midori-terminal

A complete terminal theme system based on [benjaminloschen.com](https://benjaminloschen.com)'s
"Midori MD Paper" design language — Ghostty, Claude Code, tmux, fzf, oh-my-posh,
Vivaldi, and Cursor/VS Code, all switching light/dark together with macOS
appearance.

**Midori Paper** (light) · **Midori Night** (dark)

## Quick start (new machine)

```sh
git clone https://github.com/loschenbd/midori-terminal.git
cd midori-terminal
./install.sh
```

Then restart Ghostty. For the Vivaldi themes: quit Vivaldi and run
`./vivaldi/install-vivaldi.sh`. For Cursor/VS Code: `./vscode/install-vscode.sh`
(it prints the settings snippet to wire up auto light/dark + icons). For
Obsidian: `./obsidian/install-obsidian.sh`.

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
| `obsidian/` | "Dot Grid" Obsidian theme (Midori palette, Spectral/M PLUS fonts), installer for iCloud vaults |
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

## Claude Code notes

- The installer sets `"theme": "custom:midori"` in `~/.claude/settings.json`.
  If Claude Code ever looks stock/wrong, check that setting first — picking a
  stock preset in `/theme` silently overwrites it.
- The watcher owns `~/.claude/themes/midori.json`; don't hand-edit it (edits
  are clobbered on the next appearance flip). Change the token maps in
  `watcher/midori-claude-theme.sh` instead, then re-run `./install.sh`.
- **Diff colours are a binary patch, not a theme token.** Since ~2.1.186
  Claude Code renders diffs through a syntax theme (GitHub/Monokai) with
  colours hardcoded in the compiled binary — `~/.claude/themes` can't reach
  them (upstream issues #66937/#69445). `tools/apply-claude-midori-patch.sh`
  unpacks the binary (via `tweakcc`), rewrites the eight add/remove band
  constants to the Midori washes (`tools/patch-claude-diffs.py`), and repacks +
  re-signs it, so diffs stay Midori *with syntax highlighting on*. Needs
  node/npx/python3. `brew upgrade claude-code` reverts it; the `claude` shell
  wrapper in `shell/zshrc.midori` self-heals on next launch (re-patches only
  when the resolved binary path changed). Opt out with `MIDORI_SKIP_CC_PATCH`;
  restore stock with `brew reinstall claude-code`. Stock binary is backed up
  under `~/.config/midori/claude-backup/`.

## Keeping machines in sync

On the machine where the theme evolves:

```sh
./sync.sh        # live files -> repo (paths de-personalized)
git diff         # review
git commit -am "..." && git push
```

On other machines: `git pull && ./install.sh`.
