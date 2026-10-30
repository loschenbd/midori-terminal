# Midori for SilverBullet

Paper and Night for [SilverBullet](https://silverbullet.md) 2.12.0, as one
stylesheet. 558 lines, 178 declarations, verified against a running instance at
86 assertions across both modes.

| file | what it is |
|---|---|
| `midori.css` | the theme |
| `wrap-midori.sh` | wraps it for either install route; writes to stdout only |
| `dev-harness.sh` | throwaway server + browser + staged page, for verification |
| `../tests/check_rendered_silverbullet.py` | grades a running instance |
| `../tests/sabotage-silverbullet.sh` | breaks things, requires the checker to notice |

## This file is load-bearing: a live install reads it from its path

As of 2026-10-06 the theme is wired into the SilverBullet install on this
machine, with Ben's approval. `silverbullet-hub` embeds **this very path** —
`~/Projects/midori-terminal/silverbullet/midori.css` — as each space's
`headHtml`, read at build time. CFA and tokentrail are themed.

That has three consequences:

- **Do not move or rename `midori.css` casually.** The installer resolves it
  by path. The path is configurable there (`SBHUB_THEME_CSS`), so the
  stylesheet is swappable rather than hard-wired — but the default points
  here, and moving the file without updating that variable breaks the next
  `sb-theme` run.
- **Editing it does not change anything live.** The stylesheet is copied into
  each space's config at build time. Someone has to run `sb-theme`, which
  re-applies it to every out-of-date space. `sb-theme --off` removes it.
- **A bad commit here reaches real spaces** the next time anyone runs
  `sb-theme`, and those spaces are client project folders. The truncation
  guards below are not pedantry any more.
- **Existing spaces do not lose their theme if this file disappears**, because
  `headHtml` is stored in each space's `spaces.json` entry. Losing the file
  breaks the next `sb-theme` run and any newly created space, not the spaces
  that are already themed.

`sb-theme` lives in the silverbullet-hub repo and is that session's to run.
Nothing in *this* repo should drive it.

**Nothing in this directory installs anything**, and that is still deliberate:
`wrap-midori.sh` renders to stdout, `dev-harness.sh` builds its own throwaway
space. Neither knows the path to a real space, and neither should learn one.

## Two sequences this stylesheet may never contain

Each install route wraps the whole file in something, and each wrapper has a
character sequence that ends it early. Both failures are silent — the page
renders, the markup parses, the theme installs, and only the rules below the
cut are missing.

| route | wrapper | forbidden |
|---|---|---|
| space-style | a fenced code block | ` ``` ` |
| headHtml | a `<style>` element | `</style` |

Both are checked by `wrap-midori.sh` before it emits anything, and by
`tests/check_style_literals.py` in `tests/lint.sh` on every commit. The
backtick case has already happened once: a comment in `midori.css` that named
the block type with a three-backtick fence truncated the installed stylesheet
at line 33 of just over 400. silverbullet-hub additionally refuses CSS
containing `</style` at install time.

A CSS *comment* is the realistic way to trip either one — a stylesheet that
documents its own install route will want to write both sequences. That is not
a hypothetical: it has now happened three times in this file, most recently in
the comment introducing the sentinel below, which explained the hazard by
quoting it. Describe the sequences; do not write them.

### The completeness sentinel

The guards above stop a truncated file from being *shipped*. They do not help a
reader asking "is the copy I just read whole?" — and neither does an empty-file
check or a minimum length, because the realistic failure is
truncated-but-nonempty: the raw-token blocks survive, the semantic mapping does
not, and the result is a half-themed space with nothing logged.

So the last non-blank line of `midori.css` is a fixed string:

```
/* END midori.css -- if this line is missing, the file was truncated. */
```

That turns "did the whole stylesheet arrive" into a question with an exact
answer rather than a guess at a plausible size. `tests/check_style_literals.py`
asserts it on every commit, and anything reading the file by path can assert the
same one line. Sabotage-proved: truncating the file at the semantic block leaves
8,893 bytes of perfectly valid CSS, and the check rejects it.

## A SilverBullet space is a project folder

SilverBullet's documented theming route is a `space-style` fenced code block in
a page *of the space*. A space is a directory of markdown files, and in the
setup this machine is heading towards, that directory is a real project repo
(`~/Projects/<project>`). Installing the theme the documented way therefore
means **writing a markdown page into a working repository**.

So `wrap-midori.sh` renders to stdout and stops. You decide where it goes.
`dev-harness.sh` builds its own space out of a staged sample page in a temp
directory and never touches anything else. Neither script knows the path to any
real space, and neither should learn one.

## The two install routes

```sh
sh silverbullet/wrap-midori.sh --space-style > "Midori Theme.md"   # a page
sh silverbullet/wrap-midori.sh --head-html                          # a JSON string
```

### space-style

The client runs `index.objects("space-style")` across the whole space, orders
the results by `priority` **descending**, wraps each in its own `<style>`, and
assigns the lot to `document.getElementById("custom-styles").innerHTML`. That
div is the last child of `<body>`, after `main.css` in `<head>`, so these rules
win equal-specificity ties against everything SilverBullet ships.

Two things about that ordering are worth knowing:

- **Higher `priority` means lower cascade precedence.** Descending order puts
  the highest priority *first* in the document, and CSS resolves
  equal-specificity ties by taking the *last* one. The name reads like
  importance; it behaves like load order, matching `space-lua`.
- **A stock space already has one `space-style` block.** The bundled Library
  ships `.sb-video-embed { border: 0 !important }`. Harmless, but "there are no
  other blocks" is not true of a fresh space.

### headHtml

A per-space `headHtml` string in `spaces.json`, injected into the editor page's
`<head>`. Measured on the served HTML: `main.css` is at line 27 and the
injected `<style>` at line 55, so it also beats stock rules on order — but it
loses to any `space-style` block, which lands later still.

Verified: the stylesheet works as a raw `<style>` in `headHtml`, 86/86
assertions, both modes.

### Which to choose

| | space-style | headHtml |
|---|---|---|
| writes into the space folder | **yes, a page** | no |
| survives a space being re-created | yes, it is in the space | only if the config writes it again |
| themes plug panels rendered in an iframe | yes | no |
| themes the tree / mentions sidebars | yes | yes |
| themes `/.dashboard` and the login page | no | no |

If a tool provisions spaces and may not write pages into them, `headHtml` is
the route. That is the situation here.

## What the panel-iframe row actually means

Reading SilverBullet's source, the conclusion looks obvious: `panelStyles()`
builds panel documents from `components.css` plus the collected space styles,
an `<iframe srcdoc>` does not inherit its parent's stylesheets, therefore
`headHtml` cannot theme panels and `space-style` can.

Measured, **stock SilverBullet 2.12.0 opens no panel iframe at all.** After
running each of `Navigate: Tree`, `Navigate: Mentions` and
`Navigate: Linked Mentions`, `document.querySelectorAll('iframe').length` is 0
and all four panel slots (`lhs`, `rhs`, `bhs`, `modal`) are null. Those
sidebars are `.sb-nav-root` elements in the main document, and they are themed
under both routes — checked under `headHtml`: `.sb-nav-root` paints `#161513`
via `--panel-background-color`, its text `#ebe8e2`, its font Spectral, and
`.sb-nav-title` sage.

The iframe path is reached only by a plug calling `editor.showPanel`. For those
and only those, the route matters.

## Font weights this theme needs

The stylesheet names three families and assumes a local install. Under hub
delivery they come from Google Fonts instead, so the served weights have to
cover what the theme asks for.

| family | used for | weights needed | on Google Fonts |
|---|---|---|---|
| Spectral | `--ui-font`, headings, chrome | 400, **600**, italic 400 | served; max is 800 |
| M PLUS 1p | `--editor-font` (prose) | 400, **500**, 700 | served |
| M PLUS 1 Code | code | 400, 700 | both served |

Group 5 of `midori.css` caps every weight at the Midori scale — sans prose
500, serif headings and chrome 600, nothing at 700 or above — so what the
theme needs is no longer what SilverBullet's own CSS asks for. The 700 in the
M PLUS 1p row is still required: `.sb-hr` is deliberately left at stock bold.

### A correction: this section used to say 900 was required

It said "the 900 is the one that bites", with `.sb-strong { font-weight: 900 }`
quoted as the reason, and on the strength of it the hub added `;900` to the
M PLUS 1p axis in `FONTS_URL`. **That was wrong, and it made the rendering
worse rather than better.**

What was true: `.sb-strong` really is 900 in SilverBullet 2.12.0, it really is
the rule for `**bold**`, and 900 really is a distinct face — measured at 18px
over a 22-character string, M PLUS 1p renders 700 at 196.0px and 900 at
207.3px, 5.8% wider. Every measurement in the old section holds.

What was wrong was the inference drawn from them. Reading a stock rule as a
*requirement* assumes the application's design decisions are ours, and they
are not: the Midori scale comes from benjaminloschen.com, where `<strong>`
resolves to 500 in sans prose and 600 in serif, and where 300 and 700 were
deleted outright as unreachable. Against a 400 body, 900 is an 11.1% advance
increase where the design language asks for 2.0%. Before the hub served a real
900, bold rendered as a browser-synthesised 700 — too heavy, but an
approximation. Adding the face replaced it with a faithful black, which is
why the defect became visible enough to report.

This is the repo's own warning about measurements, in its narrowest form: the
numbers were right for the whole of the time the conclusion beside them was
wrong. Nothing here requests 900 any more, so that axis value is dead weight
on every page load until the hub drops it.

### Why `.sb-keyword` is still 700

Capping it at 600 would be consistent, but `M PLUS 1 Code` is served at
`wght@400;700`. Two discrete values from the css2 API are two static faces,
not a variable range, so a 600 request there synthesises from 400 rather than
resolving — worse than an honest 700. Capping it needs the Code axis changed
to `400;600` in the hub first. The rendered check asserts the 700 so that
changing it is a decision rather than a drift.

**If you add or rename a family or a weight here, the hub's `FONTS_URL` in
`lib/sbhub/theme.py` has to change to match.** Tell that session.

## Phone overrides

Hub delivery appends a small stylesheet after this one: under
`max-width: 600px` it sets `#sb-main .cm-editor` to 16px and
`#sb-top .main .inner` to 22px.

Neither disturbs the measure, and the second is the reason `--editor-width` is
an absolute length. It is consumed as `max-width` by the top bar as well as the
text column; at 22px an em-based 33.726em would resolve to 742px there. A px
value is immune. And at a viewport of 600px or less the 647px max-width never
binds at all, so on a phone the column is simply the viewport — which is the
right answer there.

## Verifying a change

```sh
sh silverbullet/dev-harness.sh /path/to/silverbullet
python3 tests/check_rendered_silverbullet.py http://127.0.0.1:3099/ --cdp 9333
```

Needs a `silverbullet` binary (not vendored), a Chromium at `$BROWSER_BIN`
(defaults to Vivaldi), and `websocket-client`. The harness provisions a
throwaway data folder, installs the theme as a `space-style` page, and launches
a headless browser on a profile created seconds earlier.

Deliberately **not** in `tests/lint.sh`: it needs a live server and a live
browser. What lint does cover is `tests/check_style_literals.py`, below.

### Results

102 assertions, 51 per mode, 0 failures, via both install routes.

| | light | dark |
|---|---|---|
| space-style | 51/51 | 51/51 |
| headHtml | 51/51 | 51/51 |

(43 per mode before group 5, plus the eight font-weight probes. One of those
asserts `.sb-keyword` at its stock 700 rather than a Midori value, so that
changing it later has to be deliberate.)

### Four things the checker refuses to do

Each one has already produced a confident all-clear against nothing, here or in
the MarkText target:

- **Grade a window it did not open.** It closes every page target before
  opening one. A server restart leaves the previous client running and still
  answering CDP; graded stale, this checker once reported "58 bytes, no midori
  token" for a theme that was installed and working.
- **Grade a short viewport.** CodeMirror builds DOM only for lines in view. At
  the headless default 800×600 the sample page renders 26 of its 91 lines, so
  every probe into a fenced code block finds nothing. The viewport is forced to
  1440×4200 and the line count is printed; below `MIN_LINES` the run is
  refused.
- **Pass on a selector that matched nothing.** A zero-match probe is a failure,
  not a skip, and every probe prints its match count.
- **Assume the theme is installed.** It reports which route it found and how
  many bytes of CSS, so a truncated install is visible rather than inferred.

### Sabotage proofs

`sh tests/sabotage-silverbullet.sh /path/to/silverbullet [case]` breaks things
on **scratch copies** and requires the checker to fail naming what broke. The
real stylesheet is read-only throughout and its md5 is printed at the end.

| case | what it breaks | result |
|---|---|---|
| `a` | semantic block loses its `html[data-theme]` branch | 29 named failures, all `dark/*`; light untouched |
| `b` | light `--midori-sage` repointed to `#808080` | 5 named failures, all `light/*` sage probes |
| `c` | the four admonition rules deleted | 8 named failures, 4 per mode |
| `d` | stylesheet truncated mid-file | 86 named failures |
| `weight` | heading weight rule drops `.cm-line`, falling to (1,2,0) | 6 named failures: h1/h2/h3 weight read 700 in both modes |
| `lines` | checker pointed at a 4-line page | refuses the run: "only 5 cm-lines rendered (need >= 60)" |
| `stale` | extra page targets left open | closes 3, grades 1, prints the count |

Case `d` is the one worth dwelling on. Truncating the stylesheet left the
`--midori-` token check **passing**, because the raw-token block survives the
cut. Only the probes caught it. An install check that asks "is the theme there"
cannot tell you "is all of it there".

Case `weight` is the one that nearly shipped. Group 1 sets heading
`font-family` with `#sb-main .cm-editor .sb-line-h1`, (1,2,0), and that works,
because the stock heading rule declares no `font-family` to contest. It does
declare `font-weight`, at `#sb-main .cm-editor .cm-line.sb-line-h1`, (1,3,0).
Copying group 1's selector for the weight rule produces something that reads
exactly like the rule above it and changes nothing. That is this repo's
recorded failure mode — "guard tests passed while the rule they named lost a
specificity contest and did nothing" — so the sabotage exists to prove the
probe catches it. It does: headings render 700 and all six probes name it.

### The lint check

`tests/check_style_literals.py` runs in `tests/lint.sh` and fails on a triple
backtick anywhere in `silverbullet/*.css`, because one would end a
`space-style` fence and silently truncate the installed theme. It also fails if
it finds no `silverbullet/*.css` at all — scanning nothing is not the same as
finding nothing wrong. Both halves are sabotage-proved.

## Traps found along the way

**`html[data-theme=dark]` beats a plain `html` block.** This cost 29 probes.
The two selectors target the same element, so redefining a raw palette token
for dark genuinely does reach every consumer — but only if the consumer wins.
`html[data-theme=dark]` is (0,1,1) and `html` is (0,0,1), so for each of the
142 properties SilverBullet redefines in its own dark block, its value beats
ours and the carefully redefined token is never read. The fix is the selector
list `html, html[data-theme="dark"]` on the semantic block: it matches via the
(0,1,1) branch in dark, ties, and wins on order. Light mode passed 43/43
throughout, which is what made it look finished.

**A client's local index can hold a zero-byte copy of a page, and
`Space: Reindex` does not repair it.** The server's own listing (`GET /.fs`)
reported 28,522 bytes for the stylesheet page while the client's `allPages`
entry still said `size: 0`, so the `space-style` query returned nothing and the
theme simply was not installed. Restarting the server does not fix it and
neither does reloading the tab — the index lives in the browser's IndexedDB.
Wipe the browser profile. Comparing `/.fs` against the client's own listing is
the cheap tell.

**`document.fonts.check()` returns `true` for fonts that do not exist.** It
reported `true` for `ThisFontDoesNotExist`. To test availability, measure a
string twice with two different generic fallbacks (`"X", serif` and
`"X", monospace`): a resolved family gives the same width both times, a missing
one tracks the fallback and differs.

**The `access` enum is `none | read | write`.** Not `full`, which the server
rejects at boot with `unknown variant`.

**Headless screenshots tile** if `Emulation.setDeviceMetricsOverride` is
re-applied between captures. Launch the browser with `--window-size` and
capture with no override.

## Two defects in SilverBullet 2.12.0 that this theme fixes

**`--editor-text-color` is read with no fallback and declared nowhere.**
`.sb-comment-resolve:hover` and
`#sb-main .cm-editor .sb-lua-bottom-widget blockquote` both say
`color: var(--editor-text-color)`. An undeclared custom property makes the
declaration invalid at computed-value time, which for `color` means it computes
to `inherit` — so both rules silently do nothing today. Declaring the property
makes them work.

**Admonition colours sit outside the token set.** `--admonition-color` is
declared per type on the type's own selector, as four saturated values
(`#00b8d4`, `#ff9100`, `#d50000`, `#00c853`). A theme can redefine all 153
documented properties and still leave admonitions cyan — this one did, until
the rendered check caught it.

Five further properties are read only as `var()` fallbacks and are brought onto
the palette here: `--editor-monospace-font`, `--editor-error-color`,
`--editor-accent-muted`, and the `--editor-code-{deleted,inserted}-{color,bg}`
pairs.

## Departures from stock

| | stock | here | why |
|---|---|---|---|
| editor font | iA-Mono, everything | M PLUS 1p prose, Spectral headings, M PLUS 1 Code code | the Midori writing surface is proportional; matches `obsidian/theme.css` |
| `--editor-width` | 800px | 647px | 70 characters × 0.4818em average advance × 18px, + 40px border-box padding |
| syntax marks | dark red `#650007` | sage | structure, not error |
| keywords | bold, no colour | bold, purple | completes the Midori code roles |
| `.sb-punctuation` | no rule | code-punctuation | same |
| admonitions | four saturated hues | indigo / ochre / wine / olive | the palette is closed |

Two consequences of the font change, recorded rather than fixed:

- SilverBullet sets **no font-family for code anywhere**, because its editor
  font is already monospace. Changing `--editor-font` takes fenced code with
  it, which is why the stylesheet has an explicit monospace rule for code.
- `--editor-column: 1ch` and `--blockquote-step: 2ch` are declared on
  `.cm-content`. `ch` is the advance of `0`: iA-Mono 0.600em → 10.80px at 18px,
  M PLUS 1p 0.620em → 11.16px. The indent grid moves +0.36px per column and the
  blockquote pitch 21.60px → 22.32px. Left alone; pinning it would mean a
  (1,2,0) rule reaching into SilverBullet's layout for a third of a pixel.

And one thing deliberately *not* carried over: `obsidian/theme.css` sets
`caret-color: transparent` and draws its own caret, because the native Chromium
caret sits ~3px low against Spectral. That fix needs the companion
`plugins/midori-caret` to put a caret back, and SilverBullet has no plugin here
to do it — hiding the native caret would leave the writing surface with none.

## Not wired into install.sh

`install.sh` orchestrates per-target scripts that copy files into known
locations. SilverBullet has no such location: the theme's destination is either
a page inside a space, or a JSON field in a server config. Both are decisions
about a specific running server, not about this machine, and the space folders
are live project repos.

That hook now exists, and it is **not** here. silverbullet-hub's
`space_config()` embeds this stylesheet as per-space `headHtml`, and `sb-theme`
re-applies it. Applying the theme is that repo's job; this one's job is to keep
the stylesheet correct at its path.
