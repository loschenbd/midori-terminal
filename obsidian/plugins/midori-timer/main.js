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
 *    THE RESERVE IS GONE, and its removal is the same decision as its
 *    addition. It existed because a proportional countdown changes width twice
 *    a second; the readout is now a board of fixed-width cards, so its width
 *    changes only when a CELL is dropped — at 1:00:00 to 59:59, and at 10:00 to
 *    9:59. Twice in a session, not twice a second. Reserving for that costs a
 *    permanently visible gap beside the cards, because reserved emptiness that
 *    was invisible in a run of text is perfectly visible next to objects. Two
 *    rare one-cell shifts is the cheaper of the two.
 *
 *    The readout is the SAME split-flap board as the setting window, at one
 *    seventh the size — see FlapBoard and the bar variant in the stylesheet.
 *    The flip is a setting, because motion at the edge of vision is the one
 *    thing the caret display exists to avoid, and off it is genuinely off —
 *    see FlapBoard.still for why that cannot be done by hiding the animation
 *    in CSS.
 *
 * 3. SET IT BY DRAGGING, OR BY TYPING, AND NEVER ONLY ONE. The window is a
 *    row of drums you flick — real scroll containers, so the momentum and
 *    snapping are the platform's — reading out through a split-flap clock. But
 *    the plugin's premise is a duration you TYPE, opened by a hotkey, so the
 *    field stays autofocused and Enter still submits the instant the window
 *    opens. Each drives the other, and with hours, minutes and seconds all on
 *    drums, everything under a day is now reachable either way.
 *
 *    AND TWO WAYS TO SAY IT. "For 25 minutes" and "until 1pm" are the two forms
 *    a session takes in the head, and neither is a special case of the other,
 *    so both are first-class: a segmented control, two sets of drums, one
 *    field that parses whichever the mode expects. Until-mode works out the
 *    exact hours, minutes and seconds to the target and hands that to the same
 *    machinery — so downstream there is still only a number of seconds, and
 *    switching modes carries the value across rather than resetting it.
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
 * (`.is-mobile .status-bar { display: none }` in app.css) and offers no other
 * surface a plugin can park a persistent item in. So on a phone there is no
 * readout at all: the caret is the display, which is what it is on desktop by
 * default anyway.
 *
 * THIS WAS TRIED THE OTHER WAY AND WITHDRAWN. The readout was homed in the
 * note's own header, beside the reading-mode and overflow buttons, on the
 * grounds that it was existing chrome rather than the writing surface. It was
 * removed on sight in use, and the reason is the same one that retired six
 * painted timer designs: the header is where the eye goes to leave the note,
 * and a countdown parked there is a persistent thing to look at that nobody
 * asked to see. Fitting it took four rounds of specificity and geometry
 * fights, which was the tell — a control that has to be argued into a row it
 * does not belong in. The caret needs none of that. It is the same caret on a
 * phone, which is the other reason it is the default.
 *
 * The setting window needs two concessions there, both about the keyboard.
 * It is NOT autofocused, because summoning the keyboard covers the drums and
 * the flaps — the control you came for, hidden by one you did not ask for. And
 * when the keyboard is opened deliberately, the window is lifted by exactly the
 * overlap, measured off visualViewport: a software keyboard does not resize the
 * layout viewport, so no media query and no CSS knows it is there. The drums
 * are also shorter on a phone, which is one number — see --drum-h.
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
  barFlap: true,              // flip the status-bar readout, or just replace it
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

/* Clock-time entry: "until 1pm" rather than "for 25 minutes".
 *
 * NOW IS A PARAMETER, not Date.now() read inside. Every interesting case here
 * is about the relationship between the target and the current time — the
 * rollover past midnight, which meridiem is meant, whether 1:00 has already
 * happened today — and none of them can be tested at all if the function reads
 * the clock itself. The one caller passes Date.now().
 */
const CLOCK_RE = /^(\d{1,2})(?::(\d{2}))?\s*(am|pm|a|p)?$/i;

/**
 * "1pm", "13:00", "1:30 pm", "noon" -> the next Date at that wall-clock time.
 * Returns null if it is not a time. Always strictly in the future.
 */
function parseClockTime(raw, now) {
  const text = String(raw == null ? '' : raw).trim().toLowerCase().replace(/\./g, '');
  if (!text) return null;

  let hour;
  let minute = 0;
  let meridiem = null;

  if (text === 'noon' || text === 'midday') {
    hour = 12;
  } else if (text === 'midnight') {
    hour = 0;
  } else {
    const m = CLOCK_RE.exec(text);
    if (!m) return null;
    hour = Number(m[1]);
    minute = m[2] == null ? 0 : Number(m[2]);
    meridiem = m[3] ? m[3][0] : null;          // "am"/"a" -> "a"
    if (minute > 59) return null;
    if (meridiem && (hour < 1 || hour > 12)) return null;
    if (!meridiem && hour > 23) return null;
  }

  const base = new Date(now);
  const at = new Date(now);
  at.setSeconds(0, 0);
  at.setMinutes(minute);

  if (meridiem) {
    at.setHours((hour % 12) + (meridiem === 'p' ? 12 : 0));
  } else if (hour >= 1 && hour <= 12) {
    /* A bare "1" could mean either 01:00 or 13:00, and the useful answer is
     * whichever comes round first — the kitchen-timer reading. Try both and
     * take the soonest that is still ahead.
     *
     * HOUR 0 IS EXCLUDED, and that is not an off-by-one. "0:15" and "midnight"
     * are 24-hour notation, which is unambiguous: nobody writing 0 means 12.
     * Letting it into this branch pairs 00:15 against 12:15 and picks the
     * sooner one, so "midnight" came back as noon. */
    const candidates = [hour % 12, (hour % 12) + 12].map((h) => {
      const c = new Date(at);
      c.setHours(h);
      if (c <= base) c.setDate(c.getDate() + 1);
      return c;
    });
    return candidates.sort((a, b) => a - b)[0];
  } else {
    at.setHours(hour);
  }

  if (at <= base) at.setDate(at.getDate() + 1);  // already gone today
  return at;
}

