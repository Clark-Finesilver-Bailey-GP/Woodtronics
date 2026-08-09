"""Timed SHOW-step sequences: loading show files and running them.

A "show" is just a list of (t_ms, rocket, show) steps. A HALT sequence is
the exact same structure, generated at trigger time instead of loaded from
a file — see make_halt_steps.
"""
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path

from link import RocketLink


@dataclass
class Step:
    t_ms: int
    rocket: str
    show: str


def load_show(path: Path) -> list[Step]:
    data = json.loads(path.read_text())
    steps = [Step(**entry) for entry in data]
    steps.sort(key=lambda s: s.t_ms)
    return steps


def pick_random_show(shows_dir: Path) -> list[Step]:
    paths = sorted(shows_dir.glob("*.json"))
    return load_show(random.choice(paths))


def make_halt_steps(rocket_addrs: list[str], jitter_max_ms: int) -> list[Step]:
    steps = [
        Step(t_ms=random.randint(0, jitter_max_ms), rocket=addr, show="HALT")
        for addr in rocket_addrs
    ]
    steps.sort(key=lambda s: s.t_ms)
    return steps


class Scheduler:
    def __init__(self, steps: list[Step]):
        self.steps = steps
        self._start = time.monotonic()
        self._next_index = 0

    def tick(self, link: RocketLink) -> None:
        now_ms = (time.monotonic() - self._start) * 1000
        while self._next_index < len(self.steps) and self.steps[self._next_index].t_ms <= now_ms:
            step = self.steps[self._next_index]
            link.send(step.rocket, "SHOW", step.show)
            self._next_index += 1

    def is_done(self) -> bool:
        return self._next_index >= len(self.steps)
