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

> **herdr is the one component here that does not wear the Midori palette.**
> Its chrome is a built-in theme pair; only the accent and the background stay
> Midori. This is a workaround with an expiry date — see below.

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
- `black`, `dim` — not valid `[theme.custom]` keys at all
- `panel_bg = "reset"` — no effect on either element

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
panel_bg = "reset"
accent   = "green"
```

| Element | Under `terminal` | Now |
|---|---|---|
| Selected row (dark) | `#9c958a` slab | `#101010` bg, white bold — **17.9:1** |
| Active tab (dark) | sage on sage — **1.22:1** | `#101010` on sage — **~8:1** |
| Active tab (light) | — | cream on `#5f6f5e` — **~5.4:1** |

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

Agent state colours are not overridden. `red`/`green`/`yellow` land on ANSI
1/2/3 — wine, sage, ochre — already the mapping the design language wants
(ochre = needs you, sage = progress, wine = failure).

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
tmux new-session -d -s hprobe -x 100 -y 30 'herdr'; sleep 3
tmux capture-pane -p -e -t hprobe: | head -1     # tab row
tmux kill-session -t hprobe
```

The probe attaches a second client; it does not disturb an attached session.

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