/** Whole seconds from `now` until `target`, never negative. */
function secondsUntil(target, now) {
  return Math.max(0, Math.round((target.getTime() - now) / 1000));
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
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
  display: inline-flex;
}

/* The bar's board is the SAME cells as the window's, at one seventh the size
   and with nothing taken away. It keeps the card, the seam and the radius: a
   flip card that is only a flipping glyph is a flourish, and a flip card that
   is a card is an OBJECT — a small mechanical clock parked in the status bar,
   which is what it is meant to read as. Scaling it down is a matter of
   numbers, and the numbers are here.

   Every half stays painted, which is also what makes the fold work at all. A
   fold works by COVERING: the old top swings down over the new glyph and the
   new bottom swings up over the old one. Halves that are transparent do not
   cover, they superimpose — two digits showing through each other, a double
   exposure rather than a card turning. */
/* THE CARD'S PROPORTIONS ARE FOUR NUMBERS, STATED ONCE. Width, height,
   separator width and gap have to move together — raise the height alone and
   the glyph's line-height stops matching its own card — and there are two
   places that want a different set: a desktop status bar, and a phone's note
   header, which is a much larger and more generously spaced row. Naming them
   makes the second place one block of values rather than six overrides hunted
   through the sheet. */
.midori-timer-flaps.is-bar {
  --flap-w: 0.76em;
  --flap-h: 1.32em;
  --flap-sep: 0.24em;
  --flap-gap: 0.09em;
  --flap-radius: 2px;

  gap: var(--flap-gap);
  margin: 0;
  perspective: 60px;                /* shallower: the cards are ~9px tall */
}
.midori-timer-flaps.is-bar .midori-timer-flap {
  width: var(--flap-w);
  height: var(--flap-h);
  font-size: inherit;
  color: inherit;
}
.midori-timer-flaps.is-bar .midori-timer-flap.is-sep {
  width: var(--flap-sep);
}

/* THE CARD IS MIXED, NOT NAMED, and that took three tries to get right.

   Naming a surface variable was wrong twice. --background-modifier-form-field,
   which the window's cards use, sits a hair off --background-secondary — and a
   status bar is --background-secondary, so those cards were invisible against
   it and all that survived was the seam: a hairline straight through the
   middle of every digit, reading as a strikethrough. Switching to
   --background-primary fixed the harness and not the app, because THIS theme
   sets '.status-bar { background-color: transparent }' — the bar shows the
   PAGE ground, which is exactly --background-primary. Same bug, other colour.

   There is no surface variable reliably distinct from a ground a theme is free
   to redefine, so the card is derived from the ground: lifted off it, the way
   a real card sits on the desk it is lying on. It stays fully OPAQUE, which a
   translucent tint would not — the fold has to cover the glyph beneath it, not
   filter it.

   TWO AMOUNTS, ONE DIRECTION, and the second table is unavoidable rather than
   lazy. "Lighter" is one instruction, but the room to obey it is not
   symmetric: Midori Paper's ground is #f3f1eb, twelve points of headroom below
   white, while Night's #1a1917 has almost the whole range. A single percentage
   toward white is either invisible on paper or a floodlight at night. So the
   mix is stated per theme and the DIRECTION is what stays constant.

   It is stated as a custom property rather than as two background rules, so
   that the theme branch and the is-sep exception cannot end up tied on
   specificity and settled by document order. */
