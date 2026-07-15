#!/bin/sh
# Midori terminal theme system — installer.
# Idempotent: safe to re-run after `git pull` to pick up updates.
# macOS only (launchd, defaults, Ghostty app support paths).
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
GHOSTTY_CFG_DIR="$HOME/Library/Application Support/com.mitchellh.ghostty"
LABEL="com.benjaminloschen.midori-claude-theme"

render() {  # __HOME__ -> real home
  sed "s|__HOME__|$HOME|g" "$1" > "$2"
}

echo "== Midori terminal theme system =="

# --- 1. Homebrew deps -------------------------------------------------------
if [ -n "$MIDORI_SKIP_BREW" ]; then
  echo "-- skipping brew (MIDORI_SKIP_BREW set)"
elif command -v brew >/dev/null 2>&1; then
  echo "-- brew bundle (Brewfile: ghostty, tmux, fzf, oh-my-posh, eza, zoxide, ...)"
  brew bundle --file "$REPO/Brewfile" || echo "   (brew bundle had failures — continuing)"
else
  echo "-- Homebrew not found. Install the Brewfile deps manually."
fi

# --- 2. Fonts ---------------------------------------------------------------
echo "-- fonts -> ~/Library/Fonts"
mkdir -p "$HOME/Library/Fonts"
cp -f "$REPO/fonts/"*.ttf "$HOME/Library/Fonts/"

# --- 3. Ghostty -------------------------------------------------------------
echo "-- ghostty themes, backgrounds, shader"
mkdir -p "$HOME/.config/ghostty/themes" "$HOME/.config/ghostty/backgrounds" \
         "$HOME/.config/ghostty/shaders"
for t in midori-paper midori-night; do
  render "$REPO/ghostty/themes/$t" "$HOME/.config/ghostty/themes/$t"
done
cp -f "$REPO/ghostty/backgrounds/"*.png "$HOME/.config/ghostty/backgrounds/"
cp -f "$REPO/ghostty/shaders/rounded-cursor.glsl" "$HOME/.config/ghostty/shaders/"

# Default symlinks -> @2x (retina) — but only when missing: the watcher owns
# them afterwards and may have flipped to @1x for the current display.
for m in paper night; do
  for k in glow dots; do
    [ -e "$HOME/.config/ghostty/backgrounds/midori-$m-$k.png" ] || \
      ln -sf "midori-$m-$k@2x.png" "$HOME/.config/ghostty/backgrounds/midori-$m-$k.png"
  done
done

mkdir -p "$GHOSTTY_CFG_DIR"
render "$REPO/ghostty/config" /tmp/midori-ghostty-config
if [ ! -f "$GHOSTTY_CFG_DIR/config" ]; then
  cp /tmp/midori-ghostty-config "$GHOSTTY_CFG_DIR/config"
  echo "   installed Ghostty config"
elif cmp -s /tmp/midori-ghostty-config "$GHOSTTY_CFG_DIR/config"; then
  echo "   Ghostty config already up to date"
else
  cp /tmp/midori-ghostty-config "$GHOSTTY_CFG_DIR/config.midori"
  echo "   !! Existing Ghostty config differs — wrote config.midori next to it."
  echo "      Merge or replace manually: $GHOSTTY_CFG_DIR"
fi
rm -f /tmp/midori-ghostty-config

# --- 4. Prompt (oh-my-posh) --------------------------------------------------
echo "-- prompt -> ~/.config/midori.omp.json"
mkdir -p "$HOME/.config"
cp -f "$REPO/prompt/midori.omp.json" "$HOME/.config/midori.omp.json"

# --- 5. Shell + tmux fragments ----------------------------------------------
echo "-- shell/tmux fragments -> ~/.config/midori"
mkdir -p "$HOME/.config/midori"
cp -f "$REPO/shell/zshrc.midori" "$HOME/.config/midori/zshrc.midori"
cp -f "$REPO/tmux/midori.tmux.conf" "$HOME/.config/midori/midori.tmux.conf"

touch "$HOME/.zshrc"
if grep -q "midori" "$HOME/.zshrc"; then
  echo "   .zshrc already references midori — not appending"
