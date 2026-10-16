#!/bin/sh
# Install the Midori herdr config.
# This repo is the single source of truth; ~/.config/herdr/config.toml is an
# install target. Idempotent — re-run after edits.
#
# herdr has no theme *files*, so unlike Ghostty/Antinote there is nothing here
# but one config.toml. See README.md in this directory for why (short version:
# the theme list is fixed, so Midori rides on the built-in "terminal" theme plus
# per-appearance overrides — and those overrides only exist from herdr 0.9.0).
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_DIR="$HOME/.config/herdr"
DEST="$DEST_DIR/config.toml"
SRC="$REPO_DIR/config.toml"

if ! command -v herdr >/dev/null 2>&1; then
  echo "herdr not installed — skipping. (brew install herdr)"
  exit 0
fi

# The config needs 0.9.0: [theme.custom.light] / [theme.custom.dark] and the
# surface keys are new there. 0.8.x ignores them as unknown keys, and the
# "terminal" base then renders its ANSI 8 slab (README.md, "0.8.x"). Warn rather
# than refuse — this is still the right file to have in place for the upgrade.
herdr_version=$(herdr --version 2>/dev/null | awk '{print $2}')
case "$herdr_version" in
  0.[0-8].*)
    echo "!! herdr $herdr_version is older than 0.9.0; this config needs 0.9.0."
    echo "   brew upgrade herdr — then see herdr/README.md, \"Upgrading from 0.8.x\"."
    ;;
esac

# ── herdr's config is not ours alone ────────────────────────────────────────
# WHY THESE FUNCTIONS EXIST. Every other surface switched here is a file only
# this repo writes, so "which language is live" is a `cmp` and switching is a
# `cp`. herdr is not one of those: herdr writes into config.toml itself.
# Dismissing the onboarding overlay leaves `onboarding = false` PREPENDED at
# line 1, and neither language file contains it — so a live herdr config is
# always a language file PLUS keys this repo did not write.
#
# That broke this in both directions, and both symptoms read as someone else's
# problem rather than as a bug here:
#
#   * `cmp -s` could never match, so the report said `herdr  ?` forever and
#     install-herdr.sh announced "matches neither language" and wrote a
#     config.repo-version.toml nobody needed. A report that is permanently
#     wrong is worse than no report: it teaches you to ignore the one time it
#     is right.
#   * the switch was `cp -f config.<lang>.toml config.toml`, which DELETED
#     that line — a line this repo did not write, out of a live user config.
#     Same rule as the zen-mode.css snippet in CLAUDE.md: never remove what
#     the installer did not put there.
#
# WHAT THE DROPPED LINE COSTS, measured rather than assumed — herdr 0.9.4, an
# isolated XDG_CONFIG_HOME per herdr/README.md "Verifying", same config in both
# arms, only the key differing. Key absent: herdr draws the onboarding overlay
# over the workspace ("this is a mouse-first terminal … ↵ continue", 2 matching
# lines in the capture). `onboarding = false` present: no overlay, 0 matching
# lines. So dropping it costs that panel on the next herdr start.
#
# AND HERDR DOES NOT PUT IT BACK BY ITSELF. The config came back byte-identical
# (md5) after a full server start in every probe, including one where the key
# was absent and one where it was `true`. So once dropped it stays dropped
# until the overlay is dismissed again. A first reading of those probes said
# the key was inert and there was nothing to preserve — wrong, and wrong for a
# dull reason worth recording: the capture was truncated above the line the
# overlay starts on, so arm and control looked identical.
#
# THE REGION IS "ABOVE THE FIRST TABLE HEADER", because that is the only place
# TOML allows a top-level key. A key APPENDED to this file is filed under the
# LAST section instead, which herdr/README.md records as having cost a
# debugging round (`unknown config key ui.toast.pane_scrollbars` — a message
# naming the wrong owner). So carried keys are prepended, never appended.
#
# tools/midori-theme and herdr/install-herdr.sh carry these functions
# separately. That duplication is deliberate, for the reason CLAUDE.md gives
# about the per-target installers: midori-theme must work on a machine with no
# checkout, so it cannot source anything out of the repo.

