"""Conductor entry point: button -> show -> rockets, per protocol/PROTOCOL.md."""
import argparse
import logging
import time
from pathlib import Path

import serial

from fake_button import FakeButton
from link import RocketLink
from schedule import Scheduler, make_halt_steps, pick_random_show

ROCKET_ADDRS = ["R1", "R2", "R3", "R4", "R5"]
# On Pi 5, /dev/serial0 is the debug-header UART, not GPIO14/15. The bus
# uses GPIO14/15, which needs dtoverlay=uart0-pi5 in config.txt and shows
# up as /dev/ttyAMA0. See protocol/PROTOCOL.md "Pi 5 UART setup".
SERIAL_PORT = "/dev/ttyAMA0"
BAUD = 115200
BUTTON_PIN = 17
SHOWS_DIR = Path(__file__).parent.parent / "shows"
HALT_JITTER_MAX_MS = 800
TICK_S = 0.02

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class ButtonState:
    pressed = False


def run(link: RocketLink, button: object, shows_dir: Path) -> None:
    state = ButtonState()
    button.when_pressed = lambda: setattr(state, "pressed", True)

    scheduler = None
    while True:
        if state.pressed:
            state.pressed = False
            if scheduler is None:
                steps = pick_random_show(shows_dir)
                logger.info("show triggered: %d steps", len(steps))
                scheduler = Scheduler(steps)
            else:
                logger.info("halt triggered mid-show")
                scheduler = Scheduler(make_halt_steps(ROCKET_ADDRS, HALT_JITTER_MAX_MS))

        if scheduler is not None:
            scheduler.tick(link)
            if scheduler.is_done():
                scheduler = None

        time.sleep(TICK_S)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fake-button", action="store_true",
                         help="use spacebar instead of the real arcade button (no hardware yet)")
    parser.add_argument("--port", default=SERIAL_PORT,
                         help="serial device, e.g. a tools/fake_rockets.py pty for bench testing")
    args = parser.parse_args()

    conn = serial.Serial(args.port, BAUD)
    link = RocketLink(conn)

    if args.fake_button:
        button = FakeButton()
        logger.info("fake button active: press SPACE to trigger")
    else:
        from gpiozero import Button
        button = Button(BUTTON_PIN, bounce_time=0.05)

    run(link, button, SHOWS_DIR)


if __name__ == "__main__":
    main()
