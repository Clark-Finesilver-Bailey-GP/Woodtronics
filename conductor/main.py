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
SHOWS_DIR = Path(__file__).parent.parent / "shows"
HALT_JITTER_MAX_MS = 800
TICK_S = 0.02

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class ButtonState:
    pressed = False


def run(link: RocketLink, button: object, shows_dir: Path, roster: list[str]) -> None:
    state = ButtonState()
    button.when_pressed = lambda: setattr(state, "pressed", True)

    scheduler = None
    while True:
        if state.pressed:
            state.pressed = False
            if scheduler is None:
                # Only address rockets that exist. Steps for absent rockets
                # would each cost a blocking read timeout + retry, dragging the
                # staggered timing the whole show depends on.
                steps = [s for s in pick_random_show(shows_dir) if s.rocket in roster]
                logger.info("show triggered: %d steps for %s", len(steps), ",".join(roster))
                scheduler = Scheduler(steps)
            else:
                logger.info("halt triggered mid-show")
                scheduler = Scheduler(make_halt_steps(roster, HALT_JITTER_MAX_MS))

        if scheduler is not None:
            scheduler.tick(link)
            if scheduler.is_done():
                scheduler = None

        time.sleep(TICK_S)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fake-button", action="store_true",
                         help="use spacebar (stdin) instead of the real USB arcade button")
    parser.add_argument("--no-grab", action="store_true",
                         help="do not EVIOCGRAB the button; its Enter presses also reach "
                              "the console. Handy for bench testing, not for the exhibit.")
    parser.add_argument("--port", default=SERIAL_PORT,
                         help="serial device, e.g. a tools/fake_rockets.py pty for bench testing")
    parser.add_argument("--rockets", default=",".join(ROCKET_ADDRS),
                         help="comma-separated rockets actually on the bus, e.g. R3,R4. "
                              "Absent rockets are skipped so their timeouts don't skew timing.")
    args = parser.parse_args()

    roster = [r.strip() for r in args.rockets.split(",") if r.strip()]

    conn = serial.Serial(args.port, BAUD)
    link = RocketLink(conn)

    if args.fake_button:
        button = FakeButton()
        logger.info("fake button active: press SPACE to trigger")
    else:
        from usb_button import UsbButton
        button = UsbButton(grab=not args.no_grab)
        logger.info("USB arcade button active%s", "" if not args.no_grab else " (not grabbed)")

    run(link, button, SHOWS_DIR, roster)


if __name__ == "__main__":
    main()
