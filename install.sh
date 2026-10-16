#!/bin/sh
# Midori terminal theme system — installer.
# Idempotent: safe to re-run after `git pull` to pick up updates.
# macOS only (launchd, defaults, Ghostty app support paths).
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
GHOSTTY_CFG_DIR="$HOME/Library/Application Support/com.mitchellh.ghostty"
LABEL="com.benjaminloschen.midori-claude-theme"

# MIDORI_LANG picks the design language for every target that has a twin, the
# same variable and the same default the watcher and shell/zshrc.midori use. It
# is read ONCE here so a half-switched install is impossible: one value drives
# the plist's environment, the prompt and the Claude Code theme together.
# The language file is the single answer to "which design language am I in".
# Defaulting to the literal `midori` here instead would have made every
# install.sh run a silent switch BACK for anyone who had moved: the installer
# re-renders the live Ghostty config, the plist and the tmux symlink, so a
# default that ignored the current choice would undo it on the next run and
# look like the switch had not stuck.
if [ -z "${MIDORI_LANG:-}" ] && [ -f "$HOME/.config/midori/language" ]; then
  MIDORI_LANG=$(cat "$HOME/.config/midori/language")
fi
: "${MIDORI_LANG:=midori}"
case "$MIDORI_LANG" in
  midori|lemonardo) ;;
  *) echo "!! MIDORI_LANG=$MIDORI_LANG is not a design language in this repo"
     echo "   known: midori, lemonardo"; exit 1 ;;
esac

render() {  # __HOME__ -> real home, __LANG__ -> the design language
  sed -e "s|__HOME__|$HOME|g" -e "s|__LANG__|$MIDORI_LANG|g" "$1" > "$2"
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
# Counted, like the themes and shaders below, and for the same reason: a bare
# cp of a glob that matches nothing succeeds silently on some shells and the
# install reads as fine. Both design languages' faces live here -- Midori's
# M PLUS/Spectral and Lemonardo's Besley/Instrument Sans/Special Elite/Reenie
# Beanie -- and tests/test_fonts_are_vendored.py fails if a theme names a
# family this directory does not carry.
FONTS=0
for f in "$REPO/fonts/"*.ttf; do
  [ -f "$f" ] || continue
  cp -f "$f" "$HOME/Library/Fonts/"
  FONTS=$((FONTS + 1))
done
if [ "$FONTS" -eq 0 ]; then
  echo "   !! no .ttf found in $REPO/fonts — nothing installed"
  exit 1
fi
echo "   $FONTS font file(s) installed"

# --- 3. Ghostty -------------------------------------------------------------
echo "-- ghostty themes, backgrounds, shader"
mkdir -p "$HOME/.config/ghostty/themes" "$HOME/.config/ghostty/backgrounds" \
         "$HOME/.config/ghostty/shaders"
# Every theme in ghostty/themes/, not a hand-maintained list. That list read
# "midori-paper midori-night" after the Lemonardo pair landed, so the two
# Lemonardo themes shipped in the repo and were never installed: `theme =
# light:lemonardo-paintpot` in a config resolved to nothing. A missing theme at
# least reports itself — `ghostty +validate-config` exits 1 and prints every
# path it tried — which a missing FONT does not (see ghostty/config.lemonardo:
# it exits 0 and renders JetBrains Mono). Globbing means adding a theme file is
# the whole job.
GH_THEMES=0
for t in "$REPO/ghostty/themes/"*; do
  [ -f "$t" ] || continue
  render "$t" "$HOME/.config/ghostty/themes/$(basename "$t")"
  GH_THEMES=$((GH_THEMES + 1))
done
# A loop over an unexpanded glob installs nothing and says nothing, which in
# this repo is the documented failure mode rather than a pass.
if [ "$GH_THEMES" -eq 0 ]; then
  echo "   !! no theme files found in $REPO/ghostty/themes — nothing installed"
  exit 1
fi
echo "   $GH_THEMES ghostty theme(s) installed"
cp -f "$REPO/ghostty/backgrounds/"*.png "$HOME/.config/ghostty/backgrounds/"
# Every shader in ghostty/shaders/, for the same reason the themes above are
# globbed: this line named rounded-cursor.glsl alone, so when the Lemonardo
# shader landed, config.lemonardo pointed at a path the installer never wrote.
# Ghostty does NOT report a missing custom-shader the way it reports a missing
# theme — it renders without it, so the symptom is a square cursor and no
# lattice, with nothing on stderr and +validate-config still exiting 0.
GH_SHADERS=0
for s in "$REPO/ghostty/shaders/"*.glsl; do
  [ -f "$s" ] || continue
  cp -f "$s" "$HOME/.config/ghostty/shaders/"
  GH_SHADERS=$((GH_SHADERS + 1))
done
if [ "$GH_SHADERS" -eq 0 ]; then
  echo "   !! no .glsl found in $REPO/ghostty/shaders — nothing installed"
  exit 1
fi
echo "   $GH_SHADERS ghostty shader(s) installed"

# Default symlinks -> @2x (retina) — but only when missing: the watcher owns
# them afterwards and may have flipped to @1x for the current display.
for m in paper night; do
  for k in glow dots; do
    [ -e "$HOME/.config/ghostty/backgrounds/midori-$m-$k.png" ] || \
      ln -sf "midori-$m-$k@2x.png" "$HOME/.config/ghostty/backgrounds/midori-$m-$k.png"
  done
done

mkdir -p "$GHOSTTY_CFG_DIR"

# BOTH languages are rendered, every run, as config.<language>. These are the
# switch SOURCES that midori-theme copies from; the live `config` is only ever
# a copy of one of them.
#
# config.midori USED TO MEAN SOMETHING ELSE, and the rename matters. It was
# written only when the live config differed from the repo's, as a "merge this
# by hand" artifact, so its presence meant a conflict. It now always exists and
# means "the Midori config". A live config that differs from both languages is
# reported below and left alone; midori-theme is what backs it up, and only at
# the moment it would overwrite it.
GH_CONFIGS=0
for lang in midori lemonardo; do
  case "$lang" in
    midori) src="$REPO/ghostty/config" ;;
    *)      src="$REPO/ghostty/config.$lang" ;;
  esac
  [ -f "$src" ] || { echo "!! $src is missing"; exit 1; }
  render "$src" "$GHOSTTY_CFG_DIR/config.$lang"
  GH_CONFIGS=$((GH_CONFIGS + 1))
