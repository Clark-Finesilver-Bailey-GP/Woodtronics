"""Bench test: verify set_pixel_xy's serpentine mapping against the real
matrix, before trusting anything in shows.py. Run alone at the REPL with
ONE matrix wired up.

    >>> import bench_pixel_test
    >>> bench_pixel_test.main()

Each pixel lights alone, swept in (x, y) order: (0,0) is the BOTTOM-LEFT
of the panel (y=0 is bottom, per protocol/PROTOCOL.md's canvas
convention), sweeping left-to-right, bottom-to-top. The REPL prints each
(x, y) as it lights, so you can follow along on the panel. If what lights
doesn't match what's printed — wrong pixel, wrong row order, mirrored row
— check MATRIX_SERPENTINE in anim.py against the physical wiring before
going any further.

After the sweep, all four corners light together in different colors as
a second, independent check of orientation.

Once a single matrix checks out, wire up the second one and run
main_both() instead — it drives both from the same buffer each frame
(matching the "compute once, write to both strands" rule both matrices
must follow in shows.py) and checks they render identically.
"""
import time
from machine import Pin
import neopixel

import anim

MATRIX_A_PIN = 10  # matches rocket/main.py's MATRIX_A_PIN/MATRIX_B_PIN
MATRIX_B_PIN = 11
MATRIX_PIN = MATRIX_A_PIN  # used by the single-matrix functions below
MATRIX_PIXELS = 64
STEP_MS = 300
SWEEP_COLOR = (0, 60, 0)  # dim green - easy on the eyes, bright enough to see


def _blit(strip, buf):
    for i, c in enumerate(buf):
        strip[i] = c
    strip.write()


def _clear(strip):
    _blit(strip, anim.new_buffer())


def sweep(strip):
    for y in range(anim.MATRIX_H):
        for x in range(anim.MATRIX_W):
            buf = anim.new_buffer()
            anim.set_pixel_xy(buf, x, y, SWEEP_COLOR, 255)
            _blit(strip, buf)
            print("(x=%d, y=%d)" % (x, y))
            time.sleep_ms(STEP_MS)


def corners(strip):
    """All four corners at once, different colors — sanity-checks
    orientation (is y=0 really the bottom?) independent of the sweep."""
    buf = anim.new_buffer()
    anim.set_pixel_xy(buf, 0, 0, (60, 0, 0), 255)   # red    = bottom-left
    anim.set_pixel_xy(buf, 7, 0, (0, 60, 0), 255)   # green  = bottom-right
    anim.set_pixel_xy(buf, 0, 7, (0, 0, 60), 255)   # blue   = top-left
    anim.set_pixel_xy(buf, 7, 7, (60, 60, 0), 255)  # yellow = top-right
    _blit(strip, buf)
    print("corners: red=bottom-left  green=bottom-right  blue=top-left  yellow=top-right")


def main():
    strip = neopixel.NeoPixel(Pin(MATRIX_PIN), MATRIX_PIXELS)
    _clear(strip)
    print("sweeping all 64 pixels, ~%dms apart..." % STEP_MS)
    sweep(strip)
    print("\nnow lighting all four corners together:")
    corners(strip)


def sweep_both(strip_a, strip_b):
    """Same buffer, both strips, every frame — matches how shows.py is
    required to drive matrix_a/matrix_b (identical content, computed
    once). If the two panels ever show different pixels here, it's a
    wiring/pin mixup, not a set_pixel_xy bug (that's already verified)."""
    for y in range(anim.MATRIX_H):
        for x in range(anim.MATRIX_W):
            buf = anim.new_buffer()
            anim.set_pixel_xy(buf, x, y, SWEEP_COLOR, 255)
            _blit(strip_a, buf)
            _blit(strip_b, buf)
            print("(x=%d, y=%d)" % (x, y))
            time.sleep_ms(STEP_MS)


def corners_both(strip_a, strip_b):
    buf = anim.new_buffer()
    anim.set_pixel_xy(buf, 0, 0, (60, 0, 0), 255)   # red    = bottom-left
    anim.set_pixel_xy(buf, 7, 0, (0, 60, 0), 255)   # green  = bottom-right
    anim.set_pixel_xy(buf, 0, 7, (0, 0, 60), 255)   # blue   = top-left
    anim.set_pixel_xy(buf, 7, 7, (60, 60, 0), 255)  # yellow = top-right
    _blit(strip_a, buf)
    _blit(strip_b, buf)
    print("corners: red=bottom-left  green=bottom-right  blue=top-left  yellow=top-right")


def main_both():
    strip_a = neopixel.NeoPixel(Pin(MATRIX_A_PIN), MATRIX_PIXELS)
    strip_b = neopixel.NeoPixel(Pin(MATRIX_B_PIN), MATRIX_PIXELS)
    _clear(strip_a)
    _clear(strip_b)
    print("sweeping both matrices together, ~%dms apart..." % STEP_MS)
    sweep_both(strip_a, strip_b)
    print("\nnow lighting all four corners together on both:")
    corners_both(strip_a, strip_b)
    print("\nWatch both panels: they should match, pixel for pixel, the whole way through.")


if __name__ == "__main__":
    main()
