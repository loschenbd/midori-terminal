# Antinote — Midori Paper / Midori Night

Two Antinote themes cut from the same palette as `ghostty/themes/midori-*`,
`obsidian/theme.css` and `vscode/midori-theme` — warm paper neutrals, sage
accent, and the site's Color-Dot set (indigo / olive / wine / ochre / mint /
plum / terracotta).

```sh
./install-antinote.sh
# then: Antinote -> Settings -> Visuals -> "Reload Custom Themes"
```

Antinote themes are flat JSON: 24 colour keys, no nesting, no comments. The
installer copies both files into Antinote's theme folder, which is inside the
app sandbox and differs per distribution:

| Build | Theme folder |
|---|---|
| Setapp | `~/Library/Containers/com.chabomakers.Antinote-setapp/Data/Documents/Themes` |
| Direct / App Store | `~/Library/Containers/com.chabomakers.Antinote/Data/Documents/Themes` |
| Non-sandboxed | `~/Library/Application Support/Antinote/Themes` |

Settings → Visuals has an "open your theme folder" button if the installer
finds none of these.

## What each key actually paints

Antinote publishes no theme schema — <https://antinote.io/theme-maker> is a
Svelte app that keeps the role descriptions in its route chunk. They are
transcribed here so a colour can be chosen for its job rather than by nudging
sliders until the preview looks right.

| Key | Paints |
|---|---|
| `background` | Main background |
| `backgroundFade` | Inline code and code blocks |
| `typeMain` | Primary text |
| `typeSubtle` | Hyperlinks |
| `typeSubtlePlus` | Shortened hyperlinks (`+google.com/.../efian35+`) |
| `typeHighlight` | Highlighted-text background, scrollbar |
| `typeLight` | Checked items, strikethrough, search secondary, button click |
| `typeSuperlight` | The `/x` check tag, hyperlink underline |
| `typeHyperLight` | Button hover, search-bar background |
| `typeReverse` | Text inside message pills (i.e. on accent fills) |
| `accent1Main` | `math` keyword, **text caret**, success pills, H1, stopwatch milestone |
| `accent1Secondary` | Variable assignment, H2 |
| `accent1Tertiary` | Variable use, H3 |
| `accent2Main` | `list` keyword, variable colon, timer time, checkbox hover |
| `accent2Secondary` | Checkbox **checked** |
| `accent3Main` | Pinned button, `sum` / `paste` keywords, math total, pomo break + cycle |
| `accent3Secondary` | Pinned hover, sum total |
| `accent4Main` | Warning pills, `average` / `code` / `timer` keywords |
| `accent4Secondary` | Average total |
| `accent5Main` | Error pills, `count` keyword |
| `accent5Secondary` | Count total |
| `gridSuperlight` / `gridClear` / `gridBold` | The three grid-line densities |

`isDarkTheme` is a boolean, not a colour — it tells Antinote which chrome and
blur treatment to use, so it must match the background or the window furniture
fights the note.

Values accept 8-digit hex (`#RRGGBBAA`); the grid keys use it here.

## Why these colours

The accent slots line up with Antinote's stock themes, which all follow the
same order — accent1 cool/primary, accent2 purple, accent3 green, accent4
warm, accent5 red — and the Midori palette happens to carry exactly that set.

### The math block is the binding constraint

Everywhere else in Midori, roles are separated by *position* — a heading is a
heading because of where it sits. Antinote's `math` block breaks that: four
roles land on one line, in monospace, at one weight:

```
deducted:  income * taxes =  459.20
└─assign   └─use    └─use    └─total
```

The first cut of these themes used the site palette verbatim, and it did not
work. In OKLCh every Midori accent sits at **chroma 4–7** — near-neutral —
and below roughly C 12 hue barely registers at 13 px. So all separation has to
come from lightness, and four roles were stacked at L 53–57:

| pair on one line | ΔL (before) | ΔL (now) |
|---|---|---|
| variable use vs total | 0.7 | 16.1 |
| assignment vs total | 3.0 | 10.1 |
| assignment vs use | 3.7 | 6.0 |

Two rules came out of it, and they are the reason this file diverges from
`obsidian/theme.css` rather than copying it:

