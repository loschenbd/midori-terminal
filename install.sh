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
# Homebrew is per MACHINE but this installer runs per ACCOUNT, and a second
# account on the same Mac differs in two ways (checked Sept 2026, Darwin 25.6):
#   * /opt/homebrew/bin is not on its PATH. /etc/paths lists /usr/local/bin but
#     not /opt/homebrew/bin; only a `brew shellenv` line in an account's own
#     profile adds it, and nothing puts one in a second account's. Left alone,
#     every `command -v` in this run misses the shared install: brew reads as
#     "not found" and the herdr step skips itself as not installed.
#   * It cannot write the prefix, which belongs to whoever installed Homebrew,
#     so `brew bundle` there can only fail. The apps are shared, though, so
#     check the Brewfile instead. `--no-upgrade` asks "installed?" rather than
#     "up to date?": plain `check` fails on any outdated formula, and did on the
#     owning account when this was written (tmux, fzf, gh, glow), nothing missing.
if ! command -v brew >/dev/null 2>&1 && [ -x /opt/homebrew/bin/brew ]; then
  PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
  export PATH
  echo "-- Homebrew is at /opt/homebrew but not on this account's PATH — using it for this run"
fi

if [ -n "$MIDORI_SKIP_BREW" ]; then
  echo "-- skipping brew (MIDORI_SKIP_BREW set)"
elif ! command -v brew >/dev/null 2>&1; then
  echo "-- Homebrew not found. Install the Brewfile deps manually."
elif brew_owner=$(stat -f %Su "$(brew --prefix)") && [ "$brew_owner" != "$(id -un)" ]; then
  echo "-- Homebrew belongs to $brew_owner — checking the Brewfile instead of installing"
  if HOMEBREW_NO_AUTO_UPDATE=1 brew bundle check --no-upgrade --file "$REPO/Brewfile" >/dev/null 2>&1; then
    echo "   every Brewfile dep is already installed"
  else
    echo "   !! brew bundle check did not pass from this account: a dep is missing, or"
    echo "      this Homebrew won't run for a non-owner. From $brew_owner's account, run"
    echo "      brew bundle --file <that account's midori-terminal clone>/Brewfile"
  fi
else
  echo "-- brew bundle (Brewfile: ghostty, tmux, fzf, oh-my-posh, eza, zoxide, ...)"
  brew bundle --file "$REPO/Brewfile" || echo "   (brew bundle had failures — continuing)"
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
# Detect the actual source line (not any mention of "midori" — inline references
# elsewhere used to false-match and leave the fragment unsourced, which silently
# disabled the Claude self-heal wrapper).
if grep -q "config/midori/zshrc.midori" "$HOME/.zshrc"; then
  echo "   .zshrc already sources the midori fragment — not appending"
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
  # bootout can return before launchd has finished removing the job, and a
  # bootstrap landing in that window fails. A re-run in Sept 2026 printed
  # "Bootstrap failed: 5: Input/output error" right after the bootout; under
  # set -e that aborted the install with the watcher stopped, so steps 7-10 never
  # ran and the watcher stayed down. The same bootstrap run by hand moments later,
  # with nothing loaded, worked first time. That points at the race, though it
  # was not reproduced in isolation. So: wait for the job to be gone (up to ~5 s),
  # and never let a failed registration take the remaining steps with it.
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  i=0
  while launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 && [ "$i" -lt 50 ]; do
    sleep 0.1
    i=$((i + 1))
  done
  if launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/$LABEL.plist" &&
     launchctl kickstart "gui/$(id -u)/$LABEL"; then
    echo "   watcher running (writes ~/.claude/themes/midori.json within ~3s)"
  else
    echo "   !! watcher registration failed — continuing with the rest. To retry:"
    echo "      launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/$LABEL.plist"
  fi
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

# --- 7b. dumbzone status line: wrap instead of truncate -----------------------
# Only touched if dumbzone is actually the configured status line. It writes one
# long line; Claude Code cuts the status line to the pane and marks it with a
# single ellipsis, so on a phone-width pane (~50 columns in Moshi) everything
# past the cut is gone — including the advice text, which only appears once the
# line is long enough to be truncated. tools/dumbzone-fit.py packs the segments
# onto as many lines as the pane needs. Measurements are in that file's header.
if command -v python3 >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/midori"
  cp -f "$REPO/tools/dumbzone-fit.py" "$HOME/.config/midori/dumbzone-fit.py"
  chmod +x "$HOME/.config/midori/dumbzone-fit.py"
  python3 - <<'EOF'
import json, os, shutil, time
p = os.path.expanduser("~/.claude/settings.json")
fit = os.path.expanduser("~/.config/midori/dumbzone-fit.py")
try:
    s = json.load(open(p))
except (FileNotFoundError, json.JSONDecodeError):
    s = {}
