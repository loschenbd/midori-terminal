#!/bin/sh
# Install the "Midori" Obsidian theme (Midori palette, mint dot grid + page
# glow, Spectral/M PLUS fonts) into every iCloud-synced Obsidian vault, plus
# any vault listed in extra-vaults.txt.
# This repo is the single source of truth; the vaults are install targets.
#
# Re-run after edits, then reload Obsidian (or toggle the theme) to pick up
# changes. Idempotent. Use ../sync.sh to pull live edits back into the repo.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VAULTS="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"
EXTRA="$REPO_DIR/extra-vaults.txt"
THEME="Midori"
LEGACY="Dot Grid"   # theme was renamed; clean up the old install

# A VAULT THIS DOES NOT SCAN DOES NOT FAIL — IT DRIFTS, which is worse, because
# nothing announces it. A vault kept outside iCloud (~/Projects/CFA) sat 11
# theme commits and eleven plugin minor versions behind on whatever build had
# last been hand-copied in, still looking like a working install. Worse than
# looking stale: theme rules are deliberately gated on a body class introduced
# by the SAME plugin build that implements them, so a current stylesheet over an
# old main.js silently applies none of them.
#
# extra-vaults.txt is one absolute vault path per line, # for comments, and is
# gitignored: which vaults live on THIS machine is a local fact, not a repo one.
list_vaults() {
  for vault in "$VAULTS"/*/; do
    [ -d "$vault.obsidian" ] && printf '%s\n' "$vault"
  done
  [ -f "$EXTRA" ] || return 0
  # `|| [ -n "$line" ]` so a final line with no trailing newline is not dropped.
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|\#*) continue ;; esac
    vault="${line%/}/"
    if [ -d "$vault.obsidian" ]; then
      printf '%s\n' "$vault"
    else
      echo "Skipping $line: no .obsidian directory" >&2
    fi
  done < "$EXTRA"
}

pgrep -x Obsidian >/dev/null 2>&1 && obsidian_running=1 || obsidian_running=0

vault_list="$(mktemp)"
trap 'rm -f "$vault_list"' EXIT INT TERM
list_vaults > "$vault_list"

installed=0
# Read on fd 3, not stdin: the loop body feeds heredocs to python3, and keeping
# the vault list off stdin means nothing in the body can ever eat an iteration.
# A pipeline would also put the loop in a subshell and lose `installed`.
while IFS= read -r vault <&3; do

  dest="$vault.obsidian/themes/$THEME"
  mkdir -p "$dest"
  cp "$REPO_DIR/theme.css" "$REPO_DIR/manifest.json" "$dest/"

  # Retire the pre-rename copy so it stops showing up in the theme picker.
  [ -d "$vault.obsidian/themes/$LEGACY" ] && rm -rf "$vault.obsidian/themes/$LEGACY"

  # Point the vault at the renamed theme. Obsidian holds appearance.json in
  # memory and rewrites it on any settings change, so an external edit only
  # sticks while the app is closed — hence the note printed at the end.
  appearance="$vault.obsidian/appearance.json"
  if [ -f "$appearance" ]; then
    THEME="$THEME" LEGACY="$LEGACY" python3 - "$appearance" <<'PY'
import json, os, sys
path = sys.argv[1]
try:
    with open(path) as f:
        cfg = json.load(f)
except (OSError, ValueError):
    sys.exit(0)
if cfg.get("cssTheme", "") in (os.environ["LEGACY"], ""):
    cfg["cssTheme"] = os.environ["THEME"]
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
PY
  fi

  # Companion plugin. The theme cannot size the editor caret on its own — the
  # native contenteditable caret takes its height from the font, and the
  # theme's symmetric metric overrides centre it on the baseline. This draws a
  # caret the theme can style. See plugins/midori-caret/main.js.
  for plugin in "$REPO_DIR"/plugins/*/; do
    [ -f "$plugin/manifest.json" ] || continue
    id="$(basename "$plugin")"
    pdest="$vault.obsidian/plugins/$id"
    mkdir -p "$pdest"
    cp "$plugin/manifest.json" "$plugin/main.js" "$pdest/"

    # Obsidian holds community-plugins.json in memory and rewrites it on any
    # plugin change, so this only sticks reliably while the app is closed —
    # same caveat as appearance.json above, hence the note at the end.
    ID="$id" python3 - "$vault.obsidian/community-plugins.json" <<'PY'
import json, os, sys
path, pid = sys.argv[1], os.environ["ID"]
try:
    with open(path) as f:
        enabled = json.load(f)
    if not isinstance(enabled, list):
        raise ValueError
except (OSError, ValueError):
    enabled = []
if pid not in enabled:
    enabled.append(pid)
    with open(path, "w") as f:
        json.dump(enabled, f, indent=2)
PY
  done

  echo "Installed into $(basename "$vault")"
  installed=1
done 3< "$vault_list"

if [ "$installed" -eq 0 ]; then
  echo "No Obsidian vaults found under $VAULTS (or in $(basename "$EXTRA"))" >&2
  exit 1
fi

echo
if [ "$obsidian_running" -eq 1 ]; then
  echo "Obsidian is running: it keeps appearance.json and community-plugins.json"
  echo "in memory, so if the theme does not switch by itself, pick '$THEME' under"
  echo "Settings -> Appearance, and enable 'Midori Caret' under Community plugins."
else
  echo "Done. '$THEME' is selected in every vault."
fi
