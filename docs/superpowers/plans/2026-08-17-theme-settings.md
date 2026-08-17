# Midori Theme Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the Midori Obsidian theme's stated preferences — measure,
paragraph rhythm, dot grid, accent, leading, heading scale — as Style Settings
controls that cannot break the baseline grid.

**Architecture:** A `/* @settings */` YAML comment in `theme.css` that the Style
Settings plugin turns into a UI. Every control writes a `--midori-set-*`
**input** variable; the theme reads only **derived** variables computed from
those inputs. Grid-relevant inputs pass through `round(..., 2px)` on the way, so
no user value can reach a rule unquantised.

**Tech Stack:** CSS custom properties, `@supports`, CSS `round()`; the Style
Settings plugin (optional at runtime); Python 3 stdlib for guard tests; Chrome
DevTools Protocol for the rendered-page sweep.

Spec: `docs/superpowers/specs/2026-08-17-theme-settings-design.md`

## Global Constraints

- **No setting may put the note off the dot grid.** Grid-relevant values are
  quantised in CSS; free values are horizontal, colour or on/off only.
- **The setting and the value the theme uses are never the same variable.** An
  input (`--midori-set-*`) may only ever be read by another custom property,
  never by a real CSS property.
- **Rounding is to 2px, not 1px.** `--dotgrid-offset-y` adds half the row's
  growth, so an odd row puts the baseline 0.50px off.
- **Every snapped variable needs a plain declaration outside its `@supports`.**
  A custom property parses as an arbitrary token stream, so a second
  declaration always wins and the failure lands at each use site as
  invalid-at-computed-value-time. `var(--x, fallback)` does not rescue it.
- **`tests/` is stdlib-only.** No PyYAML, no third-party imports in anything
  `tests/lint.sh` runs. Verified: `python3 -c "import yaml"` fails on this
  machine's lint interpreter.
- **Every new guard test must be proven non-vacuous by sabotage** — break the
  property on a scratch copy under the session scratchpad, never the repo's
  file, and require the test to FAIL naming what you broke. Paste the output.
- **The Style Settings block must remain inert without the plugin.** It is a CSS
  comment; the theme must behave exactly as it does today when the plugin is
  absent. Defaults live in the CSS, never in the block alone.
- `AVG_ADVANCE_EM = 0.4818` — M PLUS 1p's average advance over a prose sample,
  measured with a BoundsPen on the outlines. Already defined in
  `tests/test_prose_typography.py:23`.
- Measure default **70 cpl**, slider range **40–100**. Leading default **1.5**.
  Indent default **2em**. Heading scale default **1**. Dot alpha default **1**.

## File Structure

| File | Responsibility |
|---|---|
| `obsidian/theme.css` | The `@settings` block, the input/derived split, the class-select rule sets |
| `tests/test_prose_typography.py` | The stdlib `@settings` reader and every static guard |
| `tests/check_rendered_grid.py` | **New.** The CDP matrix sweep against a running Obsidian |
| `tests/lint.sh` | Unchanged — the rendered sweep needs a live app and never runs in CI |
| `README.md` | The settings table and how to reach it |
| `obsidian/manifest.json` | Version bump |

---

### Task 1: The settings contract — reader, skeleton, and the two structural guards

Establishes the architecture before any knob exists, so every later task has a
gate to pass.

**Files:**
- Modify: `obsidian/theme.css` (add the `@settings` block at the top of the file, before the first `body {`)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Produces: `settings_block()` returning `{"name": str, "id": str, "settings": [dict, ...]}` or `None`; each setting dict has string values keyed by the YAML keys (`id`, `title`, `type`, `default`, `min`, `max`, `step`, `description`), plus `options` as a list of strings where present.
- Produces: the `--midori-set-*` input-variable naming convention.

- [ ] **Step 1: Write the stdlib YAML reader**

Add to `tests/test_prose_typography.py`, after `em_value()` (~line 67):

```python
def settings_block():
    r"""The @settings YAML, parsed by hand because tests/ is stdlib-only.

    PyYAML is not available to the interpreter tests/lint.sh runs; verified by
    `python3 -c "import yaml"` failing. Rather than add a dependency to a suite
    that is deliberately stdlib-only, this reads exactly the subset Style
    Settings needs and this theme uses: top-level `key: value`, a `settings:`
    list whose items each begin with a bare `-`, `key: value` inside those
    items, and a nested list of bare scalars under `options:`.

    NO multi-line scalars. Every description in the block is one line, which is
    a deliberate constraint on the block rather than a limitation here -- it
    keeps this forty lines instead of a YAML implementation.
    """
    m = re.search(r"/\*\s*@settings\s*\n(.*?)\*/", THEME, re.S)
    if not m:
        return None
    top, items, cur, listkey = {}, [], None, None
    for raw in m.group(1).split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if line == "-":                       # a new setting begins
            cur = {}
            items.append(cur)
            listkey = None
            continue
        if line.startswith("- "):             # a bare scalar under options:
            if listkey and cur is not None:
                cur.setdefault(listkey, []).append(line[2:].strip())
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val == "":                         # a key that introduces a list
            listkey = key
            if cur is not None:
                cur.setdefault(key, [])
            continue
        listkey = None
        if cur is None or indent == 0:
            top[key] = val
        else:
            cur[key] = val
    top["settings"] = items
    return top
```

- [ ] **Step 2: Write the three failing tests**

Append to `tests/test_prose_typography.py` and register all three in
`__main__` (see Step 6 for the exact registration):