sl = s.get("statusLine") or {}
cmd = (sl.get("command") or "").strip()
if "dumbzone" not in cmd:
    print("-- dumbzone: not the configured status line, leaving it alone")
elif "dumbzone-fit.py" in cmd:
    print("-- dumbzone: status line already wraps to the pane")
else:
    # Keep whatever binary path is already configured — dumbzone need not live
    # under ~/.local/bin, and the wrapper honours DUMBZONE_BIN.
    shutil.copy2(p, p + time.strftime(".bak-%Y%m%d-%H%M%S"))
    sl["command"] = f"DUMBZONE_BIN={cmd} {fit}"
    s["statusLine"] = sl
    json.dump(s, open(p, "w"), indent=2)
    print("-- dumbzone: status line now wraps to the pane (settings.json backed up)")
EOF
fi

# --- 8. Claude Code inline code + tips (binary patch) -------------------------
# Two render paths ignore ~/.claude/themes: inline `codespan` and the `suggestion`
# token (tips / ghost-text). Their helper looks the token up in the stock preset
# for the base mode, dropping custom overrides, so those theme values are decoys
# without this. The patch points both at the terminal's ANSI blue — Midori
# palette 4, the colour those tokens were meant to be. Diff bands need no patch
# from Claude Code 2.1.247: the theme file colours them. Idempotent +
# version-aware; needs python3 (and codesign on macOS). Any Claude Code update
# reverts it (the native updater or a brew upgrade both restore the stock binary)
# — re-run ./install.sh, or the `claude` shell wrapper self-heals on next launch.
# Opt out with MIDORI_SKIP_CC_PATCH; restore stock from the backup under
# ~/.config/midori/claude-backup/ (or brew reinstall on the cask).
if [ -n "$MIDORI_SKIP_CC_PATCH" ]; then
  echo "-- skipping Claude Code patch (MIDORI_SKIP_CC_PATCH set)"
else
  # Install the patch scripts next to each other so the shell `claude` wrapper
  # (zshrc.midori) can self-heal after any Claude Code update, then run once now.
  cp -f "$REPO/tools/apply-claude-midori-patch.sh" "$REPO/tools/patch-claude-binary.py" \
        "$HOME/.config/midori/"
  chmod +x "$HOME/.config/midori/apply-claude-midori-patch.sh"
  sh "$HOME/.config/midori/apply-claude-midori-patch.sh" || echo "   (Claude Code patch skipped/failed — non-fatal)"
fi

# --- 9. Vivaldi themes + hotkeys ---------------------------------------------
# Applies to the Default profile non-interactively (set MIDORI_VIVALDI_PROFILE
# to a name / "all" to widen). Skipped while Vivaldi is running, since it
# rewrites Preferences on exit — run ./vivaldi/install-vivaldi.sh yourself then
# (no args = interactive profile picker).
if [ -n "$MIDORI_SKIP_VIVALDI" ]; then
  echo "-- skipping Vivaldi (MIDORI_SKIP_VIVALDI set)"
elif [ ! -d "$HOME/Library/Application Support/Vivaldi" ]; then
  echo "-- Vivaldi not installed — skipping"
elif pgrep -xq Vivaldi; then
  echo "-- Vivaldi running — skipping. Quit it, then: ./vivaldi/install-vivaldi.sh"
else
  echo "-- vivaldi themes + hotkeys (profile: ${MIDORI_VIVALDI_PROFILE:-Default})"
  sh "$REPO/vivaldi/install-vivaldi.sh" --profile "${MIDORI_VIVALDI_PROFILE:-Default}" \
    || echo "   (vivaldi setup skipped/failed — non-fatal)"
fi

# --- 10. herdr ----------------------------------------------------------------
# Optional multiplexer (agent-aware). Skips itself when herdr isn't installed,
# and never clobbers an existing config — see herdr/README.md.
if [ -n "$MIDORI_SKIP_HERDR" ]; then
  echo "-- skipping herdr (MIDORI_SKIP_HERDR set)"
else
  echo "-- herdr config -> ~/.config/herdr/config.toml"
  sh "$REPO/herdr/install-herdr.sh" 2>&1 | sed 's/^/   /' \
    || echo "   (herdr setup skipped/failed — non-fatal)"
fi

# --- Done ---------------------------------------------------------------------
cat <<'EOF'

== Done ==
Next steps:
  1. Restart Ghostty (or Cmd+Shift+, to reload if already themed once).
  2. Restart Claude Code to pick up the Midori binary patch (inline code, tips).
  3. Vivaldi: applied to the Default profile above (if it was closed). To pick a
     specific profile, quit Vivaldi and run  ./vivaldi/install-vivaldi.sh
  4. New display? See README "Calibrating the dot phase" + tools/bake-backgrounds.py
EOF
