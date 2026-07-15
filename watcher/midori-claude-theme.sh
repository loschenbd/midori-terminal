#!/bin/sh
# Keeps ~/.claude/themes/midori.json in sync with macOS appearance for
# Claude Code (theme = custom:midori). Base light/dark (NOT -ansi: ANSI bases
# drop diff bg overrides). Full midori token map: diff bands = highlighter
# washes (olive/terracotta seeds from tokentrail feature-colors chroma),
# mode accents / semantic colors / chrome from the site + tokentrail palette.
# Token names dumped from the 2.1.179 binary; unknown keys are silently
# dropped by the loader, so stale names are harmless.
# Also retints live tmux pane borders on appearance change.
# Managed by: ~/Library/LaunchAgents/com.benjaminloschen.midori-claude-theme.plist

THEME_FILE="$HOME/.claude/themes/midori.json"
BG_DIR="$HOME/.config/ghostty/backgrounds"
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

write_light() {
  cat > "$THEME_FILE" <<'EOF'
{
  "name": "Midori",
  "base": "light",
  "overrides": {
    "text": "#2a2825",
    "inverseText": "#faf9f6",
    "subtle": "#8a8378",
    "suggestion": "#3a5572",
    "inactive": "#9c958a",
    "inactiveShimmer": "#b5afa3",
    "error": "#7a4a4a",
    "warning": "#b88a3a",
    "warningShimmer": "#cc9c42",
    "success": "#5f6f5e",
    "remember": "#664f63",
    "merged": "#8a5a7a",
    "planMode": "#3a5572",
    "permission": "#3a5572",
    "permissionShimmer": "#4d7095",
    "autoAccept": "#b88a3a",
    "autoAcceptShimmer": "#cc9c42",
    "fastMode": "#b06d4a",
    "fastModeShimmer": "#c9916b",
    "ide": "#548373",
    "skill": "#4a6a6b",
    "professionalBlue": "#3a5572",
    "claudeBlue_FOR_SYSTEM_SPINNER": "#3a5572",
    "claudeBlueShimmer_FOR_SYSTEM_SPINNER": "#4d7095",
    "chromeYellow": "#b88a3a",
    "effortUltra": "#664f63",
    "claude": "#b06d4a",
    "claudeShimmer": "#c9916b",
    "clawd_body": "#c9916b",
    "clawd_background": "#f0e0d4",
    "briefLabelYou": "#5f6f5e",
    "briefLabelClaude": "#b06d4a",
    "selectionBg": "#ced1c8",
    "userMessageBackground": "#ebe8e0",
    "userMessageBackgroundHover": "#e4e0d6",
    "bashMessageBackgroundColor": "#edeae2",
    "bashBorder": "#3a5572",
    "memoryBackgroundColor": "#dfe7e0",
    "promptBorder": "#c9c4b8",
    "promptBorderShimmer": "#9ebfb4",
    "rate_limit_fill": "#5f6f5e",
    "rate_limit_empty": "#ddd8cc",
    "diffAdded": "#c9cebb",
    "diffAddedDimmed": "#e3e3d9",
    "diffAddedWord": "#a9b197",
    "diffRemoved": "#ddc7b7",
    "diffRemovedDimmed": "#ebe1d8",
    "diffRemovedWord": "#cea892"
  }
}
EOF
}

write_dark() {
  cat > "$THEME_FILE" <<'EOF'
{
  "name": "Midori",
  "base": "dark",
  "overrides": {
    "text": "#ebe8e2",
    "inverseText": "#1a1917",
    "subtle": "#857e72",
    "suggestion": "#6c87a4",
    "inactive": "#6f685d",
    "inactiveShimmer": "#857e72",
    "error": "#b8868a",
    "warning": "#d8b06a",
    "warningShimmer": "#e6c489",
    "success": "#9aab97",
    "remember": "#a48ba3",
    "merged": "#b08aa5",
    "planMode": "#6c87a4",
    "permission": "#6c87a4",
    "permissionShimmer": "#8ba3bd",
    "autoAccept": "#d8b06a",
    "autoAcceptShimmer": "#e6c489",
    "fastMode": "#d4a07a",
    "fastModeShimmer": "#e0b899",
    "ide": "#9ebfb4",
    "skill": "#7f9a9b",
    "professionalBlue": "#6c87a4",
    "claudeBlue_FOR_SYSTEM_SPINNER": "#6c87a4",
    "claudeBlueShimmer_FOR_SYSTEM_SPINNER": "#8ba3bd",
    "chromeYellow": "#d8b06a",
    "effortUltra": "#a48ba3",
    "claude": "#d4a07a",
    "claudeShimmer": "#e0b899",
    "clawd_body": "#d4a07a",
    "clawd_background": "#2c2520",
    "briefLabelYou": "#9aab97",
    "briefLabelClaude": "#d4a07a",
    "selectionBg": "#40453d",
    "userMessageBackground": "#262521",
    "userMessageBackgroundHover": "#2c2b26",
    "bashMessageBackgroundColor": "#22211e",
    "bashBorder": "#6c87a4",
    "memoryBackgroundColor": "#292d2a",
    "promptBorder": "#4a463f",
    "promptBorderShimmer": "#9aab97",
    "rate_limit_fill": "#9aab97",
    "rate_limit_empty": "#33322e",
    "diffAdded": "#363c2b",
    "diffAddedDimmed": "#262a20",
    "diffAddedWord": "#4b553a",
    "diffRemoved": "#473226",
    "diffRemovedDimmed": "#302620",
    "diffRemovedWord": "#744b36"
  }
}
EOF
}

# Self-heal ~/.claude/settings.json: picking a stock preset in /theme silently
# overwrites "custom:midori" and everything looks broken until someone
# remembers this file. Re-pin it (cheap grep short-circuits the common case;
# python rewrite only on actual mismatch, so we don't race Claude Code's own
# writes on every tick).
heal_theme_setting() {
  local settings="$HOME/.claude/settings.json"
  [ -f "$settings" ] || return 0
  grep -q '"theme"[[:space:]]*:[[:space:]]*"custom:midori"' "$settings" && return 0
  /usr/bin/python3 - "$settings" <<'PYEOF' 2>/dev/null
import json, sys
path = sys.argv[1]
try:
    with open(path) as f:
        settings = json.load(f)
except Exception:
    sys.exit(0)  # malformed/mid-write: skip, retry next pass
if settings.get("theme") != "custom:midori":
    settings["theme"] = "custom:midori"
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
      write_dark
      "${TMUX_BIN:-tmux}" set -g pane-border-style "fg=#2f2e2b" 2>/dev/null
    else
      write_light
      "${TMUX_BIN:-tmux}" set -g pane-border-style "fg=#e1dfd9" 2>/dev/null
    fi
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
