// rounded-cursor.glsl — Midori rounded cursor + cursor-anchored dot lattice.
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
//   iCurrentCursorColor = live cursor color (follows the midori themes).
//   iCurrentCursorStyle.x = 1 -> hollow (unfocused window) -> draw outline.
//
// BASELINE_LIFT couples the two: the cursor bottom is lifted onto the text
// baseline, and the dot rows are DEFINED as that baseline mod pitch — cursor
// and dots coincide exactly at any cell height. 0.178 was measured 2026-07-14
// (14pt M PLUS 1 Code, 49px cell): prompt-underline y minus raw cell-bottom y
// = -8.7px = -0.178 cells. The earlier 0.27 was tuned against baked dots that
// had absorbed a bogus +4.5px "restart drift" recalibration — text sat 4.5px
// below every dot row. Calibrate against the UNDERLINE, not old dot assets.

const float BASELINE_LIFT = 0.178;

// Midori surfaces (sRGB). Dots are drawn only over near-background pixels so
// text, selections, and TUI fills stay clean.
const vec3  PAPER_BG  = vec3(243.0, 241.0, 235.0) / 255.0;  // #f3f1eb
const vec3  NIGHT_BG  = vec3( 26.0,  25.0,  23.0) / 255.0;  // #1a1917
const vec3  PAPER_DOT = vec3(158.0, 191.0, 180.0) / 255.0;
const vec3  NIGHT_DOT = vec3(154.0, 189.0, 179.0) / 255.0;
const float PAPER_DOT_ALPHA = 0.46;
const float NIGHT_DOT_ALPHA = 0.1748;  // site dark dot alpha x overlay opacity

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

    // 0.9 alpha: a hint of the glyph shows through a block cursor over text
    fragColor = mix(fragColor, vec4(iCurrentCursorColor.rgb, 1.0), shape * 0.9);
}