```python
def test_settings_block_parses():
    """The @settings block exists and every entry is well formed.

    A malformed block does not error in Obsidian -- Style Settings simply shows
    nothing, so the settings silently do not exist. This is the only thing that
    notices.
    """
    b = settings_block()
    if b is None:
        bad("no /* @settings */ block in theme.css")
        return
    for key in ("name", "id"):
        if key not in b:
            bad(f"the @settings block has no top-level {key}")
            return
    if not b["settings"]:
        bad("the @settings block declares no settings")
        return
    for s in b["settings"]:
        for key in ("id", "title", "type"):
            if key not in s:
                bad(f"a setting is missing {key}: {s}")
                return
        if s["type"] == "variable-number-slider":
            for key in ("default", "min", "max", "step"):
                if key not in s:
                    bad(f"slider {s['id']} is missing {key}, which Style "
                        f"Settings requires")
                    return
        if s["type"] == "class-select":
            if "allowEmpty" not in s:
                bad(f"class-select {s['id']} is missing allowEmpty, which "
                    f"Style Settings requires")
                return
            if not s.get("options"):
                bad(f"class-select {s['id']} declares no options")
                return
    ok(f"the @settings block parses: {len(b['settings'])} entries")


def test_settings_ids_are_real():
    """Every control points at something the stylesheet actually defines.

    Style Settings writes `--<id>` for a variable-* control and adds `<id>` as a
    body class for a class-* one. Either way a typo produces a control that
    moves nothing, and the UI still looks correct -- which is the failure mode
    worth a test.
    """
    b = settings_block()
    if b is None:
        bad("no @settings block to check")
        return
    missing = []
    for s in b["settings"]:
        t, sid = s["type"], s["id"]
        if t == "heading":
            continue
        if t.startswith("variable-"):
            if f"--{sid}:" not in THEME:
                missing.append(f"{t} {sid} -> --{sid} is never declared")
        elif t == "class-toggle":
            if f".{sid}" not in THEME:
                missing.append(f"class-toggle {sid} -> .{sid} is in no selector")
        elif t == "class-select":
            for opt in s.get("options", []):
                if f".{opt}" not in THEME:
                    missing.append(f"class-select {sid} option {opt} -> "
                                   f".{opt} is in no selector")
    if missing:
        for m in missing:
            bad(m)
    else:
        ok("every @settings control maps to a real variable or class")


def test_inputs_are_never_read_by_a_real_property():
    """An input may only be read by another custom property.

    This is what makes "no setting can break the grid" enforceable rather than
    aspirational. A user value reaches the page only through a derived variable,
    and the derivation is where clamping and round() live. The moment a real
    property reads a --midori-set-* directly, the value has bypassed every
    guard on the way in.
    """
    offenders = []
    for selector, decls in rules():
        for decl in decls.split(";"):
            if "--midori-set-" not in decl:
                continue
            name = decl.split(":", 1)[0].strip()
            if not name.startswith("--"):
                offenders.append(f"{name} in {' '.join(selector.split())[:52]}")
    if offenders:
        for o in offenders:
            bad(f"a real property reads an input directly: {o}")
    else:
        ok("inputs are read only by derived custom properties")
```

- [ ] **Step 3: Run them to make sure they fail**

Run: `python3 tests/test_prose_typography.py`
Expected: `FAIL no /* @settings */ block in theme.css` and
`FAIL no @settings block to check`. The third passes already (no inputs exist
yet) and is there to hold the line as knobs are added.

- [ ] **Step 4: Add the block skeleton**

In `obsidian/theme.css`, immediately before the first `body {` declaration
(currently around line 30, after the font-alias comment), insert:

```css
/* @settings

name: Midori
id: midori
settings:
    -
        id: midori-measure-heading
        title: Measure and rhythm
        type: heading
        level: 2
        description: What the evidence review calls preference. What it calls evidence is derived and not exposed.

*/
```

Then add the comment that explains the architecture to the next reader, above
the block:

```css
/* THE SETTING AND THE VALUE ARE NEVER THE SAME VARIABLE.

   Style Settings writes `--<id>` on body from the block below. Those are
   INPUTS, named --midori-set-*. The theme never reads one directly; it reads a
   DERIVED variable computed from it, and the derivation is where clamping and
   round() live. That indirection is the whole reason a slider cannot break the
   dot grid: there is no path from a user value to a rule that skips the
   quantisation. test_inputs_are_never_read_by_a_real_property holds the line.

   The block is a CSS comment, so with the plugin absent it is inert and the
   theme behaves exactly as it did before any of this existed. Defaults live in
   the CSS below, never only in the block -- Style Settings persists deviations
   only, so a reader who never opens settings gets the shipped design, and
   uninstalling the plugin restores it rather than orphaning state. */
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 tests/test_prose_typography.py`
Expected: `ok the @settings block parses: 1 entries`,
`ok every @settings control maps to a real variable or class`,
`ok inputs are read only by derived custom properties`.

- [ ] **Step 6: Register the tests**

In the `__main__` block of `tests/test_prose_typography.py`, add after
`test_measure()`:

```python
    test_settings_block_parses()
    test_settings_ids_are_real()
    test_inputs_are_never_read_by_a_real_property()
```

- [ ] **Step 7: Prove the guards are not vacuous**

On scratch COPIES under the session scratchpad — never the repo's files — do
all three and paste each output:

1. Change `type: heading` to `type: variable-number-slider` in the copy.
   Expected: `FAIL slider midori-measure-heading is missing default, ...`
2. Add `--midori-set-bogus: 3;` to `body` and a rule
   `.cm-line { margin-top: var(--midori-set-bogus); }`.
   Expected: `FAIL a real property reads an input directly: margin-top in .cm-line`
3. Add a setting with `id: midori-set-nothing`, `type: variable-number-slider`
   and the four required keys, declaring no such variable.
   Expected: `FAIL variable-number-slider midori-set-nothing -> --midori-set-nothing is never declared`

- [ ] **Step 8: Run the full lint and commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "settings: the contract, before any knob exists

An input may only ever be read by another custom property. That single
rule is what makes 'no setting can break the grid' testable rather than
aspirational -- a user value reaches the page through a derived variable,
and the derivation is where clamping and round() live.

The @settings reader is hand-rolled because tests/ is stdlib-only and
PyYAML is not available to the interpreter lint runs. It handles exactly
the subset Style Settings needs; descriptions are one line each, which is
a constraint on the block rather than a limitation of the reader."
```

---

### Task 2: The measure

The knob Ben asked for, and the one that changes an existing test's subject.

**Files:**
- Modify: `obsidian/theme.css:64` (`--file-line-width`)
- Modify: `tests/test_prose_typography.py` (`test_measure`)

**Interfaces:**
- Consumes: `settings_block()` from Task 1.
- Produces: `--midori-set-measure` (characters, default 70), `--midori-avg-advance` (0.4818).

- [ ] **Step 1: Rewrite `test_measure` to check a default and a range**

The existing test asserts the shipped value is 55–75 cpl and parses
`calc(var(--font-text-size) * N)` with a regex the new three-factor expression
will not match. Replace the whole function body after its docstring — keep the
existing docstring paragraph about `em` resolving against `.cm-line`, and add
the second paragraph:

```python
def test_measure():
    """The measure, in characters, and in a unit that survives its consumers.

    app.css applies --file-line-width as max-width on .cm-line, and .cm-line is
    also the heading element (.HyperMD-header-1 sets font-size: var(--h1-size)
    on it). An em there resolves against the element's OWN font-size, so an em
    measure gives heading lines a wider column than body lines: measured, 34em
    is 544px on a body line and 880px on an h1. A numeric multiple of
    --font-text-size resolves before it reaches any consumer.

    THE SUBJECT CHANGED WHEN THE MEASURE BECAME A SETTING. "The value" is now
    whatever the reader chose, so this cannot assert it. It asserts the two
    things that are still the theme's to get right: the DEFAULT sits in the
    conventional band, and the slider BOUNDS stay inside what the evidence can
    carry. Widening the band here instead of splitting it would have silently
    deleted the check rather than loosened it.
    """
    raw = theme_var("--file-line-width")
    if raw is None:
        bad("--file-line-width is not set; Obsidian's 700px default is ~91 cpl at 16px")
        return
    if em_value(raw) is not None:
        bad(f"--file-line-width is {raw!r}: an em measure is resolved against the "
            "font-size of .cm-line, which is 1.618em on a heading line")
        return
    if "var(--midori-set-measure)" not in raw:
        bad(f"--file-line-width is {raw!r}: expected it to derive from "
            "var(--midori-set-measure)")
        return
    if "var(--font-text-size)" not in raw:
        bad(f"--file-line-width is {raw!r}: must be a multiple of "
            "--font-text-size so it tracks the reader's text size")
        return
    b = settings_block()
    s = next((x for x in (b or {}).get("settings", [])
              if x["id"] == "midori-set-measure"), None)
    if s is None:
        bad("no midori-set-measure control in the @settings block")
        return
    dflt, lo, hi = float(s["default"]), float(s["min"]), float(s["max"])
    if not 55.0 <= dflt <= 75.0:
        bad(f"the measure default is {dflt:g} cpl, outside the conventional 55-75")
        return
    if lo < 40.0 or hi > 100.0:
        bad(f"the measure slider spans {lo:g}-{hi:g} cpl; 40-100 is what the "
            f"evidence carries (preference floor to the ~95 cpl speed peak)")
        return
    ok(f"measure default {dflt:g} cpl in 55-75, slider {lo:g}-{hi:g} inside 40-100")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: `FAIL --file-line-width is 'calc(var(--font-text-size) * 34)': expected it to derive from var(--midori-set-measure)`

