#!/bin/sh
# Keeps ~/.claude/themes/<language>.json in sync with macOS appearance for
# Claude Code (theme = custom:$MIDORI_LANG) -- every language's file, not only
# the active one; write_mode says why. Base light/dark (NOT -ansi: ANSI bases
# drop diff bg overrides). Full midori token map: diff bands = highlighter
# washes (olive/terracotta seeds from tokentrail feature-colors chroma),
# mode accents / semantic colors / chrome from the site + tokentrail palette.
# Token names dumped from the 2.1.179 binary; unknown keys are silently
# dropped by the loader, so stale names are harmless.
#
# DECOY TOKENS: `suggestion` (tips / ghost-text) and `permission` (inline
# `codespan`) are written here for completeness but DO NOTHING via this file —
# Claude Code looks them up in the stock preset for the base mode (UX(mode) in
# 2.1.202, _H in 2.1.272), which discards custom overrides, so stock periwinkle
# shows regardless of the value below. The BINARY PATCH
# (tools/patch-claude-binary.py) points both at the terminal's ANSI blue instead:
# palette 4 in the Ghostty themes, which is these same values. They are kept
# equal on purpose, and tests/test_patch_claude_binary.py fails if they drift, so
# to recolor tips or inline code change palette 4 and these together; changing
# only these has no effect. (Until Sept 2026 the patch injected these hexes as
# #-literals through tweakcc; see the patcher's docstring for why that stopped.)
# Also retints live tmux pane borders on appearance change.
# Managed by: ~/Library/LaunchAgents/com.benjaminloschen.midori-claude-theme.plist
#
# THE TOKEN MAPS USED TO BE TWO HEREDOCS IN THIS FILE and are now four JSON
# documents under ~/.local/share/midori/claude-themes/, installed from
# watcher/themes/. Nothing about the Midori maps changed in the move:
# tests/test_claude_themes.py holds watcher/themes/midori-{light,dark}.json
# byte-equal to watcher/midori-tokens-{light,dark}.json, which was extracted
# from those heredocs before they were removed, and that is the only reason to
# trust that this refactor did not quietly restyle Claude Code.
#
# The Lemonardo maps are GENERATED, by tools/make-claude-theme.py, which states
# each token as a rule (an ANSI slot, a palette role, an OKLCh wash off the
# ground, a tint of a role) rather than a hex. `--check` rebuilds MIDORI from
# those same rules and diffs it against the frozen reference; it reproduces 94
# of 96 tokens within dE 3.0, and the two it does not are `skill`, whose hue
# has no ancestor anywhere in this repo. Read that tool's TINT comment before
# assuming the generator could simply replace these files.
#
# NOTHING HERE IS MIDORI-ONLY ANY MORE. Until 2026-10-17 this file also owned
# set_scale/check_scale, which polled system_profiler every ~30s and flipped
# the @1x/@2x symlinks under ~/.config/ghostty/backgrounds when the main
# display changed class, because the Midori glow was a PNG baked per display.
# The glow is drawn by the Ghostty shader now, from the surface size, so there
# is no asset to pick and the poll is gone with it. It was also only half a
# fix while it existed: Ghostty re-reads images on config reload alone, so the
# flipped link did nothing until the user pressed Cmd+Shift+, -- which is how
# the ultrawide bake was still on the retina panel 25 minutes after the flip.

# MIDORI_LANG selects the design language. launchd passes it through the
# plist, which midori-theme edits in place and then restarts the job.
#
# THE FILE IS THE FALLBACK, NOT `midori`, and the order matters. launchd
# caches a loaded job's definition, so a plist edited without a restart leaves
# this process running the OLD value; and a plist that somehow lost the key
# would pin this watcher to Midori while every other surface had moved. Either
# way the result is one surface in the wrong language with no error anywhere.
# Reading the language file second means the worst case is a watcher that is
# merely a restart behind, and never one that is confidently wrong.
if [ -z "$MIDORI_LANG" ] && [ -r "$HOME/.config/midori/language" ]; then
  MIDORI_LANG=$(cat "$HOME/.config/midori/language")
fi
: "${MIDORI_LANG:=midori}"
THEME_DIR="$HOME/.local/share/midori/claude-themes"
THEME_FILE="$HOME/.claude/themes/$MIDORI_LANG.json"

# Inactive tmux pane border, per language and appearance. These are the only
# colours still written by hand here, and they duplicate the if-shell lines in
# tmux/midori.tmux.conf and tmux/lemonardo.tmux.conf on purpose: that file
# picks a border at server START, and this retints a server already running
# when the appearance flips. tests/test_lemonardo_twins.py reads both.
case "$MIDORI_LANG" in
  lemonardo) BORDER_DARK="#44484e"; BORDER_LIGHT="#c6cbd3" ;;
  *)         BORDER_DARK="#2f2e2b"; BORDER_LIGHT="#e1dfd9" ;;
