#!/usr/bin/env python3
"""Prove check_theme_contrast.FLOORS still matches the reference it claims.

The floors in check_theme_contrast.py are checked in as literals, with the
Midori measurement recorded beside each. Literals drift. If someone retunes a
Midori value, the floor it was derived from silently stops describing the
theme, and the comment beside it becomes a confident, fluent, wrong
explanation -- the exact failure this repo keeps warning about.

So: re-derive REFERENCE_MIN from themes/midori.json, and require both that it
still matches the measurement AND that every floor equals

    min(STANDARD[band], REFERENCE_MIN[band])  rounded down to 0.1

which is the rule check_theme_contrast states. A floor above the reference's
minimum means Midori now fails its own check -- how the first two versions of
that file were caught. A REFERENCE_MIN that no longer matches the theme means
a Midori value moved and the comment beside the floor is now fiction.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_theme_contrast as C  # noqa: E402

import json  # noqa: E402


def main():
    ref_path = C.THEMES / f"{C.REFERENCE}.json"
    pal = json.loads(ref_path.read_text())["palette"]

    worst = {}
    for mode in ("light", "dark"):
        for role, ground, band in C.pairs():
            if role in pal and ground in pal:
                r = C.ratio(pal[role][mode], pal[ground][mode])
                worst[band] = min(worst.get(band, 99.0), r)

    if not worst:
        print("  FAIL derived no bands from the reference theme -- "
              "nothing was compared, which is not a pass")
        return 1

    fail = 0
    for band, floor in sorted(C.FLOORS.items()):
        if band not in worst:
            print(f"  FAIL band {band!r} has a floor but no measured pair")
            fail = 1
            continue
        measured = worst[band]
        recorded = C.REFERENCE_MIN.get(band)
        if recorded is None or abs(recorded - measured) > 0.005:
            print(f"  FAIL {band:<11} REFERENCE_MIN records {recorded}, but "
                  f"{C.REFERENCE} now measures {measured:.2f}")
            fail = 1
            continue
        expect = int(min(C.STANDARD[band], measured) * 10) / 10.0
        if abs(floor - expect) > 1e-9:
            print(f"  FAIL {band:<11} floor {floor}, but min(standard "
                  f"{C.STANDARD[band]}, measured {measured:.2f}) = {expect}")
            fail = 1
        else:
            src = "standard" if C.STANDARD[band] <= measured else C.REFERENCE
            print(f"  ok   {band:<11} floor {floor} = {src} "
                  f"(standard {C.STANDARD[band]}, {C.REFERENCE} {measured:.2f})")

    extra = set(worst) - set(C.FLOORS)
    if extra:
        print(f"  FAIL bands measured but given no floor: {', '.join(sorted(extra))}")
        fail = 1

    print(f"  {len(C.FLOORS)} floor(s) re-derived from {ref_path.name}")
    return fail


if __name__ == "__main__":
    sys.exit(main())
