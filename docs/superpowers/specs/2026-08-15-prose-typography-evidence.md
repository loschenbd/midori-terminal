# What the evidence actually supports for a writing surface

**Date:** 2026-08-15
**Status:** evidence review, not yet a design decision
**Method:** 104-agent deep-research pass — 22 sources fetched, 103 claims
extracted, 25 verified adversarially (3 votes each, 2 refutes kills). **12
survived, 13 were killed.** The killed list is at the end and matters as much
as the surviving one: several of the most quotable numbers in this area do not
survive contact with their own sources.

## The short version

Three tiers, and it is worth being blunt about which is which.

1. **Type size has a real psychophysical basis.** Legge & Bigelow's *fluent
   range*: reading speed is flat across a 10× span of angular x-height,
   ~0.2° to ~2°, falls off **sharply** below the critical print size (CPS,
   consensus 0.2°) and only **gradually** above ~2°. The plateau survives RSVP,
   where eye movements are minimised, so it is not an oculomotor artefact.
   Two consequences: within the range, size cannot be optimised for
   performance — it is a comfort choice — and **erring large is much cheaper
   than erring small.**
2. **Line length has a real literature and no rule.** The famous 45–75 / 66
   characters has no experiment behind it (see below). What is real is the
   speed/preference split, confirmed 3–0: longer lines are read *faster*,
   moderate lines are *preferred*, and subjective ratings do not correlate with
   measured performance.
3. **Everything else is design, not optimisation.** Leading is bounded from
   below and nowhere else. Seven of the topics asked about have no surviving
   evidence at all.

## Where the measure rule comes from

It is a convention repeated until it sounded like a finding. Spencer (1968,
*The Visible Word*) **states** lines should not exceed ~70 cpl. Rayner &
Pollatsek (1989) **deduced** a 52 cpl optimum from Tinker's (1963) **print**
studies. No screen experiment produced the range. Dyson (2004) goes further and
proposes the preference for 50–70 cpl may be nothing but familiarity with
printed matter, predicting it will drift as web formats change.

So the case for a shorter measure cannot be "the research says 66". It has to
be made on the preference side of the speed/preference split — which is a
legitimate argument for a writing surface, where the user sits for hours by
choice and reading speed is not the task. In Dyson & Kipping (1998a) 55 cpl was
rated easiest to read and was not read fastest; in Youngman & Scharff (1998)
the longest measure tested was disliked most despite the fastest reaction
times.

**The tempting evidence here was killed.** The claim that Dyson & Haselgrove
found a 55-cpl *comprehension* advantage making 55 a genuine non-monotonic
optimum was refuted 0–3, as was the claim that Dyson identifies *characters*
rather than visual angle as the critical variable. Neither can be cited.

## Leading

Bounded from below by measurement and nowhere else. **No experiment
distinguishes 1.4 from 1.5 from 1.6.**

- Rello et al. found the only reliable line-spacing effect at the extremes and
  in comprehension: their 0.8 condition scored significantly worse than 1.0,
  1.4 and 1.8 (χ²(3) = 19.56, p < .001), with no significant effect on
  subjective readability.
- **Unit trap:** their "1.0" is the Firefox default, i.e. 120% of font size, so
  in CSS terms the tested conditions were ≈0.96, ≈1.2, ≈1.68, ≈2.16. The
  harmful condition was CSS ≈0.96 and **the safe floor is CSS ≈1.2**. Reading
  their guidance as `line-height: 1.0` adopts the condition they found harmful.
- **The much-cited Chaparro line-spacing result is a null result** for
  performance (confirmed 3–0). It affected satisfaction only, and it specifies
  leading in millimetres while never reporting the font size — so **no ratio,
  including WCAG's 1.5, can be derived from it.**
- WCAG 1.4.8's 1.5 has no experimental basis in anything that survived here. It
  is an accessibility policy floor. Worth meeting; not a finding.

## Writing, as opposed to reading

The honest answer, confirmed 3–0: **almost nothing exists.** No study has ever
manipulated type size, leading or measure and measured an effect on
composition. The foundational paper (Wengelin, Torrance, Holmqvist, Simpson,
Galbraith, V. Johansson & R. Johansson 2009) is a *tools* contribution and its
own framing is that the functions of writers' look-back are "currently poorly
understood". The field is at the instrument-building stage for this question.

What does exist is descriptive, and it says a drafting surface is only
intermittently a reading surface — Torrance et al. (2016):

- Sustained reading of one's own text: **mean 5.8% of time-on-task**
  (SD 4.8%, range 0.5–17.4%); ~13% including unpatterned hopping.
- Only 36% of look-back sequences were sustained reading.
- Look-back is **triggered by linguistic boundaries, not uniform monitoring**:
  ~75% of between-sentence opportunities vs 7% of mid-word ones
  (χ²(5) = 27, p < .001).

**Do not cite** the more attractive writing numbers that circulate — 469 ms
fixations during composition, a ~5-character visual span, 19.6% of keystrokes
preceded by a fixation, the 13%-vs-54% composition/editing contrast. All were
refuted 0–3 against their own sources.

## Nothing at all

