'use strict';

/* Midori Timer — a countdown you type, shown as a filling rail along an edge.
 *
 * WHAT IT IS. Set a duration by typing "25m", "1h30", "90s" or "1:30" into a
 * small input, which a hotkey can open — bind "Midori Timer: Set duration and
 * start". The default display is a RAIL: a thin line just inside one edge of
 * the note that FILLS as the time runs, so an empty channel is a timer just
 * started and a full one is a timer about to end. The whole line is sage,
 * then the whole line is ochre, then the whole line is wine — one hue at a
 * time, each drawn as a gradient within itself. A status-bar readout is
 * available instead of it, or alongside it; that one can be clicked to pause
 * and right-clicked for the rest. Everything is also a command.
 *
 * SEVEN DECISIONS THAT SHAPE THE CODE. (The rail's own — how it is measured
 * off the note, and why the gradient is clipped rather than stretched — are at
 * the STYLE block, next to the CSS they explain.)
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
 * 2. THE STATUS BAR MUST NOT REFLOW (when it is used at all). A proportional font gives "1" and "8"
 *    different widths, so a plain countdown makes its own item change width
 *    roughly twice a second and shoves every item to its left along with it.
 *    `font-variant-numeric: tabular-nums` fixes the digits, and the readout
 *    also reserves the width of the largest form it will show during THIS run,
 *    so the item does not jump when 1:00:00 becomes 59:59 either.
 *
 * 3. PARSE PERMISSIVELY, THEN ECHO WHAT YOU UNDERSTOOD. A duration box that
 *    rejects "25" is a bad duration box. Bare numbers are minutes, units may
 *    be spelled out or abbreviated, and clock forms work — but since the rules
 *    cannot all be guessed, the modal shows the interpretation under the field
 *    as you type ("25m -> 25:00"). Ambiguity is resolved by stopwatch
 *    convention and stated in the UI rather than in a manual you will not read:
 *    ONE colon is minutes:seconds, TWO is hours:minutes:seconds.
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
 *    come from the theme's own CSS variables, so the readout tracks Midori
 *    Paper and Midori Night — and any other theme — without hardcoding either.
 *
 * 6. THE RAIL SITS ON document.body BUT IS MEASURED OFF THE NOTE. One element
 *    then serves every layout — split panes, sidebars open or shut — and no
 *    workspace rebuild can tear it out; but its geometry is read from the
 *    editor's scroller, so it lands on the page rather than on the window and
 *    tracks the text column when a sidebar opens. It is never flush to an edge
 *    (railInset), it is trimmed clear of whatever Obsidian floats over the
 *    note — the status-bar pill on desktop, the header buttons and navigation
 *    pill on mobile — and it is pointer-events: none throughout, because it is
 *    a readout and not a control.
 *
 * 7. THE RAIL IS VISIBLE ONLY WHILE A TIMER IS GOING. Running or paused, and
 *    nothing else: idle shows nothing, and the finish is carried by the notice,
 *    the chime and the optional system banner. A rail that lingers is just a
 *    line across the page you have to dismiss.
 *
 * MOBILE. Obsidian hides the status bar on phones outright
 * (`.is-mobile .status-bar { display: none }` in app.css), so the status-bar
 * display is desktop-only in practice. The RAIL is not — it tracks the note's
 * own geometry and works on a phone, which is the other reason it is default.
 */

const { Plugin, PluginSettingTab, Setting, Modal, Menu, Notice, setIcon, Platform } = require('obsidian');

const DEFAULTS = {
  defaultDuration: 25 * 60,   // seconds; what the modal is pre-filled with
  showWhenIdle: true,         // keep a clickable clock in the bar when stopped
  chime: true,
  volume: 0.2,
  systemNotification: false,  // OS-level banner, for when Obsidian is buried
  finishMessage: '',          // blank -> "Timer finished (25m)"

  display: 'rail',            // 'rail' | 'statusbar' | 'both'
  railEdge: 'bottom',         // 'bottom' | 'top' | 'left' | 'right'
  railThickness: 3,           // px of dot diameter
  railTrack: true,            // draw the unlit remainder of the rail
  railInset: 10,              // px in from the note's edge — never flush
};


