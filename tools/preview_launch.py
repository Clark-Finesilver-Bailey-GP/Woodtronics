#!/usr/bin/env python3
"""Bench preview of the LAUNCH show, without hardware.

rocket/shows.py never actually required a real neopixel.NeoPixel — it only
needs something with __setitem__ and .write(). This drives shows.LAUNCH
across the full ~14s at the real 30fps tick rate using plain-list fakes,
and prints one summary line per phase transition plus a few sampled CLIMB
frames. It won't tell you how this reads through the diffuser, but it will
catch timing/boundary/math bugs (wrong phase length, off-by-one row,
streak math blowing up) before any of this reaches a REPL on hardware.

Usage:
    python3 tools/preview_launch.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "rocket"))

import shows

TICK_MS = 33  # matches rocket/main.py's TICK_MS


class FakeStrip(list):
    def __init__(self, n):
        super().__init__([(0, 0, 0)] * n)

    def write(self):
        pass


def avg_brightness(strip):
    n = len(strip)
    return sum(sum(c) for c in strip) / (n * 3)


def check_charge_fills_bottom_up():
    """CHARGE must light y=0 (bottom) first — CW's spec is explicit about
    this, and it's the kind of thing that silently inverts if anim.py's
    y=0-is-bottom convention gets crossed with a top-down loop again."""
    import anim

    matrix_a, matrix_b, ring = FakeStrip(64), FakeStrip(64), FakeStrip(16)
    t_first_row = shows.WAKE_MS + 1  # 1ms into CHARGE: exactly one row lit
    shows.LAUNCH(t_first_row, matrix_a, matrix_b, ring)
    bottom_lit = sum(matrix_a[anim.xy_to_index(0, 0)]) > 0
    top_lit = sum(matrix_a[anim.xy_to_index(0, 7)]) > 0
    assert bottom_lit, "CHARGE's first lit row should be y=0 (bottom)"
    assert not top_lit, "CHARGE should not light y=7 (top) before y=0"
    print("OK  check_charge_fills_bottom_up")


def main():
    check_charge_fills_bottom_up()
    print()

    matrix_a = FakeStrip(64)
    matrix_b = FakeStrip(64)
    ring = FakeStrip(16)

    boundaries = []
    running = 0
    for duration, phase in shows._LAUNCH_PHASES:
        running += duration
        boundaries.append((running, phase.__name__))

    # Sweep the full sequence at the real tick rate first, just to confirm
    # nothing throws across every t_ms a rocket would actually see.
    t_ms = 0
    while t_ms <= shows.LAUNCH_TOTAL_MS + 500:
        shows.LAUNCH(t_ms, matrix_a, matrix_b, ring)
        t_ms += TICK_MS
    print("full 30fps sweep OK, no exceptions.\n")

    # Now take explicit snapshots at the last tick *inside* each phase
    # (boundary - 1ms), so "end of X" actually shows X's own last frame
    # rather than the next phase's first one.
    for b_ms, name in boundaries:
        shows.LAUNCH(b_ms - 1, matrix_a, matrix_b, ring)
        print(f"t={b_ms - 1:6d}ms  end of {name:10s}  matrix_avg={avg_brightness(matrix_a):6.1f}  ring={tuple(ring[0])}")

    print()
    for t_ms in (7000, 7700, 8400):  # mid-CLIMB samples
        shows.LAUNCH(t_ms, matrix_a, matrix_b, ring)
        print(f"  climb sample t={t_ms}ms  matrix_avg={avg_brightness(matrix_a):6.1f}  ring={tuple(ring[0])}")

    shows.LAUNCH(shows.LAUNCH_TOTAL_MS + 500, matrix_a, matrix_b, ring)
    print(f"\nfinal (post-sequence hold) matrix_avg={avg_brightness(matrix_a):6.1f}  ring={tuple(ring[0])}")


if __name__ == "__main__":
    main()
