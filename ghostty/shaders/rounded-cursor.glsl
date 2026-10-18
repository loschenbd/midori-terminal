// rounded-cursor.glsl — Midori rounded cursor + page glow + cursor-anchored
// dot lattice.
//
// Three jobs, in draw order:
//   1. Tint background pixels with the site's --page-glow: three elliptical
//      washes evaluated per pixel as FRACTIONS of the surface size, so they
//      fit any display, density, window or split. Until 2026-10-17 this was a
//      PNG baked per display (tools/bake-backgrounds.py, @1x 2560x1080 for
//      the LG ultrawides, @2x 3456x2234 for the 16" retina panel), drawn by
//      Ghostty at physical pixels and anchored top-centre. That needed a
//      watcher to flip @1x/@2x symlinks when the main display changed, and a
//      manual config reload for Ghostty to re-read the file, and when either
//      lagged the other display's bake showed: measured 2026-10-17 22:39 on
//      the retina panel, the 2560-wide ultrawide bake sat 448px in from each
//      edge with its right-hand wash centred at x=3008 instead of the screen
//      edge, every sampled pixel matching that bake to within one level. The
//      washes are low-frequency, so there is nothing a bitmap did that a
//      per-pixel function does not.
//   2. Draw the 24pt dot grid anchored to the SAME cell geometry the cursor
//      reports, so the lattice tracks the text rows by construction — a
//      mis-rounded adjust-cell-height can no longer drift the grid.
//   3. Draw the cursor as a rounded rect (the native square cursor is hidden
//      via `cursor-opacity = 0` in the config), baseline-locked.
//
// Uniform facts (learned the hard way):
//   iCurrentCursor.xy = BOTTOM-left corner of the cursor cell, .zw = w/h.
//   The coordinate space is y-DOWN: SUBTRACT to move up-screen. fragCoord.y
//   is 0 at the TOP of the surface, which is why the glow's top halo at
//   cy = -0.15 lands above the top edge rather than below the bottom one.
//   For a block cursor, .w (height) = one cell = the dot pitch.
//   iCurrentCursorColor = the NATIVE cursor's colour. The themes set
//   cursor-color = cell-background, so this is the colour of the cell under
//   the cursor, not an ink — the cursor draw below does not read it.
//   iBackgroundColor = the live terminal background; follows light/dark.
//   iCurrentCursorStyle.x = 1 -> hollow (unfocused window) -> draw outline.
//   iCursorVisible = DECTCEM (CSI ?25l/h) only — NOT blink phase or focus.
//   When hidden, Ghostty leaves iCurrentCursor at its last (stale) value, so
//   the lattice below can still anchor to it; only the cursor draw is gated.
//   iResolution.xy = the surface in PHYSICAL pixels, so uv fractions are
//   density-independent and each Ghostty split gets its own glow, exactly as
//   each split got its own copy of the background image.
//
// BASELINE_LIFT couples the two: the cursor bottom is lifted onto the text
// baseline, and the dot rows are DEFINED as that baseline mod pitch — cursor
// and dots coincide exactly at any cell height. 0.178 was measured 2026-07-14
// (14pt M PLUS 1 Code, 49px cell): prompt-underline y minus raw cell-bottom y
// = -8.7px = -0.178 cells. The earlier 0.27 was tuned against baked dots that
// had absorbed a bogus +4.5px "restart drift" recalibration — text sat 4.5px
// below every dot row. Calibrate against the UNDERLINE, not old dot assets.

const float BASELINE_LIFT = 0.178;

// Midori surfaces (sRGB). Glow and dots are drawn only over pixels that ARE the
// background, so text, selections, and TUI fills stay clean.
const vec3  PAPER_BG  = vec3(243.0, 241.0, 235.0) / 255.0;  // #f3f1eb
const vec3  NIGHT_BG  = vec3( 26.0,  25.0,  23.0) / 255.0;  // #1a1917
const vec3  PAPER_DOT = vec3(158.0, 191.0, 180.0) / 255.0;
const vec3  NIGHT_DOT = vec3(154.0, 189.0, 179.0) / 255.0;
const float PAPER_DOT_ALPHA = 0.46;
const float NIGHT_DOT_ALPHA = 0.1748;  // site dark dot alpha x overlay opacity

