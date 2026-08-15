'use strict';

/* Midori Timer — a countdown you type, carried by the colour of the caret.
 *
 * WHAT IT IS. Set a duration by typing "25m", "1h30", "90s" or "1:30" into a
 * small input, which a hotkey can open — bind "Midori Timer: Set duration and
 * start". While it runs, the CARET drifts from its resting indigo through sage
 * and ochre to wine. That is the entire display. A status-bar readout is
 * available instead of it, or alongside it, for when you want the number; that
 * one can be clicked to pause and right-clicked for the rest. Everything is
 * also a command.
 *
 * WHY THE CARET, WHICH IS THE SEVENTH ANSWER TO THIS QUESTION. Six painted
 * indicators were built and rejected: a dotted rail inside the note's edge, the
 * same rail as a solid gradient, a warming page-wide glow, a tinted dot grid, a
 * corner bloom, and discrete marks at session breakpoints. Each rejection was
 * read as a tuning problem and answered with a better-tuned version of the same
 * idea, which is how you get six of them.
 *
 * The constraint that explains all six is that nothing may enter the visual
 * field unbidden. That leaves two legal moves — change a property of something
 * ALREADY on screen, or reveal something that was ASKED for — and every one of
 * the six was new matter on the page. The caret is the first legal one: it is
 * already there, it is already the theme's, and it is the only thing in FOVEAL
 * vision while writing, which is where colour discrimination is best and where
 * none of the six were. That is why 1.5px of it is enough.
 *
 * The history and the evidence are in
 * docs/superpowers/specs/2026-08-15-timer-caret-design.md.
 *
 * IT DEPENDS ON midori-caret. The native caret takes its colour from
 * `caret-color`, which a theme can set on its own, but its GEOMETRY comes from
 * font metrics, and this theme's symmetric overrides put it in the wrong place
 * — which is why midori-caret exists and draws a replacement element. This
 * plugin recolours THAT element. With midori-caret disabled, body.midori-drawn
 * is never set, the rules here never match, and the caret display is simply
 * inert: no error, no half-state, and the status-bar readout still works.
 *
 * SEVEN DECISIONS THAT SHAPE THE CODE. (The caret's own — why the CSS wins on
 * specificity rather than order, and why there is no transition — are at the
 * STYLE block, next to the rules they explain.)
 *
 * 1. A DEADLINE, NOT A COUNTDOWN. The obvious implementation keeps a
 *    `remaining` number and subtracts one per tick. That timer runs slow, and
 *    the amount is not small: Chromium — which is what Obsidian is — clamps
 *    background timers to roughly one wake per minute once a window is hidden,
 *    and suspends them outright while the machine sleeps. A 25-minute
 *    decrementing timer left in the background can finish many minutes late,
 *    and the bug is invisible while you are watching it, because watching it
 *    is what keeps the window in the foreground.
 *
 *    So the only stored quantity is `endsAt`, an absolute epoch time, and
 *    every tick recomputes `endsAt - Date.now()`. Ticks are then free to be
 *    late, coalesced or skipped entirely: the arithmetic is right whenever it
 *    next runs, including on the far side of a lid close. The tick rate only
 *    controls how promptly the display refreshes, never accuracy.
 *
 * 2. THE STATUS BAR MUST NOT REFLOW, when it is used at all. A proportional
 *    font gives "1" and "8" different widths, so a plain countdown makes its
 *    own item change width roughly twice a second and shoves every item to its
 *    left along with it. `font-variant-numeric: tabular-nums` fixes the digits,
 *    and the readout also reserves the width of the largest form it will show
 *    during THIS run, so the item does not jump when 1:00:00 becomes 59:59.
 *
 * 3. SET IT BY DRAGGING, OR BY TYPING, AND NEVER ONLY ONE. The window is a
 *    drum you flick — a real scroll container, so the momentum and snapping are
 *    the platform's — reading out through a split-flap clock. But the plugin's
 *    premise is a duration you TYPE, opened by a hotkey, so the field stays
 *    autofocused and Enter still submits the instant the window opens. Each
 *    drives the other. The drum enumerates whole minutes, so 90s, 1:30 and 2h30
 *    are typed rather than scrolled, which is the honest cost of a dial.
 *
 *    Parsing stays permissive, because a duration box that rejects "25" is a
 *    bad duration box, and the echo says what was understood rather than the
 *    manual saying what the rules are. Ambiguity follows stopwatch convention
 *    and is stated in the UI: ONE colon is minutes:seconds, TWO is
 *    hours:minutes:seconds. The echo also answers the question actually being
 *    asked — not just how long, but WHEN IT ENDS in wall-clock time, which is
 *    what tells you whether the session collides with the thing at 11:15.
 *
 * 4. SURVIVE A RELOAD. The deadline is persisted, so quitting Obsidian
 *    mid-timer and coming back resumes the same countdown rather than losing
 *    it. Because the stored value is absolute, a deadline that passed while
 *    the app was shut announces itself once on load instead of silently
 *    resuming a negative countdown.
 *
 * 5. NO ASSET FILES. install-obsidian.sh copies exactly `main.js` and
 *    `manifest.json` into each vault, so anything this plugin needs has to
 *    live in this file. The stylesheet is injected from here, and the chime is
 *    synthesised with WebAudio rather than shipped as a sound file. Colours
 *    come from the theme's own CSS variables, so the drift tracks Midori Paper
 *    and Midori Night — and any other theme — without hardcoding either.
 *
 * 6. THE DISPLAY IS A PROPERTY, NOT AN ELEMENT. Nothing is created, positioned
 *    or measured. The rejected designs needed a fixed element, a live
 *    measurement of the note's scroller, and a list of Obsidian's floating
 *    chrome to dodge; deleting them deleted all of that, including every
 *    mobile-placement special case. The mobile problem was not solved. It
 *    stopped existing.
 *
 * 7. NOTHING APPEARS, INCLUDING AT THE START. The drift begins at the caret's
 *    own resting colour, so starting a timer changes nothing visible. The one
 *    deliberate exception is the FINISH, which breaks through with a Notice,
 *    the chime and the optional banner — that being the event the timer was
 *    set for. Finishing then resets: the caret returns to indigo in the same
 *    frame, with no state left to dismiss.
 *
 * MOBILE. Obsidian hides the status bar on phones outright
 * (`.is-mobile .status-bar { display: none }` in app.css), so the status-bar
 * display is desktop-only in practice. The caret is not — it is the same caret
 * on a phone, which is the other reason it is the default.
 */

