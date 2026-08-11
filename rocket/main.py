"""Rocket entry point. Untestable off-hardware — see rocket/link.py and
rocket/anim.py for the parts of this that ARE tested (checksum/frame
parsing, animation math). Keep this file obvious: it's debugged on
hardware over a REPL, not in an editor.
"""
import time
from machine import UART, Pin
import neopixel

import link
import shows
from config import ROCKET_ID

UART_ID = 0
UART_TX_PIN = 0
UART_RX_PIN = 1
BAUD = 115200  # must match protocol/PROTOCOL.md

MATRIX_A_PIN = 10
MATRIX_B_PIN = 11
RING_PIN = 12
MATRIX_PIXELS = 64  # 8x8
RING_PIXELS = 16

TICK_MS = 33  # ~30fps frame clock, per protocol/spec — the rate show math is tuned against
MAX_BUF_BYTES = 128  # matches PROTOCOL.md's 64-byte max line, with headroom


def _handle(word, args):
    """Returns (reply_bytes, new_show_name_or_None)."""
    if word == "PING":
        return link.build_frame("PI", "ACK", "PING"), None
    if word == "SHOW":
        if len(args) == 1 and args[0] in shows.SHOWS:
            return link.build_frame("PI", "ACK", "SHOW"), args[0]
        return link.build_frame("PI", "ERR", "ARG"), None
    return link.build_frame("PI", "ERR", "UNK"), None


def main():
    uart = UART(UART_ID, baudrate=BAUD, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))
    matrix_a = neopixel.NeoPixel(Pin(MATRIX_A_PIN), MATRIX_PIXELS)
    matrix_b = neopixel.NeoPixel(Pin(MATRIX_B_PIN), MATRIX_PIXELS)
    ring = neopixel.NeoPixel(Pin(RING_PIN), RING_PIXELS)

    buf = b""
    current = "IDLE"
    show_start = time.ticks_ms()

    while True:
        n = uart.any()
        if n:
            buf += uart.read(n)
            if len(buf) > MAX_BUF_BYTES:
                buf = buf[-MAX_BUF_BYTES:]
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                frame = link.parse_frame(line)
                if frame is None:
                    continue
                addr, word, args = frame
                if addr != ROCKET_ID:
                    continue
                reply, new_show = _handle(word, args)
                uart.write(reply)
                if new_show is not None:
                    current = new_show
                    show_start = time.ticks_ms()

        elapsed = time.ticks_diff(time.ticks_ms(), show_start)
        shows.SHOWS[current](elapsed, matrix_a, matrix_b, ring)
        time.sleep_ms(TICK_MS)


if __name__ == "__main__":
    main()