.midori-timer-flaps.is-bar {
  --midori-flap-card: color-mix(in oklab, #fff 85%, var(--background-primary));
}
.theme-dark .midori-timer-flaps.is-bar {
  --midori-flap-card: color-mix(in oklab, var(--text-normal) 9%, var(--background-primary));
}
.midori-timer-flaps.is-bar .midori-timer-flap-half {
  background: var(--midori-flap-card);
}
/* The colon is not a card. Stated at (0,4,0) rather than left to the tie it
   would otherwise have with the rule above, which document order happens to
   resolve correctly today and would stop doing the moment either block moves. */
.midori-timer-flaps.is-bar .midori-timer-flap.is-sep .midori-timer-flap-half {
  background: none;
}
.midori-timer-flaps.is-bar .midori-timer-flap-half > span { line-height: var(--flap-h); }

/* Radius scaled to the card. 4px on a 9px half is a lozenge; 2px reads as a
   corner. The seam stays the theme's hairline, which at this size is most of
   what says "two halves" at all. */
.midori-timer-flaps.is-bar .midori-timer-flap-top {
  border-radius: var(--flap-radius) var(--flap-radius) 0 0;
}
.midori-timer-flaps.is-bar .midori-timer-flap-bottom {
  border-radius: 0 0 var(--flap-radius) var(--flap-radius);
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

  /* THE DRUM'S HEIGHT, STATED ONCE. Four rules depend on it — the drum, the
     scroller's padding, the shared band and the colons — and they were four
     separate literals that had to be edited together or the band would sit off
     the selected row and the end values would stop being reachable. The item
     height stays a literal because it is DRUM_ITEM in the JS, which does the
     scroll arithmetic and cannot read a CSS variable. */
  --drum-h: 170px;
  --drum-item: 34px;                /* = DRUM_ITEM */
}

/* Phones are shorter and the keyboard takes half of what is left, so the drums
   give back what they can spare. One number, because of the block above. */
.is-mobile .midori-timer-dial { --drum-h: 136px; }

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

/* SUPPRESSING THE FLIP IS DONE IN JS, NOT HERE, and the reason is worth
   stating where the temptation is. Hiding the two animated halves with
   'prefers-reduced-motion: reduce { display: none }' looks like the
   obvious fix and leaves a real defect: the STATIC halves still update 90ms
   apart, because the lower one is deliberately late so the fold can cover it.
   With the animation hidden there is nothing covering it, so for 90ms the top
   of the glyph is the new digit and the bottom is the old one — a torn
   character, every second. FlapBoard.flip sets both halves at once instead;
   see FlapBoard.still. */

.midori-timer-echo {
  text-align: center;
  font-size: var(--font-ui-small, 0.85em);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  min-height: 1.5em;
}
.midori-timer-echo b { color: var(--text-normal); font-weight: var(--font-semibold, 600); }
.midori-timer-dial.is-bad .midori-timer-echo { color: var(--color-red); }

/* ---- the mode switch -------------------------------------------------

   Two ways to say the same thing: how long, or until when. Neither is a
   sub-mode of the other, so this is a segmented control rather than a checkbox
   tucked under the field. */
.midori-timer-modes {
  display: flex;
  gap: 2px;
  padding: 2px;
  border-radius: 8px;
  background: var(--background-modifier-form-field, var(--background-secondary));
}
.midori-timer-modes button {
  flex: 1;
  padding: 5px 0;
  border: 0;
  border-radius: 6px;
  background: none;
  box-shadow: none;
  color: var(--text-muted);
  font-size: var(--font-ui-small, 0.87em);
  cursor: pointer;
}
.midori-timer-modes button.is-on {
  background: var(--background-primary);
  color: var(--text-normal);
  font-weight: var(--font-semibold, 600);
}

/* ---- the drum --------------------------------------------------------

   A REAL SCROLL CONTAINER, which is the whole implementation decision. Native
   overflow plus scroll-snap gives momentum, rubber-banding, wheel support,
   trackpad inertia and touch flinging for free, and every one of those is
   miserable to hand-write and never quite right when you do. The only custom
   code is pointer-drag, because a mouse press does not scroll a div.

   The padding is what lets the first and last values reach the centre band. It
   has to be (height - item) / 2 exactly, or the ends cannot be selected. */
/* Several drums sit side by side — hours, minutes, seconds — and each is an
   independent scroller. They share one band drawn across the whole row rather
   than one per column, because the row reads as a single instrument that way
   instead of as three controls that happen to be adjacent. */
.midori-timer-drums {
  position: relative;
  display: flex;
  gap: 2px;
}
.midori-timer-drums.is-hidden { display: none; }

/* Centred on the DRUM, not on the row. The row is taller than the drums by the
   height of the captions beneath them, so top: 50% would sit the band half a
   caption low. 85px is the drum's own half-height, stated once. */
.midori-timer-drums .midori-timer-drum-band {
  left: 0;
  right: 0;
  top: calc(var(--drum-h) / 2);
}
.midori-timer-column {
  flex: 1;
  min-width: 0;
}
.midori-timer-column.is-narrow { flex: 0 0 3.2em; }

/* Captions are LABELS, so they are set as labels: uppercase, tracked out, and
   small enough that they never compete with the digits above them for the
   first read. Set as lowercase running text they read as content. */
.midori-timer-caption {
  text-align: center;
  font-size: 0.68em;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-faint, var(--text-muted));
  margin-top: 3px;
}

/* Outside the columns, so it does not scroll with them, and vertically on the
   band rather than on the row — the row is taller by the captions' height. */
.midori-timer-drum-colon {
  flex: 0 0 auto;
  height: var(--drum-h);
  display: flex;
  align-items: center;
  padding: 0 1px;
  color: var(--text-faint, var(--text-muted));
  font-size: 1.1em;
  user-select: none;
}
.midori-timer-drum {
  position: relative;
  height: var(--drum-h);
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

  /* (height - item) / 2, so the first and last values can reach the centre
     band. box-sizing matters here and is not decoration: under content-box,
     height 100% plus this padding makes clientHeight 306 rather than 170, and
     anything measuring the scroller to centre an item lands two items out. The
     JS avoids measuring at all (see Drum.set), and this keeps the two agreeing. */
  box-sizing: border-box;
  padding: calc((var(--drum-h) - var(--drum-item)) / 2) 0;
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
  height: var(--drum-item);
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
  height: var(--drum-item);
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
  margin-top: 5px;
  text-align: center;
  font-size: 0.72em;
  letter-spacing: 0.03em;
  color: var(--text-faint, var(--text-muted));
}
.midori-timer-start {
  width: 100%;
  margin-top: 0.3em;
  padding: 0.6em 0;
  font-weight: var(--font-semibold, 600);
}

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
const DRUM_ITEM = 34;               // px, and must match the stylesheet
const FLAP_MS = 90;                 // per half-fold; a full flip is twice this


/* Does this reader's locale put the clock on a 12-hour dial? It decides whether
 * the "until" drums carry an AM/PM column, and it is asked of Intl rather than
 * guessed from the language, because the two disagree often enough to matter. */
function usesTwelveHour() {
  try {
    const o = new Intl.DateTimeFormat([], { hour: 'numeric' }).resolvedOptions();
    return o.hour12 !== false && o.hourCycle !== 'h23' && o.hourCycle !== 'h24';
  } catch (e) {
    return true;
  }
}

/**
 * One column of a picker: a scroll container whose selected value is whatever
 * sits under the band.
 *
 * POSITION AND VALUE ARE PURE ARITHMETIC IN BOTH DIRECTIONS, never measured.
 * The obvious centring formula reads clientHeight, which INCLUDES PADDING — and
 * these scrollers are mostly padding, so that the first and last values can
 * reach the band. Under content-box sizing clientHeight came back 306 rather
 * than 170, every scroll landed two items short, and because the scroll handler
 * writes what it finds back into state, the window quietly rewrote its own
 * default on open. A measurement bug in a control that feeds itself does not
 * look like a measurement bug; it looks like the setting not sticking.
 *
 * So centring row i is scrollTop = 34i exactly, and the inverse is one
 * division. The only thing they depend on is the stylesheet's padding being
 * (height - item) / 2, which box-sizing: border-box there keeps true.
 */
