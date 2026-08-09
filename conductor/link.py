"""Serial link to a rocket, per protocol/PROTOCOL.md.

Owns frame checksumming and the timeout/retry rule from PROTOCOL.md's
"Timeout / retry" section. Does not own port configuration — callers pass
an already-open serial.Serial, so this works identically against a real
Pi UART or tools/fake_rockets.py's pty device.
"""
import logging
from dataclasses import dataclass

import serial

logger = logging.getLogger(__name__)

READ_TIMEOUT_S = 0.2


def checksum(data: bytes) -> str:
    ck = 0
    for b in data:
        ck ^= b
    return "%02X" % ck


def build_frame(addr: str, word: str, *args: str) -> bytes:
    content = " ".join((addr, word, *args))
    return f"{content} *{checksum(content.encode())}\n".encode()


@dataclass
class LinkResult:
    ok: bool
    word: str | None = None
    code: str | None = None


class RocketLink:
    def __init__(self, conn: serial.Serial):
        self._conn = conn
        self._conn.timeout = READ_TIMEOUT_S

    def send(self, addr: str, word: str, *args: str) -> LinkResult:
        result = self._send_once(addr, word, *args)
        if result.ok:
            return result
        result = self._send_once(addr, word, *args)
        if not result.ok:
            logger.warning("%s unresponsive after retry: %s %s", addr, word, " ".join(args))
        return result

    def _send_once(self, addr: str, word: str, *args: str) -> LinkResult:
        self._conn.write(build_frame(addr, word, *args))
        line = self._conn.readline()
        if not line.endswith(b"\n"):
            return LinkResult(ok=False)

        try:
            text = line.decode("ascii").strip()
        except UnicodeDecodeError:
            return LinkResult(ok=False)

        if " *" not in text:
            return LinkResult(ok=False)
        content, _, ck_str = text.rpartition(" *")
        if checksum(content.encode()) != ck_str.upper():
            return LinkResult(ok=False)

        parts = content.split(" ")
        if len(parts) < 2 or parts[0] != "PI":
            return LinkResult(ok=False)

        reply_word, reply_args = parts[1], parts[2:]
        if reply_word == "ACK":
            return LinkResult(ok=True, word=reply_args[0] if reply_args else None)
        if reply_word == "ERR":
            return LinkResult(ok=False, code=reply_args[0] if reply_args else None)
        return LinkResult(ok=False)
