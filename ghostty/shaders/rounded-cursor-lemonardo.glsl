// rounded-cursor-lemonardo.glsl — Lemonardo rounded cursor + field guide.
//
// DERIVED FROM rounded-cursor.glsl by replacing exactly three constant blocks:
// the ground pair, the lattice colour/alpha pair, and the cursor ink pair.
// Everything below the constants is byte-identical to Midori's, verified at
// generation time, because the geometry is typographic (a 24pt rhythm anchored
// to the cell) and not brand — the two design languages SHOULD share it. If
// that file's cursor or lattice maths changes, re-derive rather than hand-edit.
//
//
// Two jobs:
//   1. Draw the cursor as a rounded rect (the native square cursor is hidden
//      via `cursor-opacity = 0` in the config), baseline-locked.
//   2. Draw the 24pt dot grid anchored to the SAME cell geometry the cursor
//      reports, so the lattice tracks the text rows by construction — a
//      mis-rounded adjust-cell-height can no longer drift the grid. The glow
//      backgrounds are baked WITHOUT dots (bake-backgrounds.py --without-dots).
//
// Uniform facts (learned the hard way):
//   iCurrentCursor.xy = BOTTOM-left corner of the cursor cell, .zw = w/h.
//   The coordinate space is y-DOWN: SUBTRACT to move up-screen.
//   For a block cursor, .w (height) = one cell = the dot pitch.
//   iCurrentCursorColor = the NATIVE cursor's colour. The themes set
//   cursor-color = cell-background, so this is the colour of the cell under
//   the cursor, not an ink — the cursor draw below does not read it.
//   iBackgroundColor = the live terminal background; follows light/dark.
//   iCurrentCursorStyle.x = 1 -> hollow (unfocused window) -> draw outline.
//   iCursorVisible = DECTCEM (CSI ?25l/h) only — NOT blink phase or focus.
//   When hidden, Ghostty leaves iCurrentCursor at its last (stale) value, so
//   the lattice below can still anchor to it; only the cursor draw is gated.
//
// BASELINE_LIFT couples the two: the cursor bottom is lifted onto the text
// baseline, and the dot rows are DEFINED as that baseline mod pitch — cursor
// and dots coincide exactly at any cell height. 0.178 was measured 2026-07-14
// (14pt M PLUS 1 Code, 49px cell): prompt-underline y minus raw cell-bottom y
// = -8.7px = -0.178 cells. The earlier 0.27 was tuned against baked dots that
// had absorbed a bogus +4.5px "restart drift" recalibration — text sat 4.5px
// below every dot row. Calibrate against the UNDERLINE, not old dot assets.

const float BASELINE_LIFT = 0.178;