// --page-glow from benjaminloschen.com globals.css, one wash per const row:
//   xy = ellipse radii as fractions of the surface (CSS rx%, ry%),
//   zw = ellipse centre as fractions of the surface (CSS cx%, cy%).
// A wash covers d = length((uv - centre) / radii) < END with alpha
// ALPHA * (1 - d / END), composited in sRGB in THIS order (the CSS lists the
// topmost wash first; the bake composited the reversed list bottom-up, and so
// does this). The numbers are the bake tool's, verbatim.
const vec4  GLOW0_GEOM = vec4(0.45, 0.45, 1.00, 0.60);  // right-edge bloom
const vec4  GLOW1_GEOM = vec4(0.55, 0.40, 0.00, 1.00);  // bottom-left bloom
const vec4  GLOW2_GEOM = vec4(1.00, 0.55, 0.50, -0.15); // top halo
const vec3  PAPER_GLOW0 = vec3(232.0, 236.0, 229.0) / 255.0;  // #e8ece5
const vec3  PAPER_GLOW1 = vec3(236.0, 233.0, 224.0) / 255.0;  // #ece9e0
const vec3  PAPER_GLOW2 = vec3(255.0, 252.0, 247.0) / 255.0;  // #fffcf7
const vec3  NIGHT_GLOW0 = vec3( 48.0,  52.0,  46.0) / 255.0;  // #30342e
const vec3  NIGHT_GLOW1 = vec3( 55.0,  52.0,  46.0) / 255.0;  // #37342e
const vec3  NIGHT_GLOW2 = vec3( 45.0,  44.0,  40.0) / 255.0;  // #2d2c28
const vec3  PAPER_GLOW_ALPHA = vec3(0.40, 0.55, 0.95);
const vec3  NIGHT_GLOW_ALPHA = vec3(0.35, 0.45, 0.90);
const vec3  GLOW_END = vec3(0.48, 0.50, 0.52);

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
const vec3 PAPER_CURSOR = vec3( 58.0,  85.0, 114.0) / 255.0;  // #3a5572
const vec3 NIGHT_CURSOR = vec3(108.0, 135.0, 164.0) / 255.0;  // #6c87a4

float sdRoundBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

// "Is this pixel the background?" — tested in BOTH sRGB and linear encodings,
// since the sampled texture's transfer function isn't guaranteed.
// Returns 0 = no, 1 = matched in sRGB, 2 = matched in linear.
//
// The tolerances used to be 0.09 sRGB / 0.17 (paper) and 0.015 (night) linear,
// wide enough to accept a background pixel the baked glow had already tinted
// by up to 29 levels. Now nothing tints the background before this shader
// sees it, so the match is near-exact: 0.02 sRGB is five levels, and the
// linear values are that same five levels pushed through the 2.2 curve at
// each ground. The old width was also how Lemonardo Paintpot (#f3eee2, 0.037
// from Midori Paper) grew a sage lattice for a day — tests/test_lemonardo_shader.py.
int bgMatch(vec3 c, vec3 bg, float tolS, float tolL) {
    if (distance(c, bg) < tolS) return 1;
    if (distance(pow(c, vec3(2.2)), pow(bg, vec3(2.2))) < tolL) return 2;
    return 0;
}

// One wash: alpha at uv, from the bake tool's `a = alpha * (1 - d / end)`.
float washAlpha(vec2 uv, vec4 geom, float alpha, float end) {
    float d = length((uv - geom.zw) / geom.xy);
    return (d < end) ? alpha * (1.0 - d / end) : 0.0;
}

// The three washes over an sRGB background pixel, composited in sRGB like the
// bake (and like the browser). Call with sRGB in, get sRGB out.
vec3 pageGlow(vec3 srgb, vec2 uv, bool night) {
    vec3 c0 = night ? NIGHT_GLOW0 : PAPER_GLOW0;
    vec3 c1 = night ? NIGHT_GLOW1 : PAPER_GLOW1;
    vec3 c2 = night ? NIGHT_GLOW2 : PAPER_GLOW2;
    vec3 al = night ? NIGHT_GLOW_ALPHA : PAPER_GLOW_ALPHA;
    srgb = mix(srgb, c0, washAlpha(uv, GLOW0_GEOM, al.x, GLOW_END.x));
    srgb = mix(srgb, c1, washAlpha(uv, GLOW1_GEOM, al.y, GLOW_END.y));
    srgb = mix(srgb, c2, washAlpha(uv, GLOW2_GEOM, al.z, GLOW_END.z));
    return srgb;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv);

    // ---- which ground is this pixel, if any ----
    // Decided ONCE, before anything is drawn on it: the glow tints the pixel,
    // and a test run afterwards would have to be as loose as the old one.
    int mp = bgMatch(fragColor.rgb, PAPER_BG, 0.02, 0.04);
    int mn = (mp == 0) ? bgMatch(fragColor.rgb, NIGHT_BG, 0.02, 0.003) : 0;
    bool isBg = (mp != 0 || mn != 0);
    bool linearTex = (mp == 2 || mn == 2);

    // ---- page glow, on background pixels only ----
    // The bake composited in sRGB. If the texture arrived linear, go to sRGB,
    // compose there, and come back, so both encodings give the bake's numbers.
    if (isBg) {
        vec3 s = linearTex ? pow(fragColor.rgb, vec3(1.0 / 2.2)) : fragColor.rgb;
        s = pageGlow(s, uv, mn != 0);
        fragColor.rgb = linearTex ? pow(s, vec3(2.2)) : s;
    }

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
    if (cov > 0.0 && isBg) {
        if (mp != 0) {
            vec3 dot_ = (mp == 2) ? pow(PAPER_DOT, vec3(2.2)) : PAPER_DOT;
            fragColor.rgb = mix(fragColor.rgb, dot_, cov * PAPER_DOT_ALPHA);
        } else {
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
