# Installer wizard — design

**Date:** 2026-07-15
**Status:** Approved (brainstorm session)
**Goal:** Make midori-terminal usable by strangers: a consent-driven install
wizard that lets people pick which tools get the theme, shows exactly what it
will touch before touching it, and can fully undo itself. Scope is "polished
repo" — no releases, no brew tap, no theme-pack API.

## Context

Today `install.sh` applies everything unconditionally: brew bundle, fonts,
Ghostty (themes/backgrounds/shader/config), oh-my-posh prompt, `.zshrc` and
`.tmux.conf` appends, a launchd appearance watcher, and an edit to
`~/.claude/settings.json`. Vivaldi, VS Code/Cursor, and Obsidian have separate
opt-in installers. That is right for the maintainer, aggressive for a
stranger: dotfile appends, a background daemon, and settings edits happen
without per-item consent.

## Decisions made during brainstorm

- **Ambition:** polished repo (git clone stays the distribution).
- **Wizard UI:** `gum` multi-select, bootstrapped via `brew install gum`
  (with a y/n first); plain `read`-based numbered-menu fallback when brew is
  unavailable.
- **Consent model:** plan-then-apply. After selection, print every file the
  install will create/append/edit plus daemons, one confirm, then apply.
  Backups of any file the repo doesn't own.
- **Uninstall:** full `--uninstall` that reverses everything recorded.

## Architecture

```
install.sh              # wizard orchestrator (gum UI + fallback prompts)
lib/common.sh           # render(), backup(), append_once(), json_set(), logging
modules/
  ghostty.sh  shell.sh  tmux.sh  claude.sh
  vivaldi.sh  vscode.sh  obsidian.sh
  _watcher.sh           # internal — never shown in the picker
Brewfile                # unchanged; maintainer "install everything" path
```

### Module contract

Each module defines four functions prefixed with its name (POSIX sh, no
namespaces). The contract is documented in a template comment in one module.

| Function      | Duty                                                       |
|---------------|------------------------------------------------------------|
| `<mod>_deps`  | Echo brew formula/cask names this module needs             |
| `<mod>_plan`  | Print plan lines; **no side effects**                      |
| `<mod>_apply` | Perform the install steps                                  |
| `<mod>_remove`| Reverse them                                               |

Plan line tags: `create` (new file under midori-owned paths), `APPEND`
(adds a line to a user dotfile), `EDIT` (modifies a user-owned file, e.g.
`~/.claude/settings.json`), `DAEMON` (launchd agent). Uppercase = touches
something the repo doesn't own.

Existing standalone installers (`vivaldi/install-vivaldi.sh`,
`vscode/install-vscode.sh`, `obsidian/install-obsidian.sh`) remain and keep
working standalone; their modules call into them rather than duplicating
logic.

### Watcher

The launchd watcher serves both Claude Code (theme base flip) and Ghostty
(retina background symlink swap). It is not a picker checkbox: `_watcher.sh`
is auto-included when Ghostty **or** Claude Code is selected, and its plan
contribution appears as an explicit `DAEMON` line. It is removed only when
neither dependent module remains installed (per the receipt).

## Wizard flow

1. **Bootstrap** — `gum` present? If not and brew exists, offer
   `brew install gum` (y/n). No brew → fallback picker (same selection
   semantics, numbered toggles via `read`).
2. **Pick** — multi-select of the 7 tools. Defaults: pre-check tools detected
   on the machine (`/Applications/Vivaldi.app`, `code`/`cursor`, Obsidian
   vault dir, etc.). Detection sets defaults only; it never hides options.
3. **Deps** — union of selected modules' `_deps`, install only missing ones.
   `MIDORI_SKIP_BREW` honored throughout.
4. **Plan** — concatenated `_plan` output, grouped by module, tagged as above.
5. **Confirm** — single y/N. Then `_apply` per module.
6. **Backups** — before the first `APPEND`/`EDIT` to a given file, copy it to
   `~/.config/midori/backups/<basename>.<YYYYMMDD-HHMMSS>`. Ghostty config
   keeps the existing behavior: differing existing config → write
   `config.midori` alongside, never overwrite.
7. **Receipt** — record applied module names, one per line, in
   `~/.config/midori/installed`. Re-runs and uninstall read this.
8. **Non-interactive** — `./install.sh --all` and
   `./install.sh --modules ghostty,shell` skip the picker (maintainer update
   path: `git pull && ./install.sh --all`). `--plan-only` prints the plan and
   exits (user dry-run + test hook).

## Uninstall

`./install.sh --uninstall`:

- Reads the receipt; runs each recorded module's `_remove`.
- Deletes files copied into midori-owned paths; removes fonts.
- Strips dotfile lines by matching the exact midori marker comment (not fuzzy
  `grep midori`).
- `launchctl bootout` + delete the plist.
- Resets `theme` in `~/.claude/settings.json` **only if** it still equals
  `custom:midori`.
- Shows the same plan-then-confirm UX as install.
- Leaves brew packages installed and says so in the summary.
- Clears the receipt.

## Error handling

Each module's apply runs under `set -e` in a subshell; a failure reports the
module and continues with the rest. Only successfully applied modules land in
the receipt, so partial installs re-run and uninstall correctly.

## Personal vs public seams

- `sync.sh` is maintainer tooling — documented as such, not part of the
  public flow.
- launchd label stays `com.benjaminloschen.midori-claude-theme` (it's only a
  label).
- `__HOME__` rendering stays; no personal paths in installed artifacts.

## README rework

Stranger-first ordering:

1. Screenshots (paper + night: Ghostty, VS Code, Vivaldi — user captures,
   stored under `docs/`).
2. Quick start: clone → `./install.sh` → wizard.
3. "What each module touches" table — sourced from the same plan text so docs
   can't drift from behavior.
4. Uninstall section.
5. Existing internals (dot-grid shader, watcher architecture, gotchas) under
   a "How it works" section, unchanged in substance.

## Testing / verification

- `--plan-only` under `HOME=$(mktemp -d)` for every module combination worth
  caring about (all, each single module) — asserts plans render and nothing
  writes outside the temp home.
- One real install → uninstall round-trip on the maintainer machine, diffing
  tracked `$HOME` paths before/after to confirm clean reversal.
- Idempotency: `--all` twice produces "already up to date" plan lines, no
  duplicate dotfile appends.

## Out of scope

- Brew tap / curl-pipe-sh distribution, versioned releases.
- Theme-pack abstraction (installing the infrastructure with non-midori
  palettes).
- Linux support (`launchd`, `defaults`, and app paths are macOS-specific).
