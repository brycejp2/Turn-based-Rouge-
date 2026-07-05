"""Ancardian calendar and time-of-day lighting (design plan §4.1, §4.2).

360-day year, 12 months of 30 days, each named for a star sign; the game
begins on day 1 of the month of the Unicorn.  Time advances with the
energy scheduler.  Sight radius depends on time of day: full by day
(~06:00–20:00), reduced at night, further modified by Perception.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...content.starsigns import MONTH_NAMES

# One "day" of game-time in scheduler ticks.  A standard action at speed
# 100 costs 1000 EP == 10 ticks here, so a day is ~1000 actions.
TICKS_PER_HOUR = 500
TICKS_PER_DAY = TICKS_PER_HOUR * 24

DAY_START_HOUR = 6
NIGHT_START_HOUR = 20


@dataclass
class Calendar:
    # The game begins on day 1 of the Unicorn at a daytime hour (§4.2), so
    # start the clock mid-morning rather than at midnight.
    ticks: float = float(8 * TICKS_PER_HOUR)
    start_month: int = 4  # Unicorn (§4.2)

    def advance_to(self, tick_time: float) -> None:
        self.ticks = tick_time

    @property
    def hour(self) -> int:
        return int((self.ticks % TICKS_PER_DAY) // TICKS_PER_HOUR)

    @property
    def day_of_year(self) -> int:
        return int(self.ticks // TICKS_PER_DAY)

    @property
    def month(self) -> int:
        return ((self.start_month - 1 + (self.day_of_year // 30)) % 12) + 1

    @property
    def day_of_month(self) -> int:
        return (self.day_of_year % 30) + 1

    @property
    def is_day(self) -> bool:
        return DAY_START_HOUR <= self.hour < NIGHT_START_HOUR

    def month_name(self) -> str:
        return MONTH_NAMES[self.month - 1]

    def describe(self) -> str:
        phase = "day" if self.is_day else "night"
        return (f"{self.day_of_month} {self.month_name()}, "
                f"{self.hour:02d}:00 ({phase})")


def sight_radius(calendar: Calendar, perception: int, in_wilderness: bool = False) -> int:
    """FOV radius from time of day + Perception (§4.1)."""
    if calendar.is_day:
        base = 8 if not in_wilderness else 11
    else:
        base = 5 if in_wilderness else 2
    # Perception widens vision (10 is the vision breakpoint, §5.1).
    base += max(0, (perception - 10) // 4)
    return max(1, base)