class Drum {
  /** @param {{text: string, value: any}[]} rows */
  constructor(host, rows, caption, onPick, onTouch) {
    this.rows = rows;
    this.onPick = onPick;
    this.onTouch = onTouch || (() => {});
    this.column = host.createDiv({ cls: 'midori-timer-column' });
    this.el = this.column.createDiv({ cls: 'midori-timer-drum' });
    this.scroller = this.el.createDiv({ cls: 'midori-timer-drum-scroll' });
    this.items = rows.map((row) => {
      const it = this.scroller.createDiv({ cls: 'midori-timer-drum-item', text: row.text });
      it.addEventListener('click', () => {
        // A press that caught a spinning drum has already done its job.
        if (this.caught) { this.caught = false; return; }
        this.set(row.value);
      });
      return it;
    });
    if (caption) this.column.createDiv({ cls: 'midori-timer-caption', text: caption });
    this.index = 0;
    this.v = 0;                     // px per frame, carried out of a drag
    this.glide = null;              // rAF id of a throw in flight
    this.caught = false;            // did the last press stop one?

    // One read per frame. A scroll event fires many times between paints and
    // each read would otherwise cost a layout, which makes a fling stutter.
    let queued = false;
    this.scroller.addEventListener('scroll', () => {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(() => {
        queued = false;
        const idx = this.centreIndex();
        if (idx === this.index) return;
        this.index = idx;
        this.paint();
        this.onPick(this.value(), 'scroll');
      });
    }, { passive: true });

    /* Announce that a HUMAN moved this drum, before any value has changed. The
     * owner needs to know the difference between a scroll it caused and a
     * scroll the reader caused — without it, positioning a drum from typed
     * text scrolls it, the scroll reads back, and the read-back overwrites the
     * half-typed text under the cursor. */
    ['pointerdown', 'wheel', 'touchstart'].forEach((ev) => {
      this.scroller.addEventListener(ev, () => this.onTouch(), { passive: true });
    });

    this.drag();
    this.paint();
  }

  value() { return this.rows[this.index].value; }

  centreIndex() {
    const i = Math.round(this.scroller.scrollTop / DRUM_ITEM);
    return Math.max(0, Math.min(this.rows.length - 1, i));
  }

  set(value, behavior, silent) {
    const idx = this.rows.findIndex((r) => r.value === value);
    if (idx < 0) return;
    this.settle();                  // a throw in flight would undo this
    const changed = idx !== this.index;
    this.index = idx;                           // BEFORE the scroll, so the
    this.paint();                               // resulting event reads as a no-op
    this.scroller.scrollTo({ top: idx * DRUM_ITEM, behavior: behavior || 'smooth' });
    if (changed && !silent) this.onPick(this.value(), 'set');
  }

  paint() {
    this.items.forEach((it, i) => {
      const d = Math.abs(i - this.index);
      it.toggleClass('is-sel', d === 0);
      it.toggleClass('is-near', d === 1);
    });
  }

  /* Pointer-drag and the throw that follows it — the two things native
   * scrolling does not provide to a mouse. A trackpad and a finger both hand
   * the platform a velocity on release and get momentum for free; a mouse
   * button hands it nothing, so a flicked drum stopped dead the instant the
   * button came up, which is the one thing that makes a dial feel like a list
   * of rows instead of a wheel.
   *
   * VELOCITY IS SMOOTHED, NOT SAMPLED. Taking the last move's distance as the
   * throw speed makes the result depend on where in the frame the button
   * happened to come up: the same gesture flies or dies depending on whether
   * the final event carried 14px or 1px. An exponential average over the moves
   * is stable across that, and pointermove arrives about once a frame, so the
   * unit is already px per frame — the same unit the glide steps in.
   *
   * SNAPPING STAYS OFF FOR THE WHOLE THROW, not just the drag. Restoring it
   * while the drum is still moving hauls it to the nearest row mid-flight; it
   * goes back on when the glide ends, which is also what settles the drum onto
   * a value. See the is-dragging rule in the stylesheet. */
  drag() {
    const el = this.scroller;
    let down = false;
    let last = 0;

    el.addEventListener('pointerdown', (ev) => {
      if (ev.button !== 0) return;
      // A press on a moving drum stops it, as it does on a phone. The flag is
      // read by the row click handler, so the press that catches a spinning
      // drum does not also select whatever row it was passing.
      this.caught = this.caught || this.glide != null;
      this.stop();
      down = true;
      last = ev.clientY;
      this.v = 0;
      el.setPointerCapture(ev.pointerId);
      el.addClass('is-dragging');
    });

    el.addEventListener('pointermove', (ev) => {
      if (!down) return;
      const dy = ev.clientY - last;
      last = ev.clientY;
      el.scrollTop -= dy;
      this.v = this.v * 0.7 + dy * 0.3;
    });

    const up = (ev) => {
      if (!down) return;
      down = false;
      try { el.releasePointerCapture(ev.pointerId); } catch (e) { /* already gone */ }
      if (Math.abs(this.v) > 1.5) this.throw();  // below that it is a placement
      else this.settle();
    };
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
  }

  /* Coast to a stop under friction.
   *
   * 0.96 A FRAME IS A LONG TAIL ON PURPOSE. It is a 25-frame e-folding and a
   * total run of about 25x the release speed: a firm flick carries fifteen
   * rows over roughly a second and a half, which is the difference between a
   * dial that keeps rolling and one that coasts politely to a halt. It can
   * afford to be long because it is trivially interruptible — a press anywhere
   * in the window stops it dead, so overshooting costs a tap rather than
   * another gesture in the opposite direction. */
  throw() {
    const el = this.scroller;
    const max = (this.rows.length - 1) * DRUM_ITEM;
    const step = () => {
      this.v *= 0.96;
      el.scrollTop -= this.v;
      // Stop at the ends rather than grinding against them: a drum pinned at 0
      // with a live glide behind it swallows the next flick.
      const done = Math.abs(this.v) < 0.25 || el.scrollTop <= 0 || el.scrollTop >= max;
      if (done) { this.settle(); return; }
      this.glide = window.requestAnimationFrame(step);
    };
    this.glide = window.requestAnimationFrame(step);
  }

