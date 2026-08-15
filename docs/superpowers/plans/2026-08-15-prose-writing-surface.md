# Prose Writing Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Midori theme's writing surface onto the settings that
survived evidence review — a measure inside the preference band, a vertical grid
that follows the reader's own text size instead of assuming one, and a heading
ladder whose *visual* steps match its em steps — then fold the writing mode into
this repo so it ships, and take ownership of the paragraph rhythm currently held
by a third-party plugin that fights the grid.

**Architecture:** Most changes are CSS custom properties in
`obsidian/theme.css` plus a static test that reads the stylesheet back and
checks the number in the units the research uses (characters per line, ratio of
leading to base size, x-height). One existing plugin moves into the repo
unchanged in behaviour. The boundary throughout: **a plugin owns the element it
creates; the theme owns how the app's chrome reacts.** The one risky change —
making the 24px grid scale — is gated behind a rendered measurement, and reverts
to a fixed grid with a documented supported range if that measurement
disagrees.

**Tech Stack:** CSS custom properties; Python 3 (stdlib only) for the static
tests, wired into `tests/lint.sh`; a generated HTML harness driven through the
browser for the rendered checks; `fontTools` (already in `obsidian/.fontenv`)
only for re-deriving font constants, never at test time.

## Global Constraints

- **Evidence source of truth:** `docs/superpowers/specs/2026-08-15-prose-typography-evidence.md`. Do not introduce a number this plan does not trace to it.
- **Design source of truth:** `docs/superpowers/specs/2026-08-15-prose-writing-experience-design.md`, which records what was cut and why. Do not re-add a declined item.
- **The reader's real base size is 14px** (`baseFontSize: 14` in the live vault), not the 15–16 the theme's own comment claims. Every number below is stated for the base it applies to, and every mechanism follows the slider rather than assuming a value.
- **A plugin owns the element it creates and styles only that element; the theme owns how the app's chrome reacts.** Same boundary `midori-timer` uses.
- **Every `body.zen-mode` rule that mentions `--header-height` must also require `.show-view-header`** — app.css sets `display: none` on `.view-header` when the setting is off.
- **Nothing enters the writing surface unbidden.** No new element, no new mark, no animation on the page. Every change here is a property of something already on screen.
- **Font constants, measured from `fonts/*.ttf` with a `BoundsPen`, not `OS/2`:** M PLUS 1p x-height `0.520`em, cap `0.730`em, average prose advance `0.4818`em. Spectral x-height `0.450`em, cap `0.660`em, average advance `0.4352`em. Re-derive with `obsidian/.fontenv/bin/python3 tests/measure_prose_type.py`.
- **Characters per line = `N ÷ 0.4818`** where the measure is `calc(var(--font-text-size) * N)`. This is the only conversion between a stylesheet number and the research's unit.
- **Target band: 55–75 cpl**, preference side of the speed/preference split. 66 cpl = `N 32`, 70 cpl = `N 34`, 75 cpl = `N 36`.
- **Never express `--file-line-width` in `em`.** app.css consumes it on `.cm-line`, which is also the heading element; see "The schema this plan works with".
- **Leading floor: CSS 1.2** (measured harm floor). **Policy floor: 1.5** (WCAG 1.4.8, not an experimental result). Aim ≥ 1.5.
- **A backtick inside an injected stylesheet template literal ends it** — not applicable to `theme.css`, but `tests/lint.sh` must stay green including `tests/check_style_literals.py`.
- **Every change must be installed and re-verified** with `sh obsidian/install-obsidian.sh`, which fans out to all three vaults.
- **Commit after every task.** `sh tests/lint.sh` must be green before each commit.

---

## The schema this plan works with

Read out of Obsidian's own `app.css`, extracted from the installed app with
`python3 obsidian/dump-app-css.py <outdir>`. Not from documentation, and not
from a blog post. Re-run it after an Obsidian update before trusting any of the
below.

**The variables, with their real defaults:**

| variable | default | notes |
|---|---|---|
| `--font-text-size` | `16px` | Set **inline on `body`** by the app from `baseFontSize`, **clamped to 10–30**. The same code also sets `font-size` on `documentElement`, so `rem` tracks it too. |
| `--file-line-width` | `700px` | Consumed on **four** elements — see the trap below. |
| `--h1-size` … `--h6-size` | `1.618em`, `1.462`, `1.318`, `1.188`, `1.076`, `1em` | **Not** the ladder this plan originally assumed. |
| `--h1-font` … `--h6-font` | `inherit` | Exists. The theme currently reaches past it with element selectors. |
| `--h1-weight`, `--hN-style`, `--hN-variant`, `--hN-color` | various | 36 heading variables in total; the theme sets 6 of them. |
| `--inline-title-size` / `-font` / `-weight` | `var(--h1-*)` | The title **follows h1 for free** if h1 is set through its variables. |

**The units trap, which is real and would have shipped as a bug.** app.css
consumes `--file-line-width` as `max-width` on `.cm-sizer`, `.cm-content` **and
`.cm-line`**, all gated behind `.is-readable-line-width`:

```css
.markdown-source-view.mod-cm6.is-readable-line-width .cm-line { max-width: var(--file-line-width); }
```

`.cm-line` is also where headings live — `.HyperMD-header-1` sets
`font-size: var(--h1-size)` on the *same element*. A `max-width` in `em`
resolves against the element's **own** font-size, so an em measure makes
heading lines wider than body lines. Measured in a browser, at a 34em measure:

| | body line | h1 line | h4 line |
|---|---|---|---|
| `34em` | 544px | **880px** | **646px** |
| `calc(var(--font-text-size) * 34)` | 544px | 544px | 544px |

So the measure must be **`calc(var(--font-text-size) * N)`**, which resolves
numerically before it reaches the consuming element. `rem` would also work
today, but only because the app happens to set `documentElement`'s font-size —
an implementation detail found by reading minified JS, not a documented
contract. `--font-text-size` is documented; prefer it.

**Two consequences beyond the measure.** The `.is-readable-line-width` gate
means everything here is inert for a reader who has turned readable line length
off — correct, and not something to fight. And app.css uses the same variable
for `.document-search`, so the find bar stays aligned to the column for free.

**The direction of em-resolution differs by consuming property**, which is why
the same reasoning does not condemn Task 4. For `max-width` (`--file-line-width`)
an em resolves against the consuming element's **own** font-size — the trap
above. For `font-size` itself (`--h1-size`…`--h6-size`, `--inline-title-size`)
an em resolves against the **parent's** font-size, and a heading's parent is at
the base size in both panes. Heading sizes in em are therefore correct and
stable; the measure in em is not. Both follow from custom properties inheriting
as unresolved token streams — Obsidian ships no `@property` registrations, so
nothing absolutises early.

**One accepted cost of the `calc`.** app.css deliberately overrides the editor
font-size in sidebars, hover popovers and footnotes
(`--sidebar-markdown-font-size`, `--popover-font-size`, `--footnote-size`). An
em measure would have adapted to those; a `calc` against `--font-text-size`
hands them the same pixel width, which is a longer measure in characters where
the text is smaller. That is what the 700px default already did, so it is not a
regression — and those columns are usually constrained by their container before
`max-width` binds.

**What no stylesheet can beat.** app.js writes these as *inline* styles on
`document.body` from vault config: `--font-text-size`, `--font-text-override`,
`--font-interface-override`, `--font-monospace-override`, `--font-print-override`,
`--accent-h/s/l`, `--text-on-accent`, `--zoom-factor`, `--indent-size`. A theme
declaration loses to all of them at any specificity, without `!important`. This
plan only ever *reads* `--font-text-size`, which is the supported direction.

It also explains the `!important` the theme currently carries on `.inline-title`:
app.css resolves the body face as
`--font-text: var(--font-text-override), var(--font-text-theme), var(--font-default)`,
so a per-vault Appearance font (inline `--font-text-override`) beats a theme's
`--font-text-theme`. The heading chain is separate — `--inline-title-font`
defaults to `var(--h1-font)` — which is why Task 4b expects the `!important` to
become unnecessary. Note the real gate while editing there:
`.inline-title:not([data-level])` is **(0,2,0)**, so a bare `.inline-title` rule
at (0,1,0) loses to app.css regardless.