else
  printf '\n# Midori terminal theme (midori-terminal repo)\n[ -f ~/.config/midori/zshrc.midori ] && source ~/.config/midori/zshrc.midori\n' >> "$HOME/.zshrc"
  echo "   appended source line to .zshrc"
fi

touch "$HOME/.tmux.conf"
# Detect the actual source-file line (not any mention of "midori" — a comment
# elsewhere used to false-match and leave the fragment unsourced).
if grep -q "config/midori/midori.tmux.conf" "$HOME/.tmux.conf"; then
  echo "   .tmux.conf already sources the midori fragment — not appending"
else
  printf '\n# Midori terminal theme (midori-terminal repo)\nsource-file ~/.config/midori/midori.tmux.conf\n' >> "$HOME/.tmux.conf"
  echo "   appended source-file line to .tmux.conf"
fi

# --- 6. Appearance watcher (launchd) -----------------------------------------
echo "-- appearance watcher (Claude Code theme + tmux borders + display scale)"
mkdir -p "$HOME/.local/bin" "$HOME/Library/LaunchAgents"
cp -f "$REPO/watcher/midori-claude-theme.sh" "$HOME/.local/bin/midori-claude-theme.sh"
chmod +x "$HOME/.local/bin/midori-claude-theme.sh"
render "$REPO/watcher/$LABEL.plist.template" "$HOME/Library/LaunchAgents/$LABEL.plist"
if [ -n "$MIDORI_SKIP_LAUNCHD" ]; then
  echo "   skipping launchd registration (MIDORI_SKIP_LAUNCHD set)"
else
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/$LABEL.plist"
  launchctl kickstart "gui/$(id -u)/$LABEL"
  echo "   watcher running (writes ~/.claude/themes/midori.json within ~3s)"
fi

# --- 7. Claude Code theme -----------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  echo "-- Claude Code: theme = custom:midori"
  mkdir -p "$HOME/.claude/themes"
  python3 - <<'EOF'
import json, os
p = os.path.expanduser("~/.claude/settings.json")
try:
    s = json.load(open(p))
except (FileNotFoundError, json.JSONDecodeError):
    s = {}
if s.get("theme") != "custom:midori":
    s["theme"] = "custom:midori"
    json.dump(s, open(p, "w"), indent=2)
    print("   set theme in ~/.claude/settings.json")
else:
    print("   already set")
EOF
fi

# --- 8. Claude Code diff-colour binary patch ---------------------------------
# Claude Code hardcodes diff-band colours in its compiled binary (theme files
# can't reach them), so we patch the binary to render the Midori washes while
# keeping syntax highlighting on. Idempotent + version-aware; needs node/npx.
# `brew upgrade claude-code` reverts it — re-run ./install.sh (or the watcher
# self-heals). Opt out with MIDORI_SKIP_CC_PATCH; restore: brew reinstall claude-code.
if [ -n "$MIDORI_SKIP_CC_PATCH" ]; then
  echo "-- skipping Claude Code diff patch (MIDORI_SKIP_CC_PATCH set)"
else
  # Install the patch scripts next to each other so the shell `claude` wrapper
  # (zshrc.midori) can self-heal after brew upgrades, then run once now.
  cp -f "$REPO/tools/apply-claude-midori-patch.sh" "$REPO/tools/patch-claude-diffs.py" \
        "$HOME/.config/midori/"
  chmod +x "$HOME/.config/midori/apply-claude-midori-patch.sh"
  sh "$HOME/.config/midori/apply-claude-midori-patch.sh" || echo "   (diff patch skipped/failed — non-fatal)"
fi

# --- Done ---------------------------------------------------------------------
cat <<'EOF'

== Done ==
Next steps:
  1. Restart Ghostty (or Cmd+Shift+, to reload if already themed once).
  2. Restart Claude Code to pick up the Midori diff-colour binary patch.
  3. Vivaldi themes: quit Vivaldi, then run  ./vivaldi/install-vivaldi.sh
  4. New display? See README "Calibrating the dot phase" + tools/bake-backgrounds.py
EOF
