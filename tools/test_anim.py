#!/usr/bin/env python3
"""Baseline checks for rocket/anim.py's drawing helpers.

rocket/ is written blind (no MicroPython in this environment), but anim.py
is deliberately hardware-import-free so it runs under plain CPython. This
script is the verification step CW's show spec calls for before any
choreography gets built on top of these helpers: run it and every assert
must pass.

Usage:
    python3 tools/test_anim.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "rocket"))

import anim

RED = (255, 0, 0)
BLUE = (0, 0, 255)
BLACK = (0, 0, 0)


def test_xy_to_index_serpentine():
    # Row 0 (even): left to right, no flip.
    assert anim.xy_to_index(0, 0) == 0
    assert anim.xy_to_index(7, 0) == 7
    # Row 1 (odd): flipped, so x=0 lands at the far end of the row.
    assert anim.xy_to_index(0, 1) == 15
    assert anim.xy_to_index(7, 1) == 8
    # Row 2 (even): flip resets.
    assert anim.xy_to_index(0, 2) == 16
    assert anim.xy_to_index(7, 2) == 23


def test_set_pixel_xy():
    buf = anim.new_buffer()
    anim.set_pixel_xy(buf, 3, 1, RED, 255)
    idx = anim.xy_to_index(3, 1)
    assert buf[idx] == (255, 0, 0)
    # Every other pixel untouched.
    assert all(c == BLACK for i, c in enumerate(buf) if i != idx)

    anim.set_pixel_xy(buf, 3, 1, RED, 128)
    assert buf[idx] == (128, 0, 0)


def test_fill():
    buf = anim.new_buffer()
    anim.fill(buf, BLUE, 255)
    assert all(c == (0, 0, 255) for c in buf)

    anim.fill(buf, BLUE, 0)
    assert all(c == BLACK for c in buf)


def test_fill_row():
    buf = anim.new_buffer()
    anim.fill_row(buf, 2, RED, 255)
    row2 = {anim.xy_to_index(x, 2) for x in range(anim.MATRIX_W)}
    for i, c in enumerate(buf):
        if i in row2:
            assert c == (255, 0, 0)
        else:
            assert c == BLACK


def test_lerp():
    assert anim.lerp(BLACK, (100, 100, 100), 0.0) == (0, 0, 0)
    assert anim.lerp(BLACK, (100, 100, 100), 1.0) == (100, 100, 100)
    assert anim.lerp(BLACK, (100, 100, 100), 0.5) == (50, 50, 50)
    # Out-of-range t clamps rather than extrapolating.
    assert anim.lerp(BLACK, (100, 100, 100), -1.0) == (0, 0, 0)
    assert anim.lerp(BLACK, (100, 100, 100), 2.0) == (100, 100, 100)


def test_sine_breathe():
    # t=0 -> phase 0 -> sin(0) = 0 -> midpoint of [min_b, max_b].
    assert anim.sine_breathe(0, 4000, 0, 100) == 50
    # Quarter period -> sin(pi/2) = 1 -> max_b.
    assert anim.sine_breathe(1000, 4000, 0, 100) == 100
    # Three-quarter period -> sin(3pi/2) = -1 -> min_b.
    assert anim.sine_breathe(3000, 4000, 0, 100) == 0


def test_pseudo_random():
    # Deterministic: same seed always gives the same value.
    a = anim.pseudo_random(7, -1.0, 1.0)
    b = anim.pseudo_random(7, -1.0, 1.0)
    assert a == b
    # In range, and different seeds (usually) give different values.
    assert -1.0 <= a < 1.0
    values = {anim.pseudo_random(i, 0.0, 1.0) for i in range(20)}
    assert len(values) > 1


def test_add_pixel_and_row():
    buf = anim.new_buffer()
    anim.set_pixel_xy(buf, 0, 0, (200, 0, 0), 255)
    anim.add_pixel_xy(buf, 0, 0, (100, 0, 0))
    assert buf[anim.xy_to_index(0, 0)] == (255, 0, 0)  # clamped, not 300

    buf = anim.new_buffer()
    anim.add_row(buf, 3, (10, 20, 30))
    row3 = {anim.xy_to_index(x, 3) for x in range(anim.MATRIX_W)}
    for i, c in enumerate(buf):
        if i in row3:
            assert c == (10, 20, 30)
        else:
            assert c == BLACK


def main():
    tests = [
        test_xy_to_index_serpentine,
        test_set_pixel_xy,
        test_fill,
        test_fill_row,
        test_lerp,
        test_sine_breathe,
        test_pseudo_random,
        test_add_pixel_and_row,
    ]
    for test in tests:
        test()
        print(f"OK  {test.__name__}")
    print(f"\n{len(tests)} checks passed.")


if __name__ == "__main__":
    main()