done
echo "   rendered $GH_CONFIGS switch source(s): config.midori, config.lemonardo"

CHOSEN="$GHOSTTY_CFG_DIR/config.$MIDORI_LANG"
if [ ! -f "$GHOSTTY_CFG_DIR/config" ]; then
  cp -f "$CHOSEN" "$GHOSTTY_CFG_DIR/config"
  echo "   installed Ghostty config ($MIDORI_LANG)"
elif cmp -s "$CHOSEN" "$GHOSTTY_CFG_DIR/config"; then
  echo "   Ghostty config already up to date ($MIDORI_LANG)"
else
  # Is it simply the OTHER language, i.e. a switch is pending? Say which,
  # rather than the old message, which read as a conflict either way.
  other=""
  for l in midori lemonardo; do
    cmp -s "$GHOSTTY_CFG_DIR/config" "$GHOSTTY_CFG_DIR/config.$l" && other="$l"
  done
  if [ -n "$other" ]; then
    echo "   live Ghostty config is $other; language is $MIDORI_LANG."
    echo "   Run: midori-theme $MIDORI_LANG"
  else
    echo "   !! Live Ghostty config matches neither language — left alone."
    echo "      Your own settings belong in $GHOSTTY_CFG_DIR/user-overrides,"
    echo "      which both language configs include; see the end of either."
  fi
fi

# --- 4. Prompt (oh-my-posh) --------------------------------------------------
echo "-- prompt -> ~/.config/midori.omp.json"
mkdir -p "$HOME/.config"
cp -f "$REPO/prompt/midori.omp.json" "$HOME/.config/midori.omp.json"
# The Lemonardo twin goes next to it, never over it — same policy as
# ghostty/config.lemonardo. shell/zshrc.midori points oh-my-posh at the midori
# path, so switching is one --config edit there.
cp -f "$REPO/prompt/lemonardo.omp.json" "$HOME/.config/lemonardo.omp.json"
echo "   wrote lemonardo.omp.json next to it (swap the --config path to switch)"

# --- 5. Shell + tmux fragments ----------------------------------------------
echo "-- shell/tmux fragments -> ~/.config/midori"
mkdir -p "$HOME/.config/midori"
cp -f "$REPO/shell/zshrc.midori" "$HOME/.config/midori/zshrc.midori"
cp -f "$REPO/tmux/midori.tmux.conf" "$HOME/.config/midori/midori.tmux.conf"
# There is NO zshrc.lemonardo and that is deliberate, not an omission: that
# fragment holds no colour values at all. Its fzf theme is `--color=16` with
# slot INDICES (hl:4, prompt:2, info:8), which the terminal resolves against
# whichever theme pair is live, so the one file is already correct for both
# design languages. Adding a twin would create a second copy of shell logic
# that has to be kept in step for no benefit.
cp -f "$REPO/tmux/lemonardo.tmux.conf" "$HOME/.config/midori/lemonardo.tmux.conf"

# active.tmux.conf is a SYMLINK, and tmux sources that name rather than a
# language's. ~/.tmux.conf is the user's own file; rewriting a line in it on
# every switch is how a switch ends up half-applied when one of the four edits
# is forgotten. One indirection means the switch is a symlink flip.
ln -sfn "$HOME/.config/midori/$MIDORI_LANG.tmux.conf" \
        "$HOME/.config/midori/active.tmux.conf"
