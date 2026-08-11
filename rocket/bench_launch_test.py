"""Bench test: run the real shows.LAUNCH sequence on hardware, standalone
(no UART/conductor needed). Run at the REPL with both matrices + ring
wired per rocket/main.py's pins.

    >>> import bench_launch_test
    >>> bench_launch_test.main()

Drives matrix_a/matrix_b/ring exactly like rocket/main.py's real loop
does (same TICK_MS, same shows.LAUNCH(t_ms, ...) call), just without the
UART command handling — this is only for watching the show run, not for
testing the protocol. Prints one line per phase as it's entered, so you
can match what you see against protocol/PROTOCOL.md's phase list.
Finishes by explicitly switching to shows.OFF (mirrors the trailing
SHOW IDLE step in shows/launch_a.json, minus the breathing).
"""
import time
from machine import Pin
import neopixel

import shows

MATRIX_A_PIN = 10
MATRIX_B_PIN = 11
RING_PIN = 12
MATRIX_PIXELS = 64
RING_PIXELS = 16
TICK_MS = 33  # matches rocket/main.py's TICK_MS


def main():
    matrix_a = neopixel.NeoPixel(Pin(MATRIX_A_PIN), MATRIX_PIXELS)
    matrix_b = neopixel.NeoPixel(Pin(MATRIX_B_PIN), MATRIX_PIXELS)
    ring = neopixel.NeoPixel(Pin(RING_PIN), RING_PIXELS)

    boundaries = []
    running = 0
    for duration, phase in shows._LAUNCH_PHASES:
        boundaries.append((running, phase.__name__))
        running += duration

    print("running LAUNCH, ~%dms total..." % shows.LAUNCH_TOTAL_MS)
    start = time.ticks_ms()
    next_idx = 0
    while True:
        t_ms = time.ticks_diff(time.ticks_ms(), start)
        if next_idx < len(boundaries) and t_ms >= boundaries[next_idx][0]:
            print("t=%6dms  entering %s" % (t_ms, boundaries[next_idx][1]))
            next_idx += 1
        if t_ms > shows.LAUNCH_TOTAL_MS:
            break
        shows.LAUNCH(t_ms, matrix_a, matrix_b, ring)
        time.sleep_ms(TICK_MS)

    shows.OFF(t_ms, matrix_a, matrix_b, ring)
    print("done.")


if __name__ == "__main__":
    main()
