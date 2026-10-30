#!/bin/sh
# Install the Midori and Lemonardo Vivaldi themes + typography CSS mods
# + canonical keyboard shortcuts, into one or more Vivaldi profiles.
#
# All four themes are installed into every selected profile, so either design
# language can be picked by hand in Vivaldi's theme panel. MIDORI_LANG decides
# only which PAIR the macOS light/dark schedule points at.
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
#   MIDORI_LANG=lemonardo ./install-vivaldi.sh    # schedule the Lemonardo pair
#
# What it does, per selected profile:
#   1. Appends all four themes to vivaldi.themes.user (skips ones already there)
#   2. Points the OS light/dark schedule at the MIDORI_LANG pair (auto-switch
#      with macOS). Vivaldi is the one surface midori-theme CANNOT switch live:
#      it rewrites Preferences on exit, so a running Vivaldi would clobber the
#      edit. Switching languages here means re-running this script with Vivaldi
#      closed -- which is why midori-theme only REPORTS Vivaldi's state.
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

# Design language: explicit env wins, else the file midori-theme maintains,
# else midori. Same precedence as install.sh, so the two agree.
if [ -z "${MIDORI_LANG:-}" ] && [ -r "$HOME/.config/midori/language" ]; then
  MIDORI_LANG="$(cat "$HOME/.config/midori/language")"
fi
: "${MIDORI_LANG:=midori}"
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

# SCOPED TO THIS UID, AND THAT IS THE WHOLE POINT. This was `pgrep -xq
# Vivaldi`, which matches EVERY user's Vivaldi on the machine. This Mac has a
# second account (fast user switching, both consoles logged in since Oct 7),
# and that account had Vivaldi open for three and a half days. So this guard
# refused every install while the only Vivaldi running belonged to uid 503 and
# could not touch uid 501's profile -- a different $HOME entirely. Three
# attempts were spent quitting a browser that was already closed, and the
# `pkill` that followed failed with "Operation not permitted" because you
# cannot signal another user's process.
#
# The same cross-account mistake this repo already made with /tmp log paths:
# a machine-global name was treated as a per-user one. A process list IS
# machine-global. Only this user's Vivaldi can rewrite this user's Preferences.
#
# Note also that Vivaldi lingers with ZERO windows after the last one closes,
# so "I quit it" and "the process is gone" are different claims -- and the
# message says so, because the silent version of this cost three rounds.
if pgrep -xqu "$(id -u)" Vivaldi; then
  msg="Vivaldi is running under $(id -un) and clobbers Preferences on exit."
  echo "$msg"                                                   # stdout, so a
  echo "$msg" >&2                                               # wrapper that
  echo "  Quit it, then CHECK IT IS GONE -- Vivaldi keeps running with no" >&2
  echo "  windows open, so closing the last window is not quitting:" >&2
  echo "    osascript -e 'tell application \"Vivaldi\" to quit'" >&2
  echo "    pgrep -xu \"\$(id -u)\" Vivaldi    # must print nothing" >&2
  exit 1
fi

mkdir -p "$CSS_DIR"
# If CSS_DIR already resolves to the repo's css-mods (e.g. it's a symlink to it
# for zero-drift maintenance), the mods are already "installed" — copying would
# just copy files onto themselves and error. Otherwise copy every stylesheet
# (not just midori-*.css — illuminated-overrides.css and future files count too).
if [ "$(cd "$CSS_DIR" && pwd -P)" = "$(cd "$REPO_DIR/css-mods" && pwd -P)" ]; then
  echo "CSS_DIR resolves to the repo css-mods dir — already in sync, skipping copy"
else
  cp "$REPO_DIR/css-mods/"*.css "$CSS_DIR/"
  echo "Installed CSS mods to $CSS_DIR"
fi

REPO_DIR="$REPO_DIR" VIVALDI_DIR="$VIVALDI_DIR" LOCAL_STATE="$LOCAL_STATE" \
CSS_DIR="$CSS_DIR" PROFILE_SEL="$PROFILE_SEL" MIDORI_LANG="$MIDORI_LANG" \
python3 - <<'EOF'
import json, os, sys, time, shutil, collections, copy