- [ ] **Step 3: Split the measure into input and derived**

Replace `obsidian/theme.css:64` and extend the comment above it:

```css
  /* THE MEASURE IS A SETTING, IN CHARACTERS, HELD IN EM.

     34em was 70.6 cpl: cpl = em / 0.4818, where 0.4818 is M PLUS 1p's average
     advance measured with a BoundsPen over a prose sample (not a pangram --
     pangrams over-weight rare letters and run ~4% narrow). The slider is in
     characters because that is what a writer thinks in and what the research
     is reported in. It is NOT a claim that characters is the variable the eye
     responds to: the evidence review refuted characters-over-visual-angle 0-3
     and lists the question as open.

     The advance constant is font-specific and is only valid because the body
     font is fixed. If fonts are ever exposed, measure it from the chosen face.

     Numeric, not em: an em here resolves against .cm-line's own font-size, and
     .cm-line is also the heading element, so an em measure hands an h1 an 880px
     column against a body line's 544px. */
  --midori-avg-advance: 0.4818;
  --midori-set-measure: 70;
  --file-line-width: calc(var(--font-text-size)
                          * var(--midori-set-measure)
                          * var(--midori-avg-advance));
```

- [ ] **Step 4: Add the slider to the `@settings` block**

Inside `settings:`, after the `midori-measure-heading` entry:

```yaml
    -
        id: midori-set-measure
        title: Line length
        description: Characters per line. Longer lines are read faster; moderate lines are preferred; ratings do not track performance. 70 is the preference end, 95 the speed peak.
        type: variable-number-slider
        default: 70
        min: 40
        max: 100
        step: 1
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 tests/test_prose_typography.py`
Expected: `ok measure default 70 cpl in 55-75, slider 40-100 inside 40-100`,
and the three Task 1 guards still green.

- [ ] **Step 6: Check the arithmetic did not move**

Run:

```bash
python3 -c "
adv = 0.4818
for cpl in (40, 70, 100):
    print(f'{cpl:3d} cpl -> {cpl*adv:.2f}em -> {cpl*adv*16:.0f}px at base 16')
"
```

Expected: `40 -> 19.27em -> 308px`, `70 -> 33.73em -> 540px`,
`100 -> 48.18em -> 771px`. The default 540px must be within 4px of the old
`34em = 544px` — if it is not, the advance constant or the default is wrong.

- [ ] **Step 7: Prove the guard is not vacuous**

On a scratch copy, set the slider's `max` to `130` and confirm
`FAIL the measure slider spans 40-130 cpl; 40-100 is what the evidence carries`.
Then set `default` to `90` and confirm
`FAIL the measure default is 90 cpl, outside the conventional 55-75`.
Paste both.

- [ ] **Step 8: Commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "settings: the measure, in characters, 40-100

34 was em, not characters -- 34em is 70.6 cpl at 0.4818 em per character
-- so the slider needs a conversion the variable did not have. The range
is argued rather than bracketed: the speed/preference split is the only
line-length finding that survived the review 3-0, and there is no single
optimum to centre on, so the slider spans its two horns. 40 sits under
every proposed preference band; 100 covers the ~95 cpl speed peak and
Obsidian's stock ~91.

test_measure changes subject with it. It asserted a value; a value is now
the reader's, so it asserts the default and the bounds instead. Widening
the band in place would have deleted the check rather than loosened it."
```

---

### Task 3: Paragraph indent and rhythm

**Files:**
- Modify: `obsidian/theme.css:1271` (`--midori-indent`) and the paragraph rules below it
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Consumes: `settings_block()`, `--midori-set-*` convention.
- Produces: `--midori-set-indent` (em, default 2), body classes `midori-rhythm-indent`, `midori-rhythm-space`, `midori-rhythm-both`.

- [ ] **Step 1: Write the failing test**

Append, and register in `__main__`:

```python
def test_rhythm_modes_all_exist():
    """Each rhythm option has rules, and only 'space' and 'both' add a gap.

    The theme's own argument for owning paragraph rhythm is that only the
    grid's owner can keep it on the lattice. That argument survives a setting
    only if every mode is a whole number of rows: an indent costs no height,
    and a gap must cost exactly one row, never a fraction.
    """
    b = settings_block()
    s = next((x for x in (b or {}).get("settings", [])
              if x["id"] == "midori-rhythm"), None)
    if s is None:
        bad("no midori-rhythm control in the @settings block")
        return
    want = ["midori-rhythm-indent", "midori-rhythm-space", "midori-rhythm-both"]
    if s.get("options") != want:
        bad(f"midori-rhythm options are {s.get('options')}, expected {want}")
        return
    gaps = [sel for sel, decls in rules()
            if "midori-rhythm-space" in sel or "midori-rhythm-both" in sel]
    if not gaps:
        bad("no rule gives the 'space' or 'both' modes a paragraph gap")
        return
    for sel, decls in rules():
        if "midori-rhythm-" not in sel:
            continue
        for decl in decls.split(";"):
            name, _, val = decl.partition(":")
            if name.strip() in ("margin-block", "margin-bottom", "margin-top"):
                v = val.strip()
                if v not in ("0", "0px") and "var(--midori-row)" not in v:
                    bad(f"a rhythm mode sets {name.strip()}: {v}, which is not "
                        f"a whole row: {' '.join(sel.split())[:50]}")
                    return
    ok("all three rhythm modes exist and every gap is a whole row")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: `FAIL no midori-rhythm control in the @settings block`.

