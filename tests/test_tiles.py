"""Headless tests for the 2D tile client.

Runs with SDL's dummy video/audio drivers so no display is needed: draws
onto off-screen surfaces and checks that something was actually rendered,
and that the keyboard-to-command mapping is correct.  Skips cleanly if
pygame isn't installed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame
    from hollowreach.ui import pygame_app as P
    from hollowreach.ui.tiles import TileAtlas
    import hollowreach.ui.tiles as tiles
    HAVE_PYGAME = True
except Exception:  # pragma: no cover
    HAVE_PYGAME = False

from hollowreach.bootstrap import new_game


class _FakeEvent:
    def __init__(self, key, unicode="", mod=0):
        self.key = key
        self.unicode = unicode
        self.mod = mod


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.font.init()
        cls.fonts = P._fonts()
        cls.atlas = TileAtlas(P.TILE)

    def _blank(self):
        s = pygame.Surface((P.WIN_W, P.WIN_H))
        s.fill(tiles.BG)
        return s

    def _non_bg_pixels(self, surf) -> int:
        # Cheap "did we draw anything" check on a sampled grid.
        count = 0
        for y in range(0, surf.get_height(), 12):
            for x in range(0, surf.get_width(), 12):
                if surf.get_at((x, y))[:3] != tiles.BG:
                    count += 1
        return count

    def test_title_renders(self):
        surf = self._blank()
        P.draw_title(surf, self.fonts)
        self.assertGreater(self._non_bg_pixels(surf), 20)

    def test_play_frame_renders(self):
        game = new_game(7, "Kael", "dwarf", "fighter", "beacon", "male",
                        permadeath=False)
        game._update_fov()
        surf = self._blank()
        P.draw_play(surf, self.fonts, self.atlas, game)
        self.assertGreater(self._non_bg_pixels(surf), 50)

    def test_atlas_tile_sizes(self):
        from hollowreach.core.world import tile as tmod
        for t in (tmod.WALL, tmod.FLOOR, tmod.GATE):
            surf = self.atlas.terrain(t)
            self.assertEqual(surf.get_size(), (P.TILE, P.TILE))
        self.assertEqual(self.atlas.hero().get_size(), (P.TILE, P.TILE))

    def test_overlays_render(self):
        game = new_game(1, "Kael", "dwarf", "fighter", "beacon", "male",
                        permadeath=False)
        game._update_fov()
        surf = self._blank()
        P.draw_play(surf, self.fonts, self.atlas, game)
        P.draw_inventory(surf, self.fonts, game)   # should not raise
        P.draw_character(surf, self.fonts, game)
        game.won = True
        P.draw_gameover(surf, self.fonts, game)


@unittest.skipUnless(HAVE_PYGAME, "pygame not installed")
class InputMappingTests(unittest.TestCase):
    def test_movement_keys(self):
        self.assertEqual(P._translate(_FakeEvent(pygame.K_h))[1], "h")
        self.assertEqual(P._translate(_FakeEvent(pygame.K_LEFT))[1], "h")
        self.assertEqual(P._translate(_FakeEvent(pygame.K_n))[1], "n")
        self.assertEqual(P._translate(_FakeEvent(pygame.K_PERIOD, "."))[1], ".")

    def test_stairs_and_actions(self):
        self.assertEqual(P._translate(_FakeEvent(pygame.K_PERIOD, ">")), ("cmd", ">"))
        self.assertEqual(P._translate(_FakeEvent(pygame.K_g)), ("select", "get"))
        self.assertEqual(P._translate(_FakeEvent(pygame.K_i)), ("overlay", "inventory"))
        self.assertEqual(P._translate(_FakeEvent(pygame.K_w)), ("select", "wield"))
        self.assertEqual(P._translate(_FakeEvent(pygame.K_q)), ("select", "quaff"))

    def test_quit_is_shift_q(self):
        self.assertEqual(
            P._translate(_FakeEvent(pygame.K_q, "Q", pygame.KMOD_SHIFT)),
            ("quit", None))

    def test_select_entries_lists_potions(self):
        game = new_game(1, "Kael", "dwarf", "fighter", "beacon", "male",
                        permadeath=False)
        entries, items = P._select_entries(game, "quaff")
        # The starter kit includes healing potions.
        self.assertTrue(len(entries) >= 1)
        self.assertEqual(len(entries), len(items))


if __name__ == "__main__":
    unittest.main()
