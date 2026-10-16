#!/usr/bin/env python3
"""herdr/install-herdr.sh, exercised against a sandboxed HOME.

WHY THIS FILE EXISTS. install-herdr.sh is the one installer whose destination
is also written by the application it installs for: dismissing herdr's
onboarding overlay leaves `onboarding = false` prepended at line 1 of
~/.config/herdr/config.toml, and neither language file contains it. So the
`cmp -s "$SRC" "$DEST"` this script used to decide "already up to date" could
never match, and every run fell through to the conflict branch and announced
"Existing herdr config matches neither language" while writing a
config.repo-version.toml nobody needed. The decision is now herdr_is(), and a
decision has to be exercised to be believed.

WHAT THIS NAMES ABSOLUTELY, which is the question CLAUDE.md insists on asking
before trusting a HOME sandbox. Two things escape $HOME here:

  * $HERDR_SOCKET_PATH is an absolute path to the live herdr server's socket
    (/Users/<me>/.config/herdr/herdr.sock in a normal shell). `herdr server
    reload-config` at the end of the installer would therefore reach the
    OPERATOR'S RUNNING SERVER from inside a sandbox.
  * `herdr` itself resolves its config directory from $XDG_CONFIG_HOME, not
    from $HOME, so redirecting HOME alone does not move it.

Both are handled the way tests/test_midori_theme.py handles launchctl: a
`herdr` recorder earlier on PATH turns "was it called, and with what" into a
log file, with nothing outside the sandbox touched either way. PATH is
otherwise stripped, the HERDR_* variables are unset, and XDG_CONFIG_HOME is
pointed into the sandbox -- belt and braces, because the recorder is the only
one of the three that would survive someone later running this under a real
herdr. The real ~/.config/herdr is fingerprinted by content before and after,
the same proof tests/dryrun-installers.sh prints for the Obsidian vaults.

Note what is NOT asserted: that herdr accepts the composed file. `herdr config
check` is the recorder here, so its "config: ok" is this file's own echo. The
real validation of a language file is herdr/README.md's rendered probe.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "herdr" / "install-herdr.sh"
ONBOARDING = "onboarding = false\n"
fails = []


def fail(msg):
    fails.append(msg)
    print(f"  FAIL  {msg}")


def fingerprint(d):
    """Content, not mtime: copying an identical file moves mtime and proves
    nothing in either direction."""
    if not d.is_dir():
        return {}
    return {p.name: p.read_bytes() for p in sorted(d.iterdir())
            if p.is_file() and p.suffix == ".toml"}


def run(home, live=None):
    """Run the installer against `home`, with herdr replaced by a recorder."""
    stub = home / ".stub-bin"
    stub.mkdir(parents=True, exist_ok=True)
    log = home / ".herdr-calls"
    (stub / "herdr").write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$*" >> {log}\n'
        'case "$*" in\n'
        '  "--version") echo "herdr 0.9.4" ;;\n'
        '  "config check") echo "config: ok" ;;\n'
        'esac\nexit 0\n')
    (stub / "herdr").chmod(0o755)
    hd = home / ".config/herdr"
    hd.mkdir(parents=True, exist_ok=True)
    if live is not None:
        (hd / "config.toml").write_text(live)
    env = {k: v for k, v in os.environ.items() if not k.startswith("HERDR_")}
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    env["PATH"] = f"{stub}:/usr/bin:/bin:/usr/sbin:/sbin"
    r = subprocess.run(["sh", str(INSTALLER)], capture_output=True, text=True,
                       env=env)
    calls = (log.read_text().splitlines() if log.exists() else [])
    return r, hd, calls


def lang_text(lang):
    return (ROOT / ("herdr/config.toml" if lang == "midori"
                    else f"herdr/config.{lang}.toml")).read_text()


# ── prove the real target is untouched ───────────────────────────────────────
REAL = pathlib.Path.home() / ".config/herdr"
real_before = fingerprint(REAL)
if not real_before:
    # A fingerprint of nothing would make the proof below vacuous.
    print(f"  note  {REAL} holds no .toml files; the untouched-proof is weak")
else:
    print(f"  ok    fingerprinted {len(real_before)} real herdr config file(s)")

ran = 0

# ── 1. no live config: a fresh install ───────────────────────────────────────
with tempfile.TemporaryDirectory() as t:
    r, hd, calls = run(pathlib.Path(t))
    ran += 1
    if r.returncode != 0:
        fail(f"a fresh install exited {r.returncode}\n{r.stdout}{r.stderr}")
    elif (hd / "config.toml").read_text() != lang_text("midori"):
        fail("a fresh install did not put the Midori config in place")
    elif not (hd / "config.midori.toml").exists() \
            or not (hd / "config.lemonardo.toml").exists():
        fail("a fresh install did not write both switch sources")
    elif (hd / "config.repo-version.toml").exists():
        fail("a fresh install cried conflict")
    else:
        print("  ok    a fresh install writes the config and both switch sources")

# ── 2. the live config is ours PLUS what herdr wrote ────────────────────────
# THE CASE THE OLD `cmp -s` GOT WRONG, and the reason this file exists. This is
# the steady state of every machine that has ever started herdr.
for lang in ("midori", "lemonardo"):
    with tempfile.TemporaryDirectory() as t:
        live = ONBOARDING + lang_text(lang)
        r, hd, calls = run(pathlib.Path(t), live=live)
        ran += 1
        out = r.stdout
        if (hd / "config.toml").read_text() != live:
            fail(f"the installer rewrote a live {lang} config")
        elif (hd / "config.repo-version.toml").exists():
            fail(f"a live {lang} config + herdr's own key was called a "
                 f"conflict:\n{out}")
        elif lang == "midori" and "already up to date" not in out:
            fail(f"a live Midori config was not recognised as current:\n{out}")
        elif lang == "midori" and "onboarding" not in out:
            fail(f"the installer did not say which keys herdr had added, so "
                 f"'already up to date' overstates what it compared:\n{out}")
        elif lang == "lemonardo" and "Live herdr config is lemonardo" not in out:
            fail(f"a live Lemonardo config was not reported as a pending "
                 f"switch:\n{out}")
        else:
            print(f"  ok    a live {lang} config + herdr's own key is read as "
                  f"{lang}, not as a conflict")

# ── 3. a config that really is someone else's is still a conflict ───────────
# The branch must not have been widened into "anything goes": a hand-written
# config has to keep tripping it, or the fix has merely silenced the alarm.
with tempfile.TemporaryDirectory() as t:
    live = ONBOARDING + '[theme]\nname = "catppuccin"\n# mine\n'
    r, hd, calls = run(pathlib.Path(t), live=live)
    ran += 1
    if (hd / "config.toml").read_text() != live:
        fail("a hand-written herdr config was overwritten")
    elif not (hd / "config.repo-version.toml").exists():
        fail(f"a config matching neither language did not trip the conflict "
             f"branch:\n{r.stdout}")
    elif "matches neither language" not in r.stdout:
        fail("the conflict was not announced")
    else:
        print("  ok    a config matching neither language still trips the alarm")

# ── 4. a live config differing from ours only INSIDE a table is a conflict ──
# The narrow edge of herdr_is: it forgives top-level keys this repo did not
# write, and must forgive nothing else. A changed colour inside [theme.custom]
# is a real divergence and has to be reported, or an edited theme would be
# silently declared up to date and never reconciled.
with tempfile.TemporaryDirectory() as t:
    live = ONBOARDING + lang_text("midori").replace("#ced1c8", "#ff0000", 1)
    r, hd, calls = run(pathlib.Path(t), live=live)
    ran += 1
    if "already up to date" in r.stdout:
        fail("a live config with an edited colour was called up to date -- "
             "herdr_is forgives more than the keys herdr writes")
    elif not (hd / "config.repo-version.toml").exists():
        fail(f"an edited colour did not trip the conflict branch:\n{r.stdout}")
    else:
        print("  ok    an edit inside a table is still a conflict")

# ── 5. the installer reached herdr, and only the recorder ───────────────────
with tempfile.TemporaryDirectory() as t:
    r, hd, calls = run(pathlib.Path(t))
    ran += 1
    if not any(c.startswith("config check") for c in calls):
        fail(f"the installer never validated the config it wrote: {calls}")
    elif not any(c.startswith("server reload-config") for c in calls):
        fail(f"the installer never tried to reload a running server: {calls}")
    else:
        print(f"  ok    the installer called herdr {len(calls)}x, all of them "
              f"the recorder")

# ── the untouched-proof ─────────────────────────────────────────────────────
real_after = fingerprint(REAL)
if real_before and real_after != real_before:
    changed = sorted(set(real_before) | set(real_after))
    fail("the REAL herdr config directory changed during this run: "
         + ", ".join(n for n in changed
                     if real_before.get(n) != real_after.get(n)))
elif real_before:
    print(f"  ok    all {len(real_before)} real herdr config file(s) "
          f"byte-identical afterwards")

print(f"\n{ran} case(s) run, {len(fails)} failure(s)")
sys.exit(1 if fails else 0)