- [ ] **Step 3: Split the indent and add the three modes**

Replace `obsidian/theme.css:1270-1272` (the `body { --midori-indent: 2em; }`
block) with:

```css
body {
  --midori-set-indent: 2em;
  --midori-indent: var(--midori-set-indent);
}
```

Then, after the existing reading-view and Live Preview indent rules, add:

```css
/* RHYTHM MODES. The default is 'indent': the indent replaces the gap, which is
   also what gives the grid a row back at every paragraph break. 'space' is the
   web convention -- one whole row between paragraphs, no indent. 'both' marks
   the boundary twice, which typographers generally call wrong; it is here
   because some readers want it, and a setting that only offers the tasteful
   options is a lecture rather than a setting.

   A GAP IS ONE ROW OR IT IS NOTHING. Any other value is a fraction of the
   lattice and every block below the paragraph leaves it.

   The default carries an explicit rule rather than relying on the base styles,
   so all three modes are addressable and switching away and back lands
   somewhere defined. */
body.midori-rhythm-indent .markdown-preview-view p {
  margin-block: 0;
  text-indent: var(--midori-indent);
}
body.midori-rhythm-space .markdown-preview-view p,
body.midori-rhythm-both .markdown-preview-view p {
  margin-block: 0 var(--midori-row);
}
body.midori-rhythm-space .markdown-preview-view p {
  text-indent: 0;
}
body.midori-rhythm-space .markdown-source-view.mod-cm6 .cm-line {
  text-indent: 0;
}
```

**Live Preview needs checking before you write a rule for it, not after.** In
Live Preview a blank line is its own `.cm-line`, so 'space' and 'both' may need
nothing at all there — or may need the blank line's row restored, depending on
what the theme's existing `.cm-line` rules already do to it. Do not guess at
CodeMirror's DOM. Open a note in Live Preview with `--midori-set-indent` at 0
and the `midori-rhythm-space` class on `body`, and read what a blank line's box
actually is:

```js
[...document.querySelectorAll('.cm-line')]
  .map(el => [el.textContent.length, el.getBoundingClientRect().height])
```

If blank lines already measure one row, add no Live Preview rule and say so in
the report. If they measure zero, add the rule the measurement calls for and
paste the numbers.

- [ ] **Step 4: Add both controls to the `@settings` block**

```yaml
    -
        id: midori-set-indent
        title: Paragraph indent
        description: The first-line indent, in em. 0 turns it off without changing the rhythm mode.
        type: variable-number-slider
        default: 2
        min: 0
        max: 4
        step: 0.5
        format: em
    -
        id: midori-rhythm
        title: Paragraph rhythm
        description: Indent is a novel's; space is the web's; both marks the boundary twice. The evidence review found nothing either way, which is why this is a setting.
        type: class-select
        allowEmpty: false
        default: midori-rhythm-indent
        options:
            - midori-rhythm-indent
            - midori-rhythm-space
            - midori-rhythm-both
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 tests/test_prose_typography.py`
Expected: `ok all three rhythm modes exist and every gap is a whole row`.

- [ ] **Step 6: Prove the guard is not vacuous**

On a scratch copy, change the `midori-rhythm-space` margin to
`margin-block: 0 18px` and confirm
`FAIL a rhythm mode sets margin-block: 0 18px, which is not a whole row`.
Paste it.

- [ ] **Step 7: Commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "settings: paragraph indent, and all three rhythms

The README already called indent-versus-blank-line a stated preference
with nothing either way in the evidence, which is a setting waiting to
happen. 'Both' is included deliberately: it double-marks the boundary and
typographers call it wrong, but a setting that offers only the tasteful
options is a lecture.

Every gap is one whole row. That is the theme's own argument for owning
paragraph rhythm -- only the grid's owner can keep it on the lattice --
and it survives being a setting only if no mode can spend a fraction."
```

---

### Task 4: Dot grid opacity

**Files:**
- Modify: `obsidian/theme.css:271` (light) and `:430` (dark)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Produces: `--midori-set-dot-alpha` (multiplier, default 1), `--dotgrid-dot-rgb`, `--dotgrid-dot-alpha` per mode.

- [ ] **Step 1: Write the failing test**

Append, and register in `__main__`:

```python
def test_dot_alpha_is_split_in_both_modes():
    """Both mode blocks must be split, or dark silently stops responding.

    --dotgrid-dot was a whole rgba() literal in each mode. The setting is a
    MULTIPLIER on the shipped per-mode alpha rather than a flat value, because
    0.46 on paper against 0.1748 on dark paper is not an accident -- one flat
    slider would flatten a relationship that was tuned twice. Split one block
    and not the other and the theme still looks right in the mode you tested.
    """
    n_rgb = THEME.count("--dotgrid-dot-rgb:")
    n_alpha = THEME.count("--dotgrid-dot-alpha:")
    if n_rgb < 2 or n_alpha < 2:
        bad(f"--dotgrid-dot is split in {min(n_rgb, n_alpha)} mode block(s); "
            f"both light and dark must be split or one stops responding")
        return
    raw = theme_var("--dotgrid-dot")
    if raw is None or "var(--midori-set-dot-alpha)" not in raw:
        bad(f"--dotgrid-dot is {raw!r}: expected it to multiply "
            "var(--midori-set-dot-alpha)")
        return
    if re.search(r"--dotgrid-dot:\s*rgba\(\s*\d", THEME):
        bad("a --dotgrid-dot declaration is still a literal rgba(), so that "
            "mode ignores the setting")
        return
    ok("the dot alpha is a multiplier on both modes' shipped values")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: `FAIL --dotgrid-dot is split in 0 mode block(s); both light and dark must be split or one stops responding`.

- [ ] **Step 3: Split both mode blocks**

Replace `obsidian/theme.css:271` (light):

```css
  --dotgrid-dot-rgb: 158, 191, 180;
  --dotgrid-dot-alpha: 0.46;
```

Replace `obsidian/theme.css:430` (dark):

```css
  --dotgrid-dot-rgb: 154, 189, 179;
  --dotgrid-dot-alpha: 0.1748;
```

Then add, once, in the same `body` block that holds `--midori-set-measure`:

```css
  /* DOT VISIBILITY, AS A MULTIPLIER AND NOT A VALUE. 0.46 on paper against
     0.1748 on dark paper is not an accident -- each was tuned against its own
     ground and against the halation around light text on dark. One flat alpha
     slider would flatten that. 0 turns the grid off, which is the single
     largest lever for anyone who wants this typography without visible dots. */
  --midori-set-dot-alpha: 1;
  --dotgrid-dot: rgba(var(--dotgrid-dot-rgb),
                      calc(var(--dotgrid-dot-alpha) * var(--midori-set-dot-alpha)));
```

