"""Show catalog. Hardware-facing (writes real NeoPixel buffers), kept thin —
the actual math lives in anim.py so it can be tested off-hardware.

Every show function has the signature (t_ms, matrix_a, matrix_b, ring) and
is responsible for setting pixels and calling .write() on whichever of the
three it touches. matrix_a/matrix_b/ring only need __setitem__ and .write()
— on hardware that's a neopixel.NeoPixel, on the bench it can be any plain
list-like fake (see tools/preview_launch.py).
"""
import anim
from config import ROCKET_ID

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# All timing/color constants live here — retuned on-site under gallery
# lighting, especially: streak speed, ignition flash duration, phase
# durations, brightness cap, ID colors.

GLOBAL_BRIGHTNESS_CAP = 140  # ~55% — behind wood + diffuser paper

IDLE_COLOR = (0, 0, 40)
IDLE_PERIOD_MS = 4000
IDLE_MIN_B = 38   # ~0.15
IDLE_MAX_B = 64   # ~0.25

ID_COLORS = {
    "R1": (255, 0, 0),      # red
    "R2": (255, 180, 0),    # amber
    "R3": (0, 200, 60),     # green
    "R4": (0, 200, 255),    # cyan
    "R5": (160, 0, 255),    # violet
}
ID_COLOR = ID_COLORS[ROCKET_ID]

HALT_DURATION_MS = 2000

# LAUNCH phase durations (ms) — sum is the ~14s in CW's spec.
WAKE_MS = 2000
CHARGE_MS = 3000
IGNITION_MS = 400
CLIMB_MS = 5000
RELAY_MS = 2000
SETTLE_MS = 1500
LAUNCH_TOTAL_MS = WAKE_MS + CHARGE_MS + IGNITION_MS + CLIMB_MS + RELAY_MS + SETTLE_MS

# WAKE
WAKE_PERIOD_START_MS = 4000
WAKE_PERIOD_END_MS = 800
WAKE_MIN_B_START = 38   # ~0.15
WAKE_MIN_B_END = 89     # ~0.35

# CHARGE
CHARGE_ROW_INTERVAL_MS = CHARGE_MS // anim.MATRIX_H  # 375ms/row, 8 rows
CHARGE_ROW_FLASH_MS = 100
CHARGE_LIT_B = 128       # ~0.5
CHARGE_FLASH_B = 255     # ~1.0
CHARGE_RING_COLOR = (60, 20, 0)
CHARGE_RING_MAX_B = 102  # ~0.4

# IGNITION
IGNITION_FLASH_MS = 80
IGNITION_RING_FLASH_COLOR = (255, 220, 180)
IGNITION_DECAY_COLOR = (255, 255, 200)  # pale yellow
IGNITION_DECAY_B = 77    # ~0.3
IGNITION_RING_COLOR = (255, 90, 0)
IGNITION_RING_MIN_B = 153  # ~0.6
IGNITION_RING_MAX_B = 255  # ~1.0
IGNITION_FLICKER_STEP_MS = 60

# CLIMB
CLIMB_SPAWN_INTERVAL_MS = 250
CLIMB_STREAK_TRAVEL_MS = 600
CLIMB_STREAK_SPEED_VARIANCE = 0.15
CLIMB_HOT_COLOR = (255, 255, 220)
CLIMB_MID_COLOR = (255, 180, 60)
CLIMB_LOW_COLOR = (255, 80, 0)
CLIMB_HOT_B = 255    # ~1.0
CLIMB_MID_B = 153    # ~0.6
CLIMB_LOW_B = 64      # ~0.25
CLIMB_BG_COLOR = (40, 10, 0)
CLIMB_BG_B = 26       # ~0.1
CLIMB_RING_START_COLOR = (255, 90, 0)
CLIMB_RING_END_COLOR = (200, 40, 0)
CLIMB_RING_B = 255

# RELAY
RELAY_PULSE_TIMES_MS = (0, 600, 1200)
RELAY_PULSE_RISE_MS = 80
RELAY_PULSE_DECAY_MS = 250
RELAY_REST_B = 26     # ~0.1
RELAY_PEAK_B = 255    # ~1.0
RELAY_RING_START_COLOR = (120, 25, 0)
RELAY_RING_END_COLOR = (0, 0, 0)


