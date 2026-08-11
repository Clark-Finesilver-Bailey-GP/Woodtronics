# Woodtronics wire protocol

Single source of truth for the conductor (Pi) and every rocket (RP2040).
If you change anything here, update both `conductor/` and `rocket/` to match.
Protocol drift between the two sides is the failure mode we care about most.

## Bus

- Single shared UART, 115200 baud, 8N1.
- The Pi is bus master. A rocket only transmits in reply to a line addressed
  to it. Two slaves never talk unprompted.
- Max line length: 64 bytes (bounds the read buffer on both sides).

## Frame format

Every line, in both directions, has the same shape:

```
<ADDR> <WORD> [ARGS...] *<CK>\n
```

- `ADDR` — `R1`..`R5` when the Pi is addressing a rocket, `PI` when a rocket
  is replying. Same shape both directions, so both sides parse with the same
  "split on spaces, check the checksum" logic.
- `WORD` — the command or reply name (see tables below).
- `ARGS` — zero or more space-separated arguments, command-dependent.
- `*<CK>` — a literal `*` followed by a 2-hex-digit checksum, uppercase.
- `\n` — line terminator.

## Checksum

8-bit XOR of every byte in the line **up to but not including** the space
before `*`. Format the result as 2 uppercase hex digits. This needs no
imports, so it's cheap on the MicroPython side.

**Worked example** — command `R1 ANIM 3`:

```
bytes:  R    1    ' '  A    N    I    M    ' '  3
hex:    52   31   20   41   4E   49   20   33
```
XOR-ing all of those together gives `0x5B`, so the full frame is:

```
R1 ANIM 3 *5B\n
```

A receiver recomputes the checksum over the bytes it read before `*` and
compares; mismatch → reply `ERR CK`.

## Commands, Pi → rocket

| Word   | Args     | Meaning                                                                 |
|--------|----------|--------------------------------------------------------------------------|
| `PING` | —        | Liveness / troubleshooting check.                                        |
| `SHOW` | `<name>` | Run the named show-state. Both matrices and the ignition ring update together as that state defines, entirely rocket-side. |

## Replies, rocket → Pi

| Word  | Args             | Meaning                                                         |
|-------|------------------|-------------------------------------------------------------------|
| `ACK` | `<echoed word>`  | Command received and applied, e.g. `PI ACK SHOW *xx`.             |
| `ERR` | `<code>`         | Command received but rejected. Codes: `CK` (bad checksum), `ARG` (bad/missing argument), `UNK` (unknown word). |

## Show catalog

`SHOW` names are a shared vocabulary between `conductor/`'s choreography
data and `rocket/`'s firmware — a name referenced by a choreography file
that isn't implemented on the rocket is exactly the protocol-drift failure
mode this document exists to prevent. New names get added here before use.

Two names are protocol-reserved because the conductor's control logic
depends on every rocket implementing them:

| Name   | Meaning                                                              |
|--------|------------------------------------------------------------------------|
| `OFF`  | Immediate blank — both matrices and the ring dark, no animation.       |
| `HALT` | Graceful faltering shutdown — wobbling brightness, dying ignition glow, ends dark. |

No other show names are defined yet; those arrive with the choreography
files that use them.

| Name       | Meaning                                                          |
|------------|---------------------------------------------------------------------|
| `IDLE`     | Quiescent bookend state — used at the start/end of every show.      |
| `LAUNCH`   | Full WAKE→CHARGE→IGNITION→CLIMB→RELAY→SETTLE sequence, ~14s. Entirely rocket-side, timed off elapsed ms since the `SHOW LAUNCH` command. `shows/launch_a.json` and `shows/launch_b.json` are two example stagger orders across the array, both using this same show. |

## Timeout / retry (conductor side)

- 200ms read timeout waiting for a reply to any sent command.
- On timeout or a checksum mismatch on the reply: retry once.
- If still no valid `ACK`: log that rocket as unresponsive for this cycle
  and continue the show. The conductor does not change choreography based
  on rocket health — this is logging only, not adaptive behavior.

## Reserved / out of scope

The countdown panel is a separate biodegradable-substrate circuit built by
others; it slaves to the Pi's clock but has no address or command defined
here. Do not design bus traffic for it — if it ever needs to join the bus,
that's a future revision of this document, not something to anticipate now.
