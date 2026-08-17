# herdr — Midori

[herdr](https://herdr.dev) is an agent-aware terminal multiplexer: it recognises
coding agents running in panes, tracks whether each is working / blocked / idle,
and rolls that state up so one sidebar answers "which project needs me?"

```sh
brew install herdr
./install-herdr.sh
```

`install.sh` at the repo root runs this too, and skips cleanly when herdr isn't
installed.

> **herdr is the one component here that does not fully wear the Midori
> palette.** Its surfaces come from a built-in theme pair; everything herdr
> exposes a key for — background, body text, accent and the four state
> colours — is named, so it resolves against the Ghostty palette in both
> appearances. The greys and surfaces that remain have no key at all. This is a
> workaround with an expiry date — see below.

## There is no "midori" theme, and you can't add one

As of 0.8.0 the theme list is fixed —

`catppuccin` · `catppuccin-latte` · `terminal` · `tokyo-night` ·
`tokyo-night-day` · `dracula` · `nord` · `gruvbox` · `gruvbox-light` ·
`one-dark` · `one-light` · `solarized` · `solarized-light` · `kanagawa` ·
`rose-pine` · `vesper`

— with no themes directory and no theme-file loader. There is also no
`[theme.custom.dark]` / `[theme.custom.light]`; overrides are global, so one set
cannot serve both appearances.

**The failure is silent.** An unrecognised theme name is not an error:

```
$ herdr config check          # with name = "midori"
config: ok
$ herdr server reload-config
{"status":"applied","diagnostics":[]}
```

Both clean — and herdr renders **Catppuccin Mocha**. Measured from a capture:
`#1e1e2e`, `#cdd6f4`, `#a6e3a1`, `#cba6f7`. Neither `config check` nor
`reload-config` validates theme *names*, so always confirm a theme change by
capturing a render (recipe at the bottom).

## Why not the `terminal` theme

`name = "terminal"` derives herdr's UI from the host terminal, which would make
Ghostty's `light:midori-paper,dark:midori-night` pair the single source of truth
and give exactly correct Midori colours. It produces an unusable UI, because
herdr hardcodes **ANSI index 8** for two roles:

| Element | Emitted as | Role |
|---|---|---|
| Selected sidebar row | `[100m` | background |
| Active tab label | `[90m` | foreground |

herdr assumes index 8 is a dark surface gray, as it is in Catppuccin and
one-dark. Midori maps index 8 to `--muted` — `#9c958a` night, `#524d46` paper —
a mid/light warm gray, because Midori uses that slot for dim **text**.
Surface-versus-text mismatch. Under `terminal` you get a glaring light slab on
the selected workspace and an active tab number at **1.22:1**.

Not reachable from config, verified by setting sentinel colours:

- `selection`, `surface`, `muted` — row stays `[100m`
- `black`, `dim`, `brightblack` — rejected; not valid colour values
- `panel_bg = "reset"` — no effect on either element

The binary settles it faster than sentinel probing does. Both codes are literal
constants, and the colour-name table has no `bright*` entries at all — so index 8
isn't merely hardcoded here, it is **unnameable from config for any setting**:

```sh
$ strings -n 4 "$(command -v herdr)" | grep -oE '\[(90|100)m' | sort | uniq -c
   1 [90m
   1 [100m
$ strings "$(command -v herdr)" | grep -oiE '\b(bright)?(black|red|green|yellow|blue|magenta|cyan|white)\b' | sort -u
black blue cyan green magenta red white yellow
```

## "Then just change Ghostty's index 8" — no, and here is the proof

The obvious counter-move is to stop bending herdr and bend the palette instead:
remap ANSI 8 to a dark surface so `name = "terminal"` becomes usable. It doesn't
work, and the reason is a constraint rather than a preference.

Index 8 has to serve three roles at once:

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

Not "hard" — impossible. No index 8 exists, in any palette, that does this. A
and C pull in opposite directions: A wants index 8 far from a dark background
(so, light), C wants it far from a mid-light sage accent (so, dark).

Drop role A — relocate the whole subdued tier off index 8 — and herdr alone
becomes satisfiable: **8.65:1** on night at luminance 0.000, **5.35:1** on paper
at luminance 1.000. But read what those numbers say index 8 would have to
become: **near-black on night, near-white on paper**. It stops being a colour
and becomes a surface.

The cost of that is the whole point:

| | index 8 today | dim-text contrast | as herdr's surface | dim-text contrast |
|---|---|---|---|---|
| Night | `#9c958a` | **5.92:1** | ~`#000000` | **1.20:1** |
| Paper | `#524d46` | **7.41:1** | ~`#ffffff` | **1.13:1** |

Midori's own consumers could be repointed — that's four files. What can't be
repointed is **every other TUI you will ever run**, because "bright black = dim
text" is a terminal-wide convention, not a Midori invention. Making index 8 a
surface fixes one app's chrome by breaking dimmed output everywhere else.

So the vesper workaround stays. The fix belongs upstream, where herdr should be
reading a surface colour from index 0 (`#22211e` night, `#2a2825` paper — an
actual surface, already correct in this palette) instead of index 8.

## What this ships instead

Built-in themes carry their own palette, so they render the index-8 role as a
proper dark surface.

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

| Element | Under `terminal` | Now |
|---|---|---|
| Selected row (dark) | `#9c958a` slab | `#101010` bg, white bold — **17.9:1** |
| Active tab (dark) | sage on sage — **1.22:1** | `#101010` on sage — **~8:1** |
| Active tab (light) | — | cream on `#5f6f5e` — **~5.4:1** |

### The full `[theme.custom]` surface is seven keys, and all seven are now used

`panel_bg` · `accent` · `red` · `green` · `yellow` · `blue` · `text`

That list is **complete and empirically established**, not read off the docs,
which only ever show four of them by example. Feed any other key to
`herdr config check` and it says so:

```
$ herdr config check          # with magenta = "green" under [theme.custom]
unknown config key theme.custom.magenta; ignoring key
```

`magenta`, `cyan`, `white`, `black`, `fg`, `bg`, `foreground`, `background`,
`border`, `selection`, `surface`, `muted`, `dim`, `warning`, `error`, `info`,
`success`, `cursor` and `highlight` are all rejected. So the vesper greys and
surfaces that remain are simply **not addressable** — that's the ceiling, and
it's why herdr can't be fully Midori rather than a matter of trying harder.

This file previously set only `panel_bg` and `accent`, on the stated grounds
that the state colours "already resolve to ANSI 1/2/3." That was true under
`name = "terminal"` and **stopped being true when this config moved to
vesper** — they were coming from vesper's palette. Naming all of them puts them
back on the Ghostty palette in both appearances.

`text = "reset"` is the one that needed thought. It means the terminal's
*default* foreground, which is Midori's `--foreground` in both appearances;
`text = "white"` would pin ANSI 7, a light warm gray that is right on night and
far too light on cream — the auto_switch trap this file avoids everywhere else.
Measured under identical render conditions: `reset` 125 terminal-resolved
emissions, `white` 122, unset 122, with `reset` also dropping vesper's
`#ffffff`.

Net effect, measured: vesper hexes in a render drop from **8 to 6**
(`#99ffe4` and `#ffffff` replaced by terminal-resolved colour), and no `[90m` /
`[100m` regression. This is a real gain but a modest one — the six that remain
(`#101010`, `#232323`, `#5c5c5c`, `#7e7e7e`, `#a0a0a0`, `#ffd1a8`) have no key,
and `#101010` is one we *want*, since it's the dark surface that makes the
selected row readable in the first place.

Caveat on the evidence: an idle probe render only exercises `green`, so `red`,
`yellow` and `blue` are unobserved. They go through the identical named-colour
path that `accent` demonstrably uses (`[42m` in every capture), but they'll only
show once an agent is actually blocked or failed.

Two overrides survive, and both keep Midori present:

- **`panel_bg = "reset"`** — herdr paints no panel fill, so Ghostty's baked
  dot-grid and glow show through the sidebar and tab row. This is most of why
  the result still reads as Midori.
- **`accent = "green"`** — a *named* colour is emitted as a raw ANSI code
  (`[42m`), which the terminal resolves against the Ghostty palette. So the
  accent is genuine Midori sage in both appearances (`#9aab97` night, `#5f6f5e`
  paper) even though the chrome around it is vesper. **A hex here would freeze
  it and lose that** — the general rule for this file is named colours yes,
  Midori hex no.

The active tab works in both directions for a related reason: herdr uses the
theme's *background* as the tab label's foreground, and both the theme
background and ANSI 2 invert together across the appearance flip.

Agent state colours land on ANSI 1/2/3/4 — wine, sage, ochre, indigo — already
the mapping the design language wants (ochre = needs you, sage = progress, wine
= failure). They are named explicitly rather than left to the base theme; see
the seven-key section above for why leaving them out stopped working.

## What else the appearance surface offers (0.8.0, audited Aug 2026)

`herdr --default-config` prints every key with its default and is the only
complete reference — the published docs omit most of `[ui]`. Audited against it,
three things were worth taking and one was worth refusing.

**Taken.** `pane_scrollbars = false` and `hide_tab_bar_when_single_tab = true`.
Both hand pixels back to the dot grid showing through `panel_bg = "reset"`,
which is the main reason this still reads as Midori; turning scrollbars off also
keeps that column out of terminal-native selections, so mouse-copy from a pane
stops picking it up. The cost is real: no interactive scrollbars. Revert by
deleting the two lines.

**Refused: sidebar token styles are hex-only, so they can't be Midori.**
`[ui.sidebar.agents]` and `[ui.sidebar.spaces]` accept per-token styling —
`rows = [[{ token = "workspace", fg = "#89b4fa", bold = true }, "tab"], ...]` —
which looks like the missing hook for painting individual sidebar elements
Midori. It isn't, for the same reason `[theme.custom]` hex is refused above: the
`fg` field takes **only** `#RGB`/`#RRGGBB`, and with `auto_switch = true` one
global value has to serve both appearances. A named colour is rejected outright:

```
$ herdr config check      # rows = [[{ token = "branch", fg = "green" }, ...]]
config parse error: TOML parse error at line 102, column 38
data did not match any variant of untagged enum RawSidebarToken
; using defaults
```

Verified on both `[ui.sidebar.agents]` and `[ui.sidebar.spaces]`. Note the tail:
**`; using defaults`** — a bad `rows` array doesn't stop startup, it silently
discards your whole sidebar layout. Same failure family as the theme-name
fallback above, so the same rule applies: confirm by capturing a render.

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
inserted *above* `[ui.toast]`.

## Upstream

Source is [github.com/herdrdev/herdr](https://github.com/herdrdev/herdr) (the
site is herdr.dev; the `clap` issue URLs in the binary are clap's, not herdr's).
Two things here are worth fixing upstream rather than working around forever:

1. **Index 8 hardcoded for a background.** Cheapest fix is adding the eight
   `bright*` names to the colour parser so `[theme.custom]` can address these
   roles; the better one is deriving the selected-row background from relative
   luminance against the terminal background instead of assuming index 8 is
   darker. Best of all would be reading index 0, which is a surface slot by
   convention and is already the right colour here. See the proof above for why
   this cannot be fixed downstream by any palette: the roles herdr assigns to
   index 8 are mutually unsatisfiable with the one the terminal convention
   assigns it. Adding `[theme.custom.dark]` / `[theme.custom.light]` would help
   independently — with `auto_switch` on, a single global block can't serve both
   appearances, which makes hex overrides useless to anyone who auto-switches.
2. **Silent fallback on an unknown theme name** — a warning from `config check`
   would have saved the whole investigation above.

## Reverting when herdr fixes this

When herdr stops hardcoding index 8 for surfaces, set all three theme names back
to `"terminal"`, keep the two `[theme.custom]` entries, and delete the
explanation. That restores exact Midori colours everywhere with no other change.

## Verifying

```sh
herdr config check                 # keys only — does NOT validate theme names
herdr server reload-config         # applies to a running server
```

Neither can tell you the theme is right. To check colours, render and read the
escape sequences:

```sh
tmux -L hprobe -f /dev/null new-session -d -x 100 -y 30 \
  'env -u HERDR_ENV -u HERDR_SESSION -u HERDR_SESSION_NAME -u HERDR_PANE_ID herdr'
sleep 6
tmux -L hprobe capture-pane -p -e | cat -v | grep -oE '\^\[\[[0-9;]*m' | sort | uniq -c | sort -rn
tmux -L hprobe kill-server
```

Three details, all load-bearing — the naive version fails in three different
silent ways:

- **`-L hprobe`** — a separate socket keeps this off your real tmux server.
- **`-f /dev/null`** — skips `~/.tmux.conf`, so tpm doesn't load tmux-continuum.
  With `@continuum-restore 'on'`, a plain `tmux new-session` **silently restores
  your entire saved session layout** as a side effect. On a machine where tmux
  is kept as a cold fallback, the naive recipe resurrects every saved session.
- **`env -u HERDR_*`** — herdr refuses to nest. Run from inside a herdr pane (the
  normal case, since you're theming herdr) those five inherited variables make it
  **exit immediately**. The symptom is an empty `capture-pane`, which reads as
  "the theme rendered nothing" rather than "herdr never started". Check
  `tmux -L hprobe list-panes` before believing an empty capture.

`sleep 3` is not always enough for first paint; 6 is reliable here.

Read the histogram, not the first line — the tab row isn't reliably line 1.
A healthy render on this config shows **`[32m`** (the named sage accent, resolved
by the terminal) and **no `[90m` or `[100m`**. Seeing those two is the regression
this whole file exists to prevent.

The probe attaches a second client to the herdr session; it does not disturb an
attached one.

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
