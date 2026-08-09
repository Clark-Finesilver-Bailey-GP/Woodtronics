"""Show catalog. Hardware-facing (writes real NeoPixel buffers), kept thin —
the actual math lives in anim.py so it can be tested off-hardware.

Every show function has the signature (t_ms, matrix_a, matrix_b, ring) and
is responsible for setting pixels and calling .write() on whichever of the
three it touches. Keep placeholder show content (LAUNCH_A/LAUNCH_B) simple
and easy to eyeball-tune on the bench per protocol/PROTOCOL.md's note that
these are placeholders.
"""
import anim

BLACK = (0, 0, 0)

HALT_DURATION_MS = 2000
LAUNCH_RISE_MS = 1200
LAUNCH_RING_RAMP_MS = 400


def _fill(strip, color):
    for i in range(len(strip)):
        strip[i] = color
    strip.write()


def OFF(t_ms, matrix_a, matrix_b, ring):
    _fill(matrix_a, BLACK)
    _fill(matrix_b, BLACK)
    _fill(ring, BLACK)


def IDLE(t_ms, matrix_a, matrix_b, ring):
    level = anim.breathe(t_ms, period_ms=4000, min_b=10, max_b=60)
    color = (level, level // 2, 0)
    _fill(matrix_a, color)
    _fill(matrix_b, color)
    _fill(ring, color)


def HALT(t_ms, matrix_a, matrix_b, ring):
    if t_ms >= HALT_DURATION_MS:
        OFF(t_ms, matrix_a, matrix_b, ring)
        return
    progress = t_ms / HALT_DURATION_MS
    ceiling = int(80 * (1 - progress))
    matrix_level = anim.flicker(ceiling, jitter=ceiling // 2 + 1)
    ring_level = anim.flicker(ceiling, jitter=ceiling // 2 + 1)
    _fill(matrix_a, (matrix_level, matrix_level, matrix_level))
    _fill(matrix_b, (matrix_level, matrix_level, matrix_level))
    _fill(ring, (ring_level, ring_level // 3, 0))


def _rising_bar(matrix, t_ms, rise_ms, color):
    fraction = min(1.0, t_ms / rise_ms)
    lit_rows = fraction * anim.MATRIX_H
    for y in range(anim.MATRIX_H):
        row_color = color if (anim.MATRIX_H - 1 - y) < lit_rows else BLACK
        for x in range(anim.MATRIX_W):
            matrix[anim.xy_to_index(x, y)] = row_color
    matrix.write()


def LAUNCH_A(t_ms, matrix_a, matrix_b, ring):
    color = (255, 120, 0)  # orange/white
    _rising_bar(matrix_a, t_ms, LAUNCH_RISE_MS, color)
    _rising_bar(matrix_b, t_ms, LAUNCH_RISE_MS, color)
    ring_level = int(255 * min(1.0, t_ms / LAUNCH_RING_RAMP_MS))
    _fill(ring, (ring_level, ring_level // 2, 0))


def LAUNCH_B(t_ms, matrix_a, matrix_b, ring):
    color = (80, 100, 255)  # blue/violet
    rise_ms = LAUNCH_RISE_MS * 1.5
    _rising_bar(matrix_a, t_ms, rise_ms, color)
    _rising_bar(matrix_b, t_ms, rise_ms, color)
    ring_level = int(255 * min(1.0, t_ms / LAUNCH_RING_RAMP_MS))
    _fill(ring, (ring_level // 2, ring_level // 2, ring_level))


SHOWS = {
    "OFF": OFF,
    "IDLE": IDLE,
    "HALT": HALT,
    "LAUNCH_A": LAUNCH_A,
    "LAUNCH_B": LAUNCH_B,
}
