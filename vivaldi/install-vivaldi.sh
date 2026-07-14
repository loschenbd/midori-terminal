#!/bin/sh
# Install the Midori Paper / Midori Night Vivaldi themes + typography CSS mods.
# Run separately from the main installer because VIVALDI MUST BE CLOSED —
# it rewrites Preferences and Local State on exit, clobbering live edits.
#
# What it does:
#  1. Appends both themes to vivaldi.themes.user (skips ones already present)
#  2. Points the OS light/dark schedule at them (auto-switch with macOS)
#  3. Installs the midori-*.css UI mods (fonts, sheet, weather icons) and
#     enables the vivaldi-css-mods labs experiment that loads them
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE="$HOME/Library/Application Support/Vivaldi/Default"
LOCAL_STATE="$HOME/Library/Application Support/Vivaldi/Local State"
CSS_DIR="$HOME/Library/Application Support/Vivaldi/CSSMods"

if [ ! -f "$PROFILE/Preferences" ]; then
  echo "Vivaldi profile not found ($PROFILE). Launch Vivaldi once first." >&2
  exit 1
fi

if pgrep -xq Vivaldi; then
  echo "Vivaldi is running. Quit it first (it clobbers Preferences on exit):" >&2
  echo "  osascript -e 'tell application \"Vivaldi\" to quit'" >&2
  exit 1
fi

cp "$PROFILE/Preferences" "$PROFILE/Preferences.bak.midori"
cp "$LOCAL_STATE" "$LOCAL_STATE.bak.midori"
echo "Backed up Preferences and Local State (*.bak.midori)"

mkdir -p "$CSS_DIR"
cp "$REPO_DIR/css-mods/"midori-*.css "$CSS_DIR/"
echo "Installed CSS mods to $CSS_DIR"

REPO_DIR="$REPO_DIR" PROFILE="$PROFILE" LOCAL_STATE="$LOCAL_STATE" CSS_DIR="$CSS_DIR" \
python3 - <<'EOF'
import json, os

repo = os.environ["REPO_DIR"]
pkg = json.load(open(os.path.join(repo, "themes.json")))

# --- Preferences: themes + OS schedule + css mods dir ---
pref_path = os.path.join(os.environ["PROFILE"], "Preferences")
prefs = json.load(open(pref_path))
v = prefs.setdefault("vivaldi", {})
themes = v.setdefault("themes", {})
user = themes.setdefault("user", [])
have = {t.get("id") for t in user}
added = []
for t in pkg["themes"]:
    if t["id"] not in have:
        user.append(t)
        added.append(t["name"])
v.setdefault("theme", {}).setdefault("schedule", {})["o_s"] = pkg["scheduleOS"]
v.setdefault("appearance", {})["css_ui_mods_directory"] = os.environ["CSS_DIR"]
json.dump(prefs, open(pref_path, "w"))

# --- Local State: enable the css-mods experiment ---
ls_path = os.environ["LOCAL_STATE"]
ls = json.load(open(ls_path))
exps = ls.setdefault("browser", {}).setdefault("enabled_labs_experiments", [])
if "vivaldi-css-mods" not in exps:
    exps.append("vivaldi-css-mods")
json.dump(ls, open(ls_path, "w"))

print(f"Themes added: {added or 'already present'}")
print("OS light/dark schedule -> Midori Paper / Midori Night")
EOF

echo "Done. Launch Vivaldi — theme follows macOS appearance automatically."