- [ ] **Step 4: Add the slider to the `@settings` block**

```yaml
    -
        id: midori-set-dot-alpha
        title: Dot grid visibility
        description: A multiplier on each mode's tuned opacity, so light and dark keep their relationship. 0 turns the grid off.
        type: variable-number-slider
        default: 1
        min: 0
        max: 1.5
        step: 0.05
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 tests/test_prose_typography.py`
Expected: `ok the dot alpha is a multiplier on both modes' shipped values`.

- [ ] **Step 6: Prove the guard is not vacuous**

On a scratch copy, revert only the DARK block to
`--dotgrid-dot: rgba(154, 189, 179, 0.1748);` and confirm the test FAILs
naming the literal. Paste it. This is the exact half-done state the test
exists to catch.

- [ ] **Step 7: Commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "settings: dot grid visibility, as a multiplier per mode

--dotgrid-dot was a whole rgba() literal in each mode block, so it had to
be split into channel and alpha parts before a setting could reach it --
the same split the theme already uses for --color-blue-rgb.

A multiplier rather than a flat alpha, because 0.46 on paper against
0.1748 on dark paper was tuned twice, against different grounds and
against the halation around light text on dark. A flat slider would
flatten that. 0 turns the grid off."
```

---

### Task 5: The accent

**Files:**
- Modify: `obsidian/theme.css` (the role assignments around `:174-185` and `:346-352`, and a new class-select block)
- Modify: `tests/test_prose_typography.py`

**Interfaces:**
- Produces: `--midori-accent`, `--midori-accent-hover`, body classes `midori-accent-<name>` for the eight palette tokens.

- [ ] **Step 1: Write the failing test**

Append, and register in `__main__`:

```python
def test_accent_options_are_palette_tokens():
    """Every accent option is an existing token, and none is a new hue.

    'The palette is closed' is a documented decision with an argument behind it:
    the ANSI-16 seam has six chromatic slots and all six are filled, and below
    C 12 hue does almost no work at body size, so an eighth accent would share
    a lightness rung with an existing role and read as a duplicate of it. A
    colour picker here would reopen that silently. A select over the existing
    tokens cannot.
    """
    b = settings_block()
    s = next((x for x in (b or {}).get("settings", [])
              if x["id"] == "midori-accent"), None)
    if s is None:
        bad("no midori-accent control in the @settings block")
        return
    if s["type"] != "class-select":
        bad(f"midori-accent is {s['type']}; a variable-select writes a STRING, "
            f"which cannot name a colour, and a variable-color reopens the "
            f"closed palette")
        return
    for opt in s.get("options", []):
        token = opt.replace("midori-accent-", "")
        if f"--midori-{token}:" not in THEME:
            bad(f"accent option {opt} has no --midori-{token} token")
            return
        if f"body.{opt}" not in THEME:
            bad(f"accent option {opt} has no body.{opt} rule")
            return
    ok(f"all {len(s.get('options', []))} accent options are existing palette tokens")
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: `FAIL no midori-accent control in the @settings block`.

- [ ] **Step 3: Add the accent indirection**

In the light `body` block, immediately after `--midori-sage-hover`, add:

```css
  /* THE ACCENT ROLE, ONE STEP BACK FROM THE TOKEN. Roles pointed straight at
     --midori-sage, so switching accent meant rewriting a dozen assignments.
     They point here instead, and the class-select below moves this one
     variable. Nothing about the palette changes -- the options are the tokens
     that already exist. */
  --midori-accent: var(--midori-sage);
  --midori-accent-hover: var(--midori-sage-hover);
```

Add the same pair to the dark `body` block after `--midori-sage-hover` there.

Then repoint the roles. In BOTH mode blocks, change every assignment that
currently reads `var(--midori-sage)` to `var(--midori-accent)` and every
`var(--midori-sage-hover)` to `var(--midori-accent-hover)`. Find them with:

```bash
grep -n "var(--midori-sage)\|var(--midori-sage-hover)" obsidian/theme.css
```

Leave `--midori-sage:` and `--midori-sage-hover:` themselves defined — they are
the default the accent points at, and the palette's sage entry.

- [ ] **Step 4: Add the eight class rules**

After the dark mode block, add:

```css
/* ACCENT SELECTION. Eight options, all existing tokens; see "The palette is
   closed" in the README for why this is a select and not a picker.

   HOVER IS DERIVED, WITH A FALLBACK, because only some tokens ship a hand-tuned
   hover variant (sage has one; mint and ochre do not). color-mix gives every
   accent the same treatment, and the plain declaration outside @supports is
   what an engine without color-mix lands on -- without it, the second
   declaration would hand every consumer an unparseable token stream and the
   hover colour would compute to its initial value, not to the accent. */
body.midori-accent-sage    { --midori-accent: var(--midori-sage); }
body.midori-accent-mint    { --midori-accent: var(--midori-mint); }
body.midori-accent-olive   { --midori-accent: var(--midori-olive); }
body.midori-accent-ochre   { --midori-accent: var(--midori-ochre); }
body.midori-accent-clay    { --midori-accent: var(--midori-clay); }
body.midori-accent-wine    { --midori-accent: var(--midori-wine); }
body.midori-accent-indigo  { --midori-accent: var(--midori-indigo); }
body.midori-accent-purple  { --midori-accent: var(--midori-purple); }

body[class*="midori-accent-"] {
  --midori-accent-hover: var(--midori-accent);
}
@supports (color: color-mix(in oklab, red, blue)) {
  body[class*="midori-accent-"] {
    --midori-accent-hover: color-mix(in oklab, var(--midori-accent) 82%, var(--text-normal));
  }
}
```

- [ ] **Step 5: Add the control to the `@settings` block**

```yaml
    -
        id: midori-accent
        title: Accent
        description: The eight tokens the palette already has. It is a select rather than a picker because the palette is closed; see the README for the argument.
        type: class-select
        allowEmpty: false
        default: midori-accent-sage
        options:
            - midori-accent-sage
            - midori-accent-mint
            - midori-accent-olive
            - midori-accent-ochre
            - midori-accent-clay
            - midori-accent-wine
            - midori-accent-indigo
            - midori-accent-purple
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 tests/test_prose_typography.py`
Expected: `ok all 8 accent options are existing palette tokens`, and
`test_row_has_a_plain_fallback` still green (Task 6 generalises it to catch the
new `color-mix` pair).

- [ ] **Step 7: Prove the guard is not vacuous**

On a scratch copy, add `- midori-accent-teal` to the options and confirm
`FAIL accent option midori-accent-teal has no --midori-teal token`. Paste it.

- [ ] **Step 8: Commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "settings: the accent, as a select over the closed palette