// Lemonardo surfaces (sRGB). Dots are drawn only over near-background pixels
// so text, selections, and TUI fills stay clean.
//
// WHY THIS FILE EXISTS AT ALL. Lemonardo loaded Midori's shader for the cursor
// and silently got Midori's lattice with it, because the grounds below were
// Midori's and the match is a distance test, not a theme lookup. Measured
// 2026-10-11 against the tolerances in bgMatch: Paintpot #f3eee2 sits 0.0372
// from Midori Paper against a 0.09 sRGB tolerance, so it MATCHED and took
// Midori's sage #9ebfb4; Inkwell #2c2a28 sits 0.1178 from Midori Night against
// the same 0.09 (and 0.0227 against the 0.015 linear tolerance), so it missed
// both and took nothing. Light mode had another brand's lattice, dark mode had
// none, and no one chose either — two tolerance comparisons fell on opposite
// sides. Pointing a design language at the other one's shader is the general
// form of that bug; install both and point each config at its own.
//
// THE LATTICE IS A FIELD GUIDE, and the colour is not invented here. Paintpot
// is a golden-era drafting bench (see themes/lemonardo.json: bond, cel, manila,
// graphite, paintpots), and the lattice that belongs on animation paper is the
// registration grid you draft over in non-photo blue — col-erase, which the
// rostrum camera could not see, so you inked straight over it without erasing.
// themes/lemonardo.json already declares that colour as the `guide` role in
// both modes, and tests/check_theme_contrast.py holds `guide`, `guide-pale` and
// `peg` BELOW a 2.0 ceiling and FAILS if one becomes legible. A guide that
// reads as text has stopped being a guide — which is exactly the property a
// background lattice needs, asserted by a test that already runs in lint.
//
// ALPHAS ARE MATCHED TO MIDORI'S PERCEIVED STRENGTH, not copied. Midori's
// lattice composites to 1.280:1 against paper and 1.418:1 against night. Solving
// for the same ratios with `guide` (computed 2026-10-11):
//
//   paintpot  #f3eee2 + #a8d7ea @ 0.8514 -> #b3dae9   1.280:1  (1.0 = 1.34:1)
//   inkwell   #2c2a28 + #3f5a68 @ 0.5400 -> #36444b   1.418:1  (1.0 = 1.96:1)
//
// Both land under the 2.0 guide ceiling with room, and both modes now get a
// lattice, so the light/dark asymmetry above is gone rather than inverted.
//
// REJECTED, so no later pass re-proposes them:
//   - `page-dot` #ffd700. Lemonardo declares it and it is the obvious reach,
//     but it is a LEMON, not a guide: 1.21:1 on bond (fine) and 10.19:1 on
//     inkwell (a field of yellow dots brighter than most of the text). The
//     role is declared for targets that paint a dot on a light page only.
//   - `guide-pale` #cde8f2 / #2f424c. Tops out at 1.105:1 and 1.365:1 — it
//     cannot reach Midori's strength even at alpha 1.0. Correct for a second,
//     quieter rule line in a target that has two; too faint to carry a lattice.
//   - No lattice at all, keeping only the cursor. This was the chosen option
//     until the drafting-bench reading surfaced a lattice with a real source
//     and a test already guarding it. To go back: delete the dot-lattice block
//     in mainImage and these six constants. Nothing else depends on them.
const vec3  PAPER_BG  = vec3(243.0, 238.0, 226.0) / 255.0;  // #f3eee2 bond
const vec3  NIGHT_BG  = vec3( 44.0,  42.0,  40.0) / 255.0;  // #2c2a28 inkwell
const vec3  PAPER_DOT = vec3(168.0, 215.0, 234.0) / 255.0;  // #a8d7ea guide
const vec3  NIGHT_DOT = vec3( 63.0,  90.0, 104.0) / 255.0;  // #3f5a68 guide
const float PAPER_DOT_ALPHA = 0.8514;
const float NIGHT_DOT_ALPHA = 0.5400;

// Cursor ink. The native cursor is composited AFTER this shader (so it can't be
// erased here) and cursor-opacity=0 does NOT hide the hollow unfocused cursor,
// so the themes set cursor-color = cell-background: every native draw takes the
// colour of the cell under it and vanishes. The ink is therefore chosen from
// the live background, never from the cursor colour.
//
// Previously the themes set the EXACT background hex and this shader decoded it
// as a sentinel, passing any other colour (an app's OSC 12) through. On Ghostty
// 1.3.1 an OSC 112 reset copies the current default into a sticky override that
// a light/dark flip never updates, so the sentinel could be the OTHER mode's
// hex: in paper mode the shader drew the night indigo and the native hollow
// cursor showed as a black box. See ghostty/themes/midori-paper. Dropping the
// passthrough is deliberate: an app recolouring the cursor was already treated
// as a bug to undo (shell/zshrc.midori resets it before every prompt).
//
// Lemonardo's ink is the `indigo` role, which in this palette is cobalt — the
// one blue in the system that is MEANT to be read (6.02:1 on bond), as opposed
// to the non-photo guide blue above, which is meant not to be. A drafting bench
// where the pen and the guide lines are the same blue would lose the joke.
const vec3 PAPER_CURSOR = vec3( 46.0,  92.0, 138.0) / 255.0;  // #2e5c8a cobalt
const vec3 NIGHT_CURSOR = vec3(135.0, 206.0, 235.0) / 255.0;  // #87ceeb indigo

float sdRoundBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