def _capped(brightness):
    """Apply GLOBAL_BRIGHTNESS_CAP to a phase-computed 0-255 brightness."""
    return brightness * GLOBAL_BRIGHTNESS_CAP // 255


def _blit(buffer, matrix_a, matrix_b):
    for i, color in enumerate(buffer):
        matrix_a[i] = color
        matrix_b[i] = color
    matrix_a.write()
    matrix_b.write()


def _ring_fill(ring, color, brightness):
    c = anim.scale(color, _capped(brightness))
    for i in range(len(ring)):
        ring[i] = c
    ring.write()


def _fill(strip, color):
    for i in range(len(strip)):
        strip[i] = color
    strip.write()


def OFF(t_ms, matrix_a, matrix_b, ring):
    _fill(matrix_a, BLACK)
    _fill(matrix_b, BLACK)
    _fill(ring, BLACK)


def IDLE(t_ms, matrix_a, matrix_b, ring):
    b = anim.sine_breathe(t_ms, IDLE_PERIOD_MS, IDLE_MIN_B, IDLE_MAX_B)
    buf = anim.new_buffer()
    anim.fill(buf, IDLE_COLOR, _capped(b))
    _blit(buf, matrix_a, matrix_b)
    _fill(ring, BLACK)


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


# --- LAUNCH phases -----------------------------------------------------
# Each _phase(t_ms, ...) takes t_ms *relative to that phase's own start*.

def _wake(t_ms, matrix_a, matrix_b, ring):
    progress = min(1.0, t_ms / WAKE_MS)
    period_ms = WAKE_PERIOD_START_MS + (WAKE_PERIOD_END_MS - WAKE_PERIOD_START_MS) * progress
    min_b = int(WAKE_MIN_B_START + (WAKE_MIN_B_END - WAKE_MIN_B_START) * progress)
    max_b = min_b + (IDLE_MAX_B - IDLE_MIN_B)
    b = anim.sine_breathe(t_ms, int(period_ms), min_b, max_b)
    color = anim.lerp(IDLE_COLOR, WHITE, progress)
    buf = anim.new_buffer()
    anim.fill(buf, color, _capped(b))
    _blit(buf, matrix_a, matrix_b)
    _fill(ring, BLACK)