Roles pointed straight at --midori-sage, so switching accent meant
rewriting a dozen assignments; they point at --midori-accent now and the
class-select moves one variable.

A select and not a colour picker, deliberately. 'The palette is closed'
is a documented decision with an argument -- six chromatic ANSI slots,
all filled, and below C 12 hue does almost no work at body size, so a
ninth colour would share a rung and read as a duplicate. A picker would
reopen that silently.

Hover is derived with color-mix and carries a plain fallback outside the
feature query, because only some tokens ship a hand-tuned hover and a
second declaration without the fallback hands every consumer an
unparseable value rather than degrading."
```

---

### Task 6: Leading and heading scale — the snapped tier

The two knobs that can touch vertical rhythm, and the generalised fallback
guard that keeps every future one safe.

**Files:**
- Modify: `obsidian/theme.css:74` and the `@supports` block at `:108-112`; the heading ladder at `:1782-1785`
- Modify: `tests/test_prose_typography.py` (generalise `test_row_has_a_plain_fallback`)

**Interfaces:**
- Consumes: `--midori-row` and the `@supports` pattern.
- Produces: `--midori-set-leading` (default 1.5), `--midori-set-heading-scale` (default 1).

- [ ] **Step 1: Generalise the fallback guard**

Replace `test_row_has_a_plain_fallback` with a version that covers every
snapped variable, not just the row:

```python
def test_snapped_vars_all_have_plain_fallbacks():
    """Every custom property defined inside @supports also has one outside.

    A custom property parses as an arbitrary token stream, so `--x: 24px;
    --x: round(...)` hands the SECOND declaration to every consumer whatever
    the engine supports, and the failure lands at each use site as
    invalid-at-computed-value-time -- the consumer computes to its initial
    value, not to the fallback. var(--x, 24px) does not rescue it either:
    var()'s fallback is for an UNDEFINED property, and this one is defined.

    So the plain declaration OUTSIDE the query is the entire fallback, and
    deleting it is invisible: every other assertion here reads the @supports
    copy and stays green. Measured -- that is exactly what happened before this
    test existed.
    """
    body = re.sub(r"/\*.*?\*/", "", THEME, flags=re.S)
    inside = set()
    for m in re.finditer(r"@supports[^{]*\{", body):
        start = m.end()
        depth, i = 1, start
        while i < len(body) and depth:
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
            i += 1
        inside.update(re.findall(r"(--[\w-]+)\s*:", body[start:i]))
    outside_text = body
    for m in reversed(list(re.finditer(r"@supports[^{]*\{", body))):
        start = m.end()
        depth, i = 1, start
        while i < len(body) and depth:
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
            i += 1
        outside_text = outside_text[:m.start()] + outside_text[i:]
    missing = [n for n in sorted(inside)
               if not re.search(re.escape(n) + r"\s*:", outside_text)]
    if missing:
        for n in missing:
            bad(f"{n} is defined only inside @supports: an engine without the "
                f"feature gets an undefined property and every consumer falls "
                f"back to its initial value, not to a sane default")
    else:
        ok(f"all {len(inside)} @supports-defined properties have plain fallbacks")
```

Replace its registration in `__main__` (`test_row_has_a_plain_fallback()` →
`test_snapped_vars_all_have_plain_fallbacks()`).

- [ ] **Step 2: Run it to make sure it passes on today's file**

Run: `python3 tests/test_prose_typography.py`
Expected: `ok all N @supports-defined properties have plain fallbacks` — N is
at least 2 after Task 5 (`--midori-row`, `--midori-accent-hover`).

- [ ] **Step 3: Write the failing test for the snapped inputs**

Append, and register in `__main__`:

```python
def test_leading_setting_is_snapped():
    """The leading slider reaches the row only through round(..., 2px).

    TWO PIXELS, NOT ONE. --dotgrid-offset-y adds HALF the row's growth, so an
    odd row puts the baseline 0.50px off. Measured against the true baseline
    (a zero-size inline-block on vertical-align: baseline, whose rect top IS
    the baseline) at every base in the 10-30 clamp: exact at even rows, -0.50px
    at odd ones, because Chromium rounds half-leading to a whole pixel.
    """
    raw = None
    for m in re.finditer(r"--midori-row\s*:\s*([^;]+);", THEME):
        if "round" in m.group(1):
            raw = " ".join(m.group(1).split())
    if raw is None:
        bad("no rounded --midori-row declaration")
        return
    if "var(--midori-set-leading)" not in raw:
        bad(f"--midori-row is {raw!r}: expected it to derive from "
            "var(--midori-set-leading)")
        return
    if not re.search(r"round\(\s*up\s*,.*,\s*2px\s*\)", raw):
        bad(f"--midori-row is {raw!r}: must round UP to 2px, not 1px -- "
            "the dot offset adds half the row's growth")
        return
    if "max(24px" not in raw:
        bad(f"--midori-row is {raw!r}: must floor at 24px")
        return
    b = settings_block()
    s = next((x for x in (b or {}).get("settings", [])
              if x["id"] == "midori-set-leading"), None)
    if s is None:
        bad("no midori-set-leading control in the @settings block")
        return
    if float(s["default"]) != 1.5:
        bad(f"the leading default is {s['default']}, not the shipped 1.5")
        return
    ok(f"leading {s['min']}-{s['max']} reaches the row only through "
       f"round(up, ..., 2px)")
```

- [ ] **Step 4: Run it to make sure it fails**

Run: `python3 tests/test_prose_typography.py`
Expected: `FAIL --midori-row is 'round(up, max(24px, var(--font-text-size) * 1.5), 2px)': expected it to derive from var(--midori-set-leading)`.

- [ ] **Step 5: Wire both snapped inputs**

In the `body` block, beside the other inputs, add:

```css
  --midori-set-leading: 1.5;
  --midori-set-heading-scale: 1;
```

Replace the `@supports` block at `:108-112`:

```css
@supports (line-height: round(up, 25px, 2px)) {
  body {
    --midori-row: round(up,
                        max(24px, var(--font-text-size) * var(--midori-set-leading)),
                        2px);
  }
}
```

And extend the ladder at `:1782-1785` so each size carries the scale:

```css
  --h1-size: calc(1.870em * var(--midori-set-heading-scale));   /* app.css 1.618 x 1.1556 */
  --h2-size: calc(1.690em * var(--midori-set-heading-scale));   /* app.css 1.462 x 1.1556 */
  --h3-size: calc(1.523em * var(--midori-set-heading-scale));   /* app.css 1.318 x 1.1556 */
  --h4-size: calc(1.373em * var(--midori-set-heading-scale));   /* app.css 1.188 x 1.1556 */