**Two more facts worth having on hand.** Theme CSS is appended to the *end* of
`<head>`, while CodeMirror's own injected rules go in at `head.firstChild` — so
equal specificity beats CM6 without `!important`, though not app.css. And there
is **no published stability or deprecation policy** for either class names or
CSS variables; Obsidian's own guidelines name broken selectors as the most
common theme-maintenance failure. `.cm-sizer` and `.cm-contentContainer` are
Obsidian-injected wrappers that do not exist in upstream CodeMirror 6 at all, so
the element this plan's measure hangs off carries no guarantee from either
vendor. Re-run `dump-app-css.py` after an update; that is the whole mitigation.

## File Structure

| File | Responsibility |
|---|---|
| `obsidian/theme.css` (modify) | All CSS changes. Measure at ~line 32 in the root variable block; `--midori-row` beside it; dot grid at 402; line-height rules at 583, 1118, 1147–1149, 1173–1179, 1357–1458; heading sizes in a new block beside the existing heading colours at 1603. |
| `tests/test_prose_typography.py` (create) | Static guardrails. Parses `theme.css`, converts to cpl and leading ratios across the app's whole 10–30px base range, asserts the bands. Stdlib only so it runs in `lint.sh` and CI. |
| `tests/prose_harness.py` (create) | Generates an HTML page from the *real* `theme.css` for rendered checks. Not run by lint; invoked by hand in verification steps. |
| `tests/lint.sh` (modify) | Wire in the new test beside the existing `midori-timer unit tests` block. |
| `tests/measure_prose_type.py` (existing) | Already committed. Re-derives the font constants. Unchanged. |
| `docs/superpowers/specs/2026-08-15-prose-typography-evidence.md` (existing) | Evidence. Unchanged by this plan. |
| `README.md` (modify) | One findings bullet per shipped change, in the established voice. |
| `obsidian/plugins/zen-toggle/` (create) | The mode's toggle, moved in from the vault: the status-bar dot, its stylesheet, the `body.zen-mode` class, the command. Owns nothing else. |
| `obsidian/install-obsidian.sh` (modify) | Plugin roster comment; renaming the superseded `zen-mode.css` snippet aside. |
| `obsidian/dump-app-css.py` (existing) | Extracts Obsidian's `app.css`/`app.js` from the asar. Unchanged; used to re-check the schema after an app update. |
| `obsidian/manifest.json` (modify) | Version bump at the end. |

---

### Task 1: The measure

The one setting currently outside every band anyone has proposed: Obsidian's
default 700px column with M PLUS 1p is ~91 cpl at a 16px base. Expressed as a
multiple of `--font-text-size` it stays inside the band when the reader changes
their text size, which a px constant does not — and unlike an `em`, it is not
re-resolved against the font-size of whatever element consumes it.

**Files:**
- Create: `tests/test_prose_typography.py`
- Modify: `obsidian/theme.css` (root variable block, ~line 32)
- Modify: `tests/lint.sh` (beside the `midori-timer unit tests` block, ~line 58)

**Interfaces:**
- Produces: `--file-line-width` as `calc(var(--font-text-size) * N)`; the helper `theme_var(name)` and constant `AVG_ADVANCE_EM = 0.4818` in `tests/test_prose_typography.py`, both consumed by Tasks 2 and 3.

- [ ] **Step 1: Write the failing test**

Create `tests/test_prose_typography.py`:

```python
#!/usr/bin/env python3
"""The writing surface, checked in the units the research is stated in.

A stylesheet says "34em" and "24px". The evidence says "characters per line"
and "ratio to base size". This converts, so a change that looks harmless in
CSS cannot quietly leave the band. Evidence and provenance for every number:
docs/superpowers/specs/2026-08-15-prose-typography-evidence.md

Font constants are measured from the real outlines with a BoundsPen (NOT from
OS/2, which is designer-typed metadata). They are inlined rather than read from
the TTFs so this runs on a stdlib interpreter in lint and CI; re-derive with
    obsidian/.fontenv/bin/python3 tests/measure_prose_type.py
"""

import math
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
THEME = (REPO / "obsidian" / "theme.css").read_text()

AVG_ADVANCE_EM = 0.4818     # M PLUS 1p, averaged over a prose sample
X_MPLUS = 0.520             # x-height, em
X_SPECTRAL = 0.450

# app.js clamps baseFontSize to 10..30 (Math.clamp(e, 10, 30)), so this is the
# whole reachable range, not a range we chose.
BASES = tuple(range(10, 31))

FAIL = []


def ok(msg):
    print(f"  ok   {msg}")


def bad(msg):
    print(f"  FAIL {msg}")
    FAIL.append(msg)


def theme_var(name):
    """Last declared value of a custom property, as a string.

    NOT anchored to the start of a line: an earlier draft was, and it silently
    reported "not set" for every declaration that shared a line with another
    one — which reads as a missing variable rather than as a regex that cannot
    see it. A `var(--x)` USE cannot match here, because a use has no colon
    after the name.
    """
    hits = re.findall(rf"{re.escape(name)}\s*:\s*([^;]+);", THEME)
    return hits[-1].strip() if hits else None


def em_value(raw):
    m = re.fullmatch(r"([0-9.]+)em", (raw or "").strip())
    return float(m.group(1)) if m else None


def test_measure():
    """The measure, in characters, and in a unit that survives its consumers.

    app.css applies --file-line-width as max-width on .cm-line, and .cm-line is
    also the heading element (.HyperMD-header-1 sets font-size: var(--h1-size)
    on it). An em there resolves against the element's OWN font-size, so an em
    measure gives heading lines a wider column than body lines: measured, 34em
    is 544px on a body line and 880px on an h1. calc(var(--font-text-size) * N)
    resolves numerically before it reaches any consumer.
    """
    raw = theme_var("--file-line-width")
    if raw is None:
        bad("--file-line-width is not set; Obsidian's 700px default is ~91 cpl at 16px")
        return
    if em_value(raw) is not None:
        bad(f"--file-line-width is {raw!r}: an em measure is resolved against the "
            "font-size of .cm-line, which is 1.618em on a heading line")
        return
    m = re.fullmatch(r"calc\(\s*var\(--font-text-size\)\s*\*\s*([0-9.]+)\s*\)", raw)
    if not m:
        bad(f"--file-line-width is {raw!r}: expected "
            "calc(var(--font-text-size) * N), which both tracks the reader's "
            "text size and is immune to the consuming element's font-size")
        return
    cpl = float(m.group(1)) / AVG_ADVANCE_EM
    if 55.0 <= cpl <= 75.0:
        ok(f"measure {raw} = {cpl:.1f} characters per line, inside 55-75")
    else:
        bad(f"measure {raw} = {cpl:.1f} characters per line, outside 55-75")


if __name__ == "__main__":
    print("== prose typography ==")
    test_measure()
    print("prose typography: all green" if not FAIL else "prose typography: failures above")
    sys.exit(1 if FAIL else 0)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: FAIL — `--file-line-width is not set; Obsidian's 700px default is ~91 cpl at 16px`, exit 1.

- [ ] **Step 3: Build the comparison harness and pick the width**

Create `tests/prose_harness.py`:

```python
#!/usr/bin/env python3
"""Render real prose in the real theme, at several measures, for a look.

Loads obsidian/theme.css itself rather than a copy, so what is judged is what
ships. Writes to the path given as argv[1] (default ./prose.html) and expects
to be served over http, not opened as file:// — Chrome blocks font loading and
some CSS on file URLs.

    python3 tests/prose_harness.py /tmp/prose.html
    python3 -m http.server 8777 --directory /tmp
"""

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CSS = (REPO / "obsidian" / "theme.css").read_text()

PROSE = """<p>The question of how long a line of text should be is older than the
screen, and most of the answers in circulation were never measured at all. A
writer revising a paragraph moves through it differently than a reader meeting
it once: the eye returns to the line just finished, hops back to the start of
the sentence, and leaves again. Whether that pattern wants a shorter measure
than reading does is, as far as the literature goes, an open question.</p>
<p>What is not open is that the same stylesheet is a different size on every
panel it lands on. An angle is not a length, and a length is not a size until
something says how far away the reader is sitting.</p>"""

WIDTHS = ("calc(var(--font-text-size) * 32)",   # 66 cpl
          "calc(var(--font-text-size) * 34)",   # 70 cpl
          "calc(var(--font-text-size) * 36)",   # 75 cpl
          "700px")                             # today, ~91 cpl

def main():
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "prose.html")
    blocks = "\n".join(
        f'<section><h3>{w}</h3>'
        f'<div class="markdown-preview-view" style="--file-line-width:{w}">'
        f'<div class="markdown-preview-sizer">{PROSE}</div></div></section>'
        for w in WIDTHS
    )
    out.write_text(f"""<!doctype html><meta charset=utf-8><title>Measure</title>
<style>{CSS}
body {{ font-family: "Midori Text", system-ui, sans-serif; }}
section {{ margin: 0 0 48px; }}
section h3 {{ font: 12px ui-monospace, Menlo, monospace; color: #888; margin: 0 0 8px; }}
.markdown-preview-sizer {{ max-width: var(--file-line-width); }}
</style>
<button onclick="document.body.classList.toggle('theme-dark');
                 document.body.classList.toggle('theme-light')">night</button>
{blocks}
<script>document.body.classList.add('theme-light');</script>
""")
    print("wrote", out)

if __name__ == "__main__":
    main()
```

