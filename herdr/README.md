# herdr — Midori

[herdr](https://herdr.dev) is an agent-aware terminal multiplexer: it recognises
coding agents running in panes, tracks whether each is working / blocked / idle,
and rolls that state up so one sidebar answers "which project needs me?"

```sh
brew install herdr        # 0.9.0 or later — see below
./install-herdr.sh
```

`install.sh` at the repo root runs this too, and skips cleanly when herdr isn't
installed.

> **herdr wears the Midori palette in both appearances, from herdr 0.9.0.**
> Through 0.8.x it was the one component here that could not, and ran vesper /
> solarized-light chrome instead; that record and the proof behind it are kept
> under [0.8.x](#08x-why-this-used-to-run-vesper) at the bottom. On 0.8.x this
> config renders the ANSI 8 slab it was written to avoid — upgrade first.

## How it works

There is still no "midori" theme name and no theme-file loader. Midori gets in
through the built-in **`terminal`** theme, which derives herdr's UI from the
host terminal: every *named* colour is emitted as a raw ANSI code that Ghostty
resolves against `light:midori-paper,dark:midori-night`. Ghostty stays the
single source of truth for everything that has an ANSI slot.

`terminal` was unusable in 0.8.0 because of what it **assigns**, not the idea.
Its palette (`Palette::terminal()` in `src/app/state.rs`) hardcodes these roles
to ANSI slots that mean something else in Midori, and 0.8.0 exposed none of them:

| Roles | Base emits | Why that fails in Midori |
|---|---|---|
| `active_row_bg`, `surface1`, `surface_dim` | DarkGray — `[100m` / `[90m`, ANSI 8 | ANSI 8 is Midori's dim **text**: a row surface at 1.76:1 paper / 2.43:1 night; the active tab label on sage at **1.22:1** |
| `overlay0`, `subtext0`, `mauve` | Gray — `[37m`, ANSI 7 | near-white: 1.54:1 on cream |
| `overlay1` | White — `[97m`, ANSI 15 | `#faf9f6`: 1.07:1 on cream, i.e. invisible |
| `selection_bg` | Reset | the navigate-mode cursor row gets no background at all |

herdr 0.9.0 exposes all nineteen palette keys and adds `[theme.custom.light]` /
`[theme.custom.dark]` (#2324), so each role is re-pointed — to a named slot that
means the right thing in both appearances where one exists, and per appearance
where none does.

### Named, both appearances

| Key | Value | Resolves to (paper / night) |
|---|---|---|
| `panel_bg` | `reset` | no fill — Ghostty's dot grid and glow show through |
| `text`, `overlay1` | `reset` | `--foreground` `#2a2825` / `#ebe8e2` |
| `accent` | `green` | sage `#5f6f5e` / `#9aab97` |
| `red` `green` `yellow` `blue` | same names | wine / sage / ochre / indigo — failure / progress / needs you |
| `overlay0`, `subtext0` | `darkgray` | ANSI 8, Midori's dim text: **7.41:1** / **5.92:1** |

`darkgray` is the reversal worth noticing. ANSI 8 was the whole problem as a
*surface*; as *secondary text* it is exactly what Midori assigns that slot.
(0.9.0's colour parser also added `darkgray` and the `light*` names; 0.8.0 had
neither.)

### Per appearance

Midori has no ANSI slot that is a surface (0 is ink on paper, 8 is dim text), so
the surfaces are hex — safe now only because they are per appearance. Every hex
already exists in the Midori palette (`ghostty/themes/*`, `palette.json`).

| Key | Paper | Night | Measured |
|---|---|---|---|
| `active_row_bg` — focused workspace / agent row | `#ced1c8` | `#40453d` | Ghostty's selection wash. Text **9.50:1** / **8.04:1** |
| `selection_bg` — navigate-mode cursor row | `#a29f98` | `#6e685f` | vs the focus wash 1.71:1 / 1.78:1; text 5.56:1 / 4.51:1 |
| `surface1` — dragged row, overlay rules | `#e1dfd9` | `#2f2e2b` | split-divider tone |
| `surface_dim` — sidebar separator + active tab label | `#e1dfd9` | `#2f2e2b` | separator = Ghostty's divider (1.18:1 / 1.29:1); tab label on sage **4.02:1** / **5.59:1** |
| `mauve` — focused row's branch line, key names, resize bar | `magenta` | `lightmagenta` | on the focus wash: 5.28:1 / 3.76:1 |

**`auto_switch` must stay `true`** even though `dark_name` and `light_name` are
both `terminal`. The per-appearance blocks are applied only when auto_switch
picks an appearance (`resolve_effective_theme`, `src/app/mod.rs`); with it off
they are silently ignored and every surface falls back to the ANSI 8 slab — the
first sabotage run below is exactly that. Appearance comes from the terminal's
OSC 11 background or its colour-scheme report; if neither answers, herdr
assumes dark.

### Where the values fight, and what lost

- **`surface_dim` is two roles.** With `panel_bg = "reset"`, herdr uses it for the
  sidebar separator *and* for text drawn on the sage accent — the active tab
  label and mode-bar label (`panel_contrast_fg`, `src/ui/widgets.rs`). A line
  wants distance from the page; a label on mid-tone sage wants the page colour.
  The divider tone is the compromise, and the tab label on paper is the cost:
  4.02:1, bold, short.
- **`mauve` sits on the focus wash, not the page.** `sidebar.rs` draws it only on
  the focused row. No single purple slot reads there in both appearances —
  `magenta` is 5.28:1 paper but 2.80:1 night, `lightmagenta` 3.76:1 night but
  3.61:1 paper — so each appearance takes its better one. 3.76:1 is the ceiling
  for any purple on the night wash; `darkgray` (3.31:1) loses the cue and
  `reset` (8.04:1) duplicates the row's first line.
- **`overlay0` also colours inactive pane borders.** Upstream couples them, so
  borders are dim-text weight rather than hairline. Split-role requests:
  herdr Discussions [#3156](https://github.com/herdrdev/herdr/discussions/3156)
  and [#3802](https://github.com/herdrdev/herdr/discussions/3802).

### Two beliefs this config was briefly built on, both wrong

Recorded because both read correctly off the source at a glance.

1. **"`selection_bg` falls back to `active_row_bg`."** It does not. They are
   different states: `sidebar.rs` paints the *selected* row (navigate cursor)
   with `selection_bg` and the *focused* row with `active_row_bg`. Leave
   `selection_bg` unset under `terminal` and the cursor has no background.
2. **"`surface_dim` is also the mouse-selection background in panes."**
   `selection_palette_background` in `src/ui/panes.rs` does return it when
   `panel_bg` is reset — but only as the input to a fallback. When the terminal
   answers OSC 11, as Ghostty does, `automatic_selection_bg` mixes the **page**
   colour 28% toward black or white and never reads `surface_dim`. The first
   draft picked the selection wash for `surface_dim` on that belief, which put
   the paper tab label at 3.46:1 instead of 4.02:1.

## Upgrading from 0.8.x

**Order matters, and the second step stops every pane.**

1. `HOMEBREW_NO_INSTALL_CLEANUP=1 brew upgrade herdr` — safe while 0.8.x runs.
   The running server and attached client keep the binary they started with,
   and the Claude Code hook (`~/.claude/hooks/herdr-agent-state.sh`) writes to
   the socket from Python rather than calling the `herdr` CLI, so agent state
   keeps reporting. Keeping the 0.8.0 keg leaves a rollback.
2. **Restart the server when you are ready to lose the panes.** 0.9.0 moved to
   endpoint generation 1 and the terminal UI into each client (#3487, #3509). A
   0.9.0 client *refuses* a 0.8.x server rather than replacing it —
   `This session needs one final server update before Herdr can attach (the
   stable endpoint generation is incompatible)` — so nothing restarts by
   surprise, but the new theme cannot show until the server is 0.9.0. The
   server owns every pane's process. On restart, restored panes are cold-spawned
   headless at 24×80, and full-screen agents lose their visible transcript
   ([#3864](https://github.com/herdrdev/herdr/issues/3864), open); relaunch them
   with `--resume`. Park or finish agents first.

Do not restart herdr **before** step 1: 0.8.0 reads this config, ignores the
0.9.0 keys as unknown, and renders the `terminal` base unmodified — the slab.

`install-herdr.sh` warns when herdr is older than 0.9.0, and no longer reports a
failed reload as "no server running": right after an upgrade, a failed reload
usually means the server is still 0.8.x.

## Sidebar token `fg` is still hex-only (unchanged in 0.9.0)

`[ui.sidebar.agents]` and `[ui.sidebar.spaces]` accept per-token styling —
`rows = [[{ token = "workspace", fg = "#89b4fa", bold = true }, "tab"], ...]` —
which looks like the hook for painting individual sidebar elements Midori. It
still isn't. `fg` takes **only** `#RGB`/`#RRGGBB` (`src/config/sidebar.rs`), has
no per-appearance form, and `auto_switch` never reaches the token layer, so one
hex has to serve paper and night. A named colour is rejected outright:

```
$ herdr config check      # rows = [[{ token = "branch", fg = "green" }, ...]]
config parse error: TOML parse error at line 102, column 38
data did not match any variant of untagged enum RawSidebarToken
; using defaults
```

(Measured on 0.8.0; the 0.9.0 source is unchanged.) Note the tail:
**`; using defaults`** — a bad `rows` array doesn't stop startup, it silently
discards your whole sidebar layout. Confirm by capturing a render.

Upstream requests, all open with no maintainer reply as of Sept 2026 — herdr
takes feature requests in **Discussions**, not Issues (a bot closes feature
issues, e.g. #3093): theme references in token `fg`
([#2772](https://github.com/herdrdev/herdr/discussions/2772)), token `fg`
following the active appearance
([#3497](https://github.com/herdrdev/herdr/discussions/3497)), and SGR colour
passthrough from custom tokens
([#3096](https://github.com/herdrdev/herdr/discussions/3096)).

## What else the appearance surface offers (0.8.0, audited Aug 2026)

`herdr --default-config` prints every key with its default and is the only
complete reference — the published docs omit most of `[ui]`. Audited against it,
three things were worth taking and one was worth refusing (the sidebar token
styles above).

**Taken.** `pane_scrollbars = false` and `hide_tab_bar_when_single_tab = true`.
Both hand pixels back to the dot grid showing through `panel_bg = "reset"`,
which is the main reason this still reads as Midori; turning scrollbars off also
keeps that column out of terminal-native selections, so mouse-copy from a pane
stops picking it up. The cost is real: no interactive scrollbars. Revert by
deleting the two lines.

**Open, deliberately not taken:** `row_gap = 1` under either sidebar block
restores the older, airier spacing. It suits Midori's typography everywhere
else, but the sidebar is a *scanning* surface, not a reading one — the agent
rollup is the reason to run herdr, and doubling row height halves how many
agents you can see at once. Density wins here; take the air only if you run few
agents.

Two knobs that are per-machine rather than per-theme, noted so they aren't
rediscovered: `sidebar_min_width` / `sidebar_max_width` (18/36) bracket the
auto-scaled `sidebar_width`, and `mobile_width_threshold` (64) is the column
count below which herdr switches to the single-column layout — the one that
matters on a phone under Moshi.

**A TOML trap worth stating**, because it cost a debugging round here: appending
keys to the end of this file files them under the **last section**, which is
`[ui.toast]`. `config check` catches it, but the message names the wrong owner
(`unknown config key ui.toast.pane_scrollbars`), which reads like the key
doesn't exist rather than like it's in the wrong place. `[ui]` keys must be
inserted *above* `[ui.toast]`. The same applies to `[theme.custom.light]` and
`[theme.custom.dark]`: a key meant for both appearances must sit above them.

## Upstream

Source is [github.com/herdrdev/herdr](https://github.com/herdrdev/herdr) (the
site is herdr.dev; the `clap` issue URLs in the binary are clap's, not herdr's).

Both things this file used to ask for landed in 0.9.0: the index-8 roles are
overridable keys, and `herdr config check` now reports an unknown theme name
(`unknown theme name theme.name = "midori"; using "catppuccin"`) where 0.8.0
printed `config: ok`. The **defaults** of the `terminal` theme are still wrong
for any palette whose ANSI 8 is dim text — open as
[#3262](https://github.com/herdrdev/herdr/issues/3262) (active tab invisible),
[#1731](https://github.com/herdrdev/herdr/issues/1731) (dark selected-row bar on
light palettes) and [#1307](https://github.com/herdrdev/herdr/issues/1307)
(`terminal` unreadable with a Ghostty light theme). This config works around
them; it does not depend on them being fixed.

## Verifying

```sh
herdr config check                 # keys AND theme names, as of 0.9.0
herdr server reload-config         # applies to a running server
```

Neither can tell you a valid config *looks* right. Render it in an isolated
herdr and check the escape sequences:

```sh
R=/tmp/hp; A=light                 # A=dark: use bg=#1a1917,fg=#ebe8e2 below
rm -rf $R; mkdir -p $R/herdr
{ echo 'onboarding = false'; cat herdr/config.toml; } > $R/herdr/config.toml
iso() { env -u HERDR_ENV -u HERDR_SOCKET_PATH -u HERDR_PANE_ID -u HERDR_TAB_ID \
  -u HERDR_WORKSPACE_ID -u TMUX XDG_CONFIG_HOME=$R XDG_STATE_HOME=$R/state "$@"; }
iso tmux -L hprobe -f /dev/null new-session -d -x 120 -y 32 -s p 'sleep 900'
iso tmux -L hprobe set -g window-style 'bg=#f3f1eb,fg=#2a2825'
iso tmux -L hprobe respawn-pane -k -t p "env -u HERDR_ENV -u HERDR_SOCKET_PATH \
  -u HERDR_PANE_ID -u HERDR_TAB_ID -u HERDR_WORKSPACE_ID \
  XDG_CONFIG_HOME=$R XDG_STATE_HOME=$R/state $(command -v herdr)"
sleep 7
iso herdr workspace create --label alpha --cwd /tmp; iso herdr tab create; sleep 4
# optional, to also exercise selection_bg: open navigate mode and move the cursor
# for k in C-b w Down; do iso tmux -L hprobe send-keys -t p $k; sleep 1; done
iso tmux -L hprobe capture-pane -p -e -t p > $R/$A.ansi
iso herdr server stop; iso tmux -L hprobe kill-server
python3 tests/check_rendered_herdr.py $R/$A.ansi '#ced1c8' '#e1dfd9'   # dark: '#40453d' '#2f2e2b'
                                   # navigate capture: light '#a29f98', dark '#6e685f'
```

Every detail is load-bearing; the naive version fails in silent ways:

- **`XDG_CONFIG_HOME` and every `HERDR_*` unset** — the probe gets its own server,
  socket and config, and never touches the live session. From inside a herdr
  pane the inherited variables would otherwise make herdr refuse to nest (0.8.x:
  it exits and the capture is empty) or aim at the live server.
- **A short `R`.** herdr puts `herdr.sock` and `herdr-client.sock` in the config
  directory, and a Unix socket path must fit `sun_path` — 104 bytes on macOS. A
  long scratch path fails with `local socket name length exceeds capacity of
  sun_path`, and the capture shows a shell, not herdr.
- **`window-style bg=`** — herdr picks the appearance from the terminal's OSC 11
  answer, and a detached tmux answers with the window style. Without it there
  is no answer, herdr assumes dark, and a "light" capture is silently a dark one.
- **`-L hprobe`** — a separate socket keeps this off your real tmux server.
- **`-f /dev/null`** — skips `~/.tmux.conf`, so tpm doesn't load tmux-continuum.
  With `@continuum-restore 'on'`, a plain `tmux new-session` **silently restores
  your entire saved session layout** as a side effect.
- **A second workspace and tab** — `hide_tab_bar_when_single_tab` hides the tab
  label otherwise, and one workspace never shows an unfocused row.

`sleep 3` is not always enough for first paint; 7 is reliable here.

What `check_rendered_herdr.py` measured on the shipped config (herdr 0.9.0,
120×32, ~1017 cells per capture — the total moves with the pane's own shell
prompt, the chrome counts below do not), identical in both appearances:

| Role | Light | Dark | Cells |
|---|---|---|---|
| sidebar separator / rules | fg `#e1dfd9` | fg `#2f2e2b` | 61 |
| focused workspace row | bg `#ced1c8` | bg `#40453d` | 52 |
| secondary text | fg ANSI 8 | fg ANSI 8 | 39 |
| active tab label | `#e1dfd9` on ANSI 2 | `#2f2e2b` on ANSI 2 | 8 |
| focused row's branch line (`mauve`) | ANSI 5 on `#ced1c8` | ANSI 13 on `#40453d` | 4 |
| navigate cursor row (`prefix+w`, `down`) | bg `#a29f98` | bg `#6e685f` | 29 |

**`ctrl+b` then `down` does not open navigate mode.** That capture came back
byte-for-byte the same colours as an idle one, which reads as "the cursor has no
background" — the exact bug `selection_bg` is set to prevent. Navigate mode is
the `workspace_picker` action (`prefix+w`; `src/client/shell/actions.rs`).

No ANSI 7/8/15 background, no ANSI 7/15 text, no ANSI 8 on the accent, and the
light capture contains no night surface. The check is sabotage-proven: with
`auto_switch = false` it fails naming `bg ansi8` (58 cells) and `fg ansi8 on
accent` (8), and with `overlay0`/`subtext0` removed it fails naming `fg ansi7`
(41).

## Not covered here

- **Workspace layout.** This config sets sidebar width and `agent_panel_sort`,
  but workspaces are per-machine state, not theme. Create them with
  `herdr workspace create --label <name> --cwd <dir> --no-focus` — `--label`
  does *not* set the directory, and omitting `--cwd` silently roots every
  workspace at the server's cwd.
- **Moshi.** herdr is first-class in Moshi (own session-picker tab, swipe =
  tabs / two-finger = panes / two-finger vertical = workspaces). Nothing here is
  needed for that; `moshi-hook` detects herdr on its own. The `MOSHI_CLIENT`
  status-bar workaround in `tmux/midori.tmux.conf` is tmux-only — herdr uses
  `$HERDR_ENV` / `$HERDR_SESSION` and has no status bar to scrape.

---

## 0.8.x: why this used to run vesper

Kept as the record. Everything below was measured on herdr 0.8.0 and was true
there; what changed in 0.9.0 is noted inline.

### There was no custom theme, and the failure was silent

The theme list was fixed —

`catppuccin` · `catppuccin-latte` · `terminal` · `tokyo-night` ·
`tokyo-night-day` · `dracula` · `nord` · `gruvbox` · `gruvbox-light` ·
`one-dark` · `one-light` · `solarized` · `solarized-light` · `kanagawa` ·
`rose-pine` · `vesper`

— with no themes directory and no theme-file loader, and no
`[theme.custom.dark]` / `[theme.custom.light]`: overrides were global, so one set
could not serve both appearances. An unrecognised theme name was not an error:

```
$ herdr config check          # with name = "midori"
config: ok
$ herdr server reload-config
{"status":"applied","diagnostics":[]}
```

Both clean — and herdr rendered **Catppuccin Mocha**: `#1e1e2e`, `#cdd6f4`,
`#a6e3a1`, `#cba6f7`. *(0.9.0 reports the unknown name.)*

### Why not the `terminal` theme

Under `terminal`, herdr emitted **ANSI index 8** for two roles:

| Element | Emitted as | Role |
|---|---|---|
| Selected sidebar row | `[100m` | background |
| Active tab label | `[90m` | foreground |

herdr assumes index 8 is a dark surface gray, as it is in Catppuccin and
one-dark. Midori maps index 8 to `--muted` — `#9c958a` night, `#524d46` paper —
a mid/light warm gray, because Midori uses that slot for dim **text**.
Surface-versus-text mismatch: a glaring light slab on the selected workspace and
an active tab number at **1.22:1**.

Not reachable from 0.8.0 config, verified by setting sentinel colours:

- `selection`, `surface`, `muted` — row stays `[100m`
- `black`, `dim`, `brightblack` — rejected; not valid colour values
- `panel_bg = "reset"` — no effect on either element

The binary settled it faster than sentinel probing did — both codes were literal
constants, and the colour-name table had no `bright*` entries:

```sh
$ strings -n 4 "$(command -v herdr)" | grep -oE '\[(90|100)m' | sort | uniq -c
   1 [90m
   1 [100m
$ strings "$(command -v herdr)" | grep -oiE '\b(bright)?(black|red|green|yellow|blue|magenta|cyan|white)\b' | sort -u
black blue cyan green magenta red white yellow
```

*(What was wrong with this reading, found in the 0.9.0 source: the strings are
not hardcoded per role — they are the entries herdr's own ANSI renderer
(`src/protocol/render_ansi.rs`) emits for `Color::DarkGray`, once each for
foreground and background, and `Palette::terminal()` assigns DarkGray to
`active_row_bg`, `surface1` and `surface_dim`. The conclusion held for 0.8.0 because those were
not config keys; it stopped holding the moment they became keys. 0.9.0 also
added `darkgray` and the `light*` names to the parser.)*

### "Then just change Ghostty's index 8" — no, and here is the proof

Still true on every version, and the reason the fix had to come from herdr:
index 8 has to serve three roles at once.

| | role | wants index 8 to be |
|---|---|---|
| **A** | Midori dim text — tmux status, fzf `info`/`header`/`border`, zsh-autosuggestions | far from the **page background** |
| **B** | herdr's selected-row **background**, under the theme foreground | far from the **foreground** |
| **C** | herdr's active-tab **foreground**, on the sage accent | far from the **accent** |

Sweeping every possible luminance in 2000 steps, the best value that satisfies
all three:

| | best `min(A,B,C)` | verdict |
|---|---|---|
| Midori Night | **2.69:1** | impossible |
| Midori Paper | **2.18:1** | impossible |

Not "hard" — impossible. A and C pull in opposite directions: A wants index 8
far from a dark background (so, light), C wants it far from a mid-light sage
accent (so, dark).

Drop role A — relocate the whole subdued tier off index 8 — and herdr alone
becomes satisfiable: **8.65:1** on night at luminance 0.000, **5.35:1** on paper
at luminance 1.000. But index 8 would then have to become **near-black on night,
near-white on paper** — a surface, not a colour:

| | index 8 today | dim-text contrast | as herdr's surface | dim-text contrast |
|---|---|---|---|---|
| Night | `#9c958a` | **5.92:1** | ~`#000000` | **1.20:1** |
| Paper | `#524d46` | **7.41:1** | ~`#ffffff` | **1.13:1** |

"Bright black = dim text" is a terminal-wide convention, not a Midori invention,
so making index 8 a surface fixes one app's chrome by breaking dimmed output in
every other TUI. 0.9.0 resolved it the right way round: herdr's roles moved off
index 8, and index 8 kept the role A — now including herdr's own secondary text.

### What 0.8.x shipped instead

```toml
[theme]
name        = "vesper"
auto_switch = true
dark_name   = "vesper"            # near-black
light_name  = "solarized-light"   # #eee8d5, closest built-in to midori-paper #f3f1eb

[theme.custom]
panel_bg = "reset"   # let Ghostty's dot grid + glow show through
text     = "reset"   # terminal default fg = Midori --foreground, both modes
accent   = "green"   # named -> ANSI -> resolved by the terminal
red      = "red"
green    = "green"
yellow   = "yellow"
blue     = "blue"
```

| Element | Under `terminal` | vesper |
|---|---|---|
| Selected row (dark) | `#9c958a` slab | `#101010` bg, white bold — **17.9:1** |
| Active tab (dark) | sage on sage — **1.22:1** | `#101010` on sage — **~8:1** |
| Active tab (light) | — | cream on `#5f6f5e` — **~5.4:1** |

The full 0.8.0 `[theme.custom]` surface was **seven keys** — `panel_bg` ·
`accent` · `red` · `green` · `yellow` · `blue` · `text` — established by feeding
candidate keys to `herdr config check`, which answered
`unknown config key theme.custom.magenta; ignoring key` for anything else
(`magenta`, `cyan`, `white`, `black`, `fg`, `bg`, `foreground`, `background`,
`border`, `selection`, `surface`, `muted`, `dim`, `warning`, `error`, `info`,
`success`, `cursor`, `highlight`). *(0.9.0: nineteen — `accent`, `panel_bg`,
`sidebar_bg`, `active_row_bg`, `selection_bg`, `surface0`, `surface1`,
`surface_dim`, `overlay0`, `overlay1`, `text`, `subtext0`, `mauve`, `green`,
`yellow`, `red`, `blue`, `teal`, `peach`.)*

That file first set only `panel_bg` and `accent`, on the grounds that the state
colours "already resolve to ANSI 1/2/3." True under `terminal`, and it **stopped
being true when the config moved to vesper** — they were coming from vesper's
palette. Naming all of them put them back on the Ghostty palette. `text =
"reset"` measured 125 terminal-resolved emissions against 122 for both `white`
and unset, and dropped vesper's `#ffffff`. Net effect: vesper hexes in a render
dropped from **8 to 6** (`#99ffe4` and `#ffffff` replaced); the six that remained
(`#101010`, `#232323`, `#5c5c5c`, `#7e7e7e`, `#a0a0a0`, `#ffd1a8`) had no key.
