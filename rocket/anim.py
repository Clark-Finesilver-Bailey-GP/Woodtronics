"""Pure animation math, no hardware imports — runs under MicroPython or CPython."""
import random

MATRIX_W = 8
MATRIX_H = 8
MATRIX_SERPENTINE = True


def xy_to_index(x, y):
    """Matrix (x, y) -> pixel index, correcting for serpentine wiring."""
    if MATRIX_SERPENTINE and y % 2 == 1:
        x = MATRIX_W - 1 - x
    return y * MATRIX_W + x


def breathe(t_ms, period_ms, min_b, max_b):
    """Triangle-wave brightness, cycling between min_b and max_b every period_ms."""
    phase = (t_ms % period_ms) / period_ms  # 0..1
    if phase < 0.5:
        level = phase * 2
    else:
        level = 2 - phase * 2
    return int(min_b + level * (max_b - min_b))


def flicker(max_b, jitter):
    """max_b with up to +/-jitter of random noise, clamped to [0, max_b]."""
    level = max_b + random.randint(-jitter, jitter)
    return max(0, min(max_b, level))