```

- [ ] **Step 6: Add both controls to the `@settings` block**

The heading-scale maximum is **1.1, not higher**, and the reason must go in its
description: an h1's Live Preview line box already floors at 25px against a
24px row, because 1.870em is 29.92px and the glyph box is 26px. Raising the
scale makes that worse.

The leading minimum is **1.4, not 1.5** — the shipped value is the default, not
the floor. Below 1.5 the `max(24px, …)` clamp swallows the difference at every
base under 18px, so at 16px the slider appears dead down there; at 20px and up
it is live (1.4 × 20 = 28px, 1.5 × 20 = 30px). Do not "simplify" the minimum up
to the default to make the small-base case look tidier — that removes a real
control from exactly the readers who set a large text size.

```yaml
    -
        id: midori-set-leading
        title: Leading
        description: A multiple of the text size. The row is rounded up to an even number of pixels whatever you pick, so the dot grid holds. No experiment distinguishes 1.4 from 1.5 from 1.6.
        type: variable-number-slider
        default: 1.5
        min: 1.4
        max: 2
        step: 0.05
    -
        id: midori-set-heading-scale
        title: Heading scale
        description: Multiplies the heading ladder. Capped at 1.1 because an h1's Live Preview line box already floors 1px over a row at the shipped size.
        type: variable-number-slider
        default: 1
        min: 0.85
        max: 1.1
        step: 0.05
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 tests/test_prose_typography.py`
Expected: `ok leading 1.5-2 reaches the row only through round(up, ..., 2px)`,
`ok all N @supports-defined properties have plain fallbacks`, and
`test_row_is_an_even_number_of_pixels` / `test_leading_holds_across_the_slider`
still green.

- [ ] **Step 8: Prove both guards are not vacuous**

On scratch copies, three sabotages, each pasted:

1. Change `2px` to `1px` in the `round()`. Expected: `FAIL ... must round UP to 2px, not 1px`.
2. Delete the plain `--midori-row: 24px;` at `:74`. Expected: `FAIL --midori-row is defined only inside @supports`.
3. Delete the plain `--midori-accent-hover` declaration outside its `@supports`. Expected: `FAIL --midori-accent-hover is defined only inside @supports`. This is the one that proves the guard generalised rather than just being renamed.

- [ ] **Step 9: Commit**

```bash
sh tests/lint.sh
git add obsidian/theme.css tests/test_prose_typography.py
git commit -m "settings: leading and heading scale, snapped so they cannot drift

The two knobs that can touch vertical rhythm. Both reach the page only
through round(up, ..., 2px) -- two pixels and not one, because
--dotgrid-offset-y adds half the row's growth and an odd row puts the
baseline 0.50px off at every base in the clamp.

Heading scale is capped at 1.1 for a measured reason: an h1's Live
Preview line box already floors at 25px against a 24px row, because
1.870em is 29.92px and the glyph box is 26. Raising the scale makes a
known defect worse, so the bound is where the measurement put it.

test_row_has_a_plain_fallback becomes
test_snapped_vars_all_have_plain_fallbacks and covers every property
defined inside a feature query, not just the row -- Task 5's color-mix
hover is the second one, and there will be more."
```

---

### Task 7: The rendered-page matrix sweep

The instrument this repo does not have, and the reason two real defects
survived nine tasks and a whole-plan review.

**Files:**
- Create: `tests/check_rendered_grid.py`
- Modify: `README.md` (how to run it)

**Interfaces:**
- Consumes: a running Obsidian with `--remote-debugging-port=9222`.
- Produces: nothing the theme depends on; it is a verification tool.

- [ ] **Step 1: Write the sweep**

Create `tests/check_rendered_grid.py`. **This is deliberately NOT wired into
`tests/lint.sh`** — it needs a running Obsidian and can never be a CI check.
It follows the same split the repo already uses for font metrics: stdlib
constants for lint, a tool with a dependency for re-deriving them.

```python
#!/usr/bin/env python3
"""Sweep the settings across their range and check the grid in the RUNNING app.

A static test reads the stylesheet. It cannot see what the browser laid out,
and this repo has already paid for that: a 16-of-16-green suite sat beside a
Live Preview where 6 of 31 lines were off the row, because the offenders were
CodeMirror's own furniture -- an <img class="cm-widgetBuffer"> with height: 1em
(a REPLACED element, so height applies) and an inline-block fold indicator on
the baseline. A harness that rebuilds the theme's DOM does not rebuild
CodeMirror's.

    open -a Obsidian --args --remote-debugging-port=9222
    python3 -m venv /tmp/cdpenv && /tmp/cdpenv/bin/pip install websocket-client
    /tmp/cdpenv/bin/python tests/check_rendered_grid.py

SUPPRESS THE ORIGIN HEADER. Chromium >= 111 rejects WebSocket clients that send
a non-allowlisted Origin, and websocket-client sends one by default. Omitting
it entirely is allowed, so no relaunch flags are needed.
"""

import json
import sys
import urllib.request

import websocket   # not stdlib; see the module docstring


def connect():
    targets = json.load(urllib.request.urlopen("http://localhost:9222/json"))
    page = next((t for t in targets if t.get("type") == "page"), None)
    if page is None:
        sys.exit("no page target; is Obsidian running with --remote-debugging-port=9222?")
    return websocket.create_connection(page["webSocketDebuggerUrl"],
                                       timeout=40, suppress_origin=True)


