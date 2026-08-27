# Woodtronics — Pi (conductor)

You are running **on the Raspberry Pi that conducts the installation**. This is
the only machine that can talk to real hardware. That is the point of working
here, and it is also the risk: code you run here drives physical LEDs, real
rockets, and eventually a public museum exhibit.

## What this project is

Kinetic light installation for the Pensacola Museum of Art. 4–5 wooden
"rockets," each with two 8x8 WS2812B matrices and an ignition ring. A viewer
presses a big red button, a countdown runs, and the rockets launch in a
staggered sweep that makes them look like they are signaling each other.

**The signaling is theater.** There is no real optical comms between rockets.
The Pi choreographs the illusion by timing when it sends each rocket its show
command. This is a locked decision — do not propose adding real inter-unit
comms.

Deadline mid-August. On display August through November.

## Role of this machine

This Pi is the **bus master**. It:
- reads the big red button (USB HID arcade encoder, read via evdev)
- keeps the real countdown clock
- picks a show and walks its timed steps
- dispatches `SHOW <name>` to each rocket with per-rocket stagger offsets
- broadcasts `HALT` (staggered 0–800ms) on a second button press mid-show

Rockets are addressed slaves. Once told which named show to run, each rocket
sequences its own animation autonomously. **The Pi does not stream frames.**

## Architecture

```
conductor/   Pi side — Python, pyserial, evdev       <-- primary work here
rocket/      RP2040 side — MicroPython              <-- do not run here
protocol/    PROTOCOL.md — single source of truth
tools/       fake_rockets.py — virtual serial harness
```

**protocol/PROTOCOL.md is authoritative.** Newline-terminated ASCII frames,
8-bit XOR checksum, commands `PING` and `SHOW <name>`. Both halves of the
system are built against it and the byte-level implementations are
cross-verified. Never change the protocol unilaterally — it breaks the rocket
firmware, which is developed on a different machine.

Rockets only transmit when polled with their own ID. Never unsolicited.
Broadcasts get no reply. This is what makes one shared RX line collision-proof.

## Button integration (done)

The real arcade button replaced the spacebar/keyboard-event trigger.

- The button is **not** on GPIO — it is a USB arcade encoder (`LinTx`,
  `8088:0015`) that enumerates as a **USB HID keyboard** and emits a single
  `KEY_ENTER` (evdev code 28) key-down per press. gpiozero cannot read it;
  it reads GPIO pins only.
- Read via **python-evdev** (apt: `python3-evdev`). See
  `conductor/usb_button.py`: `UsbButton` matches the old gpiozero/FakeButton
  `.when_pressed` interface, so `main.py`'s loop is unchanged.
- The device is matched by **USB vendor/product + KEY_ENTER capability**
  (named constants at the top of `usb_button.py`), not by a `/dev/input/eventN`
  number, which can reshuffle across reboots. Retune those constants if the
  encoder is swapped.
- Fires on **key-down only** — holding the button emits key-repeat, which we
  ignore, so one press is one trigger.
- The device is **grabbed (EVIOCGRAB) by default** so its Enter keypresses do
  not leak into the console/TTY. `--no-grab` disables this for bench use.
- **First press** starts a show. **Second press mid-show** triggers the
  staggered HALT.
- The keyboard trigger is still available via `--fake-button` (spacebar over
  stdin) for testing without the panel and for demos.

## Hardware safety rules

These are not suggestions. Violating them costs parts or a working exhibit.

1. **Never assume which serial device is real.** Before opening a port,
   confirm whether you are on `tools/fake_rockets.py` (virtual) or a physical
   UART. Default to the fake harness unless explicitly told otherwise.
2. **Do not fire shows unprompted.** Running the conductor lights real LEDs.
   Ask before executing anything that drives hardware.
3. **Brightness stays capped 40–60%.** The LEDs sit behind wood and diffuser
   panels. Full brightness is wasted current and heat, and the current budget
   assumes the cap.
4. **Do not modify `rocket/`** from this machine unless explicitly asked.
   MicroPython cannot run here; you cannot test any change you make.
5. **Physical wiring questions go to the human.** Do not infer pinouts.

## Working style

- **Plan before implementing.** Explain the approach, then write the diff.
  Clark is learning this stack deliberately, not just shipping it.
- **Small diffs.** One concern at a time.
- **Prove the smallest thing, add one variable, prove again.** Never introduce
  two unknowns at once — this is how hardware bugs become unfindable.
- **Test against `tools/fake_rockets.py` first**, then real hardware. The
  harness simulates healthy, silent, and corrupt rockets.
- All timing and color values are **named constants at the top of the file**.
  Everything will be retuned on-site under gallery lighting; that must be
  editing a handful of numbers, not hunting through animation math.

## Known state

Built and verified:
- Conductor tested end-to-end against the fake-rocket harness
- Real USB arcade button integrated and verified firing `when_pressed`
  (see `conductor/usb_button.py`); requires the `python3-evdev` apt package
- One rocket confirmed lighting on a breadboard (RP2040 + SN74AHCT125 +
  one 8x8 matrix), ~226mA when lit, ~30mA logic-only baseline

Not done:
- Real show content — only placeholder choreographies exist. A full frame-level
  spec (LAUNCH, FAIL, FALTER, SIGNAL CHAIN, FULL BURN) is written but not
  implemented.
- **Serpentine matrix mapping unconfirmed on hardware.** Highest-risk
  placeholder: it fails *plausibly* (pretty but scrambled) rather than
  obviously. Must be validated with a sequential pixel walk before any
  choreography is trusted.
- UART pin constants still placeholders (button no longer uses GPIO — it is
  USB HID)
- Only one rocket exists; four more to build
- Everything still on breadboard — nothing on a breadboard survives a
  four-month unattended display

## Deployment note

This Pi is heading toward a public exhibit that must run unattended for four
months. Prefer boring and robust over clever. The show must survive power
cycles, recover to idle on restart, and never require network access to run —
network is for maintenance access only.