  /** Cancel any throw in flight, leaving the drum exactly where it is. */
  stop() {
    if (this.glide == null) return;
    window.cancelAnimationFrame(this.glide);
    this.glide = null;
  }

  /** Hand the drum back to the platform: snap returns and pulls it onto a row. */
  settle() {
    this.stop();
    this.v = 0;
    this.scroller.removeClass('is-dragging');
  }
}

const range = (from, to, pad) => {
  const rows = [];
  for (let v = from; v <= to; v += 1) {
    rows.push({ value: v, text: pad ? String(v).padStart(2, '0') : String(v) });
  }
  return rows;
};

/* A duration the drums can hold: one second under a full day. Typing more than
 * that clamps rather than desyncing the drums from the value they feed. */
const MAX_SECONDS = 24 * 3600 - 1;

const clockLabel = (d) => d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
const sameDay = (a, b) => a.getFullYear() === b.getFullYear()
  && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

/**
 * The set-timer window.
 *
 * TWO WAYS TO SAY THE SAME THING. "For 25 minutes" and "until 1pm" are the two
 * ways people actually hold a session in their head, and neither is a special
 * case of the other, so both are first-class: a segmented control, two sets of
 * drums, and one typed field that parses whichever the current mode expects.
 *
 * ONE VALUE UNDERNEATH THEM BOTH. Everything downstream wants a number of
 * seconds, so `seconds` is the state and the mode only decides how it is
 * arrived at and described. Switching modes carries the value across rather
 * than resetting it — 25 minutes becomes the clock time 25 minutes from now,
 * and back again — so the switch is a change of framing, not of intent.
 */
/* The split-flap board, on two surfaces.
 *
 * Each glyph is a card split across the middle. Four layers per cell: the
 * static top showing the NEW glyph, the static bottom still showing the OLD
 * one, and two throwaway halves that animate over them — the old top folding
 * down over the seam, then the new bottom unfolding from behind it. Only the
 * second half of the movement reveals the new lower glyph, which is what sells
 * it as one physical card rather than two things swapping.
 *
 * WHY IT IS A CLASS. It reads the duration in the setting window, where it is
 * 2.6em and changes as fast as a drum can be flicked, and it reads the
 * countdown in the status bar, where it is 13px and changes once a second.
 * Those are the same mechanism at different sizes, and the size is the only
 * thing the two callers differ on, so it is one implementation with a variant
 * class rather than two that drift.
 */
class FlapBoard {
  constructor(host, variant) {
    this.el = host.createDiv({ cls: 'midori-timer-flaps' + (variant ? ' ' + variant : '') });
    this.cells = [];
    this.shown = '';
    this.still = false;             // set by the caller; see flip()
    this.reduce = window.matchMedia
      ? window.matchMedia('(prefers-reduced-motion: reduce)')
      : { matches: false };
  }