def evaluate(ws, expr, _id=[0]):
    _id[0] += 1
    ws.send(json.dumps({"id": _id[0], "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == _id[0]:
            res = msg.get("result", {})
            if "exceptionDetails" in res:
                sys.exit(f"page error: {res['exceptionDetails'].get('text')}")
            return res["result"].get("value")


PROBE = """
(() => {
  const b = document.body;
  b.style.setProperty('--midori-set-leading', '%(lead)s');
  b.style.setProperty('--font-text-size', '%(base)spx');
  // The row is a token stream until a real property consumes it, so read a
  // consumer -- getPropertyValue returns the unresolved round(...) expression.
  const probe = document.createElement('div');
  probe.style.cssText = 'position:absolute;visibility:hidden;line-height:var(--midori-row)';
  b.appendChild(probe);
  const row = parseFloat(getComputedStyle(probe).lineHeight);
  probe.remove();
  const lines = [...document.querySelectorAll('.cm-line')];
  const off = lines.filter(el => {
    const h = el.getBoundingClientRect().height;
    return Math.min(h %% row, row - (h %% row)) > 0.5;
  }).length;
  return {row, lines: lines.length, off};
})()
"""


def main():
    ws = connect()
    saved = evaluate(ws, "(()=>{const b=document.body;return ["
                         "b.style.getPropertyValue('--midori-set-leading'),"
                         "b.style.getPropertyValue('--font-text-size')]})()")
    failures = 0
    print(f"{'lead':>5} {'base':>5} {'row':>5} {'even':>5} {'off-row lines':>14}")
    for lead in ("1.5", "1.6", "1.75"):
        for base in range(10, 31):
            r = evaluate(ws, PROBE % {"lead": lead, "base": base})
            row, off = r["row"], r["off"]
            even = row % 2 == 0
            bad = (not even) or row < 24 or off
            if bad:
                failures += 1
            if bad or base in (10, 16, 30):
                print(f"{lead:>5} {base:>5} {row:>5.0f} {str(even):>5} "
                      f"{off:>14}" + ("   <-- FAIL" if bad else ""))
    # Put the app back the way it was found.
    evaluate(ws, "(()=>{const b=document.body;"
                 f"b.style.setProperty('--midori-set-leading', {json.dumps(saved[0])});"
                 f"b.style.setProperty('--font-text-size', {json.dumps(saved[1])});"
                 "if(!b.style.getPropertyValue('--midori-set-leading'))"
                 "b.style.removeProperty('--midori-set-leading');return 1})()")
    print()
    if failures:
        print(f"RENDERED GRID: {failures} of 63 combinations off the lattice")
        sys.exit(1)
    print("RENDERED GRID: all 63 combinations hold — even row, >= 24px, "
          "every line a whole number of rows")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it against a real Obsidian**

```bash
open -a Obsidian --args --remote-debugging-port=9222
python3 -m venv /tmp/cdpenv && /tmp/cdpenv/bin/pip install -q websocket-client
/tmp/cdpenv/bin/python tests/check_rendered_grid.py
```

Open a note with headings, lists, a code block and a footnote reference in Live
Preview first — the sweep measures what is on screen, so an empty note proves
nothing.

Expected: `RENDERED GRID: all 63 combinations hold`.

**If it reports failures, that is the point of the task, not a blocker.**
Record which combinations fail and by how much in the report; do not change the
sweep to make them pass. A known h1 defect (line box floors at 25px against a
24px row) may surface here — if it does, note it and confirm it is that one
rather than something the settings introduced, by re-running with
`--midori-set-heading-scale` at its 0.85 minimum.

- [ ] **Step 3: Verify it restores the app**

After the run, in Obsidian: the note should look exactly as it did, and
`document.body.style` should carry no leftover `--midori-set-leading`. Confirm
by re-running the probe once and checking the row matches the setting, not the
last swept value.

- [ ] **Step 4: Document how to run it**

In `README.md`, under the Obsidian section, add:

```markdown
### Checking the grid in the running app

Static tests read the stylesheet; they cannot see what the browser laid out.
Two real defects survived nine tasks and a whole-plan review because the
offenders were CodeMirror's own elements, which a theme-only harness does not
build. To sweep the settings against the live app:

    open -a Obsidian --args --remote-debugging-port=9222
    python3 -m venv /tmp/cdpenv && /tmp/cdpenv/bin/pip install websocket-client
    /tmp/cdpenv/bin/python tests/check_rendered_grid.py

It walks leading x base size — 63 combinations — and asserts the row is always
an even number of pixels and every line box is a whole number of rows. It is
not part of `tests/lint.sh` because it needs a running app.
```

- [ ] **Step 5: Commit**

```bash
sh tests/lint.sh
git add tests/check_rendered_grid.py README.md
git commit -m "tests: sweep the settings against the running app

A static test reads the stylesheet and cannot see what the browser laid
out. This repo has already paid for that: sixteen green checks sat beside
a Live Preview with 6 of 31 lines off the row, because the offenders were
CodeMirror's own furniture -- an <img class=cm-widgetBuffer> at height:
1em, which is a replaced element so height applies, and an inline-block
fold indicator sitting on the baseline. A harness that rebuilds the
theme's DOM does not rebuild CodeMirror's.

63 combinations, leading x base. Not wired into lint: it needs a running
Obsidian, so it follows the same split the font metrics already use --
stdlib constants for CI, a tool with a dependency for re-deriving them."
```

---

### Task 8: Documentation, version, install

**Files:**
- Modify: `README.md`
- Modify: `obsidian/manifest.json`

- [ ] **Step 1: Document the settings**

In `README.md`, in the Obsidian section, add a subsection. Required content —
the table, plus the principle, plus the honest note about the plugin:

```markdown
### Settings

Install the **Style Settings** community plugin and the theme's controls appear
under Settings → Style Settings → Midori. Without it the block is an inert CSS
comment and the theme behaves exactly as it does with every setting at its
default — nothing is required.

The line the settings draw: **what the evidence review called preference is
exposed; what it called evidence is derived and is not.** Paragraph rhythm is a
setting because the review found nothing either way. The ×1.1556 heading
compensation is not, because it is Spectral's x-height over M PLUS 1p's.

| Setting | Default | Range |
|---|---|---|
| Line length | 70 characters | 40–100 |
| Paragraph rhythm | Indent | Indent / Space between / Both |
| Paragraph indent | 2em | 0–4em |
| Dot grid visibility | 100% | 0–150%, 0 turns it off |
| Accent | Sage | the eight palette tokens |
| Leading | 1.5 | 1.5–2 |
| Heading scale | 1 | 0.85–1.1 |

**No setting can put the note off the dot grid.** The controls write input
variables; the theme reads derived ones, and everything that can touch vertical
rhythm passes through `round(up, …, 2px)` on the way. Two pixels rather than
one because the dot offset adds half the row's growth, so an odd row lands the
baseline 0.50px off.

Line length is in characters because that is the unit a writer thinks in and
the unit the research is reported in — not because characters is established as
what the eye responds to. That claim was refuted 0–3 in the review and the
question is open. The range spans the two ends of the one finding that
survived: 40 is under every proposed preference band, 100 covers the ~95 cpl
speed peak and Obsidian's stock ~91.
```

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

Expected: `1.2.0`.

- [ ] **Step 3: Full verification**

```bash
sh tests/lint.sh
```

Expected: `LINT: all green`, including `== prose typography ==` with every
guard from Tasks 1–6.

**Do not run `sh obsidian/install-obsidian.sh`.** It writes into live iCloud
vaults; that step is Ben's.

- [ ] **Step 4: Commit**

```bash
git add README.md obsidian/manifest.json
git commit -m "docs: the settings, and the line they draw

What the evidence review called preference is exposed; what it called
evidence is derived and is not. Paragraph rhythm is a setting because the
review found nothing either way on indent-versus-blank-line. The x1.1556
heading compensation is not, because it is one x-height over another."
```

---

## Outstanding for Ben

- `sh obsidian/install-obsidian.sh` — writes into the live iCloud vaults.
- Install the **Style Settings** plugin in at least one vault and confirm every
  control appears, moves what it claims to, and that the theme is unchanged
  with all controls at default.
- Run `tests/check_rendered_grid.py` against the app with a real note open.
- Confirm on a phone that the rhythm modes and the measure behave — the mobile
  leg has been reasoned about but not measured all week.
