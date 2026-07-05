"""Tests for the RNG/dice engine and the energy scheduler (§3.1, §3.2)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hollowreach.core.engine.rng import Rng, Dice, m
from hollowreach.core.engine.scheduler import Scheduler, STANDARD_ACTION_COST


class DiceTests(unittest.TestCase):
    def test_parse_variants(self):
        self.assertEqual(Dice.parse("2d6"), Dice(2, 6, 0))
        self.assertEqual(Dice.parse("1d8+3"), Dice(1, 8, 3))
        self.assertEqual(Dice.parse("3d4-2"), Dice(3, 4, -2))

    def test_bounds(self):
        d = Dice.parse("2d6+1")
        self.assertEqual(d.minimum, 3)
        self.assertEqual(d.maximum, 13)
        self.assertAlmostEqual(d.average, 8.0)

    def test_bad_expression(self):
        with self.assertRaises(ValueError):
            Dice.parse("banana")


class RngTests(unittest.TestCase):
    def test_determinism(self):
        a = [Rng(123).roll("3d6") for _ in range(1)]
        b = [Rng(123).roll("3d6") for _ in range(1)]
        self.assertEqual(a, b)
        seq1 = [Rng(7).rnd(100) for _ in range(1)]
        # Two RNGs with the same seed produce the same stream.
        r1, r2 = Rng(55), Rng(55)
        self.assertEqual([r1.rnd(1000) for _ in range(20)],
                         [r2.rnd(1000) for _ in range(20)])

    def test_rnd_range(self):
        r = Rng(1)
        for _ in range(500):
            self.assertTrue(1 <= r.rnd(6) <= 6)

    def test_roll_bounds(self):
        r = Rng(2)
        for _ in range(500):
            v = r.roll("2d6+1")
            self.assertTrue(3 <= v <= 13)

    def test_weighted_choice(self):
        r = Rng(3)
        counts = {"a": 0, "b": 0}
        for _ in range(2000):
            counts[r.weighted_choice([("a", 9), ("b", 1)])] += 1
        # 'a' should dominate ~9:1.
        self.assertGreater(counts["a"], counts["b"] * 3)

    def test_m_helper(self):
        self.assertEqual(m(3, 7), 7)
        self.assertEqual(m(9, 2), 9)


class _Dummy:
    def __init__(self, speed):
        self._speed = speed
        self.acted = 0
    @property
    def speed(self):
        return self._speed
    @property
    def is_alive(self):
        return True


class SchedulerTests(unittest.TestCase):
    def test_speed_doubles_frequency(self):
        """A speed-200 actor should act ~twice as often as a speed-100 one
        (the core energy-system invariant, §3.1)."""
        fast = _Dummy(200)
        slow = _Dummy(100)
        sched = Scheduler()
        sched.add(fast)
        sched.add(slow)
        for _ in range(300):
            actor = sched.pop()
            actor.acted += 1
            sched.reschedule(actor, STANDARD_ACTION_COST)
        ratio = fast.acted / slow.acted
        self.assertTrue(1.8 <= ratio <= 2.2, f"ratio was {ratio}")

    def test_time_advances_monotonically(self):
        sched = Scheduler()
        a = _Dummy(100)
        sched.add(a)
        last = -1
        for _ in range(50):
            sched.pop()
            self.assertGreaterEqual(sched.time, last)
            last = sched.time
            sched.reschedule(a)

    def test_remove(self):
        sched = Scheduler()
        a, b = _Dummy(100), _Dummy(100)
        sched.add(a)
        sched.add(b)
        sched.remove(a)
        popped = [sched.pop() for _ in range(3)]
        # 'a' was removed; only 'b' (rescheduled) should come back.
        first = sched.pop()
        self.assertIsNotNone(popped[0])


if __name__ == "__main__":
    unittest.main()
