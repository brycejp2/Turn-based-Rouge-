"""Energy / speed scheduler (design plan §3.1).

This engine is **not** round-based.  Every actor has a ``speed`` stat (base
normal speed = 100).  Actions cost **energy points** (a standard
move/attack costs 1000 EP).  Conceptually, each tick every actor gains
``speed`` EP and acts once it can afford its chosen action; the net
effect is that a speed-200 actor acts twice as often as a speed-100 one.

Rather than looping tick-by-tick (which wastes work when everyone is
waiting), we schedule each actor on a **min-heap keyed by the game time
of its next action**.  ``next_time = now + cost / speed`` reproduces the
EP model exactly while letting us jump straight to the next actor.  This
is the "priority queue of actors keyed by time of next action" the plan
recommends.
"""

from __future__ import annotations

import heapq
import itertools
from typing import Protocol

# Standard action cost in energy points (§3.1).
STANDARD_ACTION_COST = 1000
NORMAL_SPEED = 100


class Schedulable(Protocol):
    """Anything the scheduler can drive."""

    @property
    def speed(self) -> int: ...

    @property
    def is_alive(self) -> bool: ...


class Scheduler:
    """Min-heap of ``(next_time, tiebreak, actor)`` entries."""

    def __init__(self, start_time: float = 0.0):
        self._time = start_time
        self._heap: list = []
        self._counter = itertools.count()
        # Entries can be lazily invalidated (e.g. a dead monster).
        self._removed: set[int] = set()
        self._ids: dict[int, int] = {}

    @property
    def time(self) -> float:
        """Current game time in ticks (1 tick == 1 EP at speed 100... /100)."""
        return self._time

    def add(self, actor: Schedulable, delay_cost: int = 0) -> None:
        """Insert ``actor`` to act after paying ``delay_cost`` EP once."""
        speed = max(1, actor.speed)
        when = self._time + delay_cost / speed
        self._push(actor, when)

    def _push(self, actor: Schedulable, when: float) -> None:
        token = next(self._counter)
        self._ids[id(actor)] = token
        heapq.heappush(self._heap, (when, token, actor))

    def remove(self, actor: Schedulable) -> None:
        """Lazily drop an actor (dead / left the level)."""
        token = self._ids.pop(id(actor), None)
        if token is not None:
            self._removed.add(token)

    def reschedule(self, actor: Schedulable, cost: int = STANDARD_ACTION_COST) -> None:
        """Charge ``cost`` EP to ``actor`` and requeue it.

        ``next_time = now + cost / speed`` — higher speed → sooner turn.
        """
        speed = max(1, actor.speed)
        self._push(actor, self._time + cost / speed)

    def pop(self) -> "Schedulable | None":
        """Advance time to, and return, the next actor to act."""
        while self._heap:
            when, token, actor = heapq.heappop(self._heap)
            if token in self._removed:
                self._removed.discard(token)
                continue
            # Skip stale entries for an actor that was rescheduled/removed.
            if self._ids.get(id(actor)) != token:
                continue
            if not actor.is_alive:
                continue
            self._time = when
            return actor
        return None

    def __len__(self) -> int:
        return sum(
            1
            for _when, token, _actor in self._heap
            if token not in self._removed
        )
