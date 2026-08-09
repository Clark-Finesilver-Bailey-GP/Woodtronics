#!/usr/bin/env python3
"""Fake-rocket harness for bench-testing conductor/ against protocol/PROTOCOL.md.

Opens a virtual serial pair and impersonates R1..RN on it, so conductor/ can
talk real pyserial to a real device path without any rocket hardware.

Usage:
    python tools/fake_rockets.py --count 3 --fail R2=silent --fail R3=corrupt
"""
import argparse
import os
import sys

VALID_WORDS = {"PING", "ANIM", "IGNITE", "OFF"}
EXPECTED_ARGC = {"PING": 0, "ANIM": 1, "IGNITE": 1, "OFF": 0}


def checksum(data: bytes) -> str:
    ck = 0
    for b in data:
        ck ^= b
    return "%02X" % ck


def build_frame(content: str) -> bytes:
    return f"{content} *{checksum(content.encode())}\n".encode()


def build_corrupt_frame(content: str) -> bytes:
    good = int(checksum(content.encode()), 16)
    bad = good ^ 0xFF
    return f"{content} *{bad:02X}\n".encode()


def handle_command(addr: str, word: str, args: list[str]) -> str:
    """Return the reply content (without ' *CK\\n') for a well-formed, checksum-valid command."""
    if word not in VALID_WORDS:
        return f"PI ERR UNK"
    if len(args) != EXPECTED_ARGC[word]:
        return f"PI ERR ARG"
    if word in ("ANIM", "IGNITE"):
        try:
            int(args[0])
        except ValueError:
            return f"PI ERR ARG"
    return f"PI ACK {word}"


def parse_fail_arg(spec: str) -> tuple[str, str]:
    addr, _, mode = spec.partition("=")
    if mode not in ("silent", "corrupt"):
        raise argparse.ArgumentTypeError(f"bad --fail spec {spec!r}, mode must be silent or corrupt")
    return addr, mode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5, help="simulate R1..RN")
    parser.add_argument("--fail", action="append", default=[], metavar="ADDR=MODE",
                         help="e.g. R2=silent or R3=corrupt; repeatable")
    args = parser.parse_args()

    modes = {f"R{i}": "ok" for i in range(1, args.count + 1)}
    for spec in args.fail:
        addr, mode = parse_fail_arg(spec)
        if addr not in modes:
            sys.exit(f"--fail {spec}: {addr} is not in R1..R{args.count}")
        modes[addr] = mode

    master_fd, slave_fd = os.openpty()
    slave_path = os.ttyname(slave_fd)
    summary = ", ".join(f"{addr} {mode}" for addr, mode in modes.items())
    print(f"Fake rockets on {slave_path} — {summary}")
    print("Ctrl-C to stop.")

    buf = b""
    try:
        while True:
            chunk = os.read(master_fd, 256)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                process_line(master_fd, line, modes)
    except KeyboardInterrupt:
        pass
    finally:
        os.close(master_fd)
        os.close(slave_fd)


def process_line(master_fd: int, raw: bytes, modes: dict) -> None:
    try:
        line = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        print(f"<< {raw!r} (undecodable, dropped)")
        return
    if not line:
        return
    print(f"<< {line}")

    if " *" not in line:
        print("   dropped (no checksum marker)")
        return
    content, _, ck_str = line.rpartition(" *")
    parts = content.split(" ")
    addr = parts[0]
    if addr not in modes:
        return  # not addressed to any rocket we're simulating

    mode = modes[addr]
    if checksum(content.encode()) != ck_str.upper():
        reply = build_frame("PI ERR CK")
        os.write(master_fd, reply)
        print(f">> {reply.decode().strip()} (bad checksum from Pi)")
        return

    word = parts[1] if len(parts) > 1 else ""
    cmd_args = parts[2:]
    reply_content = handle_command(addr, word, cmd_args)

    if mode == "silent":
        print(f"   ({addr} is silent, no reply sent)")
        return
    if mode == "corrupt":
        reply = build_corrupt_frame(reply_content)
    else:
        reply = build_frame(reply_content)
    os.write(master_fd, reply)
    print(f">> {reply.decode().strip()}")


if __name__ == "__main__":
    main()