# Top-level `key = value` lines of $1 whose key is NOT a top-level key of $2 —
# that is, the keys herdr wrote, as distinct from any this repo ships. Keyed on
# the NAME, not the line, so a language file that later declares one of these
# keys itself takes ownership of it and stops it being carried.
herdr_foreign() {
  awk -v lang="$2" '
    BEGIN { while ((getline l < lang) > 0) {
              if (l ~ /^\[/) break
              if (l ~ /^[A-Za-z_][A-Za-z0-9_]*[ \t]*=/) {
                split(l, a, /[ \t]*=/); own[a[1]] = 1 } }
            close(lang) }
    /^\[/ { exit }
    /^[A-Za-z_][A-Za-z0-9_]*[ \t]*=/ {
      split($0, a, /[ \t]*=/); if (!(a[1] in own)) print }
  ' "$1"
}

# Just their names, for a one-line report.
herdr_foreign_keys() {
  herdr_foreign "$1" "$2" | sed 's/[[:space:]]*=.*//' | tr '\n' ' '
}

# Is the live config $1 the language file $2, ignoring what herdr wrote? This
# replaces `cmp -s live lang`, which can only answer no.
herdr_is() {
  [ -f "$1" ] || return 1
  awk -v lang="$2" '
    BEGIN { while ((getline l < lang) > 0) {
              if (l ~ /^\[/) break
              if (l ~ /^[A-Za-z_][A-Za-z0-9_]*[ \t]*=/) {
                split(l, a, /[ \t]*=/); own[a[1]] = 1 } }
            close(lang) }
    body { print; next }
    /^\[/ { body = 1; print; next }
    /^[A-Za-z_][A-Za-z0-9_]*[ \t]*=/ {
      split($0, a, /[ \t]*=/); if (a[1] in own) print; next }
    { print }
  ' "$1" | cmp -s - "$2"
}

mkdir -p "$DEST_DIR"

# BOTH languages go next to the live config, never over it, as config.<lang>.toml
# — the names midori-theme copies from. herdr reads one config.toml and has no
# include mechanism, so switching really is replacing that file plus
# `herdr server reload-config`; midori-theme does both.
#
# config.midori.toml USED TO MEAN A CONFLICT, written only when the live config
# differed from the repo's. It now always exists and means "the Midori config".
# The conflict case below writes config.repo-version.toml instead, so the two
# meanings cannot be confused — a file whose presence is the signal is a bad
# signal once something else starts writing it.
HD_CONFIGS=0
for lang in midori lemonardo; do
  case "$lang" in
    midori) hsrc="$REPO_DIR/config.toml" ;;
    *)      hsrc="$REPO_DIR/config.$lang.toml" ;;
  esac
  [ -f "$hsrc" ] || { echo "!! $hsrc is missing"; exit 1; }
  cp -f "$hsrc" "$DEST_DIR/config.$lang.toml"
  HD_CONFIGS=$((HD_CONFIGS + 1))
done
echo "Wrote $HD_CONFIGS herdr switch source(s): config.midori.toml, config.lemonardo.toml"

# Same policy as the Ghostty config in install.sh: never clobber a config the
# user has edited. herdr's config carries keybindings and per-host settings
# that are none of this repo's business.
if [ ! -f "$DEST" ]; then
  cp -f "$SRC" "$DEST"
  echo "Installed ${DEST#"$HOME"/}"
elif herdr_is "$DEST" "$SRC"; then
  # herdr_is, not `cmp -s`: the live config is this file plus whatever herdr
  # wrote into it, so cmp answered "different" every time and sent every run
  # down the conflict branch below.
  hk=$(herdr_foreign_keys "$DEST" "$SRC")
  if [ -n "$hk" ]; then
    echo "${DEST#"$HOME"/} already up to date (plus herdr's own: ${hk% })"
  else
    echo "${DEST#"$HOME"/} already up to date"
  fi
else
  # Is it simply the OTHER language, i.e. a switch is pending rather than a
  # conflict? Say which; the old message read as a conflict either way.
  hother=""
  for l in midori lemonardo; do
    if herdr_is "$DEST" "$DEST_DIR/config.$l.toml"; then hother="$l"; fi
  done
  if [ -n "$hother" ]; then
    echo "Live herdr config is $hother — run midori-theme to switch it."
  else
    cp -f "$SRC" "$DEST_DIR/config.repo-version.toml"
    echo "!! Existing herdr config matches neither language — wrote"
    echo "   config.repo-version.toml next to it. Merge the [theme] /"
    echo "   [theme.custom*] blocks by hand: $DEST_DIR"
  fi
fi

# Validate whatever ended up at the destination, then hot-reload a running
# server so the change lands without detaching.
if herdr config check 2>&1 | grep -q '^config: ok'; then
  echo "config check: ok"
else
  echo "!! herdr config check reported issues:"
  herdr config check 2>&1 | sed 's/^/   /'
fi

# A failed reload does not mean no server is running: a 0.9.0 herdr cannot
# reach a server still running 0.8.x (different endpoint generation), and that
# is exactly the state right after `brew upgrade herdr`.
if herdr server reload-config >/dev/null 2>&1; then
  echo "Reloaded the running herdr server."
else
  echo "Could not reload a running herdr server (none running, or one older than"
  echo "this herdr) — the config applies the next time the server starts."
fi
