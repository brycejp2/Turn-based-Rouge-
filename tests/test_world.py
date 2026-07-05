"""Tests for calendar/lighting, FOV, generation and permadeath saves
(§3.3, §4.1, §4.2, §4.3)."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adom.core.engine.rng import Rng
from adom.core.world.fov import compute_fov
from adom.core.world.level import Level
from adom.core.world import tile
from adom.core.generation.dungeon import generate_level
from adom.core.rules.calendar import Calendar, sight_radius, TICKS_PER_HOUR
from adom.persistence.save import SaveService


class CalendarTests(unittest.TestCase):
    def test_starts_in_daytime_unicorn(self):
        cal = Calendar()
        self.assertTrue(cal.is_day)
        self.assertEqual(cal.month_name(), "Unicorn")   # §4.2
        self.assertEqual(cal.day_of_month, 1)

    def test_night_reduces_sight(self):
        day = Calendar(ticks=12 * TICKS_PER_HOUR)     # noon
        night = Calendar(ticks=1 * TICKS_PER_HOUR)    # 01:00
        self.assertGreater(sight_radius(day, 10), sight_radius(night, 10))

    def test_perception_widens_sight(self):
        cal = Calendar(ticks=12 * TICKS_PER_HOUR)
        self.assertGreaterEqual(sight_radius(cal, 30), sight_radius(cal, 10))


class FovTests(unittest.TestCase):
    def _open_level(self, w=15, h=15):
        lvl = Level(w, h)
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                lvl.set_tile(x, y, tile.FLOOR)
        return lvl

    def test_origin_visible(self):
        lvl = self._open_level()
        vis = compute_fov(lvl, 7, 7, 5)
        self.assertIn((7, 7), vis)

    def test_symmetry_in_open_field(self):
        lvl = self._open_level()
        vis = compute_fov(lvl, 7, 7, 4)
        # An open field of radius 4 should be broadly symmetric.
        self.assertIn((7, 3), vis)
        self.assertIn((3, 7), vis)
        self.assertIn((11, 7), vis)

    def test_wall_blocks_sight(self):
        lvl = self._open_level()
        for y in range(15):
            lvl.set_tile(7, y, tile.WALL)   # solid vertical wall at column 7
        vis = compute_fov(lvl, 6, 7, 8)     # origin stands just west of it
        # The wall itself is visible; anything directly behind it is not.
        self.assertIn((7, 7), vis)
        self.assertNotIn((10, 7), vis)


class GenerationTests(unittest.TestCase):
    def test_deterministic_by_seed(self):
        a = generate_level(Rng(999), depth=2)
        b = generate_level(Rng(999), depth=2)
        grid_a = [a.tile(x, y).key for y in range(a.height) for x in range(a.width)]
        grid_b = [b.tile(x, y).key for y in range(b.height) for x in range(b.width)]
        self.assertEqual(grid_a, grid_b)

    def test_has_stairs(self):
        lvl = generate_level(Rng(3), depth=1)
        self.assertIsNotNone(lvl.stairs_up)
        self.assertIsNotNone(lvl.stairs_down)
        self.assertIs(lvl.tile(*lvl.stairs_down), tile.STAIRS_DOWN)

    def test_stairs_reachable(self):
        """Down-stairs must be reachable from up-stairs (flood fill)."""
        lvl = generate_level(Rng(5), depth=1)
        from collections import deque
        start = lvl.stairs_up
        seen = {start}
        q = deque([start])
        while q:
            cx, cy = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in seen and lvl.is_walkable(nx, ny):
                    seen.add((nx, ny))
                    q.append((nx, ny))
        self.assertIn(lvl.stairs_down, seen)

    def test_spawns_monsters(self):
        lvl = generate_level(Rng(8), depth=3)
        self.assertTrue(len(list(lvl.monsters())) > 0)


class SavePermadeathTests(unittest.TestCase):
    def test_load_consumes_save(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["ADOM_SAVE_DIR"] = d
            # Rebuild the module constant to honour the env override.
            import importlib
            from adom.persistence import save as save_mod
            importlib.reload(save_mod)
            svc = save_mod.SaveService(permadeath=True)
            svc.save("hero", {"hp": 10})
            self.assertTrue(svc.exists("hero"))
            state = svc.load("hero")
            self.assertEqual(state["hp"], 10)
            # Permadeath: the save is gone after loading.
            self.assertFalse(svc.exists("hero"))

    def test_disabled_permadeath_keeps_save(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ["ADOM_SAVE_DIR"] = d
            import importlib
            from adom.persistence import save as save_mod
            importlib.reload(save_mod)
            svc = save_mod.SaveService(permadeath=False)
            svc.save("hero", {"hp": 5})
            svc.load("hero")
            self.assertTrue(svc.exists("hero"))   # kept when permadeath off


if __name__ == "__main__":
    unittest.main()
