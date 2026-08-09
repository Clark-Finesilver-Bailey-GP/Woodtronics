"""Wire protocol logic, per protocol/PROTOCOL.md. Pure Python, no hardware
imports, so it runs identically under MicroPython on the RP2040 and under
plain CPython for testing on the laptop.

Kept free of dataclasses / "X | None" annotations since those aren't
reliably available under MicroPython.
"""


def checksum(data):
    ck = 0
    for b in data:
        ck ^= b
    return "%02X" % ck


def build_frame(addr, word, *args):
    content = " ".join((addr, word) + args)
    return ("%s *%s\n" % (content, checksum(content.encode()))).encode()


def parse_frame(line):
    """Parse one received line (bytes, without trailing newline).

    Returns (addr, word, args) on a well-formed, checksum-valid frame,
    or None otherwise (malformed or bad checksum — PROTOCOL.md says a bad
    checksum on an incoming frame is dropped, not replied to).
    """
    try:
        text = line.decode("ascii").strip()
    except Exception:
        return None
    if " *" not in text:
        return None
    content, _, ck_str = text.rpartition(" *")
    if checksum(content.encode()) != ck_str.upper():
        return None
    parts = content.split(" ")
    if len(parts) < 2:
        return None
    return parts[0], parts[1], parts[2:]
