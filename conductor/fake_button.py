"""Keyboard stand-in for the arcade button (no hardware wired yet).

Same shape as gpiozero.Button as used by conductor/main.py: a .when_pressed
attribute that gets assigned a no-arg callback. Reads raw stdin in a
background daemon thread so it never blocks the main tick loop.
"""
import sys
import termios
import threading
import tty

TRIGGER_KEY = " "


class FakeButton:
    def __init__(self):
        self.when_pressed = None
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self) -> None:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch == TRIGGER_KEY and self.when_pressed:
                    self.when_pressed()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