repo = os.environ["REPO_DIR"]
vdir = os.environ["VIVALDI_DIR"]
css_dir = os.environ["CSS_DIR"]
ls_path = os.environ["LOCAL_STATE"]
sel = os.environ.get("PROFILE_SEL", "").strip()

pkg = json.load(open(os.path.join(repo, "themes.json")))

# scheduleOS is keyed by design language. Fail by name on an unknown one rather
# than falling back: a silent fallback would schedule the wrong language and
# look like the themes simply did not apply.
lang = os.environ.get("MIDORI_LANG", "midori").strip() or "midori"
langs = {k: v for k, v in pkg["scheduleOS"].items() if not k.startswith("_")}
if lang not in langs:
    sys.exit(f"Unknown MIDORI_LANG {lang!r} -- themes.json schedules "
             f"{sorted(langs)}")
sched = langs[lang]
if set(sched) != {"light", "dark"}:
    sys.exit(f"scheduleOS[{lang!r}] must have exactly light and dark, "
             f"got {sorted(sched)}")
want = set(sched.values())
known = {t["id"] for t in pkg["themes"]}
if not want <= known:
    sys.exit(f"scheduleOS[{lang!r}] names theme id(s) no theme defines: "
             f"{sorted(want - known)}")
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
    # UPDATE IN PLACE, DO NOT ONLY APPEND. This was `extend(t for t in
    # pkg["themes"] if t["id"] not in have)`, which adds themes that are
    # missing and silently leaves alone every theme already present. Re-running
    # it after CHANGING a theme's colours therefore printed
    # "themes: already present" and installed nothing -- a confident success
    # line over a no-op. That is this repo's commonest failure shape, and it
    # cost a full quit/install/relaunch cycle before anyone looked at the live
    # values.
    #
    # The trade-off, stated because it is a real one: a theme edited by hand in
    # Vivaldi's own Theme Editor is now OVERWRITTEN by the repo copy. That is
    # the right default for themes this repo manages -- the repo is the source,
    # and sync.sh exists to pull live edits back the other way first -- but it
    # means "tweak in the editor, then re-run the installer" loses the tweak.
    # Run ./sync.sh before re-installing if the editor was used.
    repo_by_id = {t["id"]: t for t in pkg["themes"]}
    added, updated = [], []
    for idx, live in enumerate(user):
        want = repo_by_id.get(live.get("id"))
        if want is not None and live != want:
            user[idx] = copy.deepcopy(want)
            updated.append(want["name"])
    have = {t.get("id") for t in user}
    for want in pkg["themes"]:
        if want["id"] not in have:
            user.append(copy.deepcopy(want))
            added.append(want["name"])
    themes["current"] = sched["light"]
    v.setdefault("theme", {}).setdefault("schedule", {})["o_s"] = sched
    v.setdefault("appearance", {})["css_ui_mods_directory"] = css_dir
    kb_note = ""
    if kb:
        v["actions"] = kb["actions"]
        v["keyboard"] = kb["keyboard"]
        table = kb["actions"][0]
        bound = sum(1 for a in table.values() if a.get("shortcuts"))
        kb_note = f", hotkeys {bound}/{len(table)}"
    json.dump(prefs, open(pref_path, "w"))
    unchanged = len(pkg["themes"]) - len(added) - len(updated)
    what = ", ".join(filter(None, [
        f"added {added}" if added else "",
        f"updated {updated}" if updated else "",
        f"{unchanged} already current" if unchanged else ""]))
    print(f"[{profiles[d]}] themes: {what}; scheduled {lang} "
          f"({len(pkg['themes'])} total) + css mods set{kb_note}")

# --- Local State: enable the css-mods experiment (global, once) ---
ls = json.load(open(ls_path))
exps = ls.setdefault("browser", {}).setdefault("enabled_labs_experiments", [])
if "vivaldi-css-mods" not in exps:
    exps.append("vivaldi-css-mods")
    print("Enabled vivaldi-css-mods experiment (global)")
json.dump(ls, open(ls_path, "w"))
EOF

echo "Done. Relaunch Vivaldi — the $MIDORI_LANG themes follow macOS appearance."