Run it, serve it, and look at all four at your real viewing distance:

```bash
python3 tests/prose_harness.py /tmp/claude-501/prose.html
python3 -m http.server 8777 --directory /tmp/claude-501
```

**This step ends in a decision, and it is Ben's, not the implementer's.** The
evidence supports the *band*, not a point inside it: reading speed favours the
long measure, preference favours the moderate one, and a writing surface takes
the preference side. `calc(var(--font-text-size) * 34)` (70 cpl) is the default
recommendation because it is the smallest change from today's ~91 that lands
inside the band. Record the
chosen value before continuing.

- [ ] **Step 4: Set the measure**

In `obsidian/theme.css`, in the root variable block that already holds
`--font-text-theme` (~line 32), add:

```css
  /* MEASURE, IN EM AND NOT PX, WHICH IS THE WHOLE POINT.

     Obsidian's default is 700px, which with "Midori Text" is ~91 characters
     per line at a 16px base and ~97 at 15px — outside every band anyone has
     proposed. The band itself has no experiment behind it (Spencer 1968
     asserts ~70; Rayner & Pollatsek deduce 52 from Tinker's PRINT data; no
     screen study produced the range), so this is not a correction toward a
     finding. It is the preference side of the one result that IS solid: longer
     lines are read faster, moderate lines are preferred, and subjective
     ratings do not track performance. A writing surface is chosen, sat at for
     hours, and not a speed-reading task.

     In em because characters-per-line depends on BOTH width and size: a px
     constant silently becomes a different measure the moment the reader moves
     Settings -> Appearance -> Font size, and this theme now ships to people
     whose slider is not where mine is (the app clamps it to 10-30px).

     NOT em, which is the version of this that looks right and is not. app.css
     applies this variable as max-width on .cm-line -- and .cm-line is also the
     heading element, carrying font-size: var(--h1-size). An em resolves
     against the element's OWN font-size, so an em measure hands heading lines
     a wider column than body lines: measured, 34em is 544px on a body line and
     880px on an h1. A calc against --font-text-size resolves numerically
     before it ever reaches a consumer. 34 / 0.4818 average advance = 70
     characters, at any base size. See
     docs/superpowers/specs/2026-08-15-prose-typography-evidence.md */
  --file-line-width: calc(var(--font-text-size) * 34);
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 tests/test_prose_typography.py`
Expected: PASS — `ok measure calc(var(--font-text-size) * 34) = 70.6 characters per line, inside 55-75`, exit 0.

- [ ] **Step 6: Wire it into lint**

In `tests/lint.sh`, after the `== midori-timer unit tests ==` block, add:

```sh
echo "== prose typography =="
if python3 tests/test_prose_typography.py; then :; else FAIL=1; fi
```

- [ ] **Step 7: Verify in the app**

```bash
sh tests/lint.sh
sh obsidian/install-obsidian.sh
```

Open a real note. Confirm: the column is narrower, the dot grid still runs edge
to edge (it is painted on the scroller, not the sizer, so it must be
unaffected), and nothing has moved vertically.

- [ ] **Step 8: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py tests/prose_harness.py tests/lint.sh
git commit -m "theme: set the measure in em, inside the preference band

Obsidian's 700px default is ~91 characters per line with Midori Text at
a 16px base. The 45-75 rule has no experiment behind it, so this is not
a correction toward a finding; it is the preference side of the real
speed/preference split. In em rather than px because cpl depends on both
width and size, and the theme now ships to readers whose text-size
slider is not where mine is."
```

---

### Task 2: `--midori-row` as the single source of truth

Twenty-odd rules hardcode `24px`, and so does the dot grid. Before the grid can
follow anything, it has to be one number. **This task changes no pixel** — it
is a pure refactor, and the rendered check exists to prove exactly that.

**Files:**
- Modify: `obsidian/theme.css` (root variable block; then every `line-height: 24px`, the `margin-block` multiples, and `background-size` at 402)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Consumes: `theme_var()` from Task 1.
- Produces: `--midori-row`, consumed by Tasks 3 and 4.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prose_typography.py`, and add `test_row_is_one_number()`
to the `__main__` block:

```python
def test_row_is_one_number():
    raw = theme_var("--midori-row")
    if raw is None:
        bad("--midori-row is not defined; the grid is still a literal in every rule")
        return
    ok(f"--midori-row = {raw}")

    # The refactor is only real if the literals are gone. Comments are stripped
    # first: the file explains the grid in prose and those mentions are fine.
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)
    stray = re.findall(r"line-height:\s*24px", body)
    if stray:
        bad(f"{len(stray)} rules still hardcode line-height: 24px")
    else:
        ok("no rule hardcodes line-height: 24px")

    if re.search(r"background-size:\s*24px\s+24px", body):
        bad("the dot grid still hardcodes 24px 24px")
    else:
        ok("the dot grid is expressed in --midori-row")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: FAIL — `--midori-row is not defined; the grid is still a literal in every rule`.

- [ ] **Step 3: Capture the before-state for the no-change check**

```bash
python3 tests/prose_harness.py /tmp/claude-501/prose.html
python3 -m http.server 8777 --directory /tmp/claude-501 &
```

In the browser, on the served page, record every line-box top in the first
block — this exact array is what Step 6 compares against:

```js
JSON.stringify([...document.querySelectorAll('.markdown-preview-sizer p')]
  .map(p => Math.round(p.getBoundingClientRect().top * 100) / 100))
```

- [ ] **Step 4: Define the row and replace the literals**

In the root variable block, above `--dotgrid-offset-y`:

```css
  /* THE GRID ROW. 24px at a 16px base is a leading of exactly 1.50 — above the
     CSS ~1.2 floor that Rello et al. actually measured (their harmful
     condition was CSS ~0.96; the "1.0" in that paper is Firefox's default of
     120%), and on WCAG 1.4.8's 1.5, which is a policy floor and not an
     experimental result. No study distinguishes 1.4 from 1.5 from 1.6, so this
     number is defensible rather than optimal, and it is not going to move on
     evidence. It moves, if at all, because the READER's base size moved. */
  --midori-row: 24px;
```

Then replace, throughout the file:
- every `line-height: 24px` → `line-height: var(--midori-row)`
- every `line-height: 48px` on a heading or the inline title → `line-height: calc(var(--midori-row) * 2)`
- `margin-block: 0 24px` → `margin-block: 0 var(--midori-row)`, and `margin-block: 24px 0` → `margin-block: var(--midori-row) 0`
- `background-size: 24px 24px` → `background-size: var(--midori-row) var(--midori-row)`

Leave every *prose mention* of 24px in the comments alone — they are the
explanation, and the test strips comments before looking.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 tests/test_prose_typography.py`
Expected: PASS on all three row assertions.

- [ ] **Step 6: Prove nothing moved**

Regenerate the harness, reload, and re-run the Step 3 snippet. **Every value
must be identical.** If any differs, a literal was replaced with the wrong
expression — find it before continuing; this task's entire value is that it is
a no-op.

- [ ] **Step 7: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "theme: name the 24px grid row --midori-row

