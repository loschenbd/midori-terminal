#!/bin/sh
# Install the Midori Paper / Midori Night Vivaldi themes + typography CSS mods
# + canonical keyboard shortcuts, into one or more Vivaldi profiles.
#
# Run separately from the main installer because VIVALDI MUST BE CLOSED — it
# rewrites Preferences and Local State on exit, clobbering live edits.
#
# Usage:
#   ./install-vivaldi.sh                         # interactive: pick profile(s)
#   ./install-vivaldi.sh --profile all           # every profile
#   ./install-vivaldi.sh --profile "Artisan Studios"   # by display name
#   ./install-vivaldi.sh --profile Default             # by profile dir name
#   MIDORI_VIVALDI_PROFILE=all ./install-vivaldi.sh    # same, via env
#
# What it does, per selected profile:
#   1. Appends both themes to vivaldi.themes.user (skips ones already present)
#   2. Points the OS light/dark schedule at them (auto-switch with macOS)
#   3. Sets css_ui_mods_directory to the shared CSSMods dir
#   4. Applies keyboard.json -> vivaldi.actions + vivaldi.keyboard (if present)
# Globally (once): installs the midori-*.css UI mods and enables the
# vivaldi-css-mods labs experiment that loads them.
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VIVALDI_DIR="$HOME/Library/Application Support/Vivaldi"
LOCAL_STATE="$VIVALDI_DIR/Local State"
CSS_DIR="$VIVALDI_DIR/CSSMods"

PROFILE_SEL="${MIDORI_VIVALDI_PROFILE:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE_SEL="${2:-}"; shift 2 ;;
    --profile=*) PROFILE_SEL="${1#*=}"; shift ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [ ! -d "$VIVALDI_DIR" ]; then
  echo "Vivaldi not found ($VIVALDI_DIR). Launch Vivaldi once first." >&2
  exit 1
fi

if pgrep -xq Vivaldi; then
  echo "Vivaldi is running. Quit it first (it clobbers Preferences on exit):" >&2
  echo "  osascript -e 'tell application \"Vivaldi\" to quit'" >&2
  exit 1
fi

mkdir -p "$CSS_DIR"
cp "$REPO_DIR/css-mods/"midori-*.css "$CSS_DIR/"
echo "Installed CSS mods to $CSS_DIR"

REPO_DIR="$REPO_DIR" VIVALDI_DIR="$VIVALDI_DIR" LOCAL_STATE="$LOCAL_STATE" \
CSS_DIR="$CSS_DIR" PROFILE_SEL="$PROFILE_SEL" python3 - <<'EOF'
import json, os, sys, time, shutil, collections

repo = os.environ["REPO_DIR"]
vdir = os.environ["VIVALDI_DIR"]
css_dir = os.environ["CSS_DIR"]
ls_path = os.environ["LOCAL_STATE"]
sel = os.environ.get("PROFILE_SEL", "").strip()

pkg = json.load(open(os.path.join(repo, "themes.json")))
kb_path = os.path.join(repo, "keyboard.json")
kb = json.load(open(kb_path)) if os.path.exists(kb_path) else None

# --- enumerate profiles: dir -> display name (from Local State info_cache) ---
try:
    info = json.load(open(ls_path)).get("profile", {}).get("info_cache", {})
except (FileNotFoundError, json.JSONDecodeError):
    info = {}
profiles = collections.OrderedDict()
for d in sorted(os.listdir(vdir)):
    if (d == "Default" or d.startswith("Profile ")) and \
       os.path.exists(os.path.join(vdir, d, "Preferences")):
        profiles[d] = info.get(d, {}).get("name", d)
if not profiles:
    sys.exit("No Vivaldi profiles found.")

def resolve(token):
    token = token.strip()
    if token.lower() == "all":
        return list(profiles)
    if token in profiles:                       # exact dir name
        return [token]
    return [d for d, n in profiles.items()      # display name (case-insensitive)
            if n.lower() == token.lower()]

if sel:
    targets = resolve(sel)
    if not targets:
        print(f"No profile matches {sel!r}. Available:", file=sys.stderr)
        for d, n in profiles.items():
            print(f"  {n}  ({d})", file=sys.stderr)
        sys.exit(1)
else:
    # Interactive menu — only when a controlling tty is reachable. (stdin here is
    # the heredoc, so we must read the choice from /dev/tty explicitly.)
    try:
        tty = open("/dev/tty")
    except OSError:
        tty = None
    if tty is None:
        targets = ["Default"] if "Default" in profiles else [next(iter(profiles))]
        print(f"Non-interactive — defaulting to profile: {targets[0]}")
    else:
        items = list(profiles.items())
        print("\nVivaldi profiles found:")
        for i, (d, n) in enumerate(items, 1):
            print(f"  {i}) {n}   ({d})")
        print("  a) all")
        sys.stdout.write(f"Apply Midori setup to which? [1..{len(items)}/a]: ")
        sys.stdout.flush()
        choice = tty.readline().strip().lower()
        if choice == "a":
            targets = list(profiles)
        elif choice.isdigit() and 1 <= int(choice) <= len(items):
            targets = [items[int(choice) - 1][0]]
        else:
            sys.exit("Nothing selected — aborting.")

# --- apply per selected profile ---
stamp = time.strftime("%Y%m%d-%H%M%S")
for d in targets:
    pref_path = os.path.join(vdir, d, "Preferences")
    shutil.copy(pref_path, f"{pref_path}.bak.midori.{stamp}")
    prefs = json.load(open(pref_path))
    v = prefs.setdefault("vivaldi", {})
    themes = v.setdefault("themes", {})
    user = themes.setdefault("user", [])
    have = {t.get("id") for t in user}
    added = [t["name"] for t in pkg["themes"] if t["id"] not in have]
    user.extend(t for t in pkg["themes"] if t["id"] not in have)
    themes["current"] = pkg["scheduleOS"]["light"]
    v.setdefault("theme", {}).setdefault("schedule", {})["o_s"] = pkg["scheduleOS"]
    v.setdefault("appearance", {})["css_ui_mods_directory"] = css_dir
    kb_note = ""
    if kb:
        v["actions"] = kb["actions"]
        v["keyboard"] = kb["keyboard"]
        table = kb["actions"][0]
        bound = sum(1 for a in table.values() if a.get("shortcuts"))
        kb_note = f", hotkeys {bound}/{len(table)}"
    json.dump(prefs, open(pref_path, "w"))
    print(f"[{profiles[d]}] themes: {added or 'already present'}; "
          f"schedule + css mods set{kb_note}")

# --- Local State: enable the css-mods experiment (global, once) ---
ls = json.load(open(ls_path))
exps = ls.setdefault("browser", {}).setdefault("enabled_labs_experiments", [])
if "vivaldi-css-mods" not in exps:
    exps.append("vivaldi-css-mods")
    print("Enabled vivaldi-css-mods experiment (global)")
json.dump(ls, open(ls_path, "w"))
EOF

echo "Done. Relaunch Vivaldi — themes follow macOS appearance automatically."
