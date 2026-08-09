# Woodtronics — Rocket Cohort Installation

Kinetic light installation for the Pensacola Museum of Art.
4–5 wooden rockets that "signal" each other and launch on a button press.
Displays August–November. Build deadline: mid-August. Time is the binding constraint.

## Hardware

- **Conductor**: Raspberry Pi. Python 3 + pyserial. Owns the clock and all choreography.
- **Rockets**: one RP2040 per rocket, MicroPython. 4–5 units.
- **Per rocket**: 2x 8x8 WS2812B matrices (both run the same animation) + 1 WS2812B
  ignition ring behind diffuser paper.
- **Bus**: single shared UART, master-polled. Pi speaks, rockets answer when addressed.
  Never let two slaves talk unprompted.
- **Trigger**: one big red arcade button on the Pi.
- **Countdown panel**: biodegradable substrate circuit, built separately by others.
  Treat as reserved lines / TBD. It slaves to the Pi's clock. Do not design around it.

## Design decisions already made — do not relitigate

- Inter-rocket "communication" is **theater only**. Choreographed by the Pi.
  There is no real optical comms. Do not propose adding any.
- Both matrices on a rocket always display the same thing.
- MicroPython on the rockets, not C/C++.
- No camera, no person detection. The button is the trigger.

## Layout

- `conductor/` — Pi-side Python
- `rocket/`    — RP2040 MicroPython
- `protocol/`  — the ASCII protocol spec. Single source of truth for both sides.
- `tools/`     — bench harnesses, notably a fake-rocket serial responder

## Critical constraint: you cannot run the firmware

MicroPython on RP2040 is not executable in this environment. So:

- Anything in `rocket/` is written blind. Keep it simple and readable.
  Prefer obvious code over clever code — I have to debug it on hardware with a REPL.
- Anything in `conductor/` MUST be testable on the laptop against the fake-rocket
  harness in `tools/`. Build the harness before building features that need it.
- Any change to the wire protocol updates `protocol/` first, then both sides.
  Protocol drift between conductor and rocket is the failure mode I care most about.

## How I want you to work

- Plan mode by default for anything beyond a one-file edit. I read plans.
- Explain the approach before writing it. I am learning these systems, not just
  shipping them. If I approve something I do not understand, that is a failure.
- Small diffs. If a change touches more than ~3 files, stop and check with me.
- Push back on over-engineering. I would rather ship something simple that works
  in a gallery for four months than something elegant that fails on opening night.
- Be concise. Skip the preamble.

## Conventions

- Python: standard library first. pyserial is the only assumed dependency on the Pi.
- No blocking sleeps in the conductor's main loop — the button must stay responsive.
- Every serial read has a timeout. Every one.