No evidence survived on: letter spacing / tracking for body text; negative
tracking on large text; crowding (Bouma's law) applied to body copy rather than
signage; **serif vs sans for on-screen prose**; hinting and stem weight at 1×
vs 2×; paragraph separation (blank line vs first-line indent); centred vs
left-aligned; **strict baseline grids and vertical rhythm**; monospace vs
proportional for drafting; typewriter scrolling and focus mode; and caret
visibility, caret size and the cost of losing the cursor.

Two of those deserve emphasis. **Serif vs sans is not a settled null** — the
claim that Richardson's review concludes there is no difference was itself
refuted, so the honest position is *unresolved by citable evidence*, not
*proven equivalent*. And **the baseline grid has no evidence either way**,
which is informative: it means the 24px grid is the constraint that should
**yield** when it conflicts with a parameter that does have evidence, not the
one everything else is fitted to.

## The numbers, for this theme

Measured from the actual TTFs in `fonts/` with a `BoundsPen` on the outlines
(not `OS/2` metadata, which is designer-typed), and from a prose sample rather
than a pangram — pangrams over-weight rare letters and run ~4% narrow.

| | M PLUS 1p (body) | Spectral (display) |
|---|---|---|
| x-height | 520/1000 | 450/1000 |
| cap-height | 730/1000 | 660/1000 |
| avg advance, prose | 481.8/1000 | 435.2/1000 |

### 1. The measure is the one number outside every band

Obsidian's default 700px column with M PLUS 1p gives **~91 cpl at 16px**, ~97
at 15px. Every band anyone has proposed tops out at 75.

Because cpl depends on *both* width and size, the fix should not be a px
constant — it silently changes meaning when a user moves the text-size slider.
In em, it does not: cpl = width_em ÷ 0.4818.

| target | `--file-line-width` | at 16px |
|---|---|---|
| 66 cpl | `32em` | 512px |
| 70 cpl | `34em` | 544px |
| 75 cpl | `36em` | 576px |

### 2. The size is fine on the display it is actually used on

The research's applied conclusion — "16px is at or below the 0.2° floor, go to
17–18px" — assumed a Retina laptop at ~123 px/inch. **The main display here is
not that.** From EDID (`ioreg`): an 800 × 340 mm panel at 2560 × 1080, running
1×, i.e. **81.3 ppi**, 34.2 inches, 1 CSS px = 0.3125 mm — roughly 2.5× the
physical size per CSS pixel of a Retina laptop.

Angular x-height of M PLUS 1p body text, recomputed for that panel
(CPS floor 0.20°):

| base | 50cm | 60cm | 70cm | 80cm |
|---|---|---|---|---|
| 15px | 0.279 | 0.233 | 0.200 | 0.175 |
| **16px** | **0.298** | **0.248** | **0.213** | 0.186 |
| 17px | 0.317 | 0.264 | 0.226 | 0.198 |
| 18px | 0.335 | 0.279 | 0.239 | 0.209 |

16px clears the floor out to ~72cm. The size recommendation **does not
transfer** — and this is the general lesson: every CPS number in the literature
is an angle, so it cannot be applied to a stylesheet without the panel's
physical pixel pitch and a viewing distance. On a Retina laptop the same 16px
is ~0.19° at 50cm and genuinely marginal.

The corollary for shipping to others is that the *same stylesheet* is above the
floor on one machine and under it on another, and the theme cannot detect
which. That argues for making the base size easy to change and the grid follow
it — not for picking a better constant.

### 3. Leading: leave 24px alone

24/16 = **1.50**, 24/15 = 1.60. Both are inside every tested-safe band, above
the CSS ≈1.2 floor, and no experiment can tell them apart. There is no
evidence-based reason to touch it.

The one thing to know is what happens off-base: at 17px the grid is 1.41 and at
18px it is 1.33 — still above the measured harm floor, below the WCAG policy
floor. If the base ever moves up, the grid has to move with it (1.5 × base ⇒
27px at 18px), and the dot lattice with it.

### 4. Spectral needs ~15.6% more em size than M PLUS 1p

x-heights 520 vs 450 ⇒ **ratio 1.156**. A 16px M PLUS 1p body matches an
**18.5px** Spectral; an 18px body matches 20.8px. Anywhere the two sit near
each other at a shared size, the Spectral is optically ~16% small.

Caveat: the cap-height ratio is 1.106, so the answer differs by ~5% depending
on the normalisation basis. The vision-science literature states everything in
x-height, which is a reason to prefer it — but the specific typographic
normalisation claim (the 0.37–0.53 x-height-fraction range, the Times worked
example) was refuted, and no published x-height-normalised face comparison was
located.

## Open questions worth naming

1. **Does extra leading help or hurt during revision?** Asked, and nothing
   answers it. Torrance et al. explicitly excluded revision from analysis;
   every leading study measures forward reading. There is a plausible mechanism
   for leading being actively *costly* when editing — wider line boxes mean
   longer vertical saccades for the hops revision requires — and nobody has
   tested it. This is the single most decision-relevant unknown for a
   24px-grid writing surface.
2. **Should measure be specified in characters, em, or visual angle?** Genuinely
   open, since the "characters are the critical variable" claim was refuted.
   The one adjacent hard number (Atilgan, Xiong & Legge, PNAS 2020: ~13
   characters to reach 80% of maximum reading speed) is a floor so low it never
   binds on a desktop.
3. **1× rendering.** The literature on hinting, anti-aliasing and stem weight
   predates high-DPI and was never re-run — and this theme's primary display is
   81 ppi, which is exactly where it would bite. Untested, and locally
   relevant.

## Source quality, stated plainly

Uneven, and it should change how far each finding moves a number. The type-size
evidence is strong (Legge & Bigelow 2011, *Journal of Vision*, corroborated by
2020 PNAS work from the same group). The line-length evidence is one 2004
review reporting CRT-era studies with mixed tasks. The margin and leading
evidence is weakest: Chaparro et al. is n=18, non-peer-reviewed, internally
inconsistent about its own sample size, reports no effect sizes, and is
unreplicated even by the same lab.
