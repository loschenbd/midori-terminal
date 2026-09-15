#!/bin/sh
# Cheap syntax/lint guards for the parts that aren't unit-testable (shell
# scripts, the zsh/tmux fragments, the Python bakers) + the patcher unit tests.
# Local/macOS-oriented (the tmux fragment uses `defaults`); CI runs a portable
# subset (see .github/workflows/ci.yml). Run:  sh tests/lint.sh
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
FAIL=0
ok()   { printf '  ok   %s\n' "$*"; }
bad()  { printf '  FAIL %s\n' "$*"; FAIL=1; }

# DOT-DIRECTORIES ARE PRUNED, not just .git. obsidian/.fontenv is a virtualenv
# with ~2000 .py files in site-packages, and py_compiling third-party code we
# did not write turned a two-second lint into a several-minute one. Anything
# hidden is either vendored or machinery; neither is ours to check.
#
# MINDEPTH 1 IS LOAD-BEARING. Without it, `find .` visits `.` itself first,
# whose own basename is `.` -- which matches the `-name '.*'` glob -- so
# `-prune` pruned the repo root before find ever descended into it, and
# nothing below was traversed. This silently matched zero files from the day
# this helper was written until 2026-08-17: `FILES '*.py'` returned 0 files
# and `FILES '*.sh'` returned 0 files; with `-mindepth 1` they return 17 and
# 11. Every "python compiles" and "shell scripts" line below had been passing
# by checking nothing, and every task in this plan that cited "lint all
# green" as evidence was citing a check that had never run.
FILES() { find . -mindepth 1 -name '.*' -prune -o -name "$1" -print; }

# A LOOP OVER AN EMPTY SET LOOKS EXACTLY LIKE A LOOP WHERE EVERYTHING PASSED.
# That is the whole reason the bug above survived two days: zero iterations, no
# bad(), section green. Counting the set before walking it is what makes the
# next broken finder announce itself instead of going quiet, and the count is
# printed because a green run that cannot say HOW MANY things it checked is not
# evidence.
#
# THE CHECK RUNS IN THE PARENT SHELL, DELIBERATELY. Wrapping this in a helper
# called as `for f in $(found ...)` is the obvious shape and it is wrong twice:
# bad() writes to stdout, so its message would be captured and word-split into
# the loop as filenames; and `$( )` is a subshell, so the FAIL=1 it sets would
# be discarded and the run would still exit 0 -- the exact silent-pass this
# guard exists to prevent, reintroduced by the guard. Both were observed.
PY_FILES=$(FILES '*.py')
SH_FILES=$(FILES '*.sh')
count() { printf '%s\n' "$1" | wc -l | tr -d ' '; }

echo "== python compiles =="
if [ -z "$PY_FILES" ]; then
  bad "no .py files found at all -- FILES() is broken, not the repo"
else
  ok "$(count "$PY_FILES") python files to check"
  # ONE INTERPRETER, NOT ONE PER FILE. `python3 -m py_compile` in a loop pays
  # full interpreter startup per file: measured on this repo, 32s for 20 files
  # against 3s for shellcheck over 13. Batching them is the single biggest win
  # available in this script.
  #
  # The per-file ok/FAIL lines are kept deliberately. A green section that
  # cannot name what it checked is not evidence, and collapsing 20 lines into
  # "python ok" would trade a 30s saving for exactly the blindness the count
  # guard above exists to prevent. Python prints the lines; the shell reads
  # only the exit status, because bad() cannot be called from inside it.
  # shellcheck disable=SC2086
  if python3 - $PY_FILES <<'PYC'
import py_compile, sys
bad = 0
for f in sys.argv[1:]:
    try:
        py_compile.compile(f, doraise=True)
        print(f"  ok   py_compile {f}")
    except Exception as exc:
        print(f"  FAIL py_compile {f}: {exc.__class__.__name__}")
        bad = 1
sys.exit(bad)
PYC
  then :; else FAIL=1; fi
fi

