"""Tests for build variety: weapon proficiencies, class powers, skills,
and natural regeneration (design ref §5.3, §6.2, §6.3)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hollowreach.core.engine.rng import Rng
from hollowreach.core.rules.proficiency import (
    tier_for_marks, TIER_THRESHOLDS, mark_gain,
)
from hollowreach.core.rules import regen, skills

import main


def _game(cls="fighter", sign="beacon", race="human"):
    return main.make_game(3, "T", race, cls, sign, "male", permadeath=False)


class ProficiencyTests(unittest.TestCase):
    def test_tier_thresholds(self):
        self.assertEqual(tier_for_marks(0), 0)
        self.assertEqual(tier_for_marks(TIER_THRESHOLDS[1]), 1)
        self.assertEqual(tier_for_marks(TIER_THRESHOLDS[5]), 5)

    def test_class_affects_mark_rate(self):
        fighter = _game("fighter")
        wizard = _game("wizard")
        # Fighter (0.9 rate) earns marks faster than Wizard (1.3).
        self.assertGreater(mark_gain(fighter.pc), mark_gain(wizard.pc))

    def test_marks_raise_tier_and_bonuses(self):
        game = _game("fighter")
        pc, a = game.pc, game.pc.actor
        base_to_hit = a.prof_to_hit
        for _ in range(200):
            pc.proficiencies.award(pc, "sword")
        pc.refresh_combat()
        self.assertGreaterEqual(pc.proficiencies.tier["sword"], 4)
        self.assertGreater(a.prof_to_hit, base_to_hit)

    def test_master_grants_extra_attack(self):
        game = _game("fighter")
        pc, a = game.pc, game.pc.actor
        for _ in range(300):
            pc.proficiencies.award(pc, "sword")
        pc.refresh_combat()
        self.assertGreaterEqual(a.extra_attacks, 1)  # master tier => +1


class ClassPowerTests(unittest.TestCase):
    def test_fighter_tension_at_six(self):
        game = _game("fighter")
        pc, a = game.pc, game.pc.actor
        base = a.class_to_hit
        while a.char_level < 6:
            pc.award_xp(10000)
        self.assertIn("Tension", pc.granted_powers)
        self.assertEqual(a.class_to_hit, base + 3)

    def test_barbarian_speed_power(self):
        game = _game("barbarian")
        pc, a = game.pc, game.pc.actor
        base_speed = a.base_speed
        while a.char_level < 6:
            pc.award_xp(10000)
        self.assertEqual(a.base_speed, base_speed + 10)

    def test_per_level_damage_accrues(self):
        game = _game("fighter")
        pc, a = game.pc, game.pc.actor
        while a.char_level < 14:
            pc.award_xp(10000)
        # Melee mastery (L12, +1/level): at L14 that's 3 accrued points.
        self.assertGreaterEqual(a.per_level_dmg, 3)

    def test_powers_applied_once(self):
        game = _game("fighter")
        pc, a = game.pc, game.pc.actor
        while a.char_level < 8:
            pc.award_xp(10000)
        to_hit_at_8 = a.class_to_hit
        # Re-running level bookkeeping must not double-apply Tension.
        from hollowreach.core.rules.classpowers import apply_level_powers
        apply_level_powers(pc)
        self.assertEqual(a.class_to_hit, to_hit_at_8)


class SkillEffectTests(unittest.TestCase):
    def test_dodge_and_alertness_scale_dv(self):
        game = _game("fighter")
        pc = game.pc
        pc.skills["Dodge"] = 40
        pc.skills["Alertness"] = 90
        pc.refresh_combat()
        self.assertEqual(pc.actor.dodge_dv, 2)       # 40 // 20
        self.assertEqual(pc.actor.alertness_dv, 2)   # >=90

    def test_athletics_grants_speed(self):
        game = _game("fighter")
        pc = game.pc
        base = pc.actor.speed
        pc.skills["Athletics"] = 96
        pc.refresh_combat()
        self.assertGreater(pc.actor.speed, base)

    def test_find_weakness_grants_crit(self):
        game = _game("fighter")
        pc = game.pc
        pc.skills["Find Weakness"] = 50
        pc.refresh_combat()
        self.assertGreaterEqual(pc.actor.crit_bonus, 5)


class RegenTests(unittest.TestCase):
    def test_natural_regen_heals(self):
        game = _game("fighter")
        a = game.pc.actor
        a.hp = 1
        for _ in range(300):
            regen.advance_regen(game.pc)
        self.assertGreater(a.hp, 1)

    def test_healer_regen_is_faster(self):
        healer = _game("healer")
        fighter = _game("fighter")
        # Push the healer to level 6 for the Quick recovery power.
        while healer.pc.actor.char_level < 6:
            healer.pc.award_xp(10000)
        self.assertLess(healer.pc.regen_mult, fighter.pc.regen_mult)


if __name__ == "__main__":
    unittest.main()
