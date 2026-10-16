# Working in this repo

## The comments are the deliverable

`obsidian/theme.css` is 3,397 lines, of which **~2,093 (61%) are comments** in
256 blocks. They are not filler and they are not over-explanation. They are the
design record: what was measured, on what hardware, what was tried and failed,
and which apparent improvements are traps. The stylesheet can be regenerated
from understanding; the understanding cannot be regenerated from the stylesheet.

**Never delete a comment that records a measurement, a rejected alternative, or
a warning.** Three separate bugs in one session were understood only because
the note above the code survived. If a comment seems too long, it is the right
length.

Two things you MAY do to comments, and should:

- **Correct one that is false.** A confident, fluent, wrong explanation is
  worse than none, and this file has shipped several. When you correct one, say
  what was wrong and why it was believed — a silent replacement invites the
  next reader to re-derive the error.
- **Add the measurement a claim is missing.** "This is faster" with no number
  is a claim awaiting verification, not a record.

## Verification here is not trustworthy by default

This repo has a documented history of green-but-vacuous checks:

- `tests/lint.sh` traversed **zero files for two days** while every task cited
  "lint all green" as evidence.
- Guard tests passed while the rule they named lost a specificity contest and
  did nothing.
- A CDP sweep graded the wrong window and printed a confident all-clear.
- A per-level checker written to catch that shipped the same bug, selecting a
  window with no rendered `h1`.

So: **a passing check is evidence only if you know what it examined.** Print
counts. Fail on an empty input set. Before trusting a new guard, sabotage the
thing it guards on a scratch copy and require it to fail *naming* what you
broke. See `~/.claude/skills/guard-tests-need-a-sabotage-proof-not-a-reading`.

## A measurement does not validate the explanation beside it

Numbers get verified; the mechanism written next to them usually doesn't, and
decisions are made from mechanisms. When a recorded cause concludes that a fix
is expensive or that a defect is inherent, re-derive it from primary data
before accepting the conclusion. The `h1` sat 1.5px off the grid for a year
behind an invented explanation that made a free fix look impossible.

## The installers write into live user data

`install.sh` is an orchestrator; the per-target scripts under `antinote/`,
`herdr/`, `obsidian/`, `vivaldi/`, `vscode/` carry target-specific caveats that
look like duplication and are not. `obsidian/install-obsidian.sh` copies into
**nine real Obsidian vaults**, including `~/Projects` paths listed in the
gitignored `extra-vaults.txt`.

**Never run an installer to test a change to it.** Use
`tests/dryrun-installers.sh`, which runs against a sandboxed copy and then
proves the real vaults were untouched by checksum. Note that `HOME` redirection
alone is NOT sufficient: `extra-vaults.txt` holds absolute paths that ignore
`HOME` entirely, which is why the harness sandboxes the whole repo.

**That is a rule, not an anecdote about one file.** It has now caught this repo
twice, and the second time it cost the live system. Writing
`tests/test_midori_theme.py` meant running `tools/midori-theme` against a temp
`HOME` — but a launchd job is addressed as `gui/<uid>/<label>`, which has no
home in it, so the sandboxed run booted out the real appearance watcher and
bootstrapped the temp copy in its place. The temp directory was then removed
and the job was left crash-looping on a path that no longer existed, while
`launchctl list` still showed it present.

So before sandboxing by `HOME`, ask what the code **names absolutely**: a
launchd label, a D-Bus or XPC service name, a port, a well-known `/tmp` path,
an absolute path in a config file. Each of those escapes the sandbox. Where the
escape is unavoidable, make the code itself refuse — `midori-theme` resolves
the login home from the directory service and will not speak to launchd when
`$HOME` is not it — and have the test replace the escaping command with a
recorder on `PATH`, so "was it called" is answerable without calling it.

Never delete a snippet the installer did not write — `zen-mode.css` is renamed
aside to `.superseded`, never removed.

## Conventions

- Shell is POSIX `sh`, not bash. macOS-oriented; CI runs a portable subset.
- Run `sh tests/lint.sh` before every commit. It takes ~60s; that is normal.
- Rendered checks (`tests/check_rendered_grid.py`,
  `tests/check_rendered_headings.py`) need a running Obsidian with
  `--remote-debugging-port=9222` and are deliberately not in lint.
- Vivaldi's UI is CSS and can only be checked by rendering it, which used to
  mean relaunching the browser the operator is using. `tests/vivaldi-sandbox.sh`
  starts a second Vivaldi on a debugging port with its own throwaway profile
  wearing this repo's themes, so `tests/check_vivaldi_tab_material.py` (and
  anything after it) measures real pixels without touching live data.
  **`~/Library/Application Support/Vivaldi/CSSMods` is a symlink to
  `vivaldi/css-mods` here**, even though `install-vivaldi.sh` copies — so a
  write to a mod file in the repo is a write to what the live browser loads.
  Anything that mutates one works on a copy and points the sandbox at it with
  `MODS=`; see `tests/sabotage-vivaldi-tab-material.sh`.
- **`Page.captureScreenshot` does not return sRGB.** It comes back in the
  display's colour space — a div painted `#dc931e` reads `#d6882c`, ~4.9
  dE2000 — and alpha layers composite *after* that transform, so a
  pre-blended hex is wrong too. Compare a screenshot against a patch painted
  and captured the same way, never against a nominal value. Same trap as the
  t3 night grounds.
- **An installer's destination may also be written by the application.**
  `~/.config/herdr/config.toml` is the one here: herdr prepends
  `onboarding = false` to it when its onboarding overlay is dismissed, and no
  language file contains that line. So `cmp -s` against a language file could
  never match — `midori-theme` printed `herdr  ?` forever and
  `install-herdr.sh` announced "matches neither language" on a config that was
  exactly ours — and the `cp -f` that switched it deleted a line this repo did
  not write. Both now go through `herdr_is` / `herdr_compose`, which compare
  and compose ignoring the top-level keys herdr owns; the functions carry the
  measurements. Before `cmp`-ing or `cp`-ing over any live config, ask whether
  the app writes it too.
- Plugins under `obsidian/plugins/` must be a single self-contained `main.js`
  plus `manifest.json` — the installer copies nothing else.