def _charge(t_ms, matrix_a, matrix_b, ring):
    # y=0 is the bottom row (see anim.py); CW's spec fills bottom-up, so
    # rows light in increasing y order as lit_rows grows.
    lit_rows = min(anim.MATRIX_H, int(t_ms // CHARGE_ROW_INTERVAL_MS) + 1)
    time_in_row = t_ms % CHARGE_ROW_INTERVAL_MS
    buf = anim.new_buffer()
    for y in range(lit_rows):
        is_newest = y == lit_rows - 1
        b = CHARGE_FLASH_B if (is_newest and time_in_row < CHARGE_ROW_FLASH_MS) else CHARGE_LIT_B
        anim.fill_row(buf, y, WHITE, _capped(b))
    _blit(buf, matrix_a, matrix_b)
    ring_b = int(CHARGE_RING_MAX_B * min(1.0, t_ms / CHARGE_MS))
    _ring_fill(ring, CHARGE_RING_COLOR, ring_b)


def _ignition(t_ms, matrix_a, matrix_b, ring):
    buf = anim.new_buffer()
    if t_ms < IGNITION_FLASH_MS:
        anim.fill(buf, WHITE, _capped(255))
        _blit(buf, matrix_a, matrix_b)
        _ring_fill(ring, IGNITION_RING_FLASH_COLOR, 255)
        return
    decay_progress = (t_ms - IGNITION_FLASH_MS) / (IGNITION_MS - IGNITION_FLASH_MS)
    color = anim.lerp(WHITE, IGNITION_DECAY_COLOR, decay_progress)
    b = int(255 + (IGNITION_DECAY_B - 255) * decay_progress)
    anim.fill(buf, color, _capped(b))
    _blit(buf, matrix_a, matrix_b)
    step = int(t_ms // IGNITION_FLICKER_STEP_MS)
    ring_b = int(anim.pseudo_random(step, IGNITION_RING_MIN_B, IGNITION_RING_MAX_B))
    _ring_fill(ring, IGNITION_RING_COLOR, ring_b)


def _climb(t_ms, matrix_a, matrix_b, ring):
    buf = anim.new_buffer()
    anim.fill(buf, CLIMB_BG_COLOR, _capped(CLIMB_BG_B))

    last_index = int(t_ms // CLIMB_SPAWN_INTERVAL_MS)
    for i in range(last_index + 1):
        spawn_ms = i * CLIMB_SPAWN_INTERVAL_MS
        variance = anim.pseudo_random(i, -CLIMB_STREAK_SPEED_VARIANCE, CLIMB_STREAK_SPEED_VARIANCE)
        duration_ms = CLIMB_STREAK_TRAVEL_MS * (1 + variance)
        elapsed = t_ms - spawn_ms
        if elapsed < 0 or elapsed >= duration_ms:
            continue
        y_s = anim.MATRIX_H * (elapsed / duration_ms)
        head = int(y_s)
        for offset, color, b in (
            (0, CLIMB_HOT_COLOR, CLIMB_HOT_B),
            (-1, CLIMB_MID_COLOR, CLIMB_MID_B),
            (-2, CLIMB_LOW_COLOR, CLIMB_LOW_B),
        ):
            y = head + offset
            if 0 <= y < anim.MATRIX_H:
                anim.add_row(buf, y, anim.scale(color, _capped(b)))

    _blit(buf, matrix_a, matrix_b)
    ring_color = anim.lerp(CLIMB_RING_START_COLOR, CLIMB_RING_END_COLOR, t_ms / CLIMB_MS)
    _ring_fill(ring, ring_color, CLIMB_RING_B)


def _relay(t_ms, matrix_a, matrix_b, ring):
    b = RELAY_REST_B
    for pulse_start in RELAY_PULSE_TIMES_MS:
        since_pulse = t_ms - pulse_start
        if 0 <= since_pulse < RELAY_PULSE_RISE_MS:
            b = int(RELAY_REST_B + (RELAY_PEAK_B - RELAY_REST_B) * (since_pulse / RELAY_PULSE_RISE_MS))
            break
        if RELAY_PULSE_RISE_MS <= since_pulse < RELAY_PULSE_RISE_MS + RELAY_PULSE_DECAY_MS:
            decay_progress = (since_pulse - RELAY_PULSE_RISE_MS) / RELAY_PULSE_DECAY_MS
            b = int(RELAY_PEAK_B + (RELAY_REST_B - RELAY_PEAK_B) * decay_progress)
            break
    buf = anim.new_buffer()
    anim.fill(buf, ID_COLOR, _capped(b))
    _blit(buf, matrix_a, matrix_b)
    ring_color = anim.lerp(RELAY_RING_START_COLOR, RELAY_RING_END_COLOR, t_ms / RELAY_MS)
    _ring_fill(ring, ring_color, 255)


def _settle(t_ms, matrix_a, matrix_b, ring):
    progress = min(1.0, t_ms / SETTLE_MS)
    color = anim.lerp(ID_COLOR, IDLE_COLOR, progress)
    b = int(RELAY_REST_B + (IDLE_MIN_B - RELAY_REST_B) * progress)
    buf = anim.new_buffer()
    anim.fill(buf, color, _capped(b))
    _blit(buf, matrix_a, matrix_b)
    _fill(ring, BLACK)


_LAUNCH_PHASES = (
    (WAKE_MS, _wake),
    (CHARGE_MS, _charge),
    (IGNITION_MS, _ignition),
    (CLIMB_MS, _climb),
    (RELAY_MS, _relay),
    (SETTLE_MS, _settle),
)


def LAUNCH(t_ms, matrix_a, matrix_b, ring):
    remaining = t_ms
    for duration, phase in _LAUNCH_PHASES:
        if remaining < duration:
            phase(remaining, matrix_a, matrix_b, ring)
            return
        remaining -= duration
    # Past the end of the sequence — hold SETTLE's final frame. The
    # conductor's show file is expected to send SHOW IDLE shortly after
    # LAUNCH_TOTAL_MS; this is just a safe fallback, not the real hand-off.
    _settle(SETTLE_MS, matrix_a, matrix_b, ring)


SHOWS = {
    "OFF": OFF,
    "IDLE": IDLE,
    "HALT": HALT,
    "LAUNCH": LAUNCH,
}
