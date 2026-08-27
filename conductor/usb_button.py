"""Real viewer trigger: a USB arcade button that enumerates as a HID keyboard.

The panel button is a LinTx USB encoder. The OS sees it as a USB *keyboard*
(not a GPIO pin, so gpiozero cannot read it), and each press emits a single
KEY_ENTER key-down on its evdev node. This module reads that node and exposes
the same `.when_pressed` callback interface as conductor/fake_button.py, so
conductor/main.py does not care which input source it was handed.

Design notes tied to the actual hardware (verified by capture):
- Match the device by USB vendor/product AND the presence of KEY_ENTER. The
  encoder exposes two interfaces (keyboard + mouse); only the keyboard one
  carries the button. This is more robust than a fixed /dev/input/eventN
  number, which can reshuffle across reboots.
- Fire on key-DOWN only. Holding the button emits key-repeat events; we ignore
  repeat and key-up so one press is one trigger.
- Grab the device (EVIOCGRAB) by default. Because it is a real keyboard sending
  Enter, an ungrabbed press also types Enter into the console/foreground app.
  On the unattended exhibit we do not want presses leaking into the TTY.
"""
import logging
import threading
import time

from evdev import InputDevice, categorize, ecodes, list_devices

logger = logging.getLogger(__name__)

# --- Hardware identity of the panel button. Retune here if the encoder is
# --- swapped for a different USB model (see `lsusb` / the capture tooling).
BUTTON_VENDOR_ID = 0x8088
BUTTON_PRODUCT_ID = 0x0015
BUTTON_KEYCODE = ecodes.KEY_ENTER  # evdev code 28; what this encoder emits
RECONNECT_POLL_S = 1.0  # how often to look for the button after it disappears


def find_button_device() -> InputDevice:
    """Return the InputDevice for the arcade button, or raise if not found.

    Selects by USB vendor/product and requires the node to actually carry
    BUTTON_KEYCODE, which disambiguates the encoder's keyboard interface from
    its (irrelevant) mouse interface.
    """
    for path in list_devices():
        dev = InputDevice(path)
        keys = dev.capabilities().get(ecodes.EV_KEY) or []
        if (dev.info.vendor == BUTTON_VENDOR_ID
                and dev.info.product == BUTTON_PRODUCT_ID
                and BUTTON_KEYCODE in keys):
            return dev
        dev.close()
    raise RuntimeError(
        f"USB arcade button not found "
        f"(looked for {BUTTON_VENDOR_ID:04x}:{BUTTON_PRODUCT_ID:04x} with "
        f"keycode {BUTTON_KEYCODE}). Is it plugged in? Try `lsusb`."
    )


class UsbButton:
    """gpiozero.Button-shaped adapter over the USB HID arcade button.

    Assign a no-arg callable to `.when_pressed`; it fires once per press from a
    background daemon thread, exactly like conductor/fake_button.py.
    """

    def __init__(self, grab: bool = True):
        self.when_pressed = None
        self._grab = grab
        # Strict at startup: raise if the button is absent, so a boot before
        # the USB device enumerates just fails and lets systemd restart us.
        # Mid-run unplug is handled by _reconnect, not by crashing.
        self._dev = self._open()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _open(self) -> InputDevice:
        dev = find_button_device()
        if self._grab:
            # Stops button presses from also reaching the console as Enter.
            dev.grab()
        return dev

    def _listen(self) -> None:
        while True:
            try:
                for event in self._dev.read_loop():
                    if event.type != ecodes.EV_KEY:
                        continue
                    key = categorize(event)
                    # key_down == 1; ignore key_hold (repeat) and key_up.
                    if (key.scancode == BUTTON_KEYCODE
                            and key.keystate == key.key_down
                            and self.when_pressed):
                        self.when_pressed()
            except OSError as e:
                # Button was unplugged or the USB link glitched. Drop the dead
                # handle and wait for it to re-enumerate, then resume as if
                # nothing happened — any running show is unaffected.
                logger.warning("button device lost (%s); waiting for replug", e)
                self._reconnect()

    def _reconnect(self) -> None:
        try:
            self._dev.close()
        except OSError:
            pass
        while True:
            time.sleep(RECONNECT_POLL_S)
            try:
                self._dev = self._open()
            except (RuntimeError, OSError):
                continue  # not back yet (or lost a grab race) — keep polling
            logger.info("button reconnected")
            return
