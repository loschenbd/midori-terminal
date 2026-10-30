#!/usr/bin/env python3
"""tools/midori-theme, exercised end to end against a sandboxed HOME.

WHY A SANDBOX AND NOT A DRY RUN. --dry-run proves the script decides correctly
and proves nothing about what it writes, which is the whole job: this command
copies over the live Ghostty config, the live herdr config and a launch agent.
So every case here runs it for real against a fake HOME built from scratch,
then reads the files back. A FAKE HOME IS NOT A SANDBOX FOR LAUNCHD, and this file learned that the
expensive way. A launchd label is `gui/<uid>/<label>` -- machine-global, with
no home in it -- so the first version of this test, run under a temp HOME,
booted out the live watcher and bootstrapped the temp copy in its place. When
the temp directory was removed the job was left crash-looping on a path that
no longer existed, while `launchctl list` still showed it present. Same shape
as the extra-vaults.txt warning in CLAUDE.md: HOME redirection is not a
sandbox when the thing being addressed is named absolutely.

midori-theme now resolves the LOGIN home from the directory service and
refuses to speak to launchd when $HOME is not it, which is a property worth
having outside the tests too. These cases therefore exercise the plist EDIT
(PlistBuddy, which does take a path) and assert that the launchd branch
announces itself as skipped. `herdr server reload-config` is kept out the
plainer way: PATH is stripped, so the binary is simply absent.

WHAT EACH CASE IS FOR is on the case itself. The ones worth naming here:

  * a ~/.tmux.conf that sources a LANGUAGE fragment directly is the state every
    machine was in before active.tmux.conf existed. Left alone it pins the
    panes to one language through any number of switches, silently. install.sh
    migrates it; this holds that migration.
  * a live Ghostty config that matches no language is someone's own file. The
    switch must keep a copy, and must NOT keep one when the live config is
    simply the other language -- a backup on every switch is a backup nobody
    reads.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
# $MIDORI_THEME lets tests/sabotage-herdr-carryover.sh point this file at a
# BROKEN copy of the script and require these cases to go red. Without it the
# only way to prove a case can fail is to break the real script in place,
# which is the thing that gets forgotten half-done.
TOOL = pathlib.Path(os.environ.get("MIDORI_THEME")
                    or ROOT / "tools" / "midori-theme")
LANGS = ("midori", "lemonardo")
fails = []


def fail(msg):
    fails.append(msg)
    print(f"  FAIL  {msg}")


def build_home(d, tmux_conf=None, ghostty_live="midori", plist_lang="midori",
               herdr_written=("onboarding = false",), herdr_live="midori"):
    """A HOME with everything install.sh would have put in place."""
    gh = d / "Library/Application Support/com.mitchellh.ghostty"
    mid = d / ".config/midori"
    herdr = d / ".config/herdr"
    maps = d / ".local/share/midori/claude-themes"
    for p in (gh, mid, herdr, maps, d / "Library/LaunchAgents",
              d / ".local/bin", d / ".config"):
        p.mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        src = ROOT / ("ghostty/config" if lang == "midori"
                      else f"ghostty/config.{lang}")
        (gh / f"config.{lang}").write_text(
            src.read_text().replace("__HOME__", str(d)))
        hsrc = ROOT / ("herdr/config.toml" if lang == "midori"
                       else f"herdr/config.{lang}.toml")
        shutil.copy(hsrc, herdr / f"config.{lang}.toml")
        tsrc = ROOT / ("tmux/midori.tmux.conf" if lang == "midori"
                       else f"tmux/{lang}.tmux.conf")
        shutil.copy(tsrc, mid / f"{lang}.tmux.conf")
        for mode in ("light", "dark"):
            shutil.copy(ROOT / f"watcher/themes/{lang}-{mode}.json",
                        maps / f"{lang}-{mode}.json")
        (d / f".config/{lang}.omp.json").write_text("{}\n")
    if ghostty_live is not None:
        shutil.copy(gh / f"config.{ghostty_live}", gh / "config")
    # THE LIVE HERDR CONFIG IS A LANGUAGE FILE PLUS WHAT HERDR WROTE, and that
    # is the DEFAULT here because it is the state of every machine that has
    # ever started herdr: dismissing the onboarding overlay leaves
    # `onboarding = false` prepended at line 1, and neither language file
    # contains it. Building the live config as a clean copy of ours is exactly
    # what let the old `cmp -s` identity check look right in this test while
    # the real machine reported `herdr  ?` for weeks.
    (herdr / "config.toml").write_text(
        "".join(f"{line}\n" for line in herdr_written)
        + (herdr / f"config.{herdr_live}.toml").read_text())
    (mid / "language").write_text("midori\n")
    if tmux_conf is not None:
        (d / ".tmux.conf").write_text(tmux_conf)
    tpl = (ROOT / "watcher"
           / "com.benjaminloschen.midori-claude-theme.plist.template").read_text()
    (d / "Library/LaunchAgents"
       / "com.benjaminloschen.midori-claude-theme.plist").write_text(
        tpl.replace("__HOME__", str(d)).replace("__LANG__", plist_lang))
    return d


def run(home, *args):
    """Run midori-theme against `home`, with launchctl replaced by a recorder.

    THE STUB IS NOT A CONVENIENCE. Asserting the launchd guard by removing it
    and watching what happens would mean actually booting out the live
    watcher, which is the exact damage the guard exists to prevent -- a
    sabotage proof that has to break the live system to run is not one that
    can be run. A `launchctl` earlier on PATH turns the question into "was it
    called", answerable from a log file, with nothing outside this directory
    touched either way.

    PATH is otherwise stripped, which also keeps `herdr server reload-config`
    away from the live herdr server.
    """
    stub = home / ".stub-bin"
    stub.mkdir(exist_ok=True)
    log = home / ".launchctl-calls"
    (stub / "launchctl").write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$*" >> {log}\nexit 0\n')
    (stub / "launchctl").chmod(0o755)
    env = dict(os.environ, HOME=str(home))
    env["PATH"] = f"{stub}:/usr/bin:/bin:/usr/sbin:/sbin"
    return subprocess.run(["sh", str(TOOL), *args], capture_output=True,
                          text=True, env=env)


def herdr_head(path):
    """The lines of a herdr config above its first table header.

    The only region TOML allows a top-level key in. A key appended below a
    `[section]` belongs to that section instead -- herdr/README.md records
    that costing a debugging round, because `config check` then names the
    wrong owner (`unknown config key ui.toast.pane_scrollbars`).
    """
    lines = path.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("["):
            return "".join(lines[:i])
    return "".join(lines)


def herdr_problems(home, lang, written=("onboarding = false",)):
    """Is the live herdr config `lang`'s file plus exactly `written`?

    ASSERTED BY SUBTRACTION, on purpose. Removing the expected written lines
    and requiring what is left to be the language file byte for byte is
    independent of how the script decides which lines those are. A check that
    re-implemented the top-level-key scan would agree with a buggy
    implementation and call it green.
    """
    live_path = home / ".config/herdr/config.toml"
    live = live_path.read_text()
    want = (home / f".config/herdr/config.{lang}.toml").read_text()
    head = herdr_head(live_path)
    out, rest = [], live
    for w in written:
        n = live.count(w + "\n")
        if n != 1:
            out.append(f"{w!r} appears {n}x in the live config, want exactly 1")
        elif w + "\n" not in head:
            out.append(f"{w!r} is not above the first table header -- TOML "
                       f"files it under the last section instead")
        rest = rest.replace(w + "\n", "", 1)
    if rest != want:
        out.append(f"with {list(written)} removed, the live config is still "
                   f"not config.{lang}.toml byte for byte")
    return out


def launchctl_calls(home):
    f = home / ".launchctl-calls"
    return f.read_text().splitlines() if f.exists() else []


def plist_lang(home):
    p = (home / "Library/LaunchAgents"
         / "com.benjaminloschen.midori-claude-theme.plist")
    r = subprocess.run(["/usr/libexec/PlistBuddy", "-c",
                        "Print :EnvironmentVariables:MIDORI_LANG", str(p)],
                       capture_output=True, text=True)
    return r.stdout.strip()


ran = 0

# ── 1. a full switch writes every surface ────────────────────────────────────
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t),
                      tmux_conf="source-file ~/.config/midori/active.tmux.conf\n")
    r = run(home, "lemonardo")
    ran += 1
    if r.returncode != 0:
        fail(f"a clean switch exited {r.returncode}\n{r.stdout}{r.stderr}")
    gh = home / "Library/Application Support/com.mitchellh.ghostty"
    checks = {
        "language file":
            (home / ".config/midori/language").read_text().strip() == "lemonardo",
        "ghostty config is the lemonardo one":
            (gh / "config").read_text() == (gh / "config.lemonardo").read_text(),
        "tmux symlink points at lemonardo":
            os.readlink(home / ".config/midori/active.tmux.conf")
            .endswith("lemonardo.tmux.conf"),
        # NOT byte equality: the live config carries what herdr wrote.
        "herdr config is the lemonardo one, with herdr's key kept":
            not herdr_problems(home, "lemonardo"),
        "launch agent carries the language": plist_lang(home) == "lemonardo",
    }
    for name, got in checks.items():
        if not got:
            fail(f"after `midori-theme lemonardo`: {name} -- no")
    print(f"  ok    a full switch wrote all {len(checks)} surfaces")

    # ... and switching back is not one-way.
    r = run(home, "midori")
    ran += 1
    if (gh / "config").read_text() != (gh / "config.midori").read_text():
        fail("switching back left the Ghostty config on lemonardo")
    if plist_lang(home) != "midori":
        fail(f"switching back left the launch agent on {plist_lang(home)}")
    print("  ok    switching back restores every surface")

# ── 2. --dry-run writes nothing ──────────────────────────────────────────────
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t),
                      tmux_conf="source-file ~/.config/midori/active.tmux.conf\n")
    # The harness's own launchctl stub and its log are not the subject; they
    # are written by run() itself, so they would show up as "--dry-run created
    # a file" in every case.
    def harness(path):
        r = str(path.relative_to(home))
        return r.startswith(".stub-bin/") or r == ".launchctl-calls"

    before = {p: p.read_bytes() for p in home.rglob("*")
              if p.is_file() and not harness(p)}
    r = run(home, "lemonardo", "--dry-run")
    ran += 1
    if r.returncode != 0:
        fail(f"--dry-run exited {r.returncode}")
    changed = [str(p.relative_to(home)) for p, b in before.items()
               if not p.exists() or p.read_bytes() != b]
    new = [str(p.relative_to(home)) for p in home.rglob("*")
           if p.is_file() and p not in before and not harness(p)]
    if changed or new:
        fail(f"--dry-run changed {changed} and created {new}")
    if "would:" not in r.stdout:
        fail("--dry-run printed no `would:` lines, so it reported nothing")
    print(f"  ok    --dry-run left all {len(before)} files byte-identical")

# ── 3. a hand-written Ghostty config is kept ─────────────────────────────────
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t), ghostty_live="midori")
    gh = home / "Library/Application Support/com.mitchellh.ghostty"
    (gh / "config").write_text("font-size = 99\n# mine\n")
    run(home, "lemonardo")
    ran += 1
    bak = gh / "config.before-midori-theme"
    if not bak.exists():
        fail("a hand-written Ghostty config was overwritten with no backup")
    elif bak.read_text() != "font-size = 99\n# mine\n":
        fail(f"the backup is not the file that was there: {bak.read_text()!r}")
    else:
        print("  ok    a config matching no language is kept as "
              "config.before-midori-theme")

# ── 4. ... and an ordinary switch does NOT leave a backup ────────────────────
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t), ghostty_live="midori")
    run(home, "lemonardo")
    ran += 1
    gh = home / "Library/Application Support/com.mitchellh.ghostty"
    if (gh / "config.before-midori-theme").exists():
        fail("an ordinary switch left a backup -- a backup on every switch is "
             "one nobody reads")
    else:
        print("  ok    switching from a known language leaves no backup")

# ── 5. an unknown language changes nothing ───────────────────────────────────
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t))
    before = {p: p.read_bytes() for p in home.rglob("*") if p.is_file()}
    r = run(home, "chartreuse")
    ran += 1
    if r.returncode == 0:
        fail("an unknown language exited 0")
    if "chartreuse" not in r.stderr:
        fail(f"the refusal does not name the language: {r.stderr!r}")
    changed = [str(p.relative_to(home)) for p, b in before.items()
               if p.read_bytes() != b]
    if changed:
        fail(f"a refused switch still wrote {changed}")
    print("  ok    an unknown language is refused by name, nothing written")

# ── 6. a language with no Claude map is not offered ──────────────────────────
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t))
    (home / ".local/share/midori/claude-themes/lemonardo-dark.json").unlink()
    r = run(home, "lemonardo")
    ran += 1
    if r.returncode == 0:
        fail("a language missing half its Claude Code maps was still offered")
    else:
        print("  ok    a half-installed language is not offered")

# ── 7. the report mode names each surface's actual state ─────────────────────
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t), ghostty_live="lemonardo",
                      plist_lang="midori",
                      tmux_conf="source-file ~/.config/midori/active.tmux.conf\n")
    (home / ".config/midori/language").write_text("midori\n")
    r = run(home)
    ran += 1
    out = r.stdout
    if r.returncode != 0:
        fail(f"the report exited {r.returncode}")
    # Ghostty is on lemonardo while the language file says midori. A report
    # that cannot show a disagreement cannot be used to diagnose one.
    gl = [l for l in out.splitlines() if l.strip().startswith("ghostty")]
    if not gl or "lemonardo" not in gl[0]:
        fail(f"the report does not show Ghostty as lemonardo: {gl}")
    if "language: midori" not in out:
        fail("the report does not show the language file's value")
    else:
        print("  ok    the report shows a disagreement between surfaces")

# ── 8. launchd is left alone when HOME is not the login home ─────────────────
# The guard that exists because this test broke the live watcher once.
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t))
    r = run(home, "lemonardo")
    ran += 1
    calls = launchctl_calls(home)
    if calls:
        fail(f"midori-theme called launchctl {len(calls)} time(s) under a "
             f"sandboxed HOME: {calls} -- a launchd label is machine-global, "
             f"so those addressed the REAL watcher")
    elif "leaving launchd" not in r.stdout:
        fail("midori-theme skipped launchd without saying so -- a silent "
             "guard cannot be told apart from a broken one")
    elif plist_lang(home) != "lemonardo":
        fail("the guard skipped the plist EDIT too; only the launchd calls "
             "should be skipped, or a sandboxed switch proves nothing")
    else:
        print("  ok    a sandboxed HOME edits the plist, calls launchctl 0 times")

# ── 9. a .tmux.conf naming a language fragment is repaired ──────────────────
# THE STATE EVERY MACHINE WAS IN before active.tmux.conf existed, and the one
# a symlink cannot fix: the source-file line names midori.tmux.conf or
# lemonardo.tmux.conf directly, so flipping the symlink moves nothing and the
# panes stay in the old language with no error anywhere.
#
# This case used to assert by GREPPING install.sh for its sed line, and a
# sabotage that prefixed that line with `false &&` left it green -- the check
# could see the line was present and not that it ran. The repair now lives in
# midori-theme, where running the command is the check.
for conf, label in (
    ("source-file ~/.config/midori/midori.tmux.conf\n", "midori"),
    ("# notes\nsource-file ~/.config/midori/lemonardo.tmux.conf\nset -g mouse on\n",
     "lemonardo, with other lines around it"),
):
    with tempfile.TemporaryDirectory() as t:
        home = build_home(pathlib.Path(t), tmux_conf=conf)
        run(home, "lemonardo")
        ran += 1
        got = (home / ".tmux.conf").read_text()
        if "config/midori/active.tmux.conf" not in got:
            fail(f"a .tmux.conf naming {label} was not repointed: {got!r}")
        elif re.search(r"config/midori/(midori|lemonardo)\.tmux\.conf", got):
            fail(f"a .tmux.conf naming {label} still names it: {got!r}")
        elif not got.strip():
            fail(f"a .tmux.conf naming {label} came back EMPTY -- the repair "
                 f"destroyed it rather than leaving it alone. A redirect into "
                 f"the file sed reads from truncates it before sed runs")
        elif not (home / ".tmux.conf.pre-midori-active").exists():
            fail("the original .tmux.conf was rewritten with no copy kept")
        elif (home / ".tmux.conf.pre-midori-active").read_text() != conf:
            fail("the kept copy is not the file that was there")
        else:
            lost = [l for l in conf.splitlines()
                    if "config/midori/" not in l and l not in got.splitlines()]
            if lost:
                fail(f"the repair dropped unrelated lines: {lost}")
            else:
                print(f"  ok    a .tmux.conf naming {label} is repointed, "
                      f"original kept")

# ── 10. a repair that cannot back up leaves the original intact ─────────────
# The failure mode two sabotages found: `sed ... > "$tc"` empties the target
# before sed reads it, so anything that stops the backup being written
# destroys a file this repo does not own. Simulated by making the directory
# read-only, which is what a full disk or a locked home looks like from here.
with tempfile.TemporaryDirectory() as t:
    conf = "source-file ~/.config/midori/midori.tmux.conf\nset -g mouse on\n"
    home = build_home(pathlib.Path(t), tmux_conf=conf)
    run(home, "lemonardo")  # once, to create the stub while we can still write
    (home / ".tmux.conf").write_text(conf)
    for f in home.glob(".tmux.conf.pre-midori-active"):
        f.unlink()
    mode = home.stat().st_mode
    os.chmod(home, 0o500)                      # read + execute, no write
    try:
        run(home, "lemonardo")
        ran += 1
        got = (home / ".tmux.conf").read_text()
    finally:
        os.chmod(home, mode)
    if got != conf:
        fail(f"a .tmux.conf was modified although its backup could not be "
             f"written: {got!r}")
    else:
        print("  ok    a repair that cannot back up leaves the original intact")

# ── 11. a transform that "succeeds" but produces nothing is refused ─────────
# The branch the write-then-move fix was supposed to cover, made reachable.
# `cp -f file dir` succeeds by copying INTO the directory, and BSD sed given a
# DIRECTORY as input writes nothing and exits 0 (measured, Darwin 25.6) -- so
# `sed > new && mv new target` lands an EMPTY file with every status check
# green. The repair checks the output's shape instead: non-empty, and the same
# line count, since this transform rewrites one substring per line.
with tempfile.TemporaryDirectory() as t:
    conf = "# notes\nsource-file ~/.config/midori/midori.tmux.conf\nset -g mouse on\n"
    home = build_home(pathlib.Path(t), tmux_conf=conf)
    (home / ".tmux.conf.pre-midori-active").mkdir()
    r = run(home, "lemonardo")
    ran += 1
    got = (home / ".tmux.conf").read_text()
    if got != conf:
        fail(f"a .tmux.conf was replaced although the transform produced "
             f"nothing usable: {got!r}")
    elif "like-for-like" not in r.stdout:
        fail("the repair refused silently -- say which check rejected it, or "
             "the next reader cannot tell a refusal from a no-op")
    else:
        print("  ok    a transform that exits 0 with no output is refused")

# ── 12. ... and a .tmux.conf already on active.tmux.conf is left alone ───────
with tempfile.TemporaryDirectory() as t:
    conf = "source-file ~/.config/midori/active.tmux.conf\n"
    home = build_home(pathlib.Path(t), tmux_conf=conf)
    run(home, "lemonardo")
    ran += 1
    if (home / ".tmux.conf").read_text() != conf:
        fail("a .tmux.conf already pointing at active.tmux.conf was rewritten")
    elif (home / ".tmux.conf.pre-midori-active").exists():
        fail("a backup was left for a .tmux.conf that needed no repair")
    else:
        print("  ok    a .tmux.conf already on active.tmux.conf is untouched")

# ── 13. the keys herdr wrote survive a switch, in both directions ───────────
# THE REGRESSION THIS FILE EXISTS TO HOLD FROM NOW ON. The switch used to be
# `cp -f config.<lang>.toml config.toml`, which deleted `onboarding = false`
# from a live user config -- a line this repo did not write. Measured cost,
# herdr 0.9.4 in an isolated XDG_CONFIG_HOME: with the key absent herdr draws
# the onboarding overlay over the workspace, and herdr does not re-add the key
# by itself, so it stays gone until that overlay is dismissed again.
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t))
    for want in ("lemonardo", "midori", "lemonardo"):
        run(home, want)
        ran += 1
        probs = herdr_problems(home, want)
        if probs:
            fail(f"switching to {want}: " + "; ".join(probs))
            break
    else:
        print("  ok    herdr's own keys survive three switches, still at the top")

# ── 14. a live config with nothing written into it is copied exactly ────────
# The other half of case 13: carrying keys must not ADD anything -- a stray
# blank line or a doubled newline is still a config this repo rewrote wrongly.
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t), herdr_written=())
    run(home, "lemonardo")
    ran += 1
    live = (home / ".config/herdr/config.toml").read_text()
    want = (home / ".config/herdr/config.lemonardo.toml").read_text()
    if live != want:
        fail(f"with nothing written into it, the live herdr config came back "
             f"{len(live)} bytes against the language file's {len(want)}")
    else:
        print("  ok    a config with no written keys is the language file exactly")

# ── 15. several written keys, and one the language file claims itself ───────
# OWNERSHIP IS BY KEY NAME, NOT BY LINE, and this is the case that makes that
# matter: if a language file ever declares `onboarding` itself, carrying the
# live value too would emit the key TWICE at the top level, which is invalid
# TOML and would take herdr back to its built-in defaults -- an unthemed herdr,
# with `config check` as the only place it is visible.
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t), herdr_written=(
        "onboarding = false", "some_future_key = 3"))
    mid = home / ".config/herdr/config.midori.toml"
    mid.write_text("onboarding = true\n" + mid.read_text())
    run(home, "midori")
    ran += 1
    live = (home / ".config/herdr/config.toml").read_text()
    probs = herdr_problems(home, "midori", written=("some_future_key = 3",))
    if live.count("onboarding") != 1:
        fail(f"a key the language file declares itself was ALSO carried: "
             f"'onboarding' appears {live.count('onboarding')}x")
    elif "onboarding = true" not in live:
        fail("the language file's own value for a claimed key did not win")
    elif probs:
        fail("a second written key was not carried: " + "; ".join(probs))
    else:
        print("  ok    a key the language file claims is not carried; others are")

# ── 16. the report names herdr's language and what herdr added ──────────────
# It said `herdr  ?` on every machine that had ever started herdr, because the
# live file is never byte-equal to a language file. A permanently wrong report
# is worse than none: it trains you past the one time it is right.
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t), herdr_live="lemonardo")
    r = run(home)
    ran += 1
    hl = [l for l in r.stdout.splitlines() if l.strip().startswith("herdr")]
    if not hl:
        fail("the report has no herdr line at all")
    elif "lemonardo" not in hl[0]:
        fail(f"the report cannot name herdr's language: {hl[0]!r}")
    elif "onboarding" not in hl[0]:
        fail(f"the report hides the keys herdr wrote, so the one-word answer "
             f"looks as authoritative as the old `?` was: {hl[0]!r}")
    else:
        print(f"  ok    the report reads:{hl[0].rstrip()}")

# ── 17. --dry-run says it would carry them, and writes nothing ─────────────
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t))
    before = (home / ".config/herdr/config.toml").read_bytes()
    r = run(home, "lemonardo", "--dry-run")
    ran += 1
    if (home / ".config/herdr/config.toml").read_bytes() != before:
        fail("--dry-run rewrote the live herdr config")
    elif "carry over" not in r.stdout:
        fail("--dry-run does not say the written keys would be carried")
    else:
        print("  ok    --dry-run reports the carry-over and writes nothing")

# ── 18. a compose that cannot be written leaves the live config alone ──────
# The herdr half of case 10. The switch writes a new file and moves it into
# place, so every way the write can fail has to end with the live config still
# being a valid herdr config -- a config.toml that is empty or truncated is NOT
# a visible failure, because herdr starts on its built-in defaults and simply
# looks unthemed. A read-only directory is what a full disk or a locked home
# looks like from inside this script.
with tempfile.TemporaryDirectory() as t:
    home = build_home(pathlib.Path(t))
    run(home, "midori")                 # once, while the stub can be created
    hd = home / ".config/herdr"
    before = (hd / "config.toml").read_bytes()
    mode = hd.stat().st_mode
    os.chmod(hd, 0o500)                 # read + execute, no write
    try:
        r = run(home, "lemonardo")
        ran += 1
        after = (hd / "config.toml").read_bytes()
    finally:
        os.chmod(hd, mode)
    if after != before:
        fail(f"the live herdr config was modified although it could not be "
             f"written: {len(before)} -> {len(after)} bytes")
    elif "composing config.toml" not in r.stdout:
        fail("the switch refused to write herdr's config without saying so -- "
             "a silent refusal cannot be told apart from a successful switch, "
             "and the next line printed is a reload that did nothing")
    else:
        print("  ok    a herdr compose that cannot be written is announced, "
              "original intact")

print(f"\n{ran} case(s) run, {len(fails)} failure(s)")
sys.exit(1 if fails else 0)