echo "   active.tmux.conf -> $MIDORI_LANG.tmux.conf"

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
#
# MIGRATION, and it has to happen here rather than in midori-theme: a config
# written before active.tmux.conf existed names a LANGUAGE fragment
# (midori.tmux.conf or lemonardo.tmux.conf) directly, and such a line pins the
# panes to one language however many times the symlink is flipped. That is a
# half-switched terminal with no error anywhere. Repoint it once, in place.
if grep -q "config/midori/active.tmux.conf" "$HOME/.tmux.conf"; then
  echo "   .tmux.conf already sources active.tmux.conf — not appending"
elif grep -qE "config/midori/(midori|lemonardo)\.tmux\.conf" "$HOME/.tmux.conf"; then
  # Same shape as the repair in tools/midori-theme, and the same hazard: a
  # redirect into the file sed reads from truncates it first, so a failed
  # backup leaves an EMPTY ~/.tmux.conf. Write, then move.
  # sed exiting 0 does not mean it wrote anything: BSD sed given a DIRECTORY
  # emits nothing and exits 0 (measured, Darwin 25.6). Check the shape of the
  # output, not just the status. Same reasoning as tools/midori-theme.
  tmux_lines=$(wc -l < "$HOME/.tmux.conf")
  if ! cp -f "$HOME/.tmux.conf" "$HOME/.tmux.conf.pre-midori-active"; then
    echo "   !! could not back up .tmux.conf — left it alone"
  elif sed -E 's|config/midori/(midori\|lemonardo)\.tmux\.conf|config/midori/active.tmux.conf|g' \
         "$HOME/.tmux.conf.pre-midori-active" > "$HOME/.tmux.conf.midori-new" &&
       [ -s "$HOME/.tmux.conf.midori-new" ] &&
       [ "$(wc -l < "$HOME/.tmux.conf.midori-new" 2>/dev/null || echo -1)" \
         -eq "$tmux_lines" ]; then
    mv -f "$HOME/.tmux.conf.midori-new" "$HOME/.tmux.conf"
    echo "   repointed .tmux.conf at active.tmux.conf (kept .tmux.conf.pre-midori-active)"
  else
    rm -f "$HOME/.tmux.conf.midori-new"
    echo "   !! rewriting .tmux.conf failed — left it alone"
  fi
else
  printf '\n# Midori terminal theme (midori-terminal repo)\nsource-file ~/.config/midori/active.tmux.conf\n' >> "$HOME/.tmux.conf"
  echo "   appended source-file line to .tmux.conf"
fi

# The language file: the one answer to "which design language am I in".
# midori-theme writes it too; this seeds it so a fresh install has one.
printf '%s\n' "$MIDORI_LANG" > "$HOME/.config/midori/language"
echo "   language file = $MIDORI_LANG"

# The switch command itself. mkdir here and not only in step 6, which used to
# be the first thing to write into this directory and no longer is.
mkdir -p "$HOME/.local/bin"
cp -f "$REPO/tools/midori-theme" "$HOME/.local/bin/midori-theme"
chmod +x "$HOME/.local/bin/midori-theme"
echo "   installed midori-theme (run it with no argument to see every surface)"

# --- 6. Appearance watcher (launchd) -----------------------------------------
echo "-- appearance watcher (Claude Code theme + tmux borders + display scale)"
mkdir -p "$HOME/.local/bin" "$HOME/Library/LaunchAgents"
cp -f "$REPO/watcher/midori-claude-theme.sh" "$HOME/.local/bin/midori-claude-theme.sh"
chmod +x "$HOME/.local/bin/midori-claude-theme.sh"

# The Claude Code token maps. These used to be heredocs inside the watcher; it
# now copies one of these into ~/.claude/themes/ on every appearance flip, so
# an empty install here is the watcher silently leaving a stale theme in place
# rather than an obvious failure. Count them and refuse an empty glob, the same
# shape as the font and theme copies above.
CLAUDE_THEME_DIR="$HOME/.local/share/midori/claude-themes"
mkdir -p "$CLAUDE_THEME_DIR"
ct_n=0
for f in "$REPO"/watcher/themes/*.json; do
  [ -e "$f" ] || continue
  cp -f "$f" "$CLAUDE_THEME_DIR/"
  ct_n=$((ct_n + 1))
done
if [ "$ct_n" -eq 0 ]; then
  echo "!! no watcher/themes/*.json — the watcher would leave the live Claude"
  echo "   Code theme untouched forever. Aborting rather than half-installing."
  exit 1
fi
echo "   installed $ct_n Claude Code token map(s) (language: $MIDORI_LANG)"
if [ ! -f "$REPO/watcher/themes/$MIDORI_LANG-light.json" ] ||
   [ ! -f "$REPO/watcher/themes/$MIDORI_LANG-dark.json" ]; then
  echo "!! $MIDORI_LANG has no light+dark pair in watcher/themes/"; exit 1
fi
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
