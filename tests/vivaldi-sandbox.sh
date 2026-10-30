#!/bin/sh
# A throwaway Vivaldi, on a debugging port, wearing this repo's themes.
#
#   sh tests/vivaldi-sandbox.sh start ["Lemonardo Paintpot"]
#   sh tests/vivaldi-sandbox.sh restart "Lemonardo Inkwell"
#   sh tests/vivaldi-sandbox.sh stop
#   sh tests/vivaldi-sandbox.sh python           # prints the venv interpreter
#
# WHY THIS EXISTS. Vivaldi's UI can only be inspected over CDP, and the
# obvious way to get a CDP port is to relaunch the browser the operator is
# using -- which closes their windows, and which must be fully quit before
# Preferences can be written because Vivaldi rewrites that file from memory on
# exit. Worse, a check run against the live profile is a check that can damage
# live user data, and CLAUDE.md's rule about installers exists because this
# repo has already paid for that twice. So: a second instance, its own
# --user-data-dir under the session scratchpad, its own profile, left running
# while the operator's browser is untouched.
#
# WHAT IT REFUSES TO DO. It never writes under ~/Library, and the Python that
# patches Preferences re-checks that for itself rather than trusting the
# caller. It addresses its own instance by the user-data-dir in the command
# line, never by application name: `pkill Vivaldi` or `tell application
# "Vivaldi" to quit` would take the operator's browser with it. It also scopes
# every pgrep to this uid -- a process list is machine-global, and under fast
# user switching an unscoped match finds another account's Vivaldi, which
# cannot be signalled anyway ("Operation not permitted").
#
# BY DEFAULT THE SANDBOX READS THE REPO'S css-mods DIRECTLY, which is what
# makes it useful: edit vivaldi/css-mods/*.css, `restart`, and the change is
# live. Pass MODS=/some/dir to point it elsewhere.
#
# DO NOT ASSUME THE OPERATOR'S BROWSER READS A COPY. It may not.
# vivaldi/install-vivaldi.sh does `cp css-mods/*.css` into
# ~/Library/Application Support/Vivaldi/CSSMods, so the obvious reading is
# that the repo tree is safe to scribble on. On this machine that directory is
# a SYMLINK to vivaldi/css-mods -- same inode, so a write to the repo file is
# a write to what the live browser loads. The first sabotage run here carried
# a comment claiming otherwise and was wrong for seven cases (nothing visible
# happened, because Vivaldi re-reads the mods only on a UI restart). So
# anything that MUTATES a mod file works on a copy and sets MODS to it; see
# tests/sabotage-vivaldi-tab-material.sh.
#
# TWO PREFERENCES ARE NEEDED, NOT ONE. vivaldi.themes.current alone does not
# apply a theme in a fresh 8.2 profile: #browser keeps theme-id-Vivaldi1 and
# nothing says why. vivaldi.theme.schedule.o_s has to name it too, so this
# writes the chosen theme into BOTH of the schedule's slots -- which also pins
# the mode regardless of the OS appearance the run happens to inherit.

set -eu

CMD="${1:-start}"
WANT="${2:-Lemonardo Paintpot}"
PORT="${PORT:-9222}"
REPO=$(cd "$(dirname "$0")/.." && pwd)
VIVALDI="${VIVALDI:-/Applications/Vivaldi.app/Contents/MacOS/Vivaldi}"
MODS="${MODS:-$REPO/vivaldi/css-mods}"
WORK="${WORK:-${TMPDIR:-/tmp}/midori-vivaldi-sandbox}"
UDD="$WORK/vdata"
VENV="$WORK/cdpenv"
PY="$VENV/bin/python"

