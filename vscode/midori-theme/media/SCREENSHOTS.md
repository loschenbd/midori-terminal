# Screenshot brief

Two images for the Marketplace listing. They are the only thing most people
will judge the theme on, and the listing currently has none.

| File | Theme | Same file, same scroll position |
|---|---|---|
| `media/paper.png` | Midori Paper | `media/screenshot-sample.tsx` |
| `media/night.png` | Midori Night | `media/screenshot-sample.tsx` |

**Shoot the identical frame twice**, switching only the theme. The pair is a
before/after; if the scroll position or window size drifts between them the
comparison stops working. Take the Paper shot, switch theme with
`Preferences: Color Theme`, take the Night shot, touch nothing else.

## Frame

- **Width:** capture at 1800px wide, downscale to 900. The Marketplace renders
  README images at roughly 900px and a 1x capture there looks soft.
- **Height:** whatever fits lines 17–52 of the sample (the `classify` function
  through the end of `render()`). Roughly 3:2 — don't shoot the whole file.
- **Include the file explorer** — a narrow strip, ~180px. It shows the file
  icon set, which is a listed feature and otherwise invisible.
- **Include one tab and the breadcrumb.** They show the product icons.
- **Exclude** the terminal panel, the status bar clock, any notification
  toast, and anything with a real path or repo name in it.

## Editor state

Set these before capturing:

```jsonc
"editor.guides.bracketPairs": true,
"editor.guides.highlightActiveIndentation": "always",
"workbench.iconTheme": "midori-icons",
"workbench.productIconTheme": "midori-product-icons",
"editor.fontWeight": 450,
"editor.minimap.enabled": false,
"editor.renderWhitespace": "none",
"breadcrumbs.enabled": true
```

`editor.fontWeight: 450` matters — it is the lowest weight at which rendered
coverage saturates, and the theme is tuned around it.

- Put the cursor **inside the `render()` template literal** so the active
  indent rail is visible and lands on the nested markup.
- No text selected, no search widget open, no squiggly errors. Save the file
  first so there is no dirty-tab dot.
- Collapse nothing. No folded regions.

## What each shot has to prove

Every one of these is a claim the README makes. If the frame doesn't contain
it, the screenshot isn't doing its job:

1. **Control flow reads differently from declarations** — `if`/`return` in
   `classify()` against `const`/`class`/`interface`. This is the change most
   people will notice first.
2. **Bold marks introductions** — `classify`, `Ledger`, `LedgerRow`, `Bucket`
   are bold; the *call* to `classify` inside `total()` is not.
3. **Markup inside the template literal is coloured** — the `<section>`,
   `class=`, and `${...}` interpolation in `render()`. Nothing else on the
   Marketplace does this, so it should be plainly visible in frame.
4. **The five accents on one line** — the `reduce` line puts several roles
   adjacent, which is the case low-chroma palettes usually fail.
5. **Bracket-pair guides and the active indent rail** — visible in the nested
   JSX at the bottom and in `render()`.

## Capture

macOS, retina display, Cursor or VS Code windowed (not fullscreen — fullscreen
hides the traffic lights and changes the chrome):

```
# ⌘⇧4 then Space, click the window. Or:
screencapture -o -w ~/Downloads/paper-raw.png     # -o drops the window shadow
```

Then downscale and strip metadata:

```
cd vscode/midori-theme
sips -Z 1800 ~/Downloads/paper-raw.png --out media/paper.png
sips -Z 1800 ~/Downloads/night-raw.png --out media/night.png
```

Aim for under ~400 KB each; they ship inside the `.vsix`.

## After

The README already points at these by absolute raw URL —
`https://raw.githubusercontent.com/loschenbd/midori-terminal/main/vscode/midori-theme/media/paper.png`
— because vsce rewrites relative links as if the extension were at the repo
root, which 404s for a subdirectory package. So the images only resolve once
they are **committed and pushed to `main`**. Push before publishing, and open
the two raw URLs in a browser to confirm 200 before you tag the release.
