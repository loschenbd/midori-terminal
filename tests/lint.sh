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

echo "== python compiles =="
for py in $(find . -name '*.py' -not -path './.git/*'); do
  if python3 -m py_compile "$py" 2>/dev/null; then ok "py_compile $py"; else bad "py_compile $py"; fi
done

echo "== shell scripts =="
for sh in $(find . -name '*.sh' -not -path './.git/*'); do
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
if python3 tests/test_patch_claude_diffs.py; then :; else FAIL=1; fi

echo
[ "$FAIL" -eq 0 ] && echo "LINT: all green" || echo "LINT: failures above"
exit "$FAIL"