echo "== shell scripts =="
if [ -z "$SH_FILES" ]; then
  bad "no .sh files found at all -- FILES() is broken, not the repo"
fi
for sh in $SH_FILES; do
  if command -v shellcheck >/dev/null 2>&1; then
    # -S error: fail only on real errors, not style nits in these hand-written scripts.
    if shellcheck -S error "$sh" >/dev/null 2>&1; then ok "shellcheck $sh"; else bad "shellcheck $sh"; fi
  else
    if sh -n "$sh" 2>/dev/null; then ok "sh -n $sh"; else bad "sh -n $sh"; fi
  fi
done

echo "== zsh fragment parses =="
if command -v zsh >/dev/null 2>&1; then
  if zsh -n shell/zshrc.midori 2>/dev/null; then ok "zsh -n shell/zshrc.midori"; else bad "zsh -n shell/zshrc.midori"; fi
else
  echo "  skip (zsh not found)"
fi

echo "== tmux fragment parses =="
if command -v tmux >/dev/null 2>&1; then
  if tmux -L midori-lint -f tmux/midori.tmux.conf start-server \; kill-server >/dev/null 2>&1; then
    ok "tmux parse tmux/midori.tmux.conf"
  else
    bad "tmux parse tmux/midori.tmux.conf"
  fi
else
  echo "  skip (tmux not found)"
fi

echo "== patcher unit tests =="
if python3 tests/test_patch_claude_binary.py; then :; else FAIL=1; fi

echo "== moshi themes are current =="
if python3 tests/test_moshi_themes.py; then :; else FAIL=1; fi

echo "== midori-timer unit tests =="
if command -v node >/dev/null 2>&1; then
  if node tests/test_midori_timer.js; then :; else FAIL=1; fi
  if node tests/test_caret_writes.js; then :; else FAIL=1; fi
else
  echo "  skip (node not found)"
fi

echo "== palette has one definition =="
if python3 tests/test_palette_is_defined.py; then :; else FAIL=1; fi

echo "== prose typography =="
if python3 tests/test_prose_typography.py; then :; else FAIL=1; fi

# A BACKTICK INSIDE THE INJECTED STYLESHEET ENDS IT. Every plugin here injects
# its CSS as a template literal, and every one documents the CSS in prose above
# the rules — where it is natural to quote a selector or a property `like this`,
# which terminates the string and turns the rest of the file into syntax errors
# far from the cause. Hit three times in one session before this check existed.
# node --check does catch it, but only afterwards and pointing at the wrong
# line; this names the actual mistake.
echo "== no backticks inside injected stylesheets =="
if python3 tests/check_style_literals.py; then :; else FAIL=1; fi

echo "== obsidian plugins parse =="
if command -v node >/dev/null 2>&1; then
  for js in obsidian/plugins/*/main.js; do
    if node --check "$js" 2>/dev/null; then ok "node --check $js"; else bad "node --check $js"; fi
  done
else
  echo "  skip (node not found)"
fi

# PARSING IS NOT LOADING. A main.js truncated at a top-level boundary — by an
# edit that replaced a range and swallowed the rest of the file — is still
# valid JavaScript. It parses, the stylesheet check passes, and the only
# symptom is Obsidian saying "Failed to load plugin" with no line number.
# Happened once; this requires each plugin the way Obsidian does instead.
echo "== obsidian plugins load and export a Plugin =="
if command -v node >/dev/null 2>&1; then
  if node tests/check_plugin_loads.js; then :; else FAIL=1; fi
else
  echo "  skip (node not found)"
fi

# The t3 theme is GENERATED, and t3 validates it strictly on import -- an
# unknown role or a non-hex value throws by name. Catching that here means the
# failure lands at commit time rather than in a dialog inside someone's
# browser, and the --check half fails if the committed JSON was hand-edited
# away from the source that produced it.
echo "== t3 theme matches its source =="
if python3 t3/build-t3-theme.py --check; then :; else FAIL=1; fi

echo
[ "$FAIL" -eq 0 ] && echo "LINT: all green" || echo "LINT: failures above"
exit "$FAIL"