esac
# launchd gives us a bare PATH (/usr/bin:/bin:...) — resolve tmux across
# Apple Silicon (/opt/homebrew) and Intel (/usr/local) brew prefixes.
TMUX_BIN="$(command -v tmux || true)"
if [ -z "$TMUX_BIN" ]; then
  for p in /opt/homebrew/bin/tmux /usr/local/bin/tmux; do
    [ -x "$p" ] && TMUX_BIN="$p" && break
  done
fi
[ -z "$TMUX_BIN" ] && TMUX_BIN="tmux"
LAST=""
TICK=0


# Install the map for one appearance -- for EVERY language in THEME_DIR, not
# only $MIDORI_LANG. A theme file Claude Code cannot parse is worse than a
# stale one -- the loader falls back to a stock preset and the whole UI
# changes -- so each source is parsed before it replaces the live file, and a
# missing or broken map leaves the previous one in place and says so. The
# return value is the ACTIVE language's outcome, because that is the write
# the loop below latches on; the others are best-effort.
#
# WHY EVERY LANGUAGE. This used to write $MIDORI_LANG.json alone, which left
# the other language's file to rot the moment the switch happened. A Claude
# Code session keeps the theme it started under (settings.json is read at
# launch; `custom:midori` stays `custom:midori` in that process), and it
# reads ~/.claude/themes/midori.json -- so after `midori-theme lemonardo` any
# such session followed a file nobody maintained. Measured 2026-10-15 23:13,
# screenshot of a session in a Midori Night Ghostty (ground #1a1917): the
# selection block sampled rgb(207 209 201) and the error text rgb(115 76 75)
# -- Midori LIGHT's selectionBg #ced1c8 and error #7a4a4a, not Night's #40453d
# and #b8868a -- while ~/.claude/themes/midori.json sat at base "light" with
# an mtime of 2026-10-07 07:56. (It had been light since the 7th because the
# job itself was not running until 06e9559 fixed its log path; by the time it
# ran again MIDORI_LANG was lemonardo and midori.json was no longer its
# business.) Error text at #7a4a4a on #1a1917 is 2.3:1. Writing all of them
# costs one cp per language per appearance flip and means no file a session
# can be reading is ever a mode behind.
write_mode() {
  mode="$1"
  active="$THEME_DIR/$MIDORI_LANG-$mode.json"
  if [ ! -f "$active" ]; then
    echo "midori-claude-theme: no $active -- leaving $THEME_FILE alone" >&2
    rc=1
  else
    rc=0
  fi
  for src in "$THEME_DIR"/*-"$mode".json; do
    [ -f "$src" ] || continue
    lang=$(basename "$src" "-$mode.json")
    dest="$HOME/.claude/themes/$lang.json"
    if ! /usr/bin/python3 -c 'import json,sys; json.load(open(sys.argv[1]))' \
         "$src" 2>/dev/null; then
      echo "midori-claude-theme: $src is not valid JSON -- leaving $dest alone" >&2
      [ "$lang" = "$MIDORI_LANG" ] && rc=1
      continue
    fi
    mkdir -p "$(dirname "$dest")"
    cp -f "$src" "$dest"
  done
  return "$rc"
}

# Self-heal ~/.claude/settings.json: picking a stock preset in /theme silently
# overwrites "custom:$MIDORI_LANG" and everything looks broken until someone
# remembers this file. Re-pin it (cheap grep short-circuits the common case;
# python rewrite only on actual mismatch, so we don't race Claude Code's own
# writes on every tick).
heal_theme_setting() {
  local settings="$HOME/.claude/settings.json"
  [ -f "$settings" ] || return 0
  grep -q "\"theme\"[[:space:]]*:[[:space:]]*\"custom:$MIDORI_LANG\"" "$settings" \
    && return 0
  /usr/bin/python3 - "$settings" "custom:$MIDORI_LANG" <<'PYEOF' 2>/dev/null
import json, sys
path, want = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        settings = json.load(f)
except Exception:
    sys.exit(0)  # malformed/mid-write: skip, retry next pass
if settings.get("theme") != want:
    settings["theme"] = want
    with open(path, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
PYEOF
}

while :; do
  if defaults read -g AppleInterfaceStyle 2>/dev/null | grep -qi dark; then
    MODE="dark"
  else
    MODE="light"
  fi
  if [ "$MODE" != "$LAST" ]; then
    if [ "$MODE" = "dark" ]; then
      write_mode dark
      "${TMUX_BIN:-tmux}" set -g pane-border-style "fg=$BORDER_DARK" 2>/dev/null
    else
      write_mode light
      "${TMUX_BIN:-tmux}" set -g pane-border-style "fg=$BORDER_LIGHT" 2>/dev/null
    fi
    # Only latch the appearance once the map is actually in place: a failed
    # write_mode would otherwise be retried never, and the UI would sit on the
    # other appearance's colours until the next flip.
    LAST="$MODE"
  fi
  # settings heal every 10th tick (~30s); it reads and may rewrite a JSON
  # file, which is not worth doing every 3s
  if [ $((TICK % 10)) -eq 0 ]; then
    heal_theme_setting
  fi
  TICK=$((TICK + 1))
  sleep 3
done