Pure refactor, no rendered change: every line-box top in the harness is
identical before and after. The grid was a literal in twenty-odd rules
and in the dot-grid background-size, which made it impossible to change
in one place and impossible to make follow anything."
```

---

### Task 3: The row follows the reader's text size

The theme assumes a 15–16px base. At 18px the grid is 1.33 leading — above the
measured harm floor, under the WCAG policy floor — and the reader who did that
has no idea the theme had an opinion. **This is the change that matters for
shipping to other people**, and it is the risky one, because the dot grid's
vertical phase was measured against a 24px row.

**Files:**
- Modify: `obsidian/theme.css` (`--midori-row`, `--dotgrid-offset-y`)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Consumes: `--midori-row` (Task 2), `BASES`, `theme_var()`.
- Produces: a `--midori-row` that is a function of `--font-text-size`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prose_typography.py` and register in `__main__`:

```python
def row_px(base):
    """Mirror of the CSS: round(up, max(24px, base * 1.5), 1px)."""
    return max(24, math.ceil(base * 1.5))


def test_leading_holds_across_the_slider():
    raw = theme_var("--midori-row")
    if raw is None or "--font-text-size" not in raw:
        bad(f"--midori-row is {raw!r}: fixed, so leading falls below 1.5 "
            "as soon as the reader raises their text size")
        return
    # A LOCAL flag, not the global FAIL: an unrelated earlier failure must not
    # silently swallow this test's own ok line.
    bad_here = False
    worst = min(((base, row_px(base) / base) for base in BASES), key=lambda p: p[1])
    for base in BASES:
        ratio = row_px(base) / base
        if ratio < 1.5 - 1e-9:
            bad(f"base {base}px gives leading {ratio:.2f}, under the 1.5 policy floor")
            bad_here = True
    if not bad_here:
        ok(f"leading >= 1.5 across {BASES[0]}-{BASES[-1]}px "
           f"(worst {worst[1]:.2f} at {worst[0]}px)")


def test_row_stays_whole_pixels():
    """The guarantee is in the CSS, not in row_px().

    row_px() returns whole pixels by construction, so asserting on it proves
    nothing. What can actually regress is the stylesheet dropping the rounding
    — `max(24px, var(--font-text-size) * 1.5)` alone is 25.5px at a 17px base,
    and a fractional row puts the dot lattice on half pixels.
    """
    raw = theme_var("--midori-row") or ""
    if re.search(r"round\(\s*up\s*,.*,\s*1px\s*\)", raw):
        ok("the row is rounded up to whole pixels")
    else:
        bad(f"--midori-row is {raw!r}: no round(..., 1px), so a base size that "
            "is not a multiple of 2 gives a fractional row and blurs the dots")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: FAIL — `--midori-row is '24px': fixed, so leading falls below 1.5 as soon as the reader raises their text size`.

- [ ] **Step 3: Make the row a function of the base**

Replace the `--midori-row` declaration from Task 2 with:

```css
  /* Two declarations, and the first is the fallback: a build whose engine
     lacks CSS round() ignores the second and keeps the theme's historical
     row, rather than inheriting an invalid value and collapsing the grid. */
  --midori-row: 24px;
  --midori-row: round(up, max(24px, var(--font-text-size) * 1.5), 1px);
```

`max()` keeps small bases on the historical 24px row — at 14px, 1.5x would be
21px and at the 10px floor it would be 15px, which is a tighter page than this theme has ever been and is not what
someone reducing their text size is asking for. `round(up, ..., 1px)` keeps the
dot lattice on whole pixels.

**Already verified in a browser**, so the implementer is not testing whether
the CSS is real — applied through `line-height: var(--midori-row)` and read
back from `getComputedStyle`, this expression computes 24, 24, 24, 26, 27, 29,
30px at bases 14–20, which matches `row_px()` exactly. Step 7's in-app check is
what confirms Obsidian's own engine agrees.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 tests/test_prose_typography.py`
Expected: PASS — `ok leading >= 1.5 across 10-30px (worst 1.50 at 16px)`, and
`ok every row is a whole number of pixels`.

- [ ] **Step 5: Re-derive the dot-grid offset, and MEASURE it rather than trusting it**

`--dotgrid-offset-y: 10.98px` was measured against a 24px row. The file's own
comment says to re-tune it by measuring the baseline-to-dot delta, never by
deriving one situation's value from another's. Both halves are done here: the
derivation gives the candidate, the measurement decides whether it is kept.

Under symmetric font metrics every baseline sits at the centre of its line box,
so growing the row by `R - 24` moves each baseline down by half that. Replace
the declaration with:

```css
  /* Was a constant measured against a 24px row. With a row that follows the
     reader's text size, the first baseline moves by half the row's growth —
     the aliases seat every baseline at L/2 — so the constant becomes an
     offset from the historical row. VERIFY BY MEASURING after changing this;
     see the plan's baseline-vs-dot check. */
  --dotgrid-offset-y: calc(10.98px + (var(--midori-row) - 24px) / 2);
```

Then measure, on the served harness, at base sizes 15, 16, 17, 18 and 20 (set
each with `document.documentElement.style.setProperty('--font-text-size', '18px')`):

```js
(() => {
  const row = parseFloat(getComputedStyle(document.body).getPropertyValue('--midori-row'));
  const off = parseFloat(getComputedStyle(document.body).getPropertyValue('--dotgrid-offset-y'));
  const p = document.querySelector('.markdown-preview-sizer p');
  const box = p.getBoundingClientRect();
  const baseline = box.top + row / 2;               // symmetric metrics: baseline at L/2
  const phase = ((baseline - off) % row + row) % row;
  return { row, off, phase: Math.round(phase * 100) / 100,
           aligned: Math.min(phase, row - phase) < 0.5 };
})()
```

**Gate:** `aligned` must be true at every base size tested.

- [ ] **Step 6: If the gate fails, stop and take the documented fallback**

Do not tune the constant per base size — that is the per-device magic number
this theme's history is made of. Instead revert Step 3 and Step 5 to the fixed
`--midori-row: 24px` and `10.98px`, add to the variable's comment:

```css
  /* SUPPORTED BASE RANGE: 15-16px. Above that the grid is tighter than 1.5
     (17px -> 1.41, 18px -> 1.33) and the dots drift off the baseline. Making
     the row follow --font-text-size was tried and the dot phase did not
     survive it; the measurement is in the plan. */
```

then continue to Task 4 having recorded the failure. A documented limitation is
a result; a grid that is subtly off for everyone but me is not.

- [ ] **Step 7: Verify in the app at two sizes**

```bash
sh tests/lint.sh
sh obsidian/install-obsidian.sh
```

In Obsidian, set Settings → Appearance → Font size to 18, look at a note, then
set it back to 16. The dots must sit on the baselines at both.

- [ ] **Step 8: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "theme: let the grid row follow the reader's text size

The 24px row is 1.50 leading at a 16px base and 1.33 at 18px, so the
theme was quietly correct at one setting on the slider and drifting at
the others. round(up, max(24px, base * 1.5), 1px) holds >= 1.5 across
14-20px on whole pixels, and the dot offset becomes an offset from the
historical row rather than a constant measured against it. Baseline-vs-
dot phase measured at 15, 16, 17, 18 and 20px."
```

---

### Task 4: The heading ladder, optically

Headings are Spectral; body is M PLUS 1p; Spectral's x-height is `0.450` against
`0.520`. Obsidian's real h4 of `1.188em` (read from app.css, not assumed)
therefore renders **1.03x body text to the eye** — an h4 is, optically, body
copy in a different colour. The em ladder the app intends is not the ladder the
eye receives.

**Files:**
- Modify: `obsidian/theme.css` (new block beside the heading rules at ~1603)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Consumes: `X_MPLUS`, `X_SPECTRAL`, `theme_var()`, `--midori-row`.

- [ ] **Step 1: Write the failing test**

Append and register:

```python
# Obsidian's defaults, in em of the base size.
OBSIDIAN_H = {1: 1.618, 2: 1.462, 3: 1.318, 4: 1.188}


def test_heading_ladder_is_optical():
    """Each heading should be as much BIGGER TO THE EYE as its em says.

    Spectral carries 0.450 of x-height per em against Midori Text's 0.520, so
    a heading set at the app's default em is 13.5% smaller optically than the
    ladder claims. The test is on x-height ratio, not on em.
    """
    for level, default in OBSIDIAN_H.items():
        raw = theme_var(f"--h{level}-size")
        em = em_value(raw)
        if em is None:
            bad(f"--h{level}-size is {raw!r}; at Obsidian's default {default}em "
                f"the visual step is {default * X_SPECTRAL / X_MPLUS:.2f}x body, "
                f"not {default:.2f}x")
            continue
        visual = em * X_SPECTRAL / X_MPLUS
        if abs(visual - default) <= 0.02:
            ok(f"h{level} {raw} reads {visual:.2f}x body (intended {default:.2f}x)")
        else:
            bad(f"h{level} {raw} reads {visual:.2f}x body, intended {default:.2f}x")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: four failures, the first being