case "$WORK" in
	"$HOME"/Library/*)
		echo "refusing: WORK=$WORK is inside ~/Library" >&2; exit 2 ;;
esac

mine() { pgrep -fu "$(id -u)" "user-data-dir=$UDD" >/dev/null 2>&1; }

stop_it() {
	if curl -s --max-time 2 "http://localhost:$PORT/json/version" >/dev/null 2>&1
	then
		# Browser.close, not a signal: SIGTERM left the browser process up, and
		# anything reaching for the application NAME would hit the operator's
		# Vivaldi instead of this one. See tests/vivaldi-cdp.py.
		"$PY" "$REPO/tests/vivaldi-cdp.py" close "$PORT" || true
	fi
	i=0
	while mine && [ "$i" -lt 15 ]; do sleep 1; i=$((i + 1)); done
	if mine; then
		echo "sandbox will not shut down; pids:" >&2
		pgrep -flu "$(id -u)" "user-data-dir=$UDD" >&2
		exit 1
	fi
}

ensure_venv() {
	[ -x "$PY" ] && return 0
	mkdir -p "$WORK"
	python3 -m venv "$VENV"
	"$VENV/bin/pip" -q install websocket-client Pillow
}

wait_up() {
	i=0
	until curl -s --max-time 2 "http://localhost:$PORT/json/version" \
		>/dev/null 2>&1
	do
		sleep 1; i=$((i + 1))
		[ "$i" -gt 20 ] && { echo "sandbox never opened port $PORT" >&2; exit 1; }
	done
	# A CDP port that answers is not a UI that exists; vivaldi-cdp.py up has
	# the reason. Polling that instead of sleeping is what makes `restart`
	# usable from a script.
	i=0
	until [ "$("$PY" "$REPO/tests/vivaldi-cdp.py" up "$PORT")" = up ]; do
		sleep 1; i=$((i + 1))
		[ "$i" -gt 25 ] && { echo "#browser never appeared" >&2; exit 1; }
	done
}

# TWO TABS, NOT ONE. tests/check_vivaldi_tab_material.py compares the active
# tab against an inactive one and refuses to run with a single tab, because a
# pass earned by having nothing to compare is exactly the shape of green this
# repo keeps getting burned by. A fresh profile opens one tab, so the sandbox
# opens two.
launch() {
	nohup "$VIVALDI" \
		--user-data-dir="$UDD" \
		--remote-debugging-port="$PORT" \
		--no-first-run --no-default-browser-check --disable-sync \
		about:blank about:blank >> "$WORK/vivaldi.log" 2>&1 &
	wait_up
}

apply_theme() {
	UDD="$UDD" REPO="$REPO" WANT="$WANT" MODS="$MODS" \
		python3 -I - <<-'PY'
	import json, os, sys

	udd, repo, want, mods = (os.environ["UDD"], os.environ["REPO"],
	                         os.environ["WANT"], os.environ["MODS"])
	real = os.path.realpath(udd)
	# The code refuses for itself rather than trusting its caller. CLAUDE.md:
	# before sandboxing, ask what the code names ABSOLUTELY -- and a Vivaldi
	# profile path is the whole game here.
	if os.path.realpath(os.path.expanduser("~/Library")) in real:
	    sys.exit(f"refusing: {real} is inside ~/Library")
	if not os.path.isdir(os.path.join(real, "Default")):
	    sys.exit(f"{real}/Default does not exist yet -- the sandbox has to be "
	             f"launched once before a theme can be written into it")

	pkg = json.load(open(os.path.join(repo, "vivaldi", "themes.json")))
	ids = {t["name"]: t["id"] for t in pkg["themes"]}
	if want not in ids:
	    sys.exit(f"no theme named {want!r}; themes.json has {sorted(ids)}")

	pref_path = os.path.join(real, "Default", "Preferences")
	prefs = json.load(open(pref_path))
	v = prefs.setdefault("vivaldi", {})
	th = v.setdefault("themes", {})
	th["user"] = [dict(t) for t in pkg["themes"]]
	th["current"] = ids[want]
	# Both slots, deliberately: see the header comment. themes.current alone
	# does not apply a theme in a fresh 8.2 profile.
	v.setdefault("theme", {}).setdefault("schedule", {})["o_s"] = {
	    "light": ids[want], "dark": ids[want]}
	if not os.path.isdir(mods):
	    sys.exit(f"MODS={mods} is not a directory")
	v.setdefault("appearance", {})["css_ui_mods_directory"] = mods
	json.dump(prefs, open(pref_path, "w"))
	print(f"sandbox: {len(th['user'])} themes, current={want}, "
	      f"css mods from {mods}")
	PY
}

ensure_venv

case "$CMD" in
python)
	echo "$PY" ;;
stop)
	stop_it; echo "sandbox stopped" ;;
start|restart)
	mine && stop_it
	if [ ! -d "$UDD/Default" ]; then
		# First launch builds the profile; the theme can only be written once
		# Preferences exists, and Vivaldi rewrites it on exit, so the order is
		# launch, stop, patch, launch.
		echo "first run: building the sandbox profile"
		launch
		stop_it
	fi
	apply_theme
	launch
	echo "sandbox up on port $PORT wearing $WANT"
	;;
*)
	echo "usage: sh tests/vivaldi-sandbox.sh {start|restart|stop|python} [theme]" >&2
	exit 2 ;;
esac
