# Midori for Moshi

[Moshi](https://getmoshi.app) is the iOS/Android terminal for driving coding
agents over SSH/Mosh. It takes imported colour schemes, and it restyles **its
whole UI** from them — not just the terminal grid — so the palette shows up in
chrome, not only in text.

Two themes, generated from the Ghostty themes:

| file | mode | background |
|---|---|---|
| `midori-paper.json` | light | `#f3f1eb` |
| `midori-night.json` | dark | `#1a1917` |

## Installing

Three ways, all on the phone. Easiest first:

1. **Scan the QR** — `midori-paper-qr.png` / `midori-night-qr.png`. In Moshi:
   **Settings → Theme → Import theme**, then scan.
2. **Tap the deep link** on the device itself — the contents of
   `midori-paper.url` / `midori-night.url`.
3. **Paste the JSON** into the same import screen.

Nothing is installed on the host; `install.sh` does not touch these.

## These are generated — don't edit them

`build-moshi-themes.py` reads `ghostty/themes/midori-paper` and
`ghostty/themes/midori-night` and emits the JSON, the deep link, and the QR.
Change a colour in the Ghostty theme and re-run:

```sh
python3 moshi/build-moshi-themes.py    # needs qrencode for the QR step
```

It prints a contrast table for every colour against its own background, so a
palette edit that hurts legibility on a phone is visible at build time.

## The format (undocumented — reverse-engineered)

Moshi publishes no theme schema. This is what its own theme pages emit
(verified against `https://getmoshi.app/themes/<slug>.json` and the deep link
on that page):

```json
{"v":1,"name":"Rose Pine","mode":"dark","colors":{ ...20 keys... }}
```

* Exactly **20** colour keys: `background`, `foreground`, `cursor`, the 8 ANSI
  names, the 8 `bright*` names, and `selectionBackground`. No
  `selectionForeground`, no separate cursor-text colour.
* `mode` is `"light"` or `"dark"` and drives Moshi's UI polarity.
* Deep link is `moshi://theme?d=<base64>` over the **compact** JSON
  (no spaces), **standard** base64 (`+/`), with the trailing `=` padding
  **stripped**. The generator matches this exactly and its output round-trips.
* The palettes come from
  [mbadolato/iTerm2-Color-Schemes](https://github.com/mbadolato/iTerm2-Color-Schemes)
  (MIT), which is why the key names read like iTerm2's.

## The cursor trap

Both Ghostty themes set `cursor-color` to the **exact background hex** as a
sentinel — Ghostty composites the native cursor after the custom shader and
`cursor-opacity=0` does not hide the hollow unfocused cursor, so bg-on-bg is
how they make every native cursor draw invisible, and the shader substitutes
the indigo.

Copied verbatim into Moshi, which has no such shader, that sentinel is simply
an invisible cursor. So the generator detects `cursor == background` and
substitutes **palette 4**, which is the indigo ink in both themes
(`#3a5572` paper, `#6c87a4` night) — exactly what the shader draws.

## Contrast, measured

Against each theme's own background:

| | under 4.5:1 | notes |
|---|---|---|
| Midori Night | **1 / 18** | only `black` `#22211e`, which is the near-background shadow colour and is meant to recede |
| Midori Paper | **8 / 18** | see below |

On a light theme, ANSI 7/15 (`white` / `brightWhite`) are the reverse-video
colours — they are *supposed* to sit near the background. That is conventional,
not a defect, and Midori Paper's 8/18 sits at the good end of published light
themes:

| theme | under 4.5:1 |
|---|---|
| Piatto Light | 8 / 18 |
| **Midori Paper** | **8 / 18** |
| Atom One Light | 11 / 18 |
| Belafonte Day | 14 / 18 |

The values worth knowing about on a phone, where text is small and the screen
is often outdoors, are `yellow` (2.76:1), `brightYellow` (2.21:1),
`brightCyan` (2.73:1) and `cyan` (3.82:1). These are **unchanged from the
Ghostty theme on purpose** — the palette is closed (see the root README), and
diverging here would create a seventh variant of colours that are meant to be
one set. If phone legibility turns out to matter more than cross-surface
parity, the fix belongs in the Ghostty theme so every surface moves together.