`--h1-size is None; at Obsidian's default 1.618em the visual step is 1.40x body, not 1.62x`.

- [ ] **Step 3: Set the compensated sizes**

Each is the Obsidian default multiplied by `0.520 / 0.450 = 1.1556`. Add beside
the existing heading rules (~line 1603):

```css
/* HEADING SIZES COMPENSATED FOR SPECTRAL'S X-HEIGHT.

   Headings are "Midori Display" (Spectral, x-height 0.450em); body is
   "Midori Text" (M PLUS 1p, 0.520em). Apparent size follows x-height, not em
   — which is why every print-size result in the vision literature is stated in
   x-height rather than points. Set at Obsidian's default em ladder, an h4
   lands 1.03x body to the eye instead of the 1.19x it claims, and the bottom
   of the hierarchy stops reading as hierarchy.

   x 1.1556 = 0.520 / 0.450 restores the intended ladder optically. The em
   numbers now look large; that is the correction, not a mistake.

   Only h1-h4 — h5/h6 are Midori Text and already correct, and are uppercase,
   where cap-height rather than x-height carries the size.

   The 2-row line box absorbs this: h1 at 1.870em is 29.9px at a 16px base
   against a 48px box, and the box is now calc(var(--midori-row) * 2), so the
   headroom scales with the reader's text size rather than being spent by it. */
body {
  --h1-size: 1.870em;   /* app.css 1.618 x 1.1556 */
  --h2-size: 1.690em;   /* app.css 1.462 */
  --h3-size: 1.523em;   /* app.css 1.318 */
  --h4-size: 1.373em;   /* app.css 1.188 */
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 tests/test_prose_typography.py`
Expected: PASS — e.g. `ok h1 1.870em reads 1.62x body (intended 1.62x)`.

- [ ] **Step 5: Prove the line boxes still land on the grid**

On the served harness, with headings present, at base sizes 16 and 20:

```js
[...document.querySelectorAll('h1,h2,h3,h4')].map(h => {
  const row = parseFloat(getComputedStyle(document.body).getPropertyValue('--midori-row'));
  const box = h.getBoundingClientRect().height;
  return { tag: h.tagName, box, rows: box / row, whole: Math.abs(box / row - Math.round(box / row)) < 0.02 };
})
```

**Gate:** `whole` true for every heading. A heading's line box is
`max(strut, natural box)`, so if a compensated size outgrows its 2-row strut the
box silently becomes fractional and every line below it leaves the grid. If one
fails, raise that heading's box to 3 rows rather than shrinking the size.

- [ ] **Step 6: Verify in the app**

```bash
sh tests/lint.sh
sh obsidian/install-obsidian.sh
```

Open a note with h1–h4. The hierarchy should read as evenly stepped; an h4
should now be unmistakably a heading.

- [ ] **Step 7: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "theme: compensate heading sizes for Spectral's x-height

Apparent size follows x-height, not em — which is why the vision
literature states print size that way. Spectral carries 0.450 per em
against Midori Text's 0.520, so at Obsidian's real ladder (1.618 down to
1.188, read out of app.css) an h4 rendered 1.03x body to the eye while
claiming 1.19x, and the bottom of the hierarchy stopped reading as
hierarchy at all. x1.1556 restores the ladder
optically; line boxes re-measured against the grid at 16 and 20px."
```

---

### Task 4b: Move heading typography onto the variables Obsidian already has

Not a visual change — a **contract** change, and the reason the schema was
researched. app.css has 36 heading variables and consumes every one of them
(`font-family: var(--h1-font)`, `font-weight: var(--h1-weight)`,
`letter-spacing: var(--h1-letter-spacing)`). The theme currently sets six of
them — the colours — and reaches past the rest with element selectors, which is
why it needs *two* rules per level (`.markdown-preview-view h1` for Reading
view and `.HyperMD-header-1` for Live Preview), a separate `--inline-title-font`
declaration, and an `!important` on `.inline-title`.

**Files:**
- Modify: `obsidian/theme.css` (~1603–1690: the heading font rules, the `--inline-title-font` block, the `.inline-title` rule)

**Interfaces:**
- Consumes: `--h1-size`…`--h4-size` from Task 4.
- Produces: `--hN-font`, `--hN-weight`, `--hN-letter-spacing` set on `body`.

- [ ] **Step 1: Confirm the variables are consumed, in this Obsidian version**

```bash
python3 obsidian/dump-app-css.py /tmp/midori-appcss
grep -o -- "--h[1-4]-\(font\|weight\|letter-spacing\|size\)" /tmp/midori-appcss/app.css | sort | uniq -c
```

Expected: each name appears at least twice — once declared, once consumed. If
`--hN-letter-spacing` appears only as a consumer with no default, that is
normal and it still works.

- [ ] **Step 2: Replace the element rules with variable declarations**

Delete the `.markdown-preview-view h1, .HyperMD-header-1 { … }` pairs for h1–h4
and the `body { --inline-title-font: … }` block, and declare instead:

```css
/* HEADINGS THROUGH OBSIDIAN'S OWN VARIABLES, NOT AROUND THEM.

   app.css already reads --hN-font, --hN-weight and --hN-letter-spacing on
   every heading, in BOTH panes: .HyperMD-header-N in Live Preview and h1-h6 in
   Reading view are the same declaration block. Setting the variables therefore
   replaces two rules per level with one, and it is the supported path rather
   than a specificity fight that has to be re-won every time app.css changes.

   The inline title comes free: app.css defaults --inline-title-font,
   --inline-title-size and --inline-title-weight to their --h1-* counterparts,
   so the title follows h1 without a rule of its own. */
body {
  --h1-font: "Midori Display", ui-serif, Georgia, serif;
  --h2-font: "Midori Display", ui-serif, Georgia, serif;
  --h3-font: "Midori Display", ui-serif, Georgia, serif;
  --h4-font: "Midori Display", ui-serif, Georgia, serif;
  --h1-weight: 600;
  --h2-weight: 600;
  --h3-weight: 500;
  --h4-weight: 500;
  --h1-letter-spacing: -0.01em;
  --h2-letter-spacing: -0.01em;
}
```

- [ ] **Step 3: Try removing the `!important` on the inline title**

The existing `.inline-title { font-family: var(--inline-title-font) !important }`
was added because a per-vault Font override in Settings → Appearance drives the
title off `--font-text` and a plain rule lost. app.css explains both halves of
that: the body face resolves as
`--font-text: var(--font-text-override), var(--font-text-theme), var(--font-default)`
with `--font-text-override` written *inline* by app.js, and the title's own rule
is `.inline-title:not([data-level])` at **(0,2,0)** — so a bare `.inline-title`
declaration at (0,1,0) was losing on specificity even before the inline value
entered it. With `--h1-font` set, the title takes its face from
`--inline-title-font → var(--h1-font)`, a chain that never touches
`--font-text`. Remove the `!important`, then **verify with a vault font override
actually set** — Settings → Appearance → Font → pick any face. If the title
reverts to that face, restore the `!important` and leave the existing comment.

- [ ] **Step 3b: Move the title's bottom margin onto its variable**

The theme sets `.inline-title { margin-bottom: 0 }` so the 24px sizer padding
supplies the whole gap. app.css drives that from an **undocumented** token —
`--inline-title-margin-bottom`, default `0.5em`, consumed as `margin-block-end`
on a rule at (0,1,0). Setting the variable instead of the property keeps the
theme out of a tie it would have to win on document order:

```css
body {
  /* Undocumented but consumed by app.css on .inline-title. The sizer's own
     top padding is already one full grid row of air, so the title adds none. */
  --inline-title-margin-bottom: 0;
}
```

- [ ] **Step 4: Verify both panes and the title**

```bash
sh tests/lint.sh && sh obsidian/install-obsidian.sh
```

Open a note with h1–h4 in Live Preview, switch to Reading view, and check the
inline title. All three must be Spectral at the compensated sizes. This is the
step that catches a variable name typo, because a wrong name fails silently to
`inherit` rather than erroring.

- [ ] **Step 5: Commit**

```bash
git add obsidian/theme.css
git commit -m "theme: set headings through Obsidian's own --hN-* variables

