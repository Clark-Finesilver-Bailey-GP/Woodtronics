#!/usr/bin/env python3
"""Pi UART loopback self-test.

Confirms the Pi's serial port is enabled, configured, and wired before any
rocket is involved. Jumper a wire from the UART TX pin to the RX pin (e.g.
GPIO14 to GPIO15 on the 40-pin header) and run this with nothing else
attached to the bus.

Usage:
    python tools/uart_loopback.py [--port /dev/serial0] [--baud 115200]
"""
import argparse
import sys

import serial

READ_TIMEOUT_S = 1.0
TEST_PAYLOAD = bytes(range(256)) * 4  # 1024 bytes, exercises every byte value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/serial0")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    try:
        conn = serial.Serial(args.port, args.baud, timeout=READ_TIMEOUT_S)
    except serial.SerialException as e:
        sys.exit(f"couldn't open {args.port}: {e}")

    conn.reset_input_buffer()
    conn.write(TEST_PAYLOAD)
    conn.flush()
    received = conn.read(len(TEST_PAYLOAD))
    conn.close()

    if received == TEST_PAYLOAD:
        print(f"PASS: {len(TEST_PAYLOAD)} bytes echoed correctly on {args.port} @ {args.baud}")
        return

    if len(received) != len(TEST_PAYLOAD):
        print(f"FAIL: sent {len(TEST_PAYLOAD)} bytes, got {len(received)} back "
              f"(check the jumper, and that nothing else — e.g. a login console — "
              f"has the port open)")
    else:
        first_bad = next(i for i in range(len(TEST_PAYLOAD)) if TEST_PAYLOAD[i] != received[i])
        print(f"FAIL: byte mismatch at offset {first_bad} "
              f"(sent {TEST_PAYLOAD[first_bad]:#04x}, got {received[first_bad]:#04x})")
    sys.exit(1)


if __name__ == "__main__":
    main()