/* Obsidian's furniture that FLOATS OVER the note rather than displacing it,
 * which is exactly the set the rail has to dodge. Desktop contributes the
 * status bar; the rest is mobile, where the header buttons and the navigation
 * pill sit on top of a scroller that runs the full height of the screen. A
 * selector that matches nothing costs nothing, so the list covers both
 * platforms and several Obsidian versions at once. */
const CHROME = [
  '.status-bar',
  '.mobile-navbar',
  '.mobile-toolbar',
  '.view-header',
  '.view-actions',
  '.workspace-drawer-header',
].join(', ');
const CHROME_GAP = 8;             // px of daylight left around each obstruction

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

/* The rail's colour ramp, as a fraction of the duration REMAINING.
 *
 * ONE HUE AT A TIME. The whole line is sage, then the whole line is ochre,
 * then the whole line is wine — never a blend of the three at once. The two
 * jobs are kept separate on purpose: the HUE carries the time (three states,
 * read at a glance, out of the corner of your eye), and the gradient WITHIN
 * that hue is shape, not data. A single line carrying a continuous
 * three-colour ramp says nothing legible at a glance, because you have to
 * find the boundary and judge where it is; a line that is simply yellow says
 * "getting on" in one look.
 *
 * The hues are the theme's own, in the roles they already hold elsewhere in
 * Midori: sage is the accent, ochre is the warning slot (ANSI 3), wine is the
 * error slot (ANSI 1). Ordered most-remaining first; the first match wins. */
const RAIL_STOPS = [
  { above: 0.25, varName: '--interactive-accent', fallback: '#5f6f5e' },  // sage
  { above: 0.10, varName: '--color-yellow',       fallback: '#b88a3a' },  // ochre
  { above: -1,   varName: '--color-red',          fallback: '#7a4a4a' },  // wine
];

/* The current hue as a gradient along `dir`, faint at the rail's origin and
 * full at the leading edge, so the edge is the part that reads.
 *
 * The gradient is sized to the FILL and therefore stretches with it — the
 * opposite of what a multi-hue ramp would want, and right here for the same
 * reason: with only one hue in play the gradient carries no time information,
 * so the visible line should always show the whole of it. Anchoring it to the
 * rail's full length instead would leave an early fill showing only the
 * dimmest sliver, which reads as a faint line rather than as a green one.
 *
 * color-mix rather than an alpha channel because the colour arrives as an
 * opaque theme variable — there is no rgb triplet for the accent, and the
 * theme's --interactive-accent-hsl is known-stale (see theme.css). */
function railGradient(dir, fraction) {
  const stop = RAIL_STOPS.find((x) => fraction > x.above) || RAIL_STOPS[RAIL_STOPS.length - 1];
  const c = `var(${stop.varName}, ${stop.fallback})`;
  return `linear-gradient(${dir}, color-mix(in srgb, ${c} 30%, transparent) 0%, ${c} 100%)`;
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
.midori-timer-hint {
  color: var(--text-muted);
  font-size: var(--font-ui-smaller, 0.8em);
  min-height: 1.6em;
  margin-top: 0.5em;
}
.midori-timer-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5em;
  margin-top: 0.9em;
}

