// rounded-cursor.glsl — draws the cursor as a rounded rect.
// Pairs with `cursor-opacity = 0` in the config: the native (square) cursor
// is hidden and this shader renders it instead, using the live uniforms:
//   iCurrentCursor.xy = bottom-left corner (y-DOWN coords), .zw = width/height
//   iCurrentCursorColor = current cursor color (follows midori themes)
//   iCurrentCursorStyle.x = 1 -> hollow (unfocused window) -> draw outline
// Radius scales with the cursor, so it adapts across 1x/2x displays and
// becomes a pill on thin bar cursors. Steady (no blink) by design.

float sdRoundBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv);

    vec2 halfSize = iCurrentCursor.zw * 0.5;
    if (halfSize.x <= 0.0 || halfSize.y <= 0.0) return;

    vec2 center = iCurrentCursor.xy + vec2(halfSize.x, -halfSize.y);
    // Baseline lock: lift the cursor so its top edge touches the upper dot
    // row and its bottom rests on the baseline dot row (cursor height = one
    // grid step, so both align at once). Offset ~= font descent + vertical
    // centering pad (14pt M PLUS 1 Code + adjust-cell-height 38.9%), tuned
    // to 0.30 from @2x screenshot measurements. NOTE this coordinate space
    // is y-DOWN (iCurrentCursor.xy is the bottom-left corner): SUBTRACT to
    // move the cursor up-screen. Cell-proportional, so it holds on 1x and
    // 2x displays. Set to 0.0 to restore the stock cell-aligned cursor.
    center.y -= 0.30 * iCurrentCursor.w;
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