app.css consumes 36 heading variables and the theme was setting six of
them, reaching past the rest with element selectors -- which is why it
carried two rules per level, one for .HyperMD-header-N and one for h1-h6,
plus a separate --inline-title-font and an !important. The variables are
read in both panes from a single app.css declaration block, so setting
them replaces the pairs with one block and the inline title follows h1
for free."
```

---

### Task 5: Confirm the body text holds at 1×

The primary display here is an 800×340mm panel at 2560×1080 running 1×, i.e.
81 ppi — the regime where a WCAG ratio overstates legibility, because only ~9%
of a glyph's pixels carry full ink. Nothing in Tasks 1–4 was a colour change, so
**this is a verification task**, and it may correctly end with no code change.

**Files:**
- Modify: `README.md` only if the measurement finds something.

- [ ] **Step 1: Render the writing surface at deviceScaleFactor 1**

Serve the harness and load it with the browser at a 1× device scale, then
screenshot the prose block at its natural size (no zoom, no retina scaling).

- [ ] **Step 2: Measure ink coverage of body text**

Project every pixel in the prose region onto the background→foreground axis and
report the distribution. Paper is `--background-primary: #f3f1eb`, body ink is
`--text-normal: #33302b`:

```python
BG = np.array([243., 241., 236.])
FG = np.array([51., 48., 43.])
d = FG - BG
cov = ((reg - BG) @ d) / (d @ d)
res = np.linalg.norm((reg - BG) - np.outer(cov, d), axis=1)
glyph = cov[(cov > 0.10) & (res < 10)]
print(glyph.mean(), np.median(glyph), np.percentile(glyph, 90), (glyph >= 0.9).mean())
```

- [ ] **Step 3: Judge by the p90 pixel, not the nominal ratio**

Nominal contrast here is ~11:1, which is not the question. Compute the ratio at
the p90-coverage colour and compare against the 5–8:1 body-text budget.

**Gate:** p90 ratio ≥ 5:1. If it clears, record the number and change nothing —
Task 1's narrower measure and Task 3's larger rows both help legibility and
neither touched a colour. If it fails, the lever is weight or lightness, never
saturation.

- [ ] **Step 4: Commit only if something changed**

If the measurement passes, there is nothing to commit; note the number in
Task 6's README bullet. If it fails, fix and commit with the measured
before/after ratios in the message.

---

### Task 6: Move `zen-toggle` into the repo

The writing mode's toggle is a plugin authored here but kept in the vault, so it
ships to nobody. Moving it in makes it a real artifact, covered by
`tests/check_plugin_loads.js` and fanned out by the installer. **Its behaviour
does not change.**

**Files:**
- Create: `obsidian/plugins/zen-toggle/main.js`, `obsidian/plugins/zen-toggle/manifest.json`
- Modify: `obsidian/install-obsidian.sh` (the plugin roster comment, ~line 84)

**Interfaces:**
- Produces: `body.zen-mode`, toggled by a status-bar dot and the command `zen-toggle:toggle-zen`. Task 7's CSS is gated entirely on that class.

- [ ] **Step 1: Copy the plugin in and confirm the load test sees it**

```bash
VAULT="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Mud & Silicon/.obsidian"
mkdir -p obsidian/plugins/zen-toggle
cp "$VAULT/plugins/zen-toggle/main.js" "$VAULT/plugins/zen-toggle/manifest.json" obsidian/plugins/zen-toggle/
node tests/check_plugin_loads.js
```

Expected: a new pair of lines, `ok zen-toggle loads and exports a Plugin` and
`ok zen-toggle manifest v1.0.0`. Do **not** copy `data.json` — that is the saved
zen state for one vault, not part of the plugin.

- [ ] **Step 2: Correct the manifest description**

It currently says "Subtle in-page dot (and command) that toggles zen mode by
flipping a body class; pairs with the zen-mode.css snippet." Two things in that
are no longer true: the dot is a **status-bar** item, not in-page, and the
snippet is being absorbed into the theme. Replace the `description` with:

```json
"description": "Toggles zen mode by flipping a body class, from a dot in the status bar or the command. The rules that respond to that class live in the Midori theme; without it this plugin sets a class nothing reads."
```

- [ ] **Step 3: Move the dot's styling out of inline JS into the plugin's own stylesheet**

The dot is currently styled by `Object.assign(this.dot.style, {...})`, which
writes **inline** styles — the reason the vault snippet's hover rule needs
`!important` to reach it. A plugin should style the element it creates the way
`midori-timer` does, so nothing downstream has to fight it. In `main.js`, delete
the `Object.assign` block and add, above `module.exports`:

```js
/* The dot is this plugin's own element, so this plugin styles it — and via a
 * stylesheet rather than inline styles, which is not a nicety: an inline style
 * can only be overridden with !important, and the theme should be able to
 * restyle a dot sitting in its own status bar without that. */
const STYLE = `
.zen-toggle-btn {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 1.5px solid var(--text-faint);
  background: transparent;
  vertical-align: middle;
  transition: background 120ms ease, border-color 120ms ease;
}
.zen-toggle-btn.is-on {
  background: var(--interactive-accent);
  border-color: var(--interactive-accent);
}
.status-bar-item:hover .zen-toggle-btn {
  border-color: var(--interactive-accent);
}
`;
```

In `onload()`, inject it the way `midori-timer` does, and drop the inline block:

```js
    const style = document.createElement('style');
    style.id = 'zen-toggle-style';
    style.textContent = STYLE;
    document.head.appendChild(style);
    this.register(() => style.remove());
```

And replace `render()` with the class form:

```js
  render() {
    if (!this.dot) return;
    this.dot.toggleClass('is-on', this.zen);
  }
```

- [ ] **Step 4: Run the guards**

```bash
python3 tests/check_style_literals.py
node tests/check_plugin_loads.js
sh tests/lint.sh
```

Expected: all green. The stylesheet check matters here — this task adds a second
template literal to the repo, and a backtick inside one has ended a stylesheet
four times in this codebase.

- [ ] **Step 5: Add it to the installer's roster**

In `obsidian/install-obsidian.sh`, in the comment block listing the companion
plugins, after the `midori-timer` entry:

```sh
  #   zen-toggle       flips `zen-mode` on <body> from a status-bar dot or a
  #                    command. The rules that respond live in theme.css, so
  #                    the plugin is inert without the theme and the theme's
  #                    zen block is inert without the plugin.
```

- [ ] **Step 6: Install and confirm the toggle still works**

```bash
sh obsidian/install-obsidian.sh
```

In Obsidian: the dot appears in the status bar, clicking it fills it, and the
`Toggle zen mode` command does the same. Nothing about the page changes yet —
Task 7 is what responds.

- [ ] **Step 7: Commit**

```bash
git add obsidian/plugins/zen-toggle obsidian/install-obsidian.sh
git commit -m "zen-toggle: move the plugin into the repo

It was authored here and kept in one vault, so the writing mode shipped
to nobody. Behaviour is unchanged; the dot's inline styles become an
injected stylesheet, because an inline style can only be overridden with
!important and the snippet's hover rule was paying that price."
```

---

### Task 7: The zen CSS, consolidated and gated

Two homes become one, and the rules stop assuming a view header that the app has
been told to hide.

**Files:**
- Modify: `obsidian/theme.css` (the zen block at ~504–562)
- Modify: `tests/test_prose_typography.py`
- Modify: `obsidian/install-obsidian.sh` (snippet retirement)

**Interfaces:**
- Consumes: `body.zen-mode` from Task 6; `--midori-row` from Task 2.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_prose_typography.py` and register in `__main__`:

```python
def rules():
    """Every (selector, declarations) pair in theme.css, comments stripped.

    SPLIT, DO NOT MATCH. The obvious regex for a CSS rule —
    `([^{}]*KEYWORD[^{}]*)\{([^{}]*)\}` — has two unbounded quantifiers on
    either side of a literal, which is polynomial: against this 90KB
    stylesheet it does not finish. Splitting on braces is linear and needs no
    cleverness. Nested at-rules degrade gracefully: the inner rule is found
    and the wrapper is ignored, which is all any check here wants.
    """
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)
    out = []
    for chunk in body.split("}"):
        if "{" not in chunk:
            continue
        selector, _, decls = chunk.rpartition("{")
        out.append((" ".join(selector.split()), decls))
    return out


