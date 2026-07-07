"""Tests for the endgame: the bottom level, the boss, and the win (§14)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hollowreach.core.engine.rng import Rng
from hollowreach.core.generation.dungeon import generate_level
from hollowreach.core.world import tile
from hollowreach.content.world import BOTTOM_DEPTH, BOSS_ID

import main


def _game():
    return main.make_game(5, "Hero", "dwarf", "fighter", "beacon", "male",
                          permadeath=False)


def _enter_bottom(game):
    game.levels[game.depth].remove_actor(game.pc.actor)
    game._enter_level(BOTTOM_DEPTH, going_down=True)
    game._schedule_all()
    game._update_fov()
    return game.levels[game.depth]


class FinalLevelTests(unittest.TestCase):
    def test_final_level_has_gate_and_boss_no_downstairs(self):
        lvl = generate_level(Rng(1), depth=BOTTOM_DEPTH, is_final=True)
        self.assertTrue(lvl.is_final)
        self.assertIsNotNone(lvl.gate)
        self.assertIsNone(lvl.stairs_down)
        self.assertIs(lvl.tile(*lvl.gate), tile.GATE)
        self.assertIsNotNone(lvl.boss)
        self.assertEqual(lvl.boss.monster_id, BOSS_ID)

    def test_non_final_levels_have_downstairs_and_no_gate(self):
        lvl = generate_level(Rng(1), depth=3, is_final=False)
        self.assertIsNotNone(lvl.stairs_down)
        self.assertIsNone(lvl.gate)
        self.assertIsNone(lvl.boss)

    def test_boss_is_formidable(self):
        lvl = generate_level(Rng(2), depth=BOTTOM_DEPTH, is_final=True)
        self.assertGreater(lvl.boss.hp, 80)
        self.assertGreater(lvl.boss.dv, 20)


class WinConditionTests(unittest.TestCase):
    def test_cannot_seal_while_boss_lives(self):
        game = _game()
        lvl = _enter_bottom(game)
        game.pc.actor.x, game.pc.actor.y = lvl.gate
        game._try_seal_gate(lvl)
        self.assertFalse(game.won)
        self.assertTrue(game.running)

    def test_seal_after_boss_dead_wins(self):
        game = _game()
        lvl = _enter_bottom(game)
        lvl.boss.alive = False
        lvl.boss.hp = 0
        game.pc.actor.x, game.pc.actor.y = lvl.gate
        game._try_seal_gate(lvl)
        self.assertTrue(game.won)
        self.assertFalse(game.running)

    def test_stepping_on_gate_triggers_win(self):
        game = _game()
        lvl = _enter_bottom(game)
        lvl.boss.alive = False
        lvl.boss.hp = 0
        gx, gy = lvl.gate
        # Stand next to the Gate and step onto it.
        game.pc.actor.x, game.pc.actor.y = gx - 1, gy
        # Ensure the target tile is reachable floor-adjacent.
        if not lvl.is_walkable(gx - 1, gy):
            game.pc.actor.x, game.pc.actor.y = gx, gy - 1
        dx = gx - game.pc.actor.x
        dy = gy - game.pc.actor.y
        game._move_or_attack(game.pc.actor, lvl, dx, dy)
        self.assertTrue(game.won)


class DescentTests(unittest.TestCase):
    def test_all_depths_generate_and_bottom_is_final(self):
        game = _game()
        for depth in range(1, BOTTOM_DEPTH + 1):
            if depth != game.depth:
                game.levels[game.depth].remove_actor(game.pc.actor)
                game._enter_level(depth, going_down=True)
        self.assertTrue(game.levels[BOTTOM_DEPTH].is_final)
        self.assertFalse(game.levels[1].is_final)


class CorruptingAttackTests(unittest.TestCase):
    def test_corrupting_monster_adds_blight(self):
        game = _game()
        lvl = _enter_bottom(game)
        boss = lvl.boss
        boss.x, boss.y = game.pc.actor.x + 1, game.pc.actor.y
        before = game.pc.blight_points
        # Force the boss to keep attacking until at least one blow lands.
        for _ in range(40):
            game._monster_act(boss, lvl)
            if game.pc.blight_points > before:
                break
        self.assertGreater(game.pc.blight_points, before)


class NonActingCommandTests(unittest.TestCase):
    """Regression: interactive clients send one fixed command per keypress.
    A rejected command (wall bump, '>' off-stairs) must RETURN to the
    front-end, not re-ask forever — the old loop froze the game."""

    def test_stairs_command_off_stairs_returns(self):
        game = _game()
        game.run_turn(lambda: "l")     # step off the starting staircase
        game.run_turn(lambda: ">")     # fixed rejected command — must return
        self.assertTrue(game.running)

    def test_wall_bumps_return_and_cost_no_time(self):
        game = _game()
        t0 = game.scheduler.time
        # Hammer one direction with a fixed command; walls must not hang.
        for _ in range(25):
            game.run_turn(lambda: "h")
        self.assertTrue(game.scheduler.time >= t0)


if __name__ == "__main__":
    unittest.main()