const { Plugin, PluginSettingTab, Setting, Modal, Menu, Notice, setIcon, Platform } = require('obsidian');

const DEFAULTS = {
  defaultDuration: 25 * 60,   // seconds; what the modal is pre-filled with
  showWhenIdle: true,         // keep a clickable clock in the bar when stopped
  chime: true,
  volume: 0.2,
  systemNotification: false,  // OS-level banner, for when Obsidian is buried
  finishMessage: '',          // blank -> "Timer finished (25m)"

  display: 'caret',           // 'caret' | 'statusbar' | 'both'
};


/* The display refresh rate, not the timekeeping rate — see decision 1. A whole
 * second here would let the readout sit up to a second behind the true value;
 * 250ms keeps the flip visually on the beat and is still nothing. */
const TICK_MS = 250;

// ---------------------------------------------------------------- durations

/* Every accepted token, anchored, so a stray "25 apples" is rejected rather
 * than silently read as 25 minutes. Written once and reused by the parser. */
const DURATION_RE =
  /^(?:\s*\d+(?:\.\d+)?\s*(?:h|hr|hrs|hours?|m|min|mins|minutes?|s|sec|secs|seconds?)?\s*)+$/i;
const TOKEN_RE =
  /(\d+(?:\.\d+)?)\s*(h|hr|hrs|hours?|m|min|mins|minutes?|s|sec|secs|seconds?)?/gi;

/**
 * "25" -> 1500, "90s" -> 90, "1h30" -> 5400, "1:30" -> 90, "1:30:00" -> 5400.
 * Returns seconds, or null if nothing sensible was found.
 */
function parseDuration(raw) {
  const s = String(raw == null ? '' : raw).trim().toLowerCase();
  if (!s) return null;

  // Clock form. One colon is mm:ss and two is hh:mm:ss — the stopwatch
  // reading, which is what "1:30" means on every kitchen timer.
  if (/^\d+(?::\d{1,2}){1,2}$/.test(s)) {
    const p = s.split(':').map(Number);
    if (p.some((n) => !Number.isFinite(n))) return null;
    const total = p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p[0] * 60 + p[1];
    return total > 0 ? Math.round(total) : null;
  }

  if (!DURATION_RE.test(s)) return null;

  let total = 0;
  let seen = false;
  TOKEN_RE.lastIndex = 0;                       // the regex is module-level
  let m;
  while ((m = TOKEN_RE.exec(s)) !== null) {
    if (m[0].trim() === '') { TOKEN_RE.lastIndex++; continue; }   // no progress
    const n = parseFloat(m[1]);
    if (!Number.isFinite(n)) continue;
    // The first letter separates h from m from s; nothing else needs looking at.
    const unit = m[2] ? m[2][0] : 'm';          // bare number means minutes
    total += n * (unit === 'h' ? 3600 : unit === 's' ? 1 : 60);
    seen = true;
  }
  const secs = Math.round(total);
  return seen && secs > 0 ? secs : null;
}

