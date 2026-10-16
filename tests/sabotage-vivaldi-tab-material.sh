#!/bin/sh
# Sabotage-proof the Lemonardo active-tab material layer's two guards.
#
# A passing check is evidence only if you know what it examined. So before
# trusting either guard, break the thing it watches and require it to FAIL
# while naming what was broken. A sabotage a guard sails through is a hole in
# the guard, and this layer has two guards with a deliberate split:
#
#   tests/check_vivaldi_tab_material.py   does the declared layer reach the
#                                         screen, in a running Vivaldi
#   make-lemonardo-palette.py --check     are the declared numbers the ones
#                                         the derivation produces
#
# THAT SPLIT IS THE INTERESTING PART, and it is why the last case asserts
# which guard catches it. The live checker reads its alphas OUT of the CSS, so
# it cannot tell a well-chosen alpha from a badly-chosen one -- only whether
# the file's alpha is what the compositor produced. Hand-edit 0.252 to 0.400
# and it still passes, correctly. The generator's --check owns that question.
# A guard that claimed both would be lying about one of them.
#
#   sh tests/sabotage-vivaldi-tab-material.sh [case]
#
# case is one of: missing wrong-host same-dir zindex content events alpha
#                 (default: all)
#
# WHAT THIS TOUCHES, AND THE MISTAKE THE FIRST VERSION MADE. It works on a
# COPY of vivaldi/css-mods under the sandbox's own work directory, and points
# the sandbox Vivaldi at that copy with MODS=. The first version sabotaged
# vivaldi/css-mods/lemonardo-palette.css itself and said in this very comment
# that the operator's browser reads a copy, "so this is safe". It does not:
# ~/Library/Application Support/Vivaldi/CSSMods is a SYMLINK to
# vivaldi/css-mods on this machine, same inode, so all seven cases were
# writing broken CSS into what the live browser loads. Nothing visible
# happened -- Vivaldi re-reads its mods only on a UI restart, and the file was
# regenerated at the end -- but the claim was false and the next person would
# have relied on it. install-vivaldi.sh really does `cp`, which is exactly why
# the symlink is so easy to miss.

set -eu

CASE="${1:-all}"
REPO=$(cd "$(dirname "$0")/.." && pwd)
GEN="$REPO/vivaldi/make-lemonardo-palette.py"
SANDBOX="$REPO/tests/vivaldi-sandbox.sh"
CHECK="$REPO/tests/check_vivaldi_tab_material.py"
THEME="${THEME:-Lemonardo Paintpot}"
WORK="${WORK:-${TMPDIR:-/tmp}/midori-vivaldi-sandbox}"
MODS="$WORK/mods-sabotage"
PAL="$MODS/lemonardo-palette.css"
REAL="$REPO/vivaldi/css-mods/lemonardo-palette.css"

PY=$(sh "$SANDBOX" python)
[ -x "$PY" ] || {
	echo "no sandbox venv; run sh tests/vivaldi-sandbox.sh start first" >&2
	exit 2
}

mkdir -p "$MODS"
cp "$REPO"/vivaldi/css-mods/*.css "$MODS/"
REAL_SHA=$(shasum -a 256 "$REAL" | cut -d' ' -f1)

# Restore the SCRATCH copy from the repo, and re-assert that the repo file
# itself never moved. The second half is the part that matters: it is the
# check that this harness is still only touching the copy.
restore() {
	cp "$REAL" "$PAL"
	now=$(shasum -a 256 "$REAL" | cut -d' ' -f1)
	[ "$now" = "$REAL_SHA" ] || {
		echo "STOP: $REAL changed during this run ($now, was $REAL_SHA)." >&2
		echo "This harness is meant to touch only $PAL." >&2
		exit 1
	}
}
trap restore EXIT INT TERM

PASS=0
HOLES=0

# grade <label> <guard> <pattern the failure must name>
# Requires BOTH a non-zero exit and output that names what was broken. An exit
# code alone is not enough: a guard that fails for an unrelated reason -- a
# crash, a missing file, the browser not up -- is indistinguishable from one
# that caught the sabotage, and that is how a sabotage harness ends up
# certifying a guard that does nothing.
grade() {
	label=$1
	guard=$2
	want=$3
	case "$guard" in
	live)
		MODS="$MODS" sh "$SANDBOX" restart "$THEME" > /dev/null 2>&1
		out=$("$PY" "$CHECK" 2>&1) && rc=0 || rc=$?
		;;
	gen)
		out=$(python3 "$GEN" --check 2>&1) && rc=0 || rc=$?
		;;
	esac
	if [ "$rc" -eq 0 ]; then
		echo "  HOLE  $label: $guard guard PASSED a sabotaged palette"
		HOLES=$((HOLES + 1))
	elif printf '%s' "$out" | grep -qi -- "$want"; then
		echo "  ok    $label"
		printf '%s\n' "$out" | grep -i -- "$want" | head -2 | sed 's/^/          /'
		PASS=$((PASS + 1))
	else
		echo "  WEAK  $label: $guard guard failed, but never named /$want/"
		printf '%s\n' "$out" | tail -6 | sed 's/^/          /'
		HOLES=$((HOLES + 1))
	fi
}

run() {
	restore
	case $1 in
	missing)
		python3 - "$PAL" <<'PY'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1])
p.write_text(re.sub(
    r"/\* Lemonardo [^*]*?\*/\n#browser[^\n]*\.tab-header::after \{[^}]*\}\n",
    "", p.read_text(), flags=re.S))