/* ---------------------------------------------------------------- the rail

   A solid line just inside one edge of the NOTE that FILLS as the timer runs:
   an empty channel at the start, a full one at the end. Three things make it
   sit on the page rather than on the window.

   1. IT IS MEASURED OFF THE SCROLLER, NOT THE WINDOW. Position and length come
      from the live geometry of the editor's scroll element (see positionRail),
      because that element is what the page actually is. A window-fixed rail
      cannot line up with a note that moves when a sidebar opens. Everything
      here that is not a colour is therefore set from JS.

   2. IT IS NEVER FLUSH TO THE EDGE. The railInset setting holds it in off the
      boundary, and the inset is measured to the rail's OUTER face, so raising
      the thickness grows the rail inward and does not walk it toward the edge.

   3. IT STOPS SHORT OF THE STATUS BAR rather than running underneath it, again
      in positionRail, because that bar is a floating pill over the bottom
      right and a line crossing behind it reads as debris.

   THE FILL IS SIZED, AND THE GRADIENT STRETCHES WITH IT. The fill element's
   own length IS the progress, so its background gradient is redrawn across
   whatever is currently visible: the line always shows the complete faint ->
   full ramp, however little of it there is. That is only correct because the
   ramp is ONE hue (see RAIL_STOPS) and therefore carries no time information
   of its own. A multi-hue ramp would have to be painted at full length and
   revealed by clip-path instead, or the leading edge would sit at the same
   colour the whole way down and the ramp would mean nothing. */
.midori-timer-rail {
  position: fixed;
  z-index: var(--layer-popover, 30);
  pointer-events: none;
  --rail-track: var(--dotgrid-dot, rgba(158, 191, 180, 0.46));
  --rail-size: 3px;
  --rail-progress: 0%;
  border-radius: var(--rail-size);
  overflow: hidden;                 /* so the fill's ends are rounded too */
}
.midori-timer-rail.is-hidden { display: none; }

.midori-timer-rail-track,
.midori-timer-rail-fill {
  position: absolute;
  inset: 0;
}
.midori-timer-rail-track { background: var(--rail-track); opacity: 0.55; }

/* Horizontal edges: fills left to right. */
.midori-timer-rail.edge-bottom,
.midori-timer-rail.edge-top { height: var(--rail-size); }
.midori-timer-rail.edge-bottom .midori-timer-rail-fill,
.midori-timer-rail.edge-top .midori-timer-rail-fill {
  background: var(--rail-ramp-x);
  right: auto;
  width: var(--rail-progress);
}

/* Vertical edges: fills top to bottom, so it reads as a level rising. */
.midori-timer-rail.edge-left,
.midori-timer-rail.edge-right { width: var(--rail-size); }
.midori-timer-rail.edge-left .midori-timer-rail-fill,
.midori-timer-rail.edge-right .midori-timer-rail-fill {
  background: var(--rail-ramp-y);
  bottom: auto;
  height: var(--rail-progress);
}

.midori-timer-rail.no-track .midori-timer-rail-track { display: none; }