  /* Render `text`, animating ONLY the cells whose glyph changed. Re-rendering
   * every cell flips the unchanged ones too, and a whole board flapping when
   * only the seconds moved reads as noise rather than as a mechanism.
   *
   * Rebuilds the row only when the LENGTH changes — 9:59 to 10:00 adds a digit
   * and every cell shifts, so there is nothing left to preserve. */
  set(text, force) {
    if (force || text.length !== this.cells.length) {
      this.el.empty();
      this.cells = [...text].map((ch) => {
        const cell = this.el.createDiv({ cls: 'midori-timer-flap' });
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
      this.flip(this.cells[i], this.shown[i], text[i]);
    }
    this.shown = text;
  }

  /* One card turning over.
   *
   * THE TIMERS ARE TRACKED AND CLEARED, not left to unwind on their own. A flip
   * schedules two callbacks, and a fast scroll starts a new flip on the same
   * cell long before they fire. Left alone they still happen to converge,
   * because setTimeout preserves scheduling order and the last one scheduled
   * carries the newest glyph — but that is an argument, not a guarantee, and it
   * stops being true the moment anything here gains a different delay. Clearing
   * them makes the cell's state depend only on the flip currently running. */
  flip(cell, from, to) {
    const top = cell.querySelector('.midori-timer-flap-top');
    const bottom = cell.querySelector('.midori-timer-flap-bottom');
    top.firstElementChild.setText(to);

    // Cancel the flip still in the air rather than queueing behind it: queued
    // flips fall behind a fast scroll and keep flapping after the drum stops.
    if (cell.midoriTimers) cell.midoriTimers.forEach((id) => window.clearTimeout(id));
    cell.querySelectorAll('.midori-timer-flap-fold, .midori-timer-flap-unfold')
      .forEach((el) => el.remove());

    /* NOT ANIMATING MEANS SETTING BOTH HALVES AT ONCE, and this is the part
     * that cannot be done in CSS. The lower half is deliberately late — it
     * changes once the fold has covered it — so hiding the fold without
     * changing this leaves the top of the glyph showing the new digit and the
     * bottom showing the old one for 90ms: a torn character, once a second.
     * Here the card just is the new glyph, which is what a stopped mechanism
     * should look like. */
    if (this.still || this.reduce.matches) {
      bottom.firstElementChild.setText(to);
      return;
    }

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

}

class DurationModal extends Modal {
  constructor(app, plugin) {
    super(app);
    this.plugin = plugin;
    this.mode = 'for';
    this.seconds = plugin.settings.defaultDuration;
    this.target = null;             // the Date being counted down to, in until
    this.twelve = usesTwelveHour();
    this.lastTouched = 'type';      // which control the human moved last
  }

  onOpen() {
    const { contentEl, titleEl } = this;
    titleEl.setText('Set timer');

    this.root = contentEl.createDiv({ cls: 'midori-timer-dial' });

    const modes = this.root.createDiv({ cls: 'midori-timer-modes' });
    this.forBtn = modes.createEl('button', { text: 'For a length' });
    this.untilBtn = modes.createEl('button', { text: 'Until a time' });
    this.forBtn.addEventListener('click', () => this.setMode('for'));
    this.untilBtn.addEventListener('click', () => this.setMode('until'));

    this.board = new FlapBoard(this.root);
    this.echoEl = this.root.createDiv({ cls: 'midori-timer-echo' });

    const pick = () => this.fromDrums();
    const touch = () => { this.lastTouched = 'drum'; };

    // The colons are what make three scrollers read as one clock rather than
    // as three adjacent controls. They sit outside the columns so they do not
    // scroll, and they are aria-hidden because the captions already say it.
    const colon = (host) => host.createDiv({ cls: 'midori-timer-drum-colon', text: ':' })
      .setAttribute('aria-hidden', 'true');

    this.forDrums = this.root.createDiv({ cls: 'midori-timer-drums' });
    this.dH = new Drum(this.forDrums, range(0, 23), 'hours', pick, touch);
    colon(this.forDrums);
    this.dM = new Drum(this.forDrums, range(0, 59, true), 'minutes', pick, touch);
    colon(this.forDrums);
    this.dS = new Drum(this.forDrums, range(0, 59, true), 'seconds', pick, touch);
    this.forDrums.createDiv({ cls: 'midori-timer-drum-band' });

    /* The until drums carry no seconds column. A target is stated to the
     * minute — nobody sets a timer for 1:00:37pm — and the seconds are what
     * the DURATION picks up, which is the whole point of stating it this way. */
    this.untilDrums = this.root.createDiv({ cls: 'midori-timer-drums' });
    this.uH = new Drum(this.untilDrums, this.twelve ? range(1, 12) : range(0, 23),
      'hour', pick, touch);
    colon(this.untilDrums);
    this.uM = new Drum(this.untilDrums, range(0, 59, true), 'minute', pick, touch);
    this.uAP = this.twelve
      ? new Drum(this.untilDrums,
        [{ value: 'am', text: 'AM' }, { value: 'pm', text: 'PM' }], '\u00a0', pick, touch)
      : null;
    if (this.uAP) this.uAP.column.addClass('is-narrow');
    this.untilDrums.createDiv({ cls: 'midori-timer-drum-band' });

    this.input = this.root.createEl('input', { cls: 'midori-timer-type', type: 'text' });
    this.input.spellcheck = false;
    this.input.addEventListener('input', () => {
      this.lastTouched = 'type';
      const raw = this.input.value.trim();
      if (this.mode === 'for') {
        const secs = parseDuration(raw);
        if (secs != null) this.seedFor(secs);
      } else {
        const at = parseClockTime(raw, Date.now());
        if (at) this.seedUntil(at);
      }
      this.render();                            // show the error, keep the value
    });

    /* The ramp is the only place this design explains itself, now that the
     * running timer is a colour drift on the caret and says nothing. A
     * two-ended legend kept trying to label the gradient's endpoints, which is
     * both wrong (it is continuous) and unreadable at this size; one sentence
     * naming what the strip IS does the job. */
    const ramp = this.root.createDiv({ cls: 'midori-timer-ramp' });
    ramp.createDiv({ cls: 'midori-timer-ramp-bar' });
    ramp.createDiv({ cls: 'midori-timer-ramp-legend',
      text: 'your caret, across the session' });

    this.startEl = this.root.createEl('button', { cls: 'midori-timer-start' });
    this.startEl.addClass('mod-cta');
    this.startEl.addEventListener('click', () => this.submit());

    // Enter submits from anywhere in the window. Escape is Obsidian's already.
    this.scope.register([], 'Enter', (ev) => { ev.preventDefault(); this.submit(); return false; });

    /* A CLICK ANYWHERE IN THE WINDOW STOPS EVERY DRUM, which is how a phone
     * behaves and is the only way to catch a throw you did not aim. In capture,
     * so it runs before the drum's own handler and before any row click; each
     * drum it actually stops is marked as having caught the press, so that
     * press selects nothing. */
    this.root.addEventListener('pointerdown', () => {
      this.drums().forEach((d) => {
        if (d.glide != null) d.caught = true;
        d.settle();
      });
    }, true);

    this.paintMode();                           // must precede the first seed
    this.seedFor(this.seconds);
    this.render(true);
    this.watchKeyboard();

    /* NOT ON A PHONE. On desktop the premise is a duration you type, opened by
     * a hotkey, so the field is focused before you can reach for it. On a phone
     * the same line summons the software keyboard, which covers the drums, the
     * flaps and half the window — the control you actually came to use, hidden
     * by the one you did not ask for. Tapping the field still opens it. */
    if (!Platform.isMobile) window.setTimeout(() => { this.input.focus(); }, 0);
  }

  /* Keep the field above the keyboard when it does open.
   *
   * A software keyboard does not resize the LAYOUT viewport, so nothing in CSS
   * knows it is there and the window stays centred on a screen half of which is
   * now covered. What it does resize is the VISUAL viewport, which is why this
   * is visualViewport rather than a resize listener or a media query.
   *
   * The window is lifted by exactly the overlap, and no further: enough to put
   * the field in the clear, so as much of the drums and the flaps stays on
   * screen as the keyboard leaves room for. The lift is also clamped to the
   * distance to the top of the screen, because a window pushed off the top is
   * not an improvement on one pushed off the bottom. */
  watchKeyboard() {
    const vv = window.visualViewport;
    if (!vv) return;

    const lift = () => {
      const el = this.modalEl;
      if (!el) return;
      el.style.transform = '';                  // measure where it truly sits
      if (document.activeElement !== this.input) return;
      const field = this.input.getBoundingClientRect();
      const over = field.bottom + 10 - (vv.offsetTop + vv.height);
      if (over <= 0) return;
      const room = Math.max(0, el.getBoundingClientRect().top - 8);
      el.style.transform = `translateY(${-Math.min(over, room)}px)`;
    };

    // The keyboard animates in, so the first measurement has to wait for it.
    this.input.addEventListener('focus', () => window.setTimeout(lift, 260));
    this.input.addEventListener('blur', lift);
    vv.addEventListener('resize', lift);
    vv.addEventListener('scroll', lift);
    this.unwatchKeyboard = () => {
      vv.removeEventListener('resize', lift);
      vv.removeEventListener('scroll', lift);
    };
  }

  /** Every drum in the window, both modes, so callers need not know the shape. */
  drums() {
    return [this.dH, this.dM, this.dS, this.uH, this.uM, this.uAP].filter(Boolean);
  }

  // ------------------------------------------------------------------ mode

  setMode(mode) {
    if (mode === this.mode) return;
    this.mode = mode;
    this.lastTouched = 'drum';                  // so the field is re-worded
    // SEED AFTER UNHIDING. scrollTo on a display:none element is a no-op, so
    // the drums have to be on screen before they can be positioned.
    this.paintMode();
    if (mode === 'until') {
      const at = new Date(Date.now() + this.seconds * 1000);
      at.setSeconds(0, 0);                      // the drums only go to minutes
      if (at.getTime() <= Date.now()) at.setMinutes(at.getMinutes() + 1);
      this.seedUntil(at);
    } else {
      this.seedFor(this.seconds);
    }
    this.input.value = this.fieldText();
    this.render();
    this.input.focus();
  }

  paintMode() {
    const isFor = this.mode === 'for';
    this.forBtn.toggleClass('is-on', isFor);
    this.untilBtn.toggleClass('is-on', !isFor);
    this.forDrums.toggleClass('is-hidden', !isFor);
    this.untilDrums.toggleClass('is-hidden', isFor);
    this.input.placeholder = isFor
      ? 'or type 25m, 1h30, 90s, 1:30'
      : 'or type 1pm, 1:30pm, 13:45, noon';
  }

  fieldText() {
    return this.mode === 'for' ? formatHuman(this.seconds)
      : (this.target ? clockLabel(this.target) : '');
  }

  // ----------------------------------------------------------------- drums

  /* Seeding writes the drums INSTANTLY, not smoothly, and that is a
   * correctness choice rather than a taste one. A smooth scroll passes through
   * every intermediate row, each of which fires a scroll event, and each of
   * those would be read back as a value the human never chose — overwriting
   * the field mid-keystroke. Landing on the row in one step means the only
   * scroll event that arrives already reads the value we just wrote, and the
   * drum's own idx-unchanged check swallows it. */
  seedFor(secs) {
    const s = Math.max(0, Math.min(MAX_SECONDS, Math.round(secs)));
    this.seconds = s;
    this.dH.set(Math.floor(s / 3600), 'auto', true);
    this.dM.set(Math.floor((s % 3600) / 60), 'auto', true);
    this.dS.set(s % 60, 'auto', true);
  }

  seedUntil(at) {
    this.target = at;
    this.seconds = secondsUntil(at, Date.now());
    const h = at.getHours();
    if (this.twelve) {
      this.uH.set(((h + 11) % 12) + 1, 'auto', true);   // 0 -> 12, 13 -> 1
      this.uAP.set(h < 12 ? 'am' : 'pm', 'auto', true);
    } else {
      this.uH.set(h, 'auto', true);
    }
    this.uM.set(at.getMinutes(), 'auto', true);
  }

  /** The soonest future moment matching the until drums. */
  targetFromDrums() {
    let h = this.uH.value();
    if (this.twelve) h = (h % 12) + (this.uAP.value() === 'pm' ? 12 : 0);
    const at = new Date();
    at.setHours(h, this.uM.value(), 0, 0);
    // Past times mean tomorrow. At 4pm, "9" is tomorrow morning, which is what
    // anyone setting it means; the alternative is a timer that ends instantly.
    if (at.getTime() <= Date.now()) at.setDate(at.getDate() + 1);
    return at;
  }

  /** A drum moved: recompute the one value from whichever set is on screen. */
  fromDrums() {
    if (this.mode === 'for') {
      this.target = null;
      this.seconds = this.dH.value() * 3600 + this.dM.value() * 60 + this.dS.value();
    } else {
      this.target = this.targetFromDrums();
      this.seconds = secondsUntil(this.target, Date.now());
    }
    // Never clobber text the human is in the middle of typing.
    if (this.lastTouched !== 'type') this.input.value = this.fieldText();
    this.render();
  }

  // ----------------------------------------------------------------- render

  /** What the field currently says, or null if it does not parse in this mode. */
  parseField() {
    const raw = this.input ? this.input.value.trim() : '';
    if (raw === '') return { ok: true, empty: true };
    if (this.mode === 'for') {
      const secs = parseDuration(raw);
      return { ok: secs != null, seconds: secs };
    }
    const at = parseClockTime(raw, Date.now());
    return { ok: at != null, at };
  }

  render(force) {
    const field = this.parseField();
    this.root.toggleClass('is-bad', !field.ok);

    if (!field.ok) {
      this.echoEl.setText(this.mode === 'for'
        ? 'Not a duration — try 25m, 1h30, 90s or 1:30'
        : 'Not a time — try 1pm, 1:30pm, 13:45 or noon');
    } else {
      this.echoEl.empty();
      this.echoEl.createEl('b', { text: formatHuman(this.seconds) });
      this.echoEl.createSpan({ text: '  ·  ' });
      if (this.mode === 'until' && this.target) {
        this.echoEl.createSpan({ text: 'until ' });
        this.echoEl.createEl('b', { text: clockLabel(this.target) });
        if (!sameDay(this.target, new Date())) this.echoEl.createSpan({ text: ' tomorrow' });
      } else {
        this.echoEl.createSpan({ text: 'ends ' });
        this.echoEl.createEl('b', { text: endsAtClock(this.seconds) });
      }
    }

    // The flaps always read the DURATION, in both modes. Spinning a target
    // time and watching the countdown assemble itself is the answer to the
    // question that mode is being used to ask.
    this.board.set(formatClock(this.seconds), force);

    // The button states what pressing it commits to, rather than 'Start' and a
    // hope that the echo was read. It goes bare when the field does not parse,
    // because naming a duration there would be naming the wrong one.
    this.startEl.setText(field.ok && this.seconds > 0
      ? `Start ${formatHuman(this.seconds)}` : 'Start');
  }

  submit() {
    const field = this.parseField();
    if (!field.ok) {
      this.render();
      return;                                   // keep the window open to fix it
    }
    // RECOMPUTED AGAINST THE CLOCK AT THE MOMENT OF STARTING. "Until 1pm" means
    // 1pm, and the seconds spent choosing it are part of what has to come off.
    const secs = this.mode === 'until' && this.target
      ? secondsUntil(this.target, Date.now())
      : this.seconds;
    if (!(secs > 0)) {
      this.render();
      return;                                   // a zero-length session is a no-op
    }
    this.close();
    this.plugin.start(secs);
  }

  onClose() {
    if (this.unwatchKeyboard) this.unwatchKeyboard();
    this.drums().forEach((d) => d.stop());      // no rAF outliving the window
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
    /* On mobile Obsidian hides the status bar entirely and offers no other
     * surface a plugin can park a persistent item in, so there is no readout
     * there and the commands are all that remain — see the MOBILE note in the
     * header for why that is the right answer rather than a gap. */
    if (Platform.isMobile) return;

    this.el = this.addStatusBarItem();
    this.el.addClass('midori-timer');
    this.el.addClass('mod-clickable');

    this.iconEl = this.el.createSpan({ cls: 'midori-timer-icon' });
    setIcon(this.iconEl, 'clock');
    this.timeEl = this.el.createSpan({ cls: 'midori-timer-time' });

    /* The readout is the same split-flap board as the setting window, one
     * seventh the size. Turning the flip OFF is a class, not a second code
     * path: the bar variant has no card and no seam, so a board that does not
     * animate is indistinguishable from plain text — which is what makes one
     * renderer able to serve both settings, and what lets the reduced-motion
     * rule do its job without a JS branch. */
    this.bar = new FlapBoard(this.timeEl, 'is-bar');

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

  render() {
    this.renderCaret();
    if (!this.el) return;

    // The status bar item is emptied outright when the caret is the only
    // display, so Obsidian's `.status-bar-item:empty { display: none }` takes
    // it out of the bar rather than leaving a dead gap where it used to be.
    if (this.settings.display === 'caret') {
      this.el.removeClass('is-running');
      this.el.removeClass('is-paused');
      this.el.addClass('is-blank');
      this.bar.set('');
      this.iconEl.hide();
      this.el.removeAttribute('aria-label');
      return;
    }
    this.el.removeClass('is-blank');
    this.bar.still = !this.settings.barFlap;

    this.el.removeClass('is-running');
    this.el.removeClass('is-paused');

    if (this.isActive()) {
      this.el.addClass(this.isPaused() ? 'is-paused' : 'is-running');
      // THE ICON IS FOR THE IDLE STATE ONLY. A running board of cards is not
      // ambiguous about what it is, and a clock face next to a clock is the
      // kind of redundancy that makes a bar feel crowded. The icon exists
      // because an idle timer needs something to click; once it is running the
      // digits are the thing to click, so the icon gets out of the way.
      // A pause is the one exception: nothing about a stopped countdown says
      // "paused" rather than "finished", so that icon stays.
      if (this.isPaused()) {
        this.iconEl.show();
        setIcon(this.iconEl, 'pause');
      } else {
        this.iconEl.hide();
      }
      this.bar.set(formatClock(this.remaining()));
      this.el.setAttr('aria-label',
        `${this.isPaused() ? 'Paused' : 'Timer'} — click to ${this.isPaused() ? 'resume' : 'pause'}, right-click for more`);
      return;
    }

    // Idle. Emptying the element makes Obsidian's own
    // `.status-bar-item:empty { display: none }` hide it, which is exactly the
    // behaviour the "show when idle" setting wants when it is off.
    this.bar.set('');
    if (this.settings.showWhenIdle) {
      this.iconEl.show();
      setIcon(this.iconEl, 'clock');
      this.el.setAttr('aria-label', 'Set a timer');
    } else {
      this.iconEl.hide();
      this.el.addClass('is-blank');             // nothing to show, so no gap
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
      .setDesc('The caret drifts from its resting indigo through sage and ochre to wine as the session runs. Nothing is added to the page and nothing appears while you write: the caret is already there, and it is the one thing on screen your eye is resting on.'
        + (Platform.isMobile
          ? ' Obsidian has no status bar on a phone, so the caret is the whole display here whichever of these is chosen \u2014 the other two take effect on desktop.'
          : ''))
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
      .setName('Flip the digits')
      .setDesc('The readout turns over like a split-flap board, one card per digit that changed — so the seconds flip every second and the minutes once a minute. It is motion at the edge of vision, which is the one thing the caret display exists to avoid, so it is a choice: off, the digits simply change. Ignored when the caret is the only display, and always off under Reduce Motion.')
      .addToggle((t) => t
        .setValue(this.plugin.settings.barFlap)
        .onChange(async (v) => {
          this.plugin.settings.barFlap = v;
          await this.plugin.save();
          this.plugin.render();
        }));

    new Setting(containerEl)
      .setName('Show when idle')
      .setDesc('Keep a clock in the status bar while no timer is running, so there is something to click. Off hides it until a timer starts. Ignored when the caret is the only display, and on a phone, which has no status bar.')
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