/** 1500 -> "25:00", 5400 -> "1:00:00". Ceils, so a fresh 25m reads 25:00. */
function formatClock(seconds) {
  const s = Math.max(0, Math.ceil(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(ss)}` : `${m}:${pad(ss)}`;
}

/* The session's colour, as stops along the elapsed fraction.
 *
 * The caret rests at the palette's ink indigo and drifts to sage, to ochre, to
 * wine, interpolated CONTINUOUSLY between the two bracketing stops. There is no
 * step, no event, and no moment at which a change is visible happening: the
 * caret is simply a different colour than when it was last registered.
 *
 * That is the whole design, and it is the seventh attempt. See
 * docs/superpowers/specs/2026-08-15-timer-caret-design.md for the six painted
 * ones rejected first, and for the constraint that explains all six — nothing
 * may enter the visual field unbidden, which leaves only a property change to
 * something already on screen, or a reveal that was asked for.
 *
 * oklch, AND THE REASON IS NOT THE USUAL ONE. The usual argument is that sRGB
 * interpolation is not perceptually uniform, so it muddies a ramp. Measured off
 * a render of this exact ramp, that argument does not apply here: sRGB and
 * oklab differ by at most deltaE 0.029 in Oklab units across all twelve
 * samples, which is around a just-noticeable difference on a large swatch and
 * nothing at all on a 1.5px caret.
 *
 * What DOES matter is that indigo and sage sit on opposite sides of neutral in
 * the a-b plane. A straight line between them — in sRGB or in oklab, both being
 * rectangular spaces — passes NEARER THE ACHROMATIC AXIS THAN EITHER ENDPOINT.
 * Measured: chroma runs 0.058 -> 0.042 -> 0.029 -> 0.024 -> 0.033, bottoming at
 * t = 0.30 BELOW sage's own 0.033. About a third of the way into a session the
 * caret would go grey, which reads as the caret losing its colour rather than
 * as time passing.
 *
 * oklch interpolates hue ANGLE and chroma separately, so it rounds the corner
 * instead of cutting across it and never dips below its endpoints: the same
 * samples give 0.054 -> 0.049 -> 0.043 -> 0.036 -> 0.032, monotonic into sage.
 * Same numbers in Night. No unit test can see any of this — a unit test can
 * only assert which space was ASKED for. The rendered check is what caught it.
 *
 * THEME VARIABLES, NOT HEX. color-mix accepts var(), so the drift resolves
 * per-theme and follows Paper and Night for free. Hardcoding the ramp would
 * mean a second table of dark-mode colours to keep in sync with theme.css. */
const CARET_STOPS = [
  { at: 0.00, varName: '--color-blue',         fallback: '#3a5572' },  // indigo
  { at: 0.40, varName: '--interactive-accent', fallback: '#5f6f5e' },  // sage
  { at: 0.80, varName: '--color-yellow',       fallback: '#b88a3a' },  // ochre
  { at: 1.00, varName: '--color-red',          fallback: '#7a4a4a' },  // wine
];

const stopColor = (stop) => `var(${stop.varName}, ${stop.fallback})`;

/**
 * The caret colour at elapsed fraction `t`, with a `key` the caller compares to
 * skip writing an identical value — see renderCaret. Clamped at both ends, so a
 * session restored past its deadline is wine rather than an extrapolation off
 * the end of the table.
 */
function caretColor(t) {
  const f = Math.max(0, Math.min(1, Number.isFinite(t) ? t : 0));
  let i = 0;
  while (i < CARET_STOPS.length - 2 && f >= CARET_STOPS[i + 1].at) i += 1;
  const a = CARET_STOPS[i];
  const b = CARET_STOPS[i + 1];
  const span = b.at - a.at;
  const pct = Math.round((span <= 0 ? 1 : (f - a.at) / span) * 100);
  return {
    key: `${i}:${pct}`,
    color: `color-mix(in oklch, ${stopColor(b)} ${pct}%, ${stopColor(a)})`,
  };
}

/**
 * When a duration started now would end, in the reader's own locale and clock.
 *
 * This is the question the modal is actually asked. "25:00" tells you how long
 * the session is; "ends 11:07" tells you whether it collides with the thing at
 * 11:15, which is the decision you are making when you set it. Locale-formatted
 * rather than hand-built, so 12- and 24-hour readers both get their own.
 */
function endsAtClock(seconds) {
  const at = new Date(Date.now() + Math.max(0, seconds) * 1000);
  return at.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

/** 1500 -> "25m", 5400 -> "1h 30m", 90 -> "1m 30s". For prose, not the readout. */
function formatHuman(seconds) {
  const s = Math.max(0, Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const parts = [];
  if (h) parts.push(`${h}h`);
  if (m) parts.push(`${m}m`);
  if (ss || !parts.length) parts.push(`${ss}s`);
  return parts.join(' ');
}

// -------------------------------------------------------------------- chime

/* Two short sine blips. Synthesised rather than shipped, because only main.js
 * is copied into the vault (decision 5). Wrapped in try/catch throughout: a
 * missing or blocked AudioContext must never take the timer down with it. */
function chime(volume) {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const start = ctx.currentTime + 0.02;
    [880, 1320].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const t = start + i * 0.18;
      osc.type = 'sine';
      osc.frequency.value = freq;
      // Ramped, not switched: a square-edged gain change clicks audibly.
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, volume), t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.34);
      osc.connect(gain).connect(ctx.destination);
      osc.start(t);
      osc.stop(t + 0.4);
    });
    window.setTimeout(() => { try { ctx.close(); } catch (e) { /* closed */ } }, 1400);
  } catch (e) {
    /* audio is a nicety, never a dependency */
  }
}

// --------------------------------------------------------------------- CSS

/* Only the readout is styled, and every colour is a theme variable with a
 * quiet fallback, so this looks native under Midori and inoffensive elsewhere. */
const STYLE = `
.midori-timer {
  display: inline-flex;
  align-items: center;
  gap: 0.4em;
  cursor: var(--cursor, pointer);
}
.midori-timer-time {
  /* Decision 2: fixed-width digits, plus a reserved width set from JS. */
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
  text-align: right;
}
.midori-timer .midori-timer-icon {
  display: inline-flex;
  opacity: 0.75;
}
.midori-timer .midori-timer-icon svg {
  width: var(--icon-xs, 14px);
  height: var(--icon-xs, 14px);
}
.midori-timer.is-running .midori-timer-time {
  color: var(--text-normal);
}
.midori-timer.is-paused {
  opacity: 0.65;
}
.midori-timer.is-paused .midori-timer-time {
  font-style: italic;
}
/* ------------------------------------------------------------- the dial

   The duration modal. Obsidian's Setting class is deliberately NOT used here:
   it lays out a settings-LIST row, name flush left and control flush right,
   which is correct for a column of twenty rows and absurd for one field. It is
   what used to put 350px between "Duration" and its box and strand Start in the
   bottom corner. A one-field window owns its own DOM.

   The modal is also the only place this design gets to explain itself, now that
   the running timer is a colour drift on the caret and says nothing. Hence the
   ramp at the bottom: setting a duration is the one moment you are looking
   here, so it is where you learn to read the caret. */
.midori-timer-dial {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.55em;
  max-width: 340px;
  margin: 0 auto;
}

/* ---- the split-flap readout ------------------------------------------

   Each digit is a card split across the middle. Four layers per cell: the
   static top showing the NEW glyph, the static bottom still showing the OLD
   one, and two animated halves — the old top folding down over the seam, then
   the new bottom unfolding from behind it. Only the second half of the fold
   reveals the new lower glyph, which is what sells it as one physical card.

   ONLY CHANGED CELLS ANIMATE. Scrolling the drum changes the value many times a
   second; re-rendering every cell would flip the unchanged ones too, and a
   whole board flapping when only the minutes moved reads as noise rather than
   as a mechanism. A cell whose glyph is unchanged is left completely alone.

   A NEW FLIP CANCELS THE ONE IN FLIGHT rather than queueing behind it. Queued
   flips fall behind a fast scroll and keep flapping after the drum has stopped,
   which looks broken. Restarting is also what produces the cascade while you
   scroll, which is the whole charm of the thing. */
.midori-timer-flaps {
  display: flex;
  justify-content: center;
  gap: 3px;
  perspective: 320px;
  margin: 0.15em 0 0.1em;
}
.midori-timer-flap {
  position: relative;
  width: 0.68em;
  height: 1.15em;
  font-size: 2.6em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
  color: var(--text-normal);
}
.midori-timer-flap.is-sep {
  width: 0.3em;
  color: var(--text-faint, var(--text-muted));
}
.midori-timer-flap.is-sep .midori-timer-flap-half { background: none; }

.midori-timer-flap-half {
  position: absolute;
  left: 0;
  right: 0;
  height: 50%;
  overflow: hidden;
  background: var(--background-modifier-form-field, var(--background-secondary));
  backface-visibility: hidden;
}
.midori-timer-flap-half > span {
  position: absolute;
  left: 0;
  width: 100%;
  height: 200%;                     /* the full glyph; each half clips it */
  line-height: 1.15em;
  text-align: center;
}
.midori-timer-flap-top    { top: 0;    border-radius: 4px 4px 0 0; }
.midori-timer-flap-top > span    { top: 0; }
.midori-timer-flap-bottom { bottom: 0; border-radius: 0 0 4px 4px; }
.midori-timer-flap-bottom > span { bottom: 0; }

/* The seam. A hairline, not a gap: a gap makes two cards, and this is one. */
.midori-timer-flap-top { box-shadow: inset 0 -1px 0 var(--background-modifier-border); }

.midori-timer-flap-fold,
.midori-timer-flap-unfold { z-index: 2; }
.midori-timer-flap-fold {
  transform-origin: bottom center;
  animation: midori-flap-fold var(--flap-ms, 90ms) ease-in forwards;
}
.midori-timer-flap-unfold {
  transform-origin: top center;
  transform: rotateX(90deg);
  animation: midori-flap-unfold var(--flap-ms, 90ms) ease-out var(--flap-ms, 90ms) forwards;
}
@keyframes midori-flap-fold   { to   { transform: rotateX(-90deg); } }
@keyframes midori-flap-unfold { from { transform: rotateX(90deg); } to { transform: rotateX(0); } }

/* Reduced motion keeps the card and drops the mechanism: the glyph simply is
   the new one. The layout must not change, or the readout jumps. */
@media (prefers-reduced-motion: reduce) {
  .midori-timer-flap-fold,
  .midori-timer-flap-unfold { display: none; }
}

.midori-timer-echo {
  text-align: center;
  font-size: var(--font-ui-smaller, 0.8em);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  min-height: 1.5em;
}
.midori-timer-echo b { color: var(--text-normal); font-weight: var(--font-semibold, 600); }
.midori-timer-dial.is-bad .midori-timer-echo { color: var(--color-red); }

/* ---- the drum --------------------------------------------------------

   A REAL SCROLL CONTAINER, which is the whole implementation decision. Native
   overflow plus scroll-snap gives momentum, rubber-banding, wheel support,
   trackpad inertia and touch flinging for free, and every one of those is
   miserable to hand-write and never quite right when you do. The only custom
   code is pointer-drag, because a mouse press does not scroll a div.

   The padding is what lets the first and last values reach the centre band. It
   has to be (height - item) / 2 exactly, or the ends cannot be selected. */
.midori-timer-drum {
  position: relative;
  height: 170px;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(transparent, #000 26%, #000 74%, transparent);
  mask-image: linear-gradient(transparent, #000 26%, #000 74%, transparent);
}
.midori-timer-drum-scroll {
  height: 100%;
  overflow-y: scroll;
  scroll-snap-type: y mandatory;
  scrollbar-width: none;
  touch-action: pan-y;
  cursor: grab;

  /* (170 - 34) / 2, so the first and last values can reach the centre band.
     box-sizing matters here and is not decoration: under content-box, height
     100% plus this padding makes clientHeight 306 rather than 170, and anything
     measuring the scroller to centre an item lands two items out. The JS avoids
     measuring at all (see scrollDrumTo), and this keeps the two agreeing. */
  box-sizing: border-box;
  padding: 68px 0;
}
.midori-timer-drum-scroll::-webkit-scrollbar { display: none; }

/* DRAGGING TURNS SNAPPING OFF, and this is the line that makes the mouse feel
   like the trackpad. With scroll-snap-type live, every scrollTop set during a
   drag is yanked back to the nearest snap point, and the drum judders. It is
   restored on release, which is also what settles the drum onto a value. */
.midori-timer-drum-scroll.is-dragging {
  cursor: grabbing;
  scroll-snap-type: none;
}
.midori-timer-drum-item {
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  scroll-snap-align: center;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
  opacity: 0.45;
  cursor: pointer;
}
.midori-timer-drum-item.is-near { opacity: 0.75; }
.midori-timer-drum-item.is-sel {
  opacity: 1;
  color: var(--text-normal);
  font-weight: var(--font-semibold, 600);
}
.midori-timer-drum-band {
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  height: 34px;
  transform: translateY(-50%);
  pointer-events: none;
  border-top: 1px solid var(--background-modifier-border);
  border-bottom: 1px solid var(--background-modifier-border);
  border-radius: 6px;
  background: var(--dotgrid-accent-wash, rgba(127, 127, 127, 0.06));
}

/* ---- typing, which is still first-class ------------------------------

   The plugin's premise is a duration you TYPE, opened by a hotkey, so the field
   stays autofocused and Enter still submits from the moment the window opens.
   The drum drives it and it drives the drum. It also carries the forms the drum
   cannot reach: the drum enumerates whole minutes, so 90s, 1:30 and 2h30 are
   typed rather than scrolled. */
.midori-timer-type {
  width: 100%;
  text-align: center;
  font-size: var(--font-ui-small, 0.87em);
}
.midori-timer-dial.is-bad .midori-timer-type { border-color: var(--color-red); }

.midori-timer-ramp { margin-top: 0.2em; }
.midori-timer-ramp-bar {
  height: 4px;
  border-radius: 2px;
  background: linear-gradient(to right in oklch,
    var(--color-blue) 0%, var(--interactive-accent) 40%, var(--color-yellow) 80%, var(--color-red) 100%);
}
.midori-timer-ramp-legend {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: var(--font-ui-smaller, 0.75em);
  color: var(--text-faint, var(--text-muted));
}
.midori-timer-start { width: 100%; margin-top: 0.3em; }

/* --------------------------------------------------------------- the caret

   The session's only display. midori-caret already draws the editor caret and
   the note-title caret as real elements; this recolours them and adds nothing.

   WHY THE SPECIFICITY IS DELIBERATE. theme.css paints the caret with
   'body.midori-drawn .midori-cursor::before { background: var(--color-blue) }',
   which is (0,2,2). The rules below are (0,3,2) and so win on specificity
   rather than on document order — which matters, because Obsidian hot-reloads
   theme CSS but NOT plugin code, so for one reload cycle the stylesheet is new
   while main.js is old, and anything relying on load order is a coin flip.

   WHY IT IS GATED ON A CLASS THIS BUILD SETS. Same reason midori-caret gates
   its own rules that way: a rule hung on a class an OLDER build already sets
   applies before the code behind it is live. midori-timer-running is new here,
   so these rules cannot apply until this build is running — and while no timer
   runs the caret is untouched, byte for byte.

   THERE IS NO TRANSITION, ON PURPOSE. A CSS transition would animate the change
   and make it a visible event, which is the one thing this design exists to
   avoid. The colour is rewritten in small steps from JS instead. */
body.midori-drawn.midori-timer-running .midori-cursor::before,
body.midori-drawn.midori-timer-running .midori-title-caret {
  background: var(--midori-timer-caret, var(--color-blue));
}
`;

// ------------------------------------------------------------------- modal

/* The typed-duration window. Opened by command (bind a hotkey to it), by
 * clicking an idle readout, or from the right-click menu. */
const DRUM_MIN = 1;                 // minutes reachable by dragging
const DRUM_MAX = 120;
const DRUM_ITEM = 34;               // px, and must match the stylesheet
const FLAP_MS = 90;                 // per half-fold; a full flip is twice this

class DurationModal extends Modal {
  constructor(app, plugin) {
    super(app);
    this.plugin = plugin;
    this.seconds = plugin.settings.defaultDuration;
    this.flaps = [];                // one cell per character of the clock
    this.shown = '';                // what those cells currently read
  }

  onOpen() {
    const { contentEl, titleEl } = this;
    titleEl.setText('Set timer');

    this.root = contentEl.createDiv({ cls: 'midori-timer-dial' });
    this.flapEl = this.root.createDiv({ cls: 'midori-timer-flaps' });
    this.echoEl = this.root.createDiv({ cls: 'midori-timer-echo' });

    this.buildDrum();

    this.input = this.root.createEl('input', { cls: 'midori-timer-type', type: 'text' });
    this.input.placeholder = 'or type 25m, 1h30, 90s, 1:30';
    this.input.spellcheck = false;
    this.input.addEventListener('input', () => {
      const secs = parseDuration(this.input.value);
      if (secs != null) this.setSeconds(secs, 'type');
      else this.render();                       // show the error, keep the value
    });

    const ramp = this.root.createDiv({ cls: 'midori-timer-ramp' });
    ramp.createDiv({ cls: 'midori-timer-ramp-bar' });
    const legend = ramp.createDiv({ cls: 'midori-timer-ramp-legend' });
    legend.createSpan({ text: 'your caret now' });
    legend.createSpan({ text: 'when it ends' });

    const start = this.root.createEl('button', { cls: 'midori-timer-start', text: 'Start' });
    start.addClass('mod-cta');
    start.addEventListener('click', () => this.submit());

    // Enter submits from anywhere in the window. Escape is Obsidian's already.
    this.scope.register([], 'Enter', (ev) => { ev.preventDefault(); this.submit(); return false; });

    this.render(true);
    this.scrollDrumTo(this.minutes(), 'auto');
    window.setTimeout(() => { this.input.focus(); }, 0);
  }

  /** Whole minutes, for the drum. A 90s duration is not on it; see setSeconds. */
  minutes() { return Math.round(this.seconds / 60); }

  // ------------------------------------------------------------------ drum

  buildDrum() {
    this.drum = this.root.createDiv({ cls: 'midori-timer-drum' });
    this.scroller = this.drum.createDiv({ cls: 'midori-timer-drum-scroll' });
    this.items = [];
    for (let m = DRUM_MIN; m <= DRUM_MAX; m += 1) {
      const it = this.scroller.createDiv({ cls: 'midori-timer-drum-item', text: String(m) });
      it.addEventListener('click', () => this.setSeconds(m * 60, 'tap'));
      this.items.push(it);
    }
    this.drum.createDiv({ cls: 'midori-timer-drum-band' });

    // Read the centre on every scroll, coalesced to one read per frame. A
    // scroll event can fire many times between paints and each read costs a
    // layout, so doing this unthrottled makes the drum stutter under a fling.
    let queued = false;
    this.scroller.addEventListener('scroll', () => {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(() => {
        queued = false;
        const m = this.centreMinute();
        if (m != null) this.setSeconds(m * 60, 'scroll');
      });
    }, { passive: true });

    this.dragDrum();
  }

  /* Position and value are pure arithmetic in both directions, deliberately.
   *
   * The obvious implementation measures: scrollTop = item.offsetTop -
   * (scroller.clientHeight - item.offsetHeight) / 2. It is also wrong in a way
   * that hides, because clientHeight INCLUDES PADDING and this scroller is
   * mostly padding — 68px top and bottom, so that the first and last values can
   * reach the centre band. Under content-box sizing clientHeight came back 306
   * rather than 170, every scrollDrumTo landed two items short, and since the
   * scroll handler writes what it finds back into state, the modal quietly
   * rewrote its own default from 25m to 23m on open. A measurement bug in a
   * control that feeds itself does not look like a measurement bug; it looks
   * like the setting not sticking.
   *
   * So neither direction reads layout. Centring item i means scrollTop = 34i,
   * exactly, and the inverse is one division. The two cannot drift apart, there
   * is no layout read on a scroll event, and the only thing they depend on is
   * the padding being (height - item) / 2 — which the stylesheet states, and
   * box-sizing: border-box there keeps true. */
  centreMinute() {
    const idx = Math.round(this.scroller.scrollTop / DRUM_ITEM);
    return Math.max(DRUM_MIN, Math.min(DRUM_MAX, idx + DRUM_MIN));
  }

  scrollDrumTo(minute, behavior) {
    const m = Math.max(DRUM_MIN, Math.min(DRUM_MAX, minute));
    this.scroller.scrollTo({
      top: (m - DRUM_MIN) * DRUM_ITEM,
      behavior: behavior || 'smooth',
    });
  }

  /* Pointer-drag, the one thing native scrolling does not give us. See the
   * is-dragging rule in the stylesheet for why snapping is switched off. */
  dragDrum() {
    let down = false;
    let last = 0;
    const el = this.scroller;
    el.addEventListener('pointerdown', (ev) => {
      if (ev.button !== 0) return;
      down = true;
      last = ev.clientY;
      el.setPointerCapture(ev.pointerId);
      el.addClass('is-dragging');
    });
    el.addEventListener('pointermove', (ev) => {
      if (!down) return;
      el.scrollTop -= ev.clientY - last;
      last = ev.clientY;
    });
    const up = (ev) => {
      if (!down) return;
      down = false;
      el.removeClass('is-dragging');            // restoring snap settles it
      try { el.releasePointerCapture(ev.pointerId); } catch (e) { /* already gone */ }
    };
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
  }

  // ------------------------------------------------------------------ state

  /**
   * The single writer. `from` says which control moved, so the others can be
   * synced without the update bouncing back and fighting the user's finger.
   */
  setSeconds(secs, from) {
    if (secs === this.seconds && from !== 'init') return;
    this.seconds = secs;
    if (from !== 'type') this.input.value = formatHuman(secs);
    if (from !== 'scroll' && from !== 'drag') {
      const m = this.minutes();
      if (m >= DRUM_MIN && m <= DRUM_MAX) this.scrollDrumTo(m);
    }
    this.render();
  }

  render(force) {
    const raw = this.input ? this.input.value.trim() : '';
    const parsed = raw === '' ? this.seconds : parseDuration(raw);
    const bad = raw !== '' && parsed == null;
    this.root.toggleClass('is-bad', bad);

    if (bad) {
      this.echoEl.setText('Not a duration — try 25m, 1h30, 90s or 1:30');
    } else {
      this.echoEl.empty();
      this.echoEl.createEl('b', { text: formatClock(this.seconds) });
      this.echoEl.createSpan({ text: '  ·  ends ' });
      this.echoEl.createEl('b', { text: endsAtClock(this.seconds) });
    }

    const m = this.minutes();
    this.items.forEach((it, i) => {
      const d = Math.abs(i + DRUM_MIN - m);
      it.toggleClass('is-sel', d === 0);
      it.toggleClass('is-near', d === 1);
    });

    this.paintFlaps(formatClock(this.seconds), force);
  }

  // ------------------------------------------------------------------ flaps

  /* Render `text` across the flap cells, animating only the ones that changed.
   * Rebuilds the row only when the LENGTH changes — 9:59 to 10:00 adds a digit
   * and every cell shifts, so there is nothing to preserve. */
  paintFlaps(text, force) {
    if (force || text.length !== this.flaps.length) {
      this.flapEl.empty();
      this.flaps = [...text].map((ch) => {
        const cell = this.flapEl.createDiv({ cls: 'midori-timer-flap' });
        if (!/\d/.test(ch)) cell.addClass('is-sep');
        cell.createDiv({ cls: 'midori-timer-flap-half midori-timer-flap-top' })
          .createSpan({ text: ch });
        cell.createDiv({ cls: 'midori-timer-flap-bottom midori-timer-flap-half' })
          .createSpan({ text: ch });
        return cell;
      });
      this.shown = text;
      return;
    }

    for (let i = 0; i < text.length; i += 1) {
      if (text[i] === this.shown[i]) continue;   // untouched cells do not flap
      this.flipCell(this.flaps[i], this.shown[i], text[i]);
    }
    this.shown = text;
  }

  /* One card turning over. The two static halves are updated immediately — top
   * to the new glyph, bottom still the old — and two throwaway halves animate
   * over them: the old top folding down, then the new bottom unfolding. Only
   * the second half of the movement reveals the new lower glyph, which is what
   * sells one card turning rather than two things swapping.
   *
   * THE TIMERS ARE TRACKED AND CLEARED, not left to unwind on their own. A
   * flip schedules two callbacks, and a fast scroll starts a new flip on the
   * same cell long before they fire. Left alone they still happen to converge,
   * because setTimeout preserves scheduling order and the last one scheduled
   * carries the newest glyph — but that is an argument, not a guarantee, and it
   * stops being true the moment anything here gains a different delay. Clearing
   * them makes the cell's state depend only on the flip currently running. */
  flipCell(cell, from, to) {
    const top = cell.querySelector('.midori-timer-flap-top');
    const bottom = cell.querySelector('.midori-timer-flap-bottom');
    top.firstElementChild.setText(to);

    // Cancel the flip still in the air rather than queueing behind it: queued
    // flips fall behind a fast scroll and keep flapping after the drum stops.
    if (cell.midoriTimers) cell.midoriTimers.forEach((id) => window.clearTimeout(id));
    cell.querySelectorAll('.midori-timer-flap-fold, .midori-timer-flap-unfold')
      .forEach((el) => el.remove());

    const fold = cell.createDiv({ cls: 'midori-timer-flap-half midori-timer-flap-top midori-timer-flap-fold' });
    fold.createSpan({ text: from });
    const unfold = cell.createDiv({ cls: 'midori-timer-flap-half midori-timer-flap-bottom midori-timer-flap-unfold' });
    unfold.createSpan({ text: to });

    cell.midoriTimers = [
      // The lower half becomes the new glyph only once the fold has covered it.
      window.setTimeout(() => { bottom.firstElementChild.setText(to); }, FLAP_MS),
      window.setTimeout(() => { fold.remove(); unfold.remove(); }, FLAP_MS * 2 + 20),
    ];
  }

  submit() {
    const raw = this.input.value.trim();
    const secs = raw === '' ? this.seconds : parseDuration(raw);
    if (secs == null) {
      this.render();
      return;                                   // keep the modal open to fix it
    }
    this.close();
    this.plugin.start(secs);
  }

  onClose() {
    this.contentEl.empty();
  }
}

// ------------------------------------------------------------------ plugin

module.exports = class MidoriTimer extends Plugin {
  async onload() {
    const data = (await this.loadData()) || {};
    this.settings = Object.assign({}, DEFAULTS, data);
    /* Runtime state, kept beside the settings under a reserved key.
     *   endsAt    epoch ms of the deadline while running   (decision 1)
     *   pausedAt  seconds left while paused
     *   total     the duration that was set, for the finish message */
    this.session = Object.assign({ endsAt: null, pausedAt: null, total: null },
                                 data.session || {});
    this.timer = null;

    const style = document.createElement('style');
    style.id = 'midori-timer-style';
    style.textContent = STYLE;
    document.head.appendChild(style);
    this.register(() => style.remove());

    this.buildStatusBar();
    this.addSettingTab(new MidoriTimerSettings(this.app, this));

    this.addCommand({
      id: 'set-duration',
      name: 'Set duration and start',
      callback: () => new DurationModal(this.app, this).open(),
    });
    this.addCommand({
      id: 'start-default',
      name: 'Start timer with the default duration',
      callback: () => this.start(this.settings.defaultDuration),
    });
    this.addCommand({
      id: 'toggle',
      name: 'Pause or resume timer',
      checkCallback: (checking) => {
        if (!this.isActive()) return false;
        if (!checking) this.toggle();
        return true;
      },
    });
    this.addCommand({
      id: 'stop',
      name: 'Stop timer',
      checkCallback: (checking) => {
        if (!this.isActive()) return false;
        if (!checking) this.stop();
        return true;
      },
    });
    this.addCommand({
      id: 'add-five',
      name: 'Add five minutes',
      checkCallback: (checking) => {
        if (!this.isActive()) return false;
        if (!checking) this.extend(300);
        return true;
      },
    });

    /* Decision 4. A deadline that passed while Obsidian was shut is announced
     * once rather than resumed as a negative countdown. Deferred to layout
     * ready so the notice is not thrown into a half-built workspace. */
    this.app.workspace.onLayoutReady(() => {
      if (this.session.endsAt != null && this.remaining() <= 0) {
        this.finish(true);
      } else if (this.session.endsAt != null) {
        this.run();
      } else {
        this.render();
      }
    });
  }

  /* The caret is the one piece of state that outlives this plugin if it is not
   * cleaned up by hand. Everything else the plugin owns is an element it
   * created, which Obsidian removes with the plugin; the caret belongs to
   * midori-caret and merely wears a class and a variable set from here. Disable
   * this plugin mid-session without unsetting them and the caret stays ochre,
   * with nothing running and nothing left to turn it back. */
  onunload() {
    this.clearTick();
    document.body.classList.remove('midori-timer-running');
    document.body.style.removeProperty('--midori-timer-caret');
  }

  async save() {
    await this.saveData(Object.assign({}, this.settings, { session: this.session }));
  }

  // ------------------------------------------------------------- lifecycle

  isRunning() { return this.session.endsAt != null; }
  isPaused()  { return this.session.pausedAt != null; }
  isActive()  { return this.isRunning() || this.isPaused(); }

  /** Seconds left, always derived from the clock — never accumulated. */
  remaining() {
    if (this.session.pausedAt != null) return this.session.pausedAt;
    if (this.session.endsAt == null) return 0;
    return (this.session.endsAt - Date.now()) / 1000;
  }

  start(seconds) {
    if (!Number.isFinite(seconds) || seconds <= 0) return;
    this.session = {
      endsAt: Date.now() + seconds * 1000,
      pausedAt: null,
      total: seconds,
    };
    this.reserveWidth(seconds);
    this.run();
    this.save();
    new Notice(`Timer set for ${formatHuman(seconds)}.`);
  }

  toggle() {
    if (this.isPaused()) {
      this.session.endsAt = Date.now() + this.session.pausedAt * 1000;
      this.session.pausedAt = null;
      this.run();
    } else if (this.isRunning()) {
      this.session.pausedAt = Math.max(0, this.remaining());
      this.session.endsAt = null;
      this.clearTick();
      this.render();
    } else {
      return;
    }
    this.save();
  }

  extend(seconds) {
    if (this.isPaused()) this.session.pausedAt += seconds;
    else if (this.isRunning()) this.session.endsAt += seconds * 1000;
    else return;
    if (this.session.total != null) this.session.total += seconds;
    this.reserveWidth(this.remaining());
    this.render();
    this.save();
    new Notice(`Timer extended to ${formatClock(this.remaining())}.`);
  }

  stop() {
    this.clearTick();
    this.session = { endsAt: null, pausedAt: null, total: null };
    this.render();
    this.save();
  }

  run() {
    this.clearTick();
    this.reserveWidth(Math.max(this.remaining(), this.session.total || 0));
    this.render();
    // registerInterval so an unload during a run cannot leave it ticking.
    this.tick = this.registerInterval(
      window.setInterval(() => this.onTick(), TICK_MS),
    );
  }

  clearTick() {
    if (this.tick != null) {
      window.clearInterval(this.tick);
      this.tick = null;
    }
  }

  onTick() {
    if (!this.isRunning()) { this.clearTick(); return; }
    if (this.remaining() <= 0) { this.finish(false); return; }
    this.render();
  }

  /* Finishing RESETS. The session is cleared, the caret returns to indigo and
   * the status bar returns to its idle clock, all in the same frame — there is no
   * sticky "finished" state to dismiss. The end of the timer is announced by
   * things that announce themselves and then stop: a Notice, the chime, and
   * the optional OS banner. A readout that sits at 0:00 wearing a bell until
   * you click it is a chore, and it is also a lie the moment you walk away
   * from the desk and come back to it hours later.
   *
   * @param {boolean} late true when the deadline passed while Obsidian was shut. */
  finish(late) {
    const total = this.session.total;
    this.clearTick();
    this.session = { endsAt: null, pausedAt: null, total: null };
    this.render();
    this.save();

    const what = total ? ` (${formatHuman(total)})` : '';
    const base = this.settings.finishMessage.trim() || `Timer finished${what}`;
    new Notice(late ? `${base} — while Obsidian was closed.` : base, 8000);

    if (this.settings.chime && !late) chime(this.settings.volume);
    if (this.settings.systemNotification && !late) this.notifySystem(base);
  }

  /* An OS banner, for when Obsidian is behind another window and an in-app
   * Notice would go unseen. Permission is only ever requested as a result of
   * the user turning the setting on. */
  notifySystem(body) {
    try {
      if (typeof Notification === 'undefined') return;
      if (Notification.permission === 'granted') {
        new Notification('Midori Timer', { body });
      } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then((p) => {
          if (p === 'granted') new Notification('Midori Timer', { body });
        });
      }
    } catch (e) {
      /* not available on every platform */
    }
  }

  // --------------------------------------------------------------- display

  /* No element to build and no geometry to measure — the caret is already on
   * screen, drawn by midori-caret, and this only sets a variable it reads. The
   * designs this replaced each needed a fixed element, a live measurement of
   * the note's scroller, and a list of floating chrome to dodge. */
  renderCaret() {
    const wanted = this.settings.display === 'caret' || this.settings.display === 'both';
    const on = wanted && this.isActive();
    document.body.classList.toggle('midori-timer-running', on);
    if (!on) {
      document.body.style.removeProperty('--midori-timer-caret');
      this.caretKey = null;
      return;
    }

    const total = this.session.total || 0;
    const done = total <= 0 ? 0 : 1 - this.remaining() / total;
    const next = caretColor(done);

    // Write only when the mix actually changes: 100 steps a segment, ~300 in a
    // session, against 6000 ticks. Recomputing is free; assigning a custom
    // property invalidates style for the subtree every single time.
    if (next.key === this.caretKey) return;
    this.caretKey = next.key;
    document.body.style.setProperty('--midori-timer-caret', next.color);
  }

  buildStatusBar() {
    // On mobile Obsidian hides the status bar entirely, so skip the widget and
    // leave the commands — see the MOBILE note in the header.
    if (Platform.isMobile) return;

    this.el = this.addStatusBarItem();
    this.el.addClass('midori-timer');
    this.el.addClass('mod-clickable');

    this.iconEl = this.el.createSpan({ cls: 'midori-timer-icon' });
    setIcon(this.iconEl, 'clock');
    this.timeEl = this.el.createSpan({ cls: 'midori-timer-time' });

    this.el.addEventListener('click', () => {
      if (this.isActive()) this.toggle();
      else new DurationModal(this.app, this).open();
    });
    this.el.addEventListener('contextmenu', (ev) => {
      ev.preventDefault();
      this.contextMenu(ev);
    });
  }

  contextMenu(ev) {
    const menu = new Menu();
    menu.addItem((i) => i.setTitle('Set duration…').setIcon('timer')
      .onClick(() => new DurationModal(this.app, this).open()));
    if (this.isActive()) {
      menu.addItem((i) => i
        .setTitle(this.isPaused() ? 'Resume' : 'Pause')
        .setIcon(this.isPaused() ? 'play' : 'pause')
        .onClick(() => this.toggle()));
      menu.addItem((i) => i.setTitle('Add 5 minutes').setIcon('plus')
        .onClick(() => this.extend(300)));
    }
    if (this.isActive()) {
      menu.addItem((i) => i.setTitle('Stop').setIcon('square')
        .onClick(() => this.stop()));
    }
    menu.showAtMouseEvent(ev);
  }

  /* Decision 2. Reserve the width of the widest string this run can produce, so
   * the item keeps one width from 1:00:00 all the way down to 0:00 instead of
   * shrinking by a character and dragging its neighbours across. Measured in
   * `ch` against tabular figures, where one ch is exactly one digit. */
  reserveWidth(seconds) {
    if (!this.timeEl) return;
    this.timeEl.style.minWidth = `${formatClock(Math.max(0, seconds || 0)).length}ch`;
  }

  render() {
    this.renderCaret();
    if (!this.el) return;

    // The status bar item is emptied outright when the caret is the only
    // display, so Obsidian's `.status-bar-item:empty { display: none }` takes
    // it out of the bar rather than leaving a dead gap where it used to be.
    if (this.settings.display === 'caret') {
      this.el.removeClass('is-running');
      this.el.removeClass('is-paused');
      this.timeEl.setText('');
      this.timeEl.style.minWidth = '';
      this.iconEl.hide();
      this.el.removeAttribute('aria-label');
      return;
    }
    this.iconEl.show();

    this.el.removeClass('is-running');
    this.el.removeClass('is-paused');

    if (this.isActive()) {
      this.el.addClass(this.isPaused() ? 'is-paused' : 'is-running');
      this.iconEl.show();
      setIcon(this.iconEl, this.isPaused() ? 'pause' : 'clock');
      this.timeEl.setText(formatClock(this.remaining()));
      this.el.setAttr('aria-label',
        `${this.isPaused() ? 'Paused' : 'Timer'} — click to ${this.isPaused() ? 'resume' : 'pause'}, right-click for more`);
      return;
    }

    // Idle. Emptying the element makes Obsidian's own
    // `.status-bar-item:empty { display: none }` hide it, which is exactly the
    // behaviour the "show when idle" setting wants when it is off.
    this.timeEl.setText('');
    this.timeEl.style.minWidth = '';
    if (this.settings.showWhenIdle) {
      this.iconEl.show();
      setIcon(this.iconEl, 'clock');
      this.el.setAttr('aria-label', 'Set a timer');
    } else {
      this.iconEl.hide();
      this.el.removeAttribute('aria-label');
    }
  }
};

// ----------------------------------------------------------------- settings

class MidoriTimerSettings extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName('Default duration')
      .setDesc('Pre-filled in the duration window, and used by "Start timer with the default duration". Same formats: 25m, 1h30, 90s, 1:30.')
      .addText((t) => {
        t.setPlaceholder('25m')
          .setValue(formatHuman(this.plugin.settings.defaultDuration))
          .onChange(async (v) => {
            const secs = parseDuration(v);
            // Ignore unparseable input rather than clobbering a good value with
            // a half-typed one — onChange fires on every keystroke.
            if (secs == null) return;
            this.plugin.settings.defaultDuration = secs;
            await this.plugin.save();
          });
      });

    containerEl.createEl('h3', { text: 'Display' });

    new Setting(containerEl)
      .setName('Show the timer as')
      .setDesc('The caret drifts from its resting indigo through sage and ochre to wine as the session runs. Nothing is added to the page and nothing appears while you write: the caret is already there, and it is the one thing on screen your eye is resting on.')
      .addDropdown((d) => d
        .addOption('caret', 'Caret only')
        .addOption('statusbar', 'Status bar only')
        .addOption('both', 'Both')
        .setValue(this.plugin.settings.display)
        .onChange(async (v) => {
          this.plugin.settings.display = v;
          await this.plugin.save();
          this.plugin.render();
        }));

    new Setting(containerEl)
      .setName('Preview the drift')
      .setDesc('Runs a 20-second timer, compressing the whole indigo-to-wine drift into 20 seconds. Over a real session it is deliberately imperceptible; this is the only way to watch the whole ramp.')
      .addButton((b) => b.setButtonText('Run 20s').onClick(() => this.plugin.start(20)));

    containerEl.createEl('h3', { text: 'Status bar' });

    new Setting(containerEl)
      .setName('Show when idle')
      .setDesc('Keep a clock in the status bar while no timer is running, so there is something to click. Off hides it until a timer starts. Ignored when the caret is the only display.')
      .addToggle((t) => t
        .setValue(this.plugin.settings.showWhenIdle)
        .onChange(async (v) => {
          this.plugin.settings.showWhenIdle = v;
          await this.plugin.save();
          this.plugin.render();
        }));

    new Setting(containerEl)
      .setName('Chime')
      .setDesc('Play two short tones when the timer finishes.')
      .addToggle((t) => t
        .setValue(this.plugin.settings.chime)
        .onChange(async (v) => { this.plugin.settings.chime = v; await this.plugin.save(); }));

    new Setting(containerEl)
      .setName('Chime volume')
      .addSlider((s) => s
        .setLimits(0.05, 1, 0.05)
        .setValue(this.plugin.settings.volume)
        .setDynamicTooltip()
        .onChange(async (v) => { this.plugin.settings.volume = v; await this.plugin.save(); }));

    new Setting(containerEl)
      .setName('System notification')
      .setDesc('Also post an OS banner, so a finished timer is visible when Obsidian is behind another window. Your OS will ask for permission the first time.')
      .addToggle((t) => t
        .setValue(this.plugin.settings.systemNotification)
        .onChange(async (v) => {
          this.plugin.settings.systemNotification = v;
          await this.plugin.save();
          if (v) this.plugin.notifySystem('Notifications are on.');
        }));

    new Setting(containerEl)
      .setName('Finish message')
      .setDesc('Shown when the timer ends. Leave empty for "Timer finished (25m)".')
      .addText((t) => t
        .setPlaceholder('(default)')
        .setValue(this.plugin.settings.finishMessage)
        .onChange(async (v) => { this.plugin.settings.finishMessage = v; await this.plugin.save(); }));

    new Setting(containerEl)
      .setName('Hotkey')
      .setDesc('Bind "Midori Timer: Set duration and start" under Settings → Hotkeys to open the duration window from the keyboard.')
      .addButton((b) => b.setButtonText('Open duration window')
        .onClick(() => new DurationModal(this.app, this.plugin).open()));
  }
}