PY
		grade "the rules are gone" live "declares no"
		;;
	wrong-host)
		# The trap the palette's own comment is about: .tab.active's ::before
		# and ::after are Vivaldi's, carrying the corner joins and the fade
		# animations, and they compute to content: none so they look free.
		#
		# BE HONEST ABOUT WHAT THIS PROVES. It is caught by the checker's
		# PATTERN, which pins `.tab.active .tab-header::after`, and so it
		# reports the same "declares no rule" as the missing case rather than
		# measuring anything. That is a real guarantee -- the trap cannot be
		# re-entered without the checker going red -- but it is a weaker one
		# than the pixel cases, and a reader who thought this case measured
		# the broken corner joins would be wrong.
		sed -i '' 's/\.tab\.active \.tab-header::after/.tab.active::after/' "$PAL"
		grade "moved onto .tab, Vivaldi's own pseudo (caught by the pattern, \
not by measurement)" live "declares no"
		;;
	same-dir)
		python3 - "$PAL" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_text(p.read_text().replace("linear-gradient(to top,",
                                   "linear-gradient(to bottom,"))
PY
		grade "both benches lit from the same side" live \
			"same surface lit from opposite"
		;;
	zindex)
		sed -i '' 's/  z-index: -1;/  z-index: 1;/' "$PAL"
		grade "layer moved on top of the label" live "z-index"
		;;
	content)
		sed -i '' '/^  content: "";$/d' "$PAL"
		grade "content dropped, so nothing paints" live "content"
		;;
	events)
		sed -i '' '/^  pointer-events: none;$/d' "$PAL"
		grade "veil left as a hit-test target" live "pointer-events"
		;;
	alpha)
		# This one belongs to the generator, and the live checker is asserted
		# to PASS it -- see the header. The generator reads the REPO file, so
		# the sabotage has to land there for this case and only this case;
		# restore() puts it back and re-checks the checksum.
		cp "$REAL" "$WORK/real.bak"
		sed -i '' 's|rgb(255 255 255 / 0\.252)|rgb(255 255 255 / 0.400)|' "$REAL"
		out=$(python3 "$GEN" --check 2>&1) && rc=0 || rc=$?
		cp "$WORK/real.bak" "$REAL"
		if [ "$rc" -ne 0 ] && printf '%s' "$out" \
			| grep -qi -- "does not match this generator"
		then
			echo "  ok    lit alpha hand-edited past the dE gate"
			printf '%s\n' "$out" | grep -i "does not match" \
				| head -1 | sed 's/^/          /'
			PASS=$((PASS + 1))
		else
			echo "  HOLE  lit alpha hand-edited past the dE gate: the "
			echo "        generator's --check did not catch it"
			HOLES=$((HOLES + 1))
		fi
		# And the inverted expectation, asserted rather than assumed: if the
		# live checker ever starts failing here, someone should find out which
		# guard moved.
		sed -i '' 's|rgb(255 255 255 / 0\.252)|rgb(255 255 255 / 0.400)|' "$PAL"
		MODS="$MODS" sh "$SANDBOX" restart "$THEME" > /dev/null 2>&1
		if "$PY" "$CHECK" > /dev/null 2>&1; then
			echo "  ok    ...and the live checker passes it, as it should:"
			echo "          it checks that the file's alpha reaches the screen,"
			echo "          not that the file's alpha was well chosen"
			PASS=$((PASS + 1))
		else
			echo "  NOTE  the live checker also failed on a hand-edited alpha."
			echo "        It is not supposed to be able to tell. Either the"
			echo "        edit broke something else or a guard moved."
			HOLES=$((HOLES + 1))
		fi
		;;
	*)
		echo "unknown case $1" >&2; exit 2 ;;
	esac
}

echo "sabotaging a COPY at $PAL"
echo "the repo file ($REAL_SHA) is only touched by the alpha case, and is"
echo "checksum-verified after every case"
echo

if [ "$CASE" = all ]; then
	set -- missing wrong-host same-dir zindex content events alpha
else
	set -- "$CASE"
fi
for c in "$@"; do run "$c"; done

restore
# Leave the sandbox pointed back at the repo's mods, so the next plain
# `restart` is not quietly still reading the sabotage copy.
sh "$SANDBOX" restart "$THEME" > /dev/null 2>&1 || true
echo
echo "sabotage: $PASS held, $HOLES hole(s)"
[ "$HOLES" -eq 0 ] || exit 1