// "Is this pixel (glow-tinted) background?" — tested in BOTH sRGB and linear
// encodings, since the sampled texture's transfer function isn't guaranteed.
// Returns 0 = no, 1 = matched in sRGB, 2 = matched in linear.
int bgMatch(vec3 c, vec3 bg, float tolS, float tolL) {
    if (distance(c, bg) < tolS) return 1;
    if (distance(pow(c, vec3(2.2)), pow(bg, vec3(2.2))) < tolL) return 2;
    return 0;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv);

    vec2 halfSize = iCurrentCursor.zw * 0.5;
    if (halfSize.x <= 0.0 || halfSize.y <= 0.0) return;  // no cursor, no anchor

    // ---- dot lattice, anchored to the cursor's cell geometry ----
    float pitch = iCurrentCursor.w;
    if (pitch < 16.0)  // thin bar/underline cursor can't give us the cell height
        pitch = (iResolution.y > 1600.0) ? 48.0 : 24.0;
    float baseline = iCurrentCursor.y - BASELINE_LIFT * pitch;

    // rows on baselines; columns every pitch, first at half a pitch from the
    // left edge (matches the retired baked tiles: cx = tile/2)
    vec2 rel = vec2(fragCoord.x - 0.5 * pitch, fragCoord.y - baseline);
    vec2 wrapped = rel - pitch * floor(rel / pitch + 0.5);
    float dd = length(wrapped);
    float rIn = pitch * (2.0 / 48.0);
    float rOut = pitch * (2.7 / 48.0);
    float cov = clamp((rOut - dd) / (rOut - rIn), 0.0, 1.0);
    if (cov > 0.0) {
        int mp = bgMatch(fragColor.rgb, PAPER_BG, 0.09, 0.17);
        int mn = (mp == 0) ? bgMatch(fragColor.rgb, NIGHT_BG, 0.09, 0.015) : 0;
        if (mp != 0) {
            vec3 dot_ = (mp == 2) ? pow(PAPER_DOT, vec3(2.2)) : PAPER_DOT;
            fragColor.rgb = mix(fragColor.rgb, dot_, cov * PAPER_DOT_ALPHA);
        } else if (mn != 0) {
            vec3 dot_ = (mn == 2) ? pow(NIGHT_DOT, vec3(2.2)) : NIGHT_DOT;
            fragColor.rgb = mix(fragColor.rgb, dot_, cov * NIGHT_DOT_ALPHA);
        }
    }

    // ---- rounded cursor, drawn over the dots ----
    // Apps that hide the cursor (Claude Code's choice UI, fzf, TUIs) send
    // CSI ?25l; the native cursor stops rendering but our replacement must
    // opt in, or it ghosts at the stale iCurrentCursor position.
    if (iCursorVisible == 0) return;
    // Baseline lock: lift so the bottom edge rests on the baseline dot row
    // and the top touches the previous dot row. Set BASELINE_LIFT to 0.0 for
    // the stock cell-aligned cursor (dots will follow it — they share it).
    vec2 center = iCurrentCursor.xy + vec2(halfSize.x, -halfSize.y);
    center.y -= BASELINE_LIFT * iCurrentCursor.w;
    vec2 p = fragCoord - center;
    if (any(greaterThan(abs(p), halfSize + 2.0))) return;

    float radius = 0.35 * min(halfSize.x, halfSize.y);
    float d = sdRoundBox(p, halfSize, radius);

    float shape;
    if (abs(iCurrentCursorStyle.x - 1.0) < 0.5) {
        // hollow style (unfocused): ~1.5px rounded outline
        shape = 1.0 - smoothstep(1.0, 2.5, abs(d));
    } else {
        // filled block / bar / underline
        shape = 1.0 - smoothstep(-0.75, 0.75, d);
    }

    // Ink by ground: light background -> paper indigo, dark -> night indigo.
    // 0.5 is safe in either encoding: #f3f1eb is 0.95 sRGB / 0.89 linear
    // luminance, #1a1917 is 0.10 / 0.01.
    float groundLum = dot(iBackgroundColor, vec3(0.2126, 0.7152, 0.0722));
    vec3 ink = (groundLum > 0.5) ? PAPER_CURSOR : NIGHT_CURSOR;

    // 0.9 alpha: a hint of the glyph shows through a block cursor over text
    fragColor = mix(fragColor, vec4(ink, 1.0), shape * 0.9);
}