/* Paused reads as arrested: the line holds position and goes quiet. */
.midori-timer-rail.is-paused { opacity: 0.4; }
`;

// ------------------------------------------------------------------- modal

/* The typed-duration window. Opened by command (bind a hotkey to it), by
 * clicking an idle readout, or from the right-click menu. */
class DurationModal extends Modal {
  constructor(app, plugin) {
    super(app);
    this.plugin = plugin;
  }

  onOpen() {
    const { contentEl, titleEl } = this;
    titleEl.setText('Set timer');

    const initial = formatHuman(this.plugin.settings.defaultDuration);

    new Setting(contentEl)
      .setName('Duration')
      .addText((text) => {
        this.input = text.inputEl;
        this.input.style.width = '12em';
        text.setPlaceholder('25m, 1h30, 90s, 1:30').setValue(initial);
        text.onChange(() => this.preview());
        // Enter submits. Obsidian's Modal already maps Escape to close.
        this.input.addEventListener('keydown', (ev) => {
          if (ev.key === 'Enter') {
            ev.preventDefault();
            this.submit();
          }
        });
      });

    // Decision 3: echo the interpretation rather than documenting the rules.
    this.hint = contentEl.createDiv({ cls: 'midori-timer-hint' });

    const presets = contentEl.createDiv({ cls: 'midori-timer-presets' });
    for (const mins of [5, 10, 15, 25, 45, 60]) {
      const b = presets.createEl('button', { text: `${mins}m` });
      b.addEventListener('click', () => {
        this.input.value = `${mins}m`;
        this.submit();
      });
    }

    new Setting(contentEl).addButton((b) =>
      b.setButtonText('Start').setCta().onClick(() => this.submit()));

    this.preview();
    // Focus and select, so typing replaces the prefill instead of appending.
    window.setTimeout(() => { this.input.focus(); this.input.select(); }, 0);
  }

  preview() {
    const secs = parseDuration(this.input.value);
    this.hint.setText(
      secs == null
        ? (this.input.value.trim() ? "Didn't understand that — try 25m, 1h30, 90s or 1:30" : '')
        : `${formatHuman(secs)}  ->  ${formatClock(secs)}`,
    );
  }

  submit() {
    const secs = parseDuration(this.input.value);
    if (secs == null) {
      this.preview();
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
    this.buildRail();
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

  onunload() {
    this.clearTick();
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

  /* Finishing RESETS. The session is cleared, the rail goes away and the
   * status bar returns to its idle clock, all in the same frame — there is no
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

  /* The rail lives on document.body rather than inside the workspace so one
   * element serves every layout — split panes, sidebars open or shut — and no
   * workspace rebuild can tear it out. Its position is measured from the
   * editor's scroller each time it is shown (positionRail). */
  buildRail() {
    this.rail = document.createElement('div');
    this.rail.className = 'midori-timer-rail is-hidden';
    this.railTrackEl = this.rail.appendChild(document.createElement('div'));
    this.railTrackEl.className = 'midori-timer-rail-track';
    this.railFillEl = this.rail.appendChild(document.createElement('div'));
    this.railFillEl.className = 'midori-timer-rail-fill';
    document.body.appendChild(this.rail);
    this.register(() => this.rail.remove());

    // Anything that can move or resize the note moves the rail with it.
    const reposition = () => { if (this.isActive()) this.positionRail(); };
    this.registerDomEvent(window, 'resize', reposition);
    this.registerEvent(this.app.workspace.on('resize', reposition));
    this.registerEvent(this.app.workspace.on('layout-change', reposition));
    this.registerEvent(this.app.workspace.on('active-leaf-change', reposition));
  }

  /* The element that actually carries the dot grid. Reading its geometry is
   * what lets the rail sit on the note rather than on the window — and the two
   * differ by the whole width of a sidebar. */
  scrollerEl() {
    // Scope to the focused leaf first, so a split shows the rail under the
    // pane you are typing in rather than under whichever one happens to be
    // first in the DOM. Fall back outward until something exists: a leaf with
    // no scroller (a graph view, say) still gets a rail, on the root split.
    const active = document.querySelector('.workspace-leaf.mod-active');
    for (const root of [active, document]) {
      if (!root) continue;
      const el = root.querySelector('.cm-scroller')
        || root.querySelector('.markdown-preview-view');
      if (el) return el;
    }
    return document.querySelector('.workspace-split.mod-root') || document.body;
  }

  /* Trim [a0, a1] along the rail's own axis so it clears any of Obsidian's
   * floating chrome that crosses it, and return the shortened span.
   *
   * This is a hard requirement rather than a nicety, and it is why the rule is
   * written against a LIST of elements measured live rather than against the
   * status bar alone. The scroller runs edge to edge underneath everything
   * that floats over it, so a rail measured off the scroller runs under it
   * too. On desktop that is the status-bar pill at the bottom right — measured
   * at x 1347..1719 on a 1728px window, a fifth of a bottom rail. On MOBILE
   * there is no status bar at all (app.css hides it), and instead a right-edge
   * rail ran from behind the header buttons at the top straight down past the
   * navigation pill and off the bottom of the screen. Same bug, different
   * furniture: the fix has to be the furniture, not the status bar.
   *
   * Only obstructions that actually cross the rail's band count, so a top rail
   * is not shortened by something sitting at the bottom. The rail is trimmed
   * from whichever END the obstruction is nearer, so it shortens rather than
   * being cut in half — a rail with a hole in it reads as two rails. */
  clipToChrome(a0, a1, vertical, pos, thick) {
    const band = thick + 6;
    for (const el of document.querySelectorAll(CHROME)) {
      const b = el.getBoundingClientRect();
      if (b.width <= 0 || b.height <= 0) continue;
      const crosses = vertical
        ? b.right > pos - band && b.left < pos + band
        : b.bottom > pos - band && b.top < pos + band;
      if (!crosses) continue;
      const s0 = vertical ? b.top : b.left;
      const s1 = vertical ? b.bottom : b.right;
      if (s1 <= a0 || s0 >= a1) continue;
      if ((s0 + s1) / 2 > (a0 + a1) / 2) a1 = Math.min(a1, s0 - CHROME_GAP);
      else a0 = Math.max(a0, s1 + CHROME_GAP);
    }
    return [a0, a1];
  }

  /* Everything geometric about the rail, in one place, from live
   * measurements. */
  positionRail() {
    if (!this.rail) return;
    const el = this.scrollerEl();
    const r = el.getBoundingClientRect();
    const cs = window.getComputedStyle(el);
    const padL = parseFloat(cs.paddingLeft) || 0;
    const padR = parseFloat(cs.paddingRight) || 0;
    const padT = parseFloat(cs.paddingTop) || 0;
    const padB = parseFloat(cs.paddingBottom) || 0;

    // The content box: the page's own text column, padding excluded, and then
    // clamped to the window. On mobile the scroller is taller than the visible
    // viewport, so an unclamped vertical rail runs off the bottom of the
    // screen — which is what it did.
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const left = Math.max(0, r.left + padL);
    const right = Math.min(vw, r.right - padR);
    const top = Math.max(0, r.top + padT);
    const bottom = Math.min(vh, r.bottom - padB);

    const inset = Math.max(0, this.settings.railInset);
    const edge = this.settings.railEdge;
    const st = this.rail.style;
    st.left = st.right = st.top = st.bottom = st.width = st.height = '';

    if (edge === 'bottom' || edge === 'top') {
      let x0 = left;
      let x1 = right;
      // Inset to the OUTER face, so thickness grows the rail inward.
      const thick = this.settings.railThickness;
      const y = edge === 'bottom' ? bottom - inset - thick : top + inset;
      [x0, x1] = this.clipToChrome(x0, x1, false, y + thick / 2, thick);
      st.left = `${x0}px`;
      st.width = `${Math.max(0, x1 - x0)}px`;
      st.top = `${y}px`;
    } else {
      const thick = this.settings.railThickness;
      const x = edge === 'left' ? left + inset : right - inset - thick;
      let [y0, y1] = this.clipToChrome(top, bottom, true, x + thick / 2, thick);
      st.left = `${x}px`;
      st.top = `${y0}px`;
      st.height = `${Math.max(0, y1 - y0)}px`;
    }
  }

  renderRail() {
    if (!this.rail) return;
    const wanted = this.settings.display === 'rail' || this.settings.display === 'both';
    // Running or paused only. A finished or idle timer shows nothing: the rail
    // is for a timer that is GOING, and the finish is carried by the notice,
    // the chime and the optional system banner.
    const active = this.isActive();

    if (!wanted || !active) {
      this.rail.addClass('is-hidden');
      return;
    }

    // ELAPSED, not remaining: the line fills as the time goes rather than
    // draining away from you, so a full rail is a finished timer.
    const total = this.session.total || 0;
    const done = total <= 0 ? 0 : 1 - Math.max(0, Math.min(1, this.remaining() / total));

    this.rail.className = [
      'midori-timer-rail',
      `edge-${this.settings.railEdge}`,
      this.settings.railTrack ? '' : 'no-track',
      this.isPaused() ? 'is-paused' : '',
    ].filter(Boolean).join(' ');

    this.rail.style.setProperty('--rail-progress', `${(done * 100).toFixed(3)}%`);
    this.rail.style.setProperty('--rail-size', `${this.settings.railThickness}px`);
    // The hue is chosen by what is LEFT, not by what is done.
    const left = 1 - done;
    this.rail.style.setProperty('--rail-ramp-x', railGradient('to right', left));
    this.rail.style.setProperty('--rail-ramp-y', railGradient('to bottom', left));
    this.positionRail();
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
    this.renderRail();
    if (!this.el) return;

    // The status bar item is emptied outright when the rail is the only
    // display, so Obsidian's `.status-bar-item:empty { display: none }` takes
    // it out of the bar rather than leaving a dead gap where it used to be.
    if (this.settings.display === 'rail') {
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
      .setDesc('The rail is a dotted line along one edge of the window that drains as the timer runs. It uses the page dot grid\'s own colour and 24px pitch, so it reads as the grid lighting up rather than as a new bar.')
      .addDropdown((d) => d
        .addOption('rail', 'Rail only')
        .addOption('statusbar', 'Status bar only')
        .addOption('both', 'Both')
        .setValue(this.plugin.settings.display)
        .onChange(async (v) => {
          this.plugin.settings.display = v;
          await this.plugin.save();
          this.plugin.render();
        }));

    new Setting(containerEl)
      .setName('Rail edge')
      .addDropdown((d) => d
        .addOption('bottom', 'Bottom')
        .addOption('top', 'Top')
        .addOption('left', 'Left')
        .addOption('right', 'Right')
        .setValue(this.plugin.settings.railEdge)
        .onChange(async (v) => {
          this.plugin.settings.railEdge = v;
          await this.plugin.save();
          this.plugin.render();
        }));

    new Setting(containerEl)
      .setName('Rail thickness')
      .setDesc('Dot diameter, in pixels.')
      .addSlider((s) => s
        .setLimits(2, 10, 1)
        .setValue(this.plugin.settings.railThickness)
        .setDynamicTooltip()
        .onChange(async (v) => {
          this.plugin.settings.railThickness = v;
          await this.plugin.save();
          this.plugin.render();
        }));

    new Setting(containerEl)
      .setName('Rail inset')
      .setDesc('How far in from the note\'s edge the rail sits, in pixels. 0 puts it flush against the edge; the default holds it in the way the dot grid\'s own outer dots are held in.')
      .addSlider((s) => s
        .setLimits(0, 40, 1)
        .setValue(this.plugin.settings.railInset)
        .setDynamicTooltip()
        .onChange(async (v) => {
          this.plugin.settings.railInset = v;
          await this.plugin.save();
          this.plugin.render();
        }));

    new Setting(containerEl)
      .setName('Show the unlit track')
      .setDesc('Off leaves only the lit dots, so the rail shortens into empty space instead of draining along a visible line.')
      .addToggle((t) => t
        .setValue(this.plugin.settings.railTrack)
        .onChange(async (v) => {
          this.plugin.settings.railTrack = v;
          await this.plugin.save();
          this.plugin.render();
        }));

    new Setting(containerEl)
      .setName('Preview the rail')
      .setDesc('Runs a 20-second timer so you can see the edge, thickness and colours without waiting.')
      .addButton((b) => b.setButtonText('Run 20s').onClick(() => this.plugin.start(20)));

    containerEl.createEl('h3', { text: 'Status bar' });

    new Setting(containerEl)
      .setName('Show when idle')
      .setDesc('Keep a clock in the status bar while no timer is running, so there is something to click. Off hides it until a timer starts. Ignored when the rail is the only display.')
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
