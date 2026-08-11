"""Pure animation math, no hardware imports — runs under MicroPython or CPython."""
import math
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


def new_buffer():
    """A fresh 8x8 frame buffer, all black. Index with xy_to_index()."""
    return [(0, 0, 0)] * (MATRIX_W * MATRIX_H)


def scale(color, brightness):
    """color scaled by brightness (0-255), per channel, clamped to [0, 255]."""
    b = max(0, min(255, brightness))
    return tuple(max(0, min(255, c * b // 255)) for c in color)


def set_pixel_xy(buffer, x, y, color, brightness):
    """Write one pixel into buffer, serpentine-corrected, brightness-scaled."""
    buffer[xy_to_index(x, y)] = scale(color, brightness)


def fill(buffer, color, brightness):
    """Set every pixel in buffer to color at brightness."""
    c = scale(color, brightness)
    for i in range(len(buffer)):
        buffer[i] = c


def fill_row(buffer, y, color, brightness):
    """Set every pixel in row y to color at brightness."""
    for x in range(MATRIX_W):
        set_pixel_xy(buffer, x, y, color, brightness)


def lerp(c1, c2, t):
    """Per-channel linear interpolation between two colors. t clamped to [0, 1]."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def sine_breathe(t_ms, period_ms, min_b, max_b):
    """Sine-wave brightness, cycling between min_b and max_b every period_ms."""
    phase = (t_ms % period_ms) / period_ms  # 0..1
    level = (1 + math.sin(2 * math.pi * phase)) / 2  # 0..1
    return int(min_b + level * (max_b - min_b))


def pseudo_random(seed, lo, hi):
    """Deterministic float in [lo, hi) from an integer seed.

    Same seed always gives the same value — used to give things like
    per-streak speed variance a stable identity without persisted state,
    since shows are recomputed from t_ms on every tick.
    """
    frac = ((seed * 2654435761) % 1000003) / 1000003  # 0..1
    return lo + frac * (hi - lo)


def add_pixel_xy(buffer, x, y, color):
    """Add color into the existing pixel at (x, y), clamped to [0, 255]."""
    idx = xy_to_index(x, y)
    existing = buffer[idx]
    buffer[idx] = tuple(max(0, min(255, a + b)) for a, b in zip(existing, color))


def add_row(buffer, y, color):
    """Add color into every pixel in row y, clamped to [0, 255]."""
    for x in range(MATRIX_W):
        add_pixel_xy(buffer, x, y, color)
