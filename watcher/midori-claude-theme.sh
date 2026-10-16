#!/bin/sh
# Keeps ~/.claude/themes/$MIDORI_LANG.json in sync with macOS appearance for
# Claude Code (theme = custom:$MIDORI_LANG). Base light/dark (NOT -ansi: ANSI bases
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
# WHAT IS STILL MIDORI-ONLY HERE: set_scale, below. It flips the @1x/@2x
# background-image symlinks, and ghostty/backgrounds holds Midori artwork only
# -- the Lemonardo themes declare no background-image at all (they say so in
# their own comments). Under MIDORI_LANG=lemonardo those symlinks are
# maintained and referenced by nothing, which is harmless and is why this was
# left alone rather than made conditional.

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
BG_DIR="$HOME/.config/ghostty/backgrounds"

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
LAST_SCALE=""
TICK=0

# Ghostty draws background images in PHYSICAL pixels (fit=none), so the dot
# grid / glow need @2x assets on the retina panel and @1x on the LG ultrawides.
# Theme files reference stable symlink names; we flip the links when the main
# display class changes. Ghostty only re-reads images on config reload —
# user still hits Cmd+Shift+, after docking/undocking.
set_scale() {
  for m in paper night; do
    for k in glow dots; do
      ln -sf "midori-$m-$k@$1.png" "$BG_DIR/midori-$m-$k.png"
    done
  done
}

check_scale() {
  if system_profiler SPDisplaysDataType 2>/dev/null | grep -B8 "Main Display: Yes" | grep -qi retina; then
    SCALE="2x"
  else
    SCALE="1x"
  fi
  if [ "$SCALE" != "$LAST_SCALE" ]; then
    set_scale "$SCALE"
    LAST_SCALE="$SCALE"
  fi
}

# Install the map for one appearance. A theme file Claude Code cannot parse is
# worse than a stale one -- the loader falls back to a stock preset and the
# whole UI changes -- so the source is parsed before it replaces the live file,
# and a missing or broken map leaves the previous one in place and says so.
write_mode() {
  src="$THEME_DIR/$MIDORI_LANG-$1.json"
  if [ ! -f "$src" ]; then
    echo "midori-claude-theme: no $src -- leaving $THEME_FILE alone" >&2
    return 1
  fi
  if ! /usr/bin/python3 -c 'import json,sys; json.load(open(sys.argv[1]))' \
       "$src" 2>/dev/null; then
    echo "midori-claude-theme: $src is not valid JSON -- leaving $THEME_FILE alone" >&2
    return 1
  fi
  mkdir -p "$(dirname "$THEME_FILE")"
  cp -f "$src" "$THEME_FILE"
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
  # display-scale check every 10th tick (~30s); system_profiler is too slow for 3s
  if [ $((TICK % 10)) -eq 0 ]; then
    check_scale
    heal_theme_setting
  fi
  TICK=$((TICK + 1))
  sleep 3
done