1. **The total is the payload, so it gets the extreme rung** — darkest on
   paper, lightest on night. It was previously *lighter* than the variable
   names, which is why the number you opened the note for receded. This also
   took its contrast from 3.96:1 to 7.63:1. The rung is the load-bearing part,
   not the hue: the answer later moved from olive to wine and nothing else had
   to change.
2. **Chroma is lifted ~1.7× across every accent** (C 4–7 → C 9–13). Still well
   under a conventional syntax theme, but far enough that a 77° hue step is
   actually visible at body size. Hue is doing work here that it does not have
   to do anywhere else in Midori.

Lightness is stated in OKLCh, not HSL — HSL's "lightness" is not perceptual,
and a green and a blue at the same HSL L differ by ~20 points of real
lightness, which is exactly the trap that produced the first cut.

### Known-tight spots

- **Paper `accent1Tertiary`** (variable use, H3) is 3.46:1. Below AA for body
  text, deliberately: on cream, anything light enough to separate cleanly from
  `accent1Secondary` falls under 4.5:1. It carries C 9 instead, so it reads as
  *teal* rather than as *faint*. Do not chase the contrast number by darkening
  it without also re-laddering `accent1Secondary`.
- **Night `accent2Main` vs `accent1Tertiary`** are only 1.9 apart in lightness.
  They are 157° apart in hue at C 9–11.6, and `accent2Main` on a math line is
  a single `:` glyph, so it is left alone.
- **`typeLight`** is ~3.2:1 in both. That is correct — it paints completed
  checklist items and strikethrough, which should recede.

### Slot by slot

- **accent1 = indigo → indigo → teal.** Indigo is the link/heading hue
  everywhere else in Midori (`--link-color`, `--code-function`) and is what
  the Ghostty shader substitutes for the cursor, so `accent1Main` doubles
  correctly as the caret. H1/H2/H3 descend by lightness within the ramp; the
  Tertiary step turns teal so that variable *use* is legible next to variable
  *assignment*.
- **accent2 splits deliberately.** `accent2Main` is plum (the derived
  wine × indigo hue the Ghostty themes use for ANSI 5) for the `list` keyword
  and timers, but `accent2Secondary` is **sage** — a checked box is sage in
  the Obsidian theme (`--checkbox-color`) and in the site's UI, and that
  reads as the same product. The two roles never appear as a pair.
- **accent3 = wine**, pushed to the extreme rung — see "the math block is the
  binding constraint" above. `accent3Secondary` (the `sum` total) goes one step
  further out again. This slot is *nominally* the green one in Antinote's stock
  themes; it holds the math answer, and wine was chosen for it deliberately.
  Green survives elsewhere — `accent2Secondary` (checked boxes) and
  `typeSubtlePlus` are both sage — but nothing else on a math line is warm,
  which is exactly what makes the answer findable.
- **Wine hosts two slots.** `accent3` is the answer; `accent5` is errors and
  `count`. They are separated by ~9 points of lightness (paper: answer L43,
  error pill L52 — night: answer L80, error pill L72) and never co-occur: an
  error is a filled pill, an answer is a bare number in a math block. Paper's
  `accent5Main` was moved lighter specifically so an error pill could not be
  mistaken for a total.
- **accent4 = ochre → terracotta**, the warm ramp. The paper `accent4Main` was
  the weakest value in the first cut at 2.76:1; the chroma lift also darkened
  it to 3.54:1.
- **accent5 = wine.** Light mode leads with the deep wine and lifts for
  totals; dark mode inverts, leading with the lifted wine so an error pill
  still carries on charcoal.
- **`backgroundFade` is *lighter* than `background` in Paper** (`--card` on
  `--background`). Code reads as a card lifted off the sheet here, matching
  `--code-background` in the Obsidian theme, rather than a recessed well.
- **Grid lines are the site's dot mint** — `#548373` on cream (the deepened
  form the Ghostty paper theme uses for ANSI 6, since `#9EBFB4` disappears on
  paper) and `#9EBFB4` on charcoal, both as alpha ramps so the three densities
  stay one hue.

## Maintenance

`sync.sh` does not round-trip these: nothing edits them on the machine, so the
repo is the only copy. Edit the JSON, re-run `./install-antinote.sh`, then hit
"Reload Custom Themes" — no restart needed.
