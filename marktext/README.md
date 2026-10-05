# Midori for MarkText

[MarkText](https://github.com/marktext/marktext) is a WYSIWYG markdown editor.
This is one stylesheet, `midori.css`, covering both modes.

## Installing

Open MarkText → **Preferences → Theme**:

1. **Follow System Theme** on.
2. Light mode theme → **Cadmium Light**. Dark mode theme → **Cadmium Dark**.
3. Paste the whole of `midori.css` into the **Custom CSS** box underneath.

Or, with MarkText **quit**, run `./marktext/apply-marktext.sh`, which writes the
same string into `customCss` in `preferences.json` and backs the file up first.
It refuses to run while MarkText is open — see "Applying it from a script".

Nothing is installed on the host beyond that one preference. `install.sh` does
not touch MarkText.

## Why this is a Custom CSS blob and not two theme files

Every other target in this repo ships named theme files. MarkText cannot take
one, and the reason is not obvious from the UI:

* **The theme ids are compiled in.** `LIGHT_THEMES` and `DARK_THEMES` in
  `out/main/index.js` inside `app.asar` are frozen arrays of ten and twenty-two
  entries. `addThemeStyle()` in the renderer is a `switch` over those literal
  ids. There is no lookup path a new id could enter.
* **The "Import Theme" UI is dead.** Preferences → Theme has rows for
  *Open themes folder* and *Import Theme*, and the i18n strings for both ship in
  the bundle. Both rows are rendered inside
  `withDirectives(createBaseVNode("section", …), [[vShow, false]])`, and neither
  button carries a click handler. They are not hidden behind a flag; they are
  hidden, full stop, in 0.20.0. There is no themes folder to open.
* So `customCss` is the whole supported surface. It is a **single string**
  shared by both colour modes, which is why light and dark live in one file.

## How MarkText applies it, and why the order matters

`addCustomStyle()` appends `<style id="custom-styles">` to `<head>`. It is
called from exactly one place: a `watch()` on the `customCss` preference. That
fires when the stored value arrives from the main process at startup, which is
*after* `addThemeStyle()` has appended `<style id="ag-theme">` on mount.

So `#custom-styles` is always later in `<head>` than the theme it is overriding,
and equal-specificity rules here win on document order. Verified in the running
app: `ag-theme` 123 bytes (Cadmium Light's two-variable patch), `ag-common-style`
133 bytes, then `custom-styles`.

That is why almost nothing in `midori.css` needs `!important`. The handful that
do are the places Cadmium Dark hardcodes a literal hex with `!important` of its
own — `#1d1d1d` on the sidebar border and the tab-strip rules — which no
variable can reach.

## `body.dark` is the mode marker

`addThemeStyle()` does `document.body.classList.remove("dark")` and re-adds it
when the selected id is in `railscastsThemes` (which contains `dark`) or is
`one-dark`. The class therefore tracks **the chosen theme, not the OS**, which
is what a theme wants: pick a dark theme on a light desktop and the class still
flips. `prefers-color-scheme` would be wrong in exactly that case.

Light values go on `:root`, dark values on `body.dark`. Body is what paints the
ground and everything the app renders is inside it, so inheritance does the rest.

## The trap that cost the first two passes: two variable families

MarkText's own chrome reads camelCase custom properties (`--editorBgColor`).
The `@muyajs/core` editor reads a kebab-case mirror (`--editor-bg-color`). Every
shipped theme defines both, and a comment inside Graphite says the camelCase set
still drives the current editor "until editor.vue switches engines". Setting one
family leaves half the app on Cadmium's defaults.

The mirror is written as `--h1-color: var(--h1Color)` so there is one source of
truth. **That is also the trap.** `var()` is substituted at the element that
*declares* it, not at the element that *consumes* it — so a mirror declared only
on `:root` freezes to the light values, and redefining `--h1Color` on
`body.dark` changes nothing a muya node can see.

Measured in the running app before the fix: a correct dark ground, correct
sidebar, correct Prism tokens — and every heading, the link, the blockquote
rule, the list marker and the checkbox still painting the **paper** values.
12 of 28 assertions. The mirror is therefore repeated verbatim inside
`body.dark`; it is not a duplicate, and deleting it reproduces the bug exactly
(see the sabotage run below).

## Two code mappings in this repo, on purpose

`midori.css` takes the **Obsidian** role mapping — keyword purple, string olive,
function indigo, property mint, number ochre, operator wine — copied from
`obsidian/theme.css`, which maps each role to the ANSI slot its terminal
highlighter would use so a fence matches Ghostty.

It deliberately does **not** take `vscode/midori-theme`'s mapping, which puts
keywords on indigo, functions on ochre and types on wine, and darkens every hex
for editor contrast. That set is tuned for reading code all day. MarkText is a
markdown editor, and a fence here should read like a fence in Obsidian.

Prism's token *classes* are grouped more coarsely than those roles, so the
class → role mapping in the stylesheet is new work, not copied. Two places it
splits a group Prism ships joined, and the reasons are in the file.

## Two deliberate departures from `obsidian/theme.css`

**All six heading levels are one colour.** Obsidian steps them down — ink, ink,
muted, mythic, mythic, faint — so depth reads as a fade. Here that made h3 and
h6 look washed out beside their neighbours; size and weight already carry the
hierarchy. `--midori-mythic` is still defined in the token block if the ramp is
ever wanted back, and the old values are in a comment beside the new ones.

**The active tab is the same sheet as the bar behind it.** Measured on Cadmium
Light: `.title-bar-editor-bg` painted `#f3f1eb` and the tab painted `#faf9f6`,
so an open tab read as a white chip floating on warm paper. The sage underline
is now the only thing marking it active.

That one needs `!important`, and a plain rule was tried first and lost. The
shipped declaration is `.tabs-container > li.active[data-v-f2591453]` — Vue's
scoped-style attribute makes it (0,3,0), so a hand-written
`.tabs-container > li.active` at (0,2,0) never applies however late it sits in
`<head>`. **Do not write the `data-v` hash into a selector**; it is a build
artefact and changes every release. Retargeting `--itemBgColor` would be the
tidier lever and is the wrong one — it also paints the search match-count chip,
`.side-bar .left-c` and the active drop target.

## Fonts

MarkText exposes an editor font and a code font in Preferences and no heading
font, so the stylesheet sets headings only:

| | family | where |
|---|---|---|
| Prose | M PLUS 1p | Preferences → General → Editor font family |
| Code | M PLUS 1 Code | Preferences → General → Code font family |
| Headings | Spectral | `midori.css` |

Stock Spectral, **not** the metric-normalised `Midori Display` alias
`obsidian/theme.css` uses. That alias exists to hold a 24px baseline lattice;
MarkText has no such lattice, and normalised metrics are what break
browser-drawn carets and selection boxes.

## Verified, and how

`tests/check_rendered_marktext.py` reads computed styles out of a **running**
MarkText over CDP and compares them to the palette. It is not in `tests/lint.sh`
— it imports `websocket` and needs a live app, the same split as the Obsidian
rendered checks.

```sh
python3 -m venv /tmp/cdpenv && /tmp/cdpenv/bin/pip install websocket-client
/Applications/MarkText.app/Contents/MacOS/MarkText \
  --user-data-dir=/tmp/mt-sandbox --remote-debugging-port=9333 some-sample.md &
/tmp/cdpenv/bin/python tests/check_rendered_marktext.py
```

**Always `--user-data-dir`.** A sandboxed data directory gets its own
single-instance lock — `setupEnvironment()` calls `app.setPath("userData", …)`
before `requestSingleInstanceLock()` — so this runs alongside your real MarkText
without touching `~/Library/Application Support/marktext`.

Results on the sample document, 28 colour assertions per mode:

| | light | dark |
|---|---|---|
| assertions checked | 31 | 31 |
| mismatched | 0 | 0 |
| selectors matching nothing | 0 | 0 |

A selector that matches nothing is a **failure**, not a silent pass: a rule that
never fires is indistinguishable from one that fired and agreed, and this repo
has shipped that mistake before. The checker prints the match count for every
probe and refuses to pass with fewer than 20 assertions.

**Sabotage proofs**, run on scratch copies, never on the shipped file:

| broken | checker said |
|---|---|
| `body.dark` kebab mirror deleted | 12 mismatches: `body text`, `h1`–`h6`, `link`, `blockquote rule`, `blockquote text`, `list marker`, `checked box` — Prism tokens and both grounds still green |
| `--linkColor` → wine, inline-code rule deleted | `MISMATCH link`, `MISMATCH inline code fg`, exit 1 |
| `--h3Color` fade restored, tab `!important` dropped | `MISMATCH h3`, `MISMATCH active tab`, exit 1 |

The guard fails on the thing it guards, and names it.

**Two harness bugs worth recording**, because each produced a result that was a
lie about something other than the stylesheet:

*MarkText does not exit on `SIGTERM`.* A relaunch after a plain `pkill` lost the
single-instance lock and exited silently, the old instance kept serving port
9333, and the checker cheerfully graded the *previous* stylesheet. The only
visible tell was the byte count of `#custom-styles`, which the checker now
prints on every run. Kill with `SIGKILL` and wait for the port to close.

*MarkText restores a modified buffer across launches.* A stray keystroke during
one relaunch put a leading space on line 1 of the sample — which turns
`# Heading` into a paragraph. The file on disk stayed byte-identical the whole
time, so nothing in the repo looked wrong; the `h1` simply stopped existing in
the DOM. Deleting `editorStates`, `Local Storage`, `Session Storage` and
`dataCenter.json` was **not** enough. Discard the whole `--user-data-dir` and
re-copy the sample between runs. This is also why a selector matching nothing is
a hard failure: that is the only signal this failure mode gives you.

## Applying it from a script

`apply-marktext.sh` writes `customCss` into
`~/Library/Application Support/marktext/preferences.json`.

It **refuses to run while MarkText is open.** MarkText keeps that file through
`electron-store` and rewrites it on every preference change, so an edit made
underneath a running app is a race you lose silently. It also writes a
timestamped backup beside the original before touching it.

## Not wired into `install.sh`

Deliberately. `tests/dryrun-installers.sh` proves the per-target installers left
real user data untouched, by checksum; adding a target to `install.sh` without
adding it there weakens that guarantee for everything else in the file. Wiring
it up is a separate change that should land with its dry-run coverage.

## Version

Read against MarkText **0.20.0** (`app.asar`, Electron 42.1.0, Chromium 148).
Everything above about `vShow: false`, the frozen theme arrays, the injection
order and the two variable families is a fact about that build. The colours are
variables and will survive; the four `!important` chrome patches are aimed at
literals in Cadmium Dark and should be re-checked after a MarkText update.
