#!/bin/sh
# Pull the LIVE theme files from this machine back into the repo, so theme
# evolution here can be committed and pulled on other machines.
# Reverse of install.sh: real $HOME paths become __HOME__ placeholders.
#
# Note: run ./install.sh once on this machine first, so the live files are
# the repo-rendered (portable) versions — otherwise machine-local hardcoded
# paths sneak back into the repo.
set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
GHOSTTY_CFG="$HOME/Library/Application Support/com.mitchellh.ghostty/config"

unrender() {  # real home -> __HOME__
  sed "s|$HOME|__HOME__|g" "$1" > "$2"
}

echo "-- ghostty"
for t in midori-paper midori-night; do
  unrender "$HOME/.config/ghostty/themes/$t" "$REPO/ghostty/themes/$t"
done
unrender "$GHOSTTY_CFG" "$REPO/ghostty/config"
cp -f "$HOME/.config/ghostty/backgrounds/"midori-*@*.png "$REPO/ghostty/backgrounds/"
cp -f "$HOME/.config/ghostty/shaders/rounded-cursor.glsl" "$REPO/ghostty/shaders/"

echo "-- watcher"
cp -f "$HOME/.local/bin/midori-claude-theme.sh" "$REPO/watcher/midori-claude-theme.sh"

echo "-- prompt / shell / tmux fragments"
cp -f "$HOME/.config/midori.omp.json" "$REPO/prompt/midori.omp.json"
[ -f "$HOME/.config/midori/zshrc.midori" ] && cp -f "$HOME/.config/midori/zshrc.midori" "$REPO/shell/zshrc.midori"
[ -f "$HOME/.config/midori/midori.tmux.conf" ] && cp -f "$HOME/.config/midori/midori.tmux.conf" "$REPO/tmux/midori.tmux.conf"

echo "-- vivaldi (themes from live Preferences + css mods)"
REPO="$REPO" python3 - <<'EOF'
import json, os
prefs = json.load(open(os.path.expanduser(
    "~/Library/Application Support/Vivaldi/Default/Preferences")))
themes = [t for t in prefs["vivaldi"]["themes"]["user"]
          if t.get("name", "").startswith("Midori")]
out_path = os.path.join(os.environ["REPO"], "vivaldi", "themes.json")
existing = json.load(open(out_path))
existing["themes"] = themes
json.dump(existing, open(out_path, "w"), indent=2)
print(f"   exported: {[t['name'] for t in themes]}")
EOF
CSS_LIVE="$HOME/Library/Application Support/Vivaldi/CSSMods"
if [ -d "$CSS_LIVE" ] && \
   [ "$(cd "$CSS_LIVE" && pwd -P)" = "$(cd "$REPO/vivaldi/css-mods" && pwd -P)" ]; then
  echo "   css mods: live dir is the repo (symlink) — already in sync"
else
  # *.css, not midori-*.css: illuminated-overrides.css and any future non-midori
  # mods must round-trip too (this glob is why illuminated-overrides drifted).
  cp -f "$CSS_LIVE/"*.css "$REPO/vivaldi/css-mods/" 2>/dev/null || true
fi

echo "-- obsidian (theme.css from the first vault that has it)"
OBS_VAULTS="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"
obs_found=0
for vault in "$OBS_VAULTS"/*/; do
  live="$vault.obsidian/themes/Midori/theme.css"
  [ -f "$live" ] || continue
  cp -f "$live" "$REPO/obsidian/theme.css"
  echo "   from: $(basename "$vault")"
  obs_found=1
  break
done
[ "$obs_found" -eq 0 ] && echo "   no vault has the Midori theme installed — skipped"

echo "-- done. Review with: git -C \"$REPO\" diff"