def test_zen_header_rules_are_gated():
    """A zen rule that compensates for the view header must check it exists.

    app.css: `body:not(.show-view-header):not(.is-phone) .view-header
    { display: none }`. With the setting off there is no header, so an
    ungated `padding-top: var(--header-height)` adds a header's worth of
    empty space above the note and shifts the dot grid to match.
    """
    ungated = []
    for selector, decls in rules():
        if "body.zen-mode" not in selector:
            continue
        if "--header-height" in decls and "show-view-header" not in selector:
            ungated.append(selector[:70])
    if ungated:
        for sel in ungated:
            bad(f"zen rule uses --header-height but is not gated on "
                f".show-view-header: {sel}")
    else:
        ok("every zen rule that compensates for the view header checks it exists")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: two failures — the `.cm-sizer` padding rule and the
`background-position` phase rule, both naming their selectors.

- [ ] **Step 3: Gate the header-dependent rules**

In `obsidian/theme.css`, add `.show-view-header` to the three rules that exist
only to compensate for the header, and leave the rest of the zen block alone:

```css
body.zen-mode.show-view-header .markdown-source-view.mod-cm6 .cm-scroller,
body.zen-mode.show-view-header .markdown-reading-view .markdown-preview-view {
  background-position: 0 calc(var(--dotgrid-offset-y) + var(--header-height));
}
body.zen-mode.show-view-header .markdown-source-view.mod-cm6 .cm-sizer {
  padding-top: var(--header-height);
}
body.zen-mode.show-view-header .markdown-reading-view .markdown-preview-sizer {
  padding-top: calc(var(--midori-row) + var(--header-height));
}
```

Note the third rule also picks up `--midori-row` in place of its literal `24px`,
which Task 2 requires.

Extend the block's existing comment with the reason, so the next reader does not
"simplify" the gate away:

```css
/* WHY .show-view-header IS PART OF THE SELECTOR. These three rules exist only
   to compensate for a header this block floats out of flow. Obsidian removes
   that header outright when Settings -> Appearance -> Show view header is off
   (`body:not(.show-view-header):not(.is-phone) .view-header { display: none }`),
   and with it gone the compensation becomes a header's worth of empty space
   above the note plus a grid phase shifted to match it. Gating on the same
   class app.css keys off makes the mode correct under both settings. */
```

- [ ] **Step 4: Absorb the snippet's rules**

Move the four rule groups from the vault's `zen-mode.css` into the same block in
`theme.css`, verbatim except for the dot rule, which now belongs to the plugin
(Task 6, Step 3) and must **not** be copied:

- `body.zen-mode .view-header-title-container { visibility: hidden; }`
- `body.zen-mode .view-header { background-color: transparent; border-bottom: none; }`
- the single-tab strip group (`:not(:has(.workspace-tab-header:nth-child(2)))`), including its 12px drag-handle height
- the commented-out "hide the inline title too" note, kept as a comment

The first two are no-ops while the header is hidden and correct for anyone who
keeps it — leave them ungated, since they cost nothing when the element is
absent.

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 tests/test_prose_typography.py`
Expected: `ok every zen rule that compensates for the view header checks it exists`.

- [ ] **Step 6: Retire the vault snippet — by renaming, never deleting**

In `obsidian/install-obsidian.sh`, beside the existing snippet handling:

```sh
  # The zen rules now live in theme.css. A vault that still has the old snippet
  # would apply both, and the snippet's copy is the ungated one. Rename it aside
  # ONCE rather than deleting it: this script did not write that file, and a
  # user's snippet is theirs.
  SNIP="$VAULT/.obsidian/snippets/zen-mode.css"
  if [ -f "$SNIP" ]; then
    mv "$SNIP" "$SNIP.superseded"
    echo "  moved zen-mode.css aside (now in theme.css) -> zen-mode.css.superseded"
  fi
```

- [ ] **Step 7: Verify in the app, both settings**

```bash
sh tests/lint.sh && sh obsidian/install-obsidian.sh
```

With `showViewHeader: false` (current): toggle zen on and off and confirm **the
note's first line does not move** — that is the bug this task fixes. Then turn
Show view header on in Settings → Appearance and toggle zen again: the header
should float over the canvas with the grid running behind it, as before.

- [ ] **Step 8: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py obsidian/install-obsidian.sh
git commit -m "theme: consolidate the zen rules and gate them on the header

The snippet and theme.css both carried zen rules; now only theme.css
does, and the installer renames the snippet aside rather than deleting a
file it did not write. Three rules that compensate for the floated view
header now require .show-view-header, the class app.css itself keys off
-- without it, a vault with 'Show view header' off got a header's worth
of empty space above every note in zen mode, and a dot grid shifted to
match."
```

---

### Task 8: Paragraph indents, grid-correct

The theme takes over what `pretty-paragraphs` does, because the plugin's version
steps off the dot grid and only the grid's owner can fix that.

**Files:**
- Modify: `obsidian/theme.css` (paragraph rules, ~1113–1130)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Consumes: `--midori-row` from Task 2.
- Produces: `--midori-indent`, default `2em`.

- [ ] **Step 1: Write the failing tests**

Append and register both:

```python
def test_blank_line_keeps_the_grid():
    """The blank line the caret sits on must be a whole grid row.

    pretty-paragraphs gives it `line-height: normal` — about 16.8px at a 14px
    base, which is not a multiple of 24 — so every line below it leaves the
    lattice whenever the caret rests on an empty line.
    """
    for selector, decls in rules():
        if ".cm-line" in selector and re.search(r"line-height:\s*normal", decls):
            bad(f"a .cm-line rule sets line-height: normal, which is not a "
                f"grid row: {selector[:70]}")
            return
    ok("no .cm-line rule sets line-height: normal")


def test_indent_excludes_non_prose():
    """Only prose is indented.

    The obvious selector — the line after a blank one — also matches a heading
    that follows a blank line, which is every heading in a real note.
    """
    indented = [sel for sel, decls in rules()
                if "text-indent: var(--midori-indent)" in decls and ".cm-line" in sel]
    if not indented:
        bad("no Live Preview rule applies --midori-indent")
        return
    for sel in indented:
        for kind in ("HyperMD-header", "HyperMD-list-line", "HyperMD-codeblock"):
            if kind not in sel:
                bad(f"the Live Preview indent does not exclude .{kind}: "
                    f"{sel[:70]}")
                return
    ok("the Live Preview indent excludes headings, lists and code")
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `python3 tests/test_prose_typography.py`
Expected: `no Live Preview rule applies --midori-indent`. (The blank-line test
passes already — the theme has no such rule yet — and is there to stop the
plugin's version being pasted in wholesale later.)

- [ ] **Step 3: Write the paragraph rules**

Replace the reading-view paragraph margin in `obsidian/theme.css` and add the
Live Preview half:

```css
/* PARAGRAPH RHYTHM: A NOVEL'S INDENTS, NOT A WEB PAGE'S GAPS.

   Taken over from the pretty-paragraphs plugin, which did this well except for
   the grid. Two defects came with it and are fixed here, both only fixable by
   whoever owns the lattice:

   1. It gave the blank line under the caret `line-height: normal` so the caret
      stays visible. `normal` is ~16.8px at a 14px base — not a multiple of the
      row — so the whole note below the caret stepped off the dots every time
      the caret rested on an empty line. One full row does the same job and
      lands where the dots are.
   2. Its indent selector was "the line after a blank line", which is also every
      heading in a real note, so headings were indented 2em.

   The evidence review found nothing either way on indent-versus-blank-line.
   This is a stated preference, and it is in the theme rather than a plugin
   because the grid-correct version cannot live anywhere else. */
body {
  --midori-indent: 2em;
}

/* Reading view: the indent replaces the paragraph gap, which also gives the
   grid a row back at every paragraph break. */
.markdown-preview-view p {
  text-indent: var(--midori-indent);
  margin-block: 0;
}
/* Not inside quotes, lists, callouts or tables — those are their own blocks. */
.markdown-preview-view :is(blockquote, li, .callout, table) p {
  text-indent: 0;
}

/* Live Preview: a paragraph is ONE .cm-line (soft-wrapped), and the blank line
   between paragraphs is its own .cm-line containing nothing but a <br>. */
