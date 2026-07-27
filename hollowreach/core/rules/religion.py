"""The divine economy — alignment, piety, sacrifice, prayer, crowning (§10).

The second progression track, and the strategic counterweight to the
Hollowing.  Devotion is grown by **sacrificing** gold and gear on a
co-aligned **altar** (marble/granite/obsidian for lawful/neutral/chaotic),
and spent by **praying**: a hurt hero is healed, a Warped hero can have
the Hollowing *eased from them* — devotion becomes a real alternative to
cure potions — and a hero of extreme alignment with deep enough favour is
**crowned a Champion**: permanently Blessed, stat-boosted, and gifted.

Alignment is a score in ``[-3000, +3000]``; killing the hollowed and the
chaotic pulls you lawful, taking corrupting blows pulls you chaotic.
"""

from __future__ import annotations

# -- alignment ---------------------------------------------------------------
ALIGN_MIN, ALIGN_MAX = -3000, 3000
ALIGN_START = {"lawful": 1000, "neutral": 0, "chaotic": -1000}
_EXTREME = 2000
_BAND = 750


def band(score: int) -> str:
    if score >= _BAND:
        return "lawful"
    if score <= -_BAND:
        return "chaotic"
    return "neutral"


def is_extreme(score: int) -> bool:
    return abs(score) >= _EXTREME


def shift_alignment(pc, delta: int) -> None:
    pc.alignment_score = max(ALIGN_MIN, min(ALIGN_MAX, pc.alignment_score + delta))


# -- piety -------------------------------------------------------------------
PIETY_DECAY_TURNS = 220
CROWNING_PIETY = 2500

# gold -> piety per coin when sacrificed on a co-aligned altar (dwarves tithe
# more generously, §10.2).
def _gold_rate(pc) -> float:
    return 0.48 if pc.race.id == "dwarf" else 0.32


def decay_piety(pc) -> None:
    floor = max(99, pc.cls.start_piety)
    if pc.piety > floor:
        pc.piety = max(floor, int(pc.piety * 0.99))


def sacrifice_gold(game, altar_align: str) -> list:
    """Offer all carried gold at an altar; return message lines."""
    pc = game.pc
    if pc.gold <= 0:
        return ["You have no gold to offer."]
    if altar_align != pc.alignment:
        # Offering at another god's altar earns nothing but ill will (§10.2).
        _retribution(game, "You offer at a rival god's altar. It is not pleased.")
        return []
    gained = int(pc.gold * _gold_rate(pc))
    pc.piety += gained
    pc.gold = 0
    return [f"You offer your gold. A warm favour settles over you. "
            f"(+{gained} piety)"]


def sacrifice_item(game, item, altar_align: str) -> list:
    """Sacrificing an item on a co-aligned altar (called from drop)."""
    pc = game.pc
    if altar_align != pc.alignment:
        _retribution(game, "The altar rejects your offering.")
        return []
    value = max(1, item.base.price) * item.quantity
    gained = int(value * 0.3)
    pc.piety += gained
    return [f"The {item.name} is consumed in cold fire. (+{gained} piety)"]


# -- prayer ------------------------------------------------------------------
def pray(game) -> list:
    """Pray for aid; effect chosen by need precedence (§10.4)."""
    pc, a = game.pc, game.pc.actor
    on_altar = _altar_align_here(game)
    devout = on_altar == pc.alignment

    # Too little favour to ask anything: the god's patience is not free.
    if pc.piety < 50:
        _retribution(game, "You pray, but your god is deaf to the faithless.")
        return []

    # 1. Crowning — the great reward (§10.5).
    if (not pc.crowned and is_extreme(pc.alignment_score)
            and pc.piety >= CROWNING_PIETY):
        return crown(game)

    cost_scale = 0.5 if devout else 1.0

    # 2. Grievous wounds — healed.
    if a.hp * 2 < a.max_hp:
        heal = a.max_hp - a.hp
        a.hp = a.max_hp
        _spend(pc, int((120 + heal) * cost_scale))
        return ["Your god mends your wounds. You are made whole."]

    # 3. The Hollowing — eased (the divine answer to corruption).
    if pc.warps or pc.blight_points > 0:
        events = game.blight.cleanse(pc, 130 if devout else 80)
        game.pc.refresh_combat()
        _spend(pc, int(200 * cost_scale))
        lines = ["A clean light passes through you; the Hollowing loosens "
                 "its grip."]
        for e in events:
            if e.warp_id:
                lines.append(f"  The {e.warp_id.replace('_', ' ')} fades.")
        return lines

    # 4. Cursed gear — released.
    from ..model.item import CURSED, UNCURSED
    worn = [it for _s, it in pc.equipment.worn_items() if it.buc == CURSED]
    if worn:
        for it in worn:
            it.buc = UNCURSED
            it.buc_known = True
        _spend(pc, int(150 * cost_scale))
        return ["Your god lifts the curses that bound your gear."]

    # 5. A minor blessing.
    a.heal(game.rng.roll("2d6"))
    _spend(pc, int(60 * cost_scale))
    return ["A quiet blessing steadies you."]


def _spend(pc, amount: int) -> None:
    pc.piety = max(0, pc.piety - max(1, amount))
    pc.prayer_timer = getattr(pc, "prayer_timer", 0) + 1


# -- crowning ----------------------------------------------------------------
def crown(game) -> list:
    pc, a = game.pc, game.pc.actor
    pc.crowned = True
    pc.piety = max(0, pc.piety - CROWNING_PIETY)
    a.blessed = True                       # permanent (folds into PV, §7.2)
    a.attributes.apply_modifier("To", 1)
    a.attributes.apply_modifier("Ch", 2)
    a.attributes.apply_modifier("Ma", 1)
    champion = {"lawful": "Order", "neutral": "Balance",
                "chaotic": "the Hollow"}[pc.alignment]
    lines = [f"*** Your god reaches down and names you a Champion of "
             f"{champion}! ***",
             "You are Blessed evermore; your body and presence are tempered."]
    if pc.alignment == "chaotic":
        # A chaotic crowning is a devil's bargain — it warps you (§10.5).
        events = game.blight.add_blight(pc, 300)
        for e in events:
            if e.warp_id:
                lines.append(f"  The bargain twists you: {e.warp_id.replace('_', ' ')}.")
    game.pc.refresh_combat()
    return lines


# -- helpers -----------------------------------------------------------------
def _altar_align_here(game):
    from ..world import tile as tiles
    a = game.pc.actor
    return tiles.altar_alignment(game.levels[game.depth].tile(a.x, a.y))


def _retribution(game, message: str) -> None:
    game.log.add(message)
    dmg = game.rng.roll("1d6")
    game.pc.actor.take_damage(dmg)
    game.log.add(f"A cold rebuke strikes you. ({dmg})")
