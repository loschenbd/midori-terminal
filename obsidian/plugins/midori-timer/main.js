'use strict';

/* Midori Timer — a countdown in the status bar, with a typed duration.
 *
 * WHAT IT IS. A status-bar countdown you set by typing "25m", "1h30", "90s"
 * or "1:30" into a small input. Click the readout to pause or resume,
 * right-click for the rest. Everything is also a command, so the input window
 * can be opened with a hotkey — bind "Midori Timer: Set duration and start".
 *
 * FIVE DECISIONS THAT SHAPE THE CODE.
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
 * 2. THE STATUS BAR MUST NOT REFLOW. A proportional font gives "1" and "8"
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
 * MOBILE. Obsidian hides the status bar on phones outright
 * (`.is-mobile .status-bar { display: none }` in app.css), so the widget half
 * of this plugin is desktop-only in practice. The commands and the finish
 * notice still work there, which is why the manifest is not marked
 * desktop-only.
 */

const { Plugin, PluginSettingTab, Setting, Modal, Menu, Notice, setIcon, Platform } = require('obsidian');

const DEFAULTS = {
  defaultDuration: 25 * 60,   // seconds; what the modal is pre-filled with
  showWhenIdle: true,         // keep a clickable clock in the bar when stopped
  chime: true,
  volume: 0.2,
  systemNotification: false,  // OS-level banner, for when Obsidian is buried
  finishMessage: '',          // blank -> "Timer finished (25m)"
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
.midori-timer.is-finished .midori-timer-time {
  color: var(--text-accent, var(--interactive-accent));
  font-weight: var(--font-semibold, 600);
}
/* The only motion, and it stops on its own after a few seconds. Anyone who
   asked the OS for less motion gets the colour change and no pulse. */
@media (prefers-reduced-motion: no-preference) {
  .midori-timer.is-finished {
    animation: midori-timer-pulse 1s ease-in-out 4;
  }
}
@keyframes midori-timer-pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.35; }
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
    this.finished = false;
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
        if (!this.isActive() && !this.finished) return false;
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
    this.finished = false;
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
    this.finished = false;
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

  /** @param {boolean} late true when the deadline passed while Obsidian was shut. */
  finish(late) {
    const total = this.session.total;
    this.clearTick();
    this.session = { endsAt: null, pausedAt: null, total: null };
    this.finished = true;
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
    if (this.isActive() || this.finished) {
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
    if (!this.el) return;

    this.el.removeClass('is-running');
    this.el.removeClass('is-paused');
    this.el.removeClass('is-finished');

    if (this.isActive()) {
      this.el.addClass(this.isPaused() ? 'is-paused' : 'is-running');
      this.iconEl.show();
      setIcon(this.iconEl, this.isPaused() ? 'pause' : 'clock');
      this.timeEl.setText(formatClock(this.remaining()));
      this.el.setAttr('aria-label',
        `${this.isPaused() ? 'Paused' : 'Timer'} — click to ${this.isPaused() ? 'resume' : 'pause'}, right-click for more`);
      return;
    }

    if (this.finished) {
      this.el.addClass('is-finished');
      this.iconEl.show();
      setIcon(this.iconEl, 'bell');
      this.timeEl.setText('0:00');
      this.el.setAttr('aria-label', 'Timer finished — click to set another');
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

    new Setting(containerEl)
      .setName('Show when idle')
      .setDesc('Keep a clock in the status bar while no timer is running, so there is something to click. Off hides it until a timer starts.')
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