.markdown-source-view.mod-cm6 .cm-line:has(> br:only-child) {
  line-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  color: transparent;
}
/* The blank line the caret is on, and a deliberate second blank line, each keep
   a whole row — visible caret, intact lattice. */
.markdown-source-view.mod-cm6 .cm-line.cm-active:has(> br:only-child),
.markdown-source-view.mod-cm6 .cm-line:has(> br:only-child) + .cm-line:has(> br:only-child) {
  line-height: var(--midori-row);
}
/* The line that starts a paragraph: the first line of the note, or the line
   after a blank one — and prose only. */
.markdown-source-view.mod-cm6 .cm-content > .cm-line:first-child:not(.HyperMD-header):not(.HyperMD-list-line):not(.HyperMD-codeblock):not(.HyperMD-quote):not(.HyperMD-table-row):not(.HyperMD-callout),
.markdown-source-view.mod-cm6 .cm-line:has(> br:only-child) + .cm-line:not(.HyperMD-header):not(.HyperMD-list-line):not(.HyperMD-codeblock):not(.HyperMD-quote):not(.HyperMD-table-row):not(.HyperMD-callout) {
  text-indent: var(--midori-indent);
}
```

**Every paragraph is indented, including the first after a heading.** That
departs from the book convention deliberately: the exception is expressible in
Reading view (`h1 + p`) and not in Live Preview, where a blank line stands
between the heading and the paragraph and the selector becomes positional and
fragile. The two panes matching matters more here, and this theme has paid for
pane divergence before.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 tests/test_prose_typography.py`
Expected: `ok no .cm-line rule sets line-height: normal` and
`ok the Live Preview indent excludes headings, lists and code`.

- [ ] **Step 5: Prove the grid survives a caret on a blank line**

This is the check the plugin would have failed, and a static test cannot see it.
Regenerate the harness with a blank-line case, serve it, and measure:

```js
(() => {
  const row = parseFloat(getComputedStyle(document.body).getPropertyValue('--midori-row'));
  const lines = [...document.querySelectorAll('.cm-line')];
  // simulate the caret sitting on the blank line
  lines.find(l => l.querySelector('br:only-child')).classList.add('cm-active');
  const top = lines[0].getBoundingClientRect().top;
  return lines.map(l => {
    const off = (l.getBoundingClientRect().top - top) % row;
    return { text: l.textContent.slice(0, 12), phase: Math.round(off * 100) / 100,
             onGrid: Math.min(off, row - off) < 0.5 };
  });
})()
```

**Gate:** `onGrid` true for every line, with the blank line active. Then remove
`cm-active` and confirm it is still true.

- [ ] **Step 6: Disable `pretty-paragraphs`**

Now redundant, and its `margin-block: 0 !important` would keep beating the
theme's paragraph rules. Turn it off in Settings → Community plugins in each
vault. **Do not automate this** — the installer manages the theme and this
repo's own plugins, and disabling a third-party plugin a user installed is not
its business. Its justify option is not carried over; nothing asked for it.

- [ ] **Step 7: Verify in the app**

```bash
sh tests/lint.sh && sh obsidian/install-obsidian.sh
```

In a real note, in both panes: paragraphs indent, no gap between them, headings
are **not** indented, list items and code are untouched, and the dots stay on
the baselines as the caret moves onto and off an empty line.

- [ ] **Step 8: Commit**

```bash
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "theme: own the paragraph indents, and keep them on the grid

Taken over from pretty-paragraphs, which did this well except for the
lattice. It gave the caret's blank line line-height: normal -- ~16.8px
at a 14px base, not a multiple of 24 -- so the note stepped off the dot
grid whenever the caret rested on an empty line; a full row does the
same job and lands where the dots are. And its indent selector was 'the
line after a blank line', which is also every heading in a real note.
Both are fixable only by whoever owns the grid."
```

---

### Task 9: Documentation, version, install

**Files:**
- Modify: `README.md` (findings bullets, in the established voice)
- Modify: `obsidian/manifest.json` (version)
- Modify: `docs/superpowers/specs/2026-08-15-prose-typography-evidence.md` (status line)

- [ ] **Step 1: Add the findings bullets to README.md**

In the Obsidian findings list, add one bullet per shipped change. Each must say
what was believed, what was measured, and what changed — matching the existing
entries. Required content:

- **The measure was outside every band and the band has no experiment behind it.** ~91 cpl at a 16px base; the rule traces to Spencer asserting and Rayner & Pollatsek deducing from print; what is real is the speed/preference split, and a writing surface takes the preference side. In `em`, so it survives the reader's text-size slider.
- **A grid tuned to one base size is tuned to one person.** 24px is exactly 1.5 leading at 16px and 1.33 at 18px. The row now follows `--font-text-size`; the dot offset became an offset from the historical row rather than a constant measured against it, and the baseline-vs-dot phase was measured at five base sizes.
- **Apparent size follows x-height, not em.** Spectral 0.450 against M PLUS 1p 0.520 meant an h4 read 1.10× body while claiming 1.27×.
- **A mode that lives in three homes ships from none of them.** The writing mode needed a plugin and a snippet that were not in this repo; only `theme.css` travelled. Folding the plugin in and absorbing the snippet made it one artifact — and doing so exposed that three of its rules compensated for a view header the app removes outright when `Show view header` is off, so zen mode was adding a header's worth of empty space above every note and shifting the dot grid to match.
- **A plugin that gets typography right can still get the grid wrong.** `pretty-paragraphs` gave the caret's blank line `line-height: normal` so the caret stays visible — about 16.8px at a 14px base, which is not a multiple of 24, so the note stepped off the lattice whenever the caret rested on an empty line. Its indent selector was also "the line after a blank line", which is every heading in a real note. Both are fixable only by whoever owns the grid, which is the argument for the theme owning paragraph rhythm rather than delegating it.
- **What was deliberately not changed**, and why: leading (no experiment separates 1.4/1.5/1.6, and the much-cited Chaparro result is a null), letter-spacing, serif-vs-sans (unresolved, not a proven null — the claim that it is settled was itself refuted), revision and look-back support, the seams around the note, and anything about typewriter scrolling or dimming (no evidence exists at all, and each was explicitly declined).

- [ ] **Step 2: Bump the theme version**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path('obsidian/manifest.json')
m = json.loads(p.read_text())
major, minor, patch = m['version'].split('.')
m['version'] = f"{major}.{int(minor) + 1}.0"
p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")
print(m['version'])
PY
```

- [ ] **Step 3: Mark the evidence doc as acted upon**

Change its status line to:

```markdown
**Status:** evidence review — acted on in `docs/superpowers/plans/2026-08-15-prose-writing-surface.md`
```

- [ ] **Step 4: Full verification**

```bash
sh tests/lint.sh
sh obsidian/install-obsidian.sh
```

Expected: `LINT: all green`, including `== prose typography ==`, and the
installer reporting all three vaults.

- [ ] **Step 5: Commit**

```bash
git add README.md obsidian/manifest.json docs/superpowers/specs/
git commit -m "docs: record the prose typography changes and what was left alone"
```

---

## Explicitly out of scope

Named because each is a plausible next idea that the evidence does not support,
and re-litigating them costs more than writing them down once.

- **Letter-spacing / tracking on body text.** No surviving evidence, on screen or off.
- **Serif vs sans for the body face.** Unresolved by citable evidence — the claim that it is a settled null was itself refuted 0–3. Not a reason to switch, and not a reason to defend the current choice on legibility grounds.
- **Changing the leading ratio.** Nothing distinguishes 1.4 from 1.5 from 1.6.
- **Raising the base size.** The recommendation to do so came from arithmetic on a Retina laptop; on this 81 ppi panel 16px clears the 0.2° critical-print-size floor out to ~72cm. The base is the reader's setting, and Task 3 makes the theme follow it rather than argue with it.
- **Typewriter scrolling, focus mode, centred column, caret size, paragraph justification.** No evidence exists in either direction, and each was explicitly declined in the design session. (**Paragraph indents moved IN** — see Task 8. Not because evidence appeared, but because the plugin currently providing them breaks the dot grid, and only the grid's owner can fix that.)
- **Revision and look-back support, and everything around the note** — starting, phone, export, print. Both declined in the design session.
- **Revision-specific leading.** The one genuinely decision-relevant unknown — whether extra leading is *costly* when the eye hops between lines to revise — and untested by anyone. Worth an experiment of our own someday; not a stylesheet change today.
