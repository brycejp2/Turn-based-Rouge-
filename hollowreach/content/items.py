"""Item base definitions (original content).

Weapons, armour, potions and scrolls built from generic fantasy /
real-world types (a long sword, a chain mail, a potion of healing).  None
of it is drawn from any other game's named content.  Potions and scrolls
are disguised at runtime behind the appearance pools below until the
player identifies them.

Adding items is a data edit here; the effect ids on consumables map to
handlers in ``core/rules/consumables.py``.
"""

from __future__ import annotations

from ..core.model.item import (
    ItemBase, SLOT_WEAPON, SLOT_BODY, SLOT_SHIELD, SLOT_HEAD, SLOT_BOOTS,
    SLOT_CLOAK, SLOT_HANDS, SLOT_GIRDLE, SLOT_NECK,
)

# -- weapons ----------------------------------------------------------------
_WEAPONS = [
    ItemBase("dagger", "dagger", "weapon", "(", 10, SLOT_WEAPON,
             dmg_dice="1d4", to_hit=1, price=10, weapon_skill="dagger"),
    ItemBase("short_sword", "short sword", "weapon", "(", 25, SLOT_WEAPON,
             dmg_dice="1d6", to_hit=1, price=25, weapon_skill="sword"),
    ItemBase("long_sword", "long sword", "weapon", "(", 40, SLOT_WEAPON,
             dmg_dice="1d8", price=60, weapon_skill="sword"),
    ItemBase("mace", "mace", "weapon", "(", 55, SLOT_WEAPON,
             dmg_dice="1d10", to_hit=-1, price=45, weapon_skill="blunt"),
    ItemBase("battle_axe", "battle axe", "weapon", "(", 75, SLOT_WEAPON,
             dmg_dice="1d12", to_hit=-1, two_handed=True, price=80,
             weapon_skill="axe"),
    ItemBase("spear", "spear", "weapon", "(", 45, SLOT_WEAPON,
             dmg_dice="1d8", to_hit=1, price=35, weapon_skill="spear"),
]

# -- armour -----------------------------------------------------------------
_ARMOUR = [
    ItemBase("leather_armor", "leather armor", "body_armor", "[", 120, SLOT_BODY,
             dv=1, pv=2, price=30),
    ItemBase("ring_mail", "ring mail", "body_armor", "[", 250, SLOT_BODY,
             dv=0, pv=4, price=90),
    ItemBase("chain_mail", "chain mail", "body_armor", "[", 400, SLOT_BODY,
             dv=-1, pv=6, price=180),
    ItemBase("plate_mail", "plate mail", "body_armor", "[", 700, SLOT_BODY,
             dv=-2, pv=9, price=400),
    ItemBase("wooden_shield", "wooden shield", "shield", ")", 80, SLOT_SHIELD,
             dv=2, pv=1, price=25),
    ItemBase("kite_shield", "kite shield", "shield", ")", 150, SLOT_SHIELD,
             dv=3, pv=2, price=70),
    ItemBase("leather_cap", "leather cap", "helmet", "]", 30, SLOT_HEAD,
             dv=0, pv=1, price=10),
    ItemBase("iron_helm", "iron helm", "helmet", "]", 90, SLOT_HEAD,
             dv=0, pv=2, price=40),
    ItemBase("leather_boots", "leather boots", "boots", "]", 40, SLOT_BOOTS,
             dv=0, pv=1, price=12),
    ItemBase("leather_gloves", "leather gloves", "gauntlets", "]", 20, SLOT_HANDS,
             dv=0, pv=1, price=10),
    ItemBase("cloak", "traveller's cloak", "cloak", "(", 30, SLOT_CLOAK,
             dv=1, pv=0, price=15),
    ItemBase("girdle", "leather girdle", "girdle", "[", 15, SLOT_GIRDLE,
             dv=0, pv=1, price=12),
]

# -- potions (effect ids resolved in consumables.py) ------------------------
_POTIONS = [
    ItemBase("potion_healing", "potion of healing", "potion", "!", 10,
             stackable=True, price=100, effect="heal"),
    ItemBase("potion_extra_healing", "potion of extra healing", "potion", "!", 10,
             stackable=True, price=250, effect="extra_heal"),
    ItemBase("potion_gain_attributes", "potion of gain attributes", "potion", "!", 10,
             stackable=True, price=400, effect="gain_attributes"),
    ItemBase("potion_might", "potion of might", "potion", "!", 10,
             stackable=True, price=200, effect="boost_strength"),
    ItemBase("potion_endurance", "potion of endurance", "potion", "!", 10,
             stackable=True, price=200, effect="boost_toughness"),
    ItemBase("potion_mana", "potion of raw mana", "potion", "!", 10,
             stackable=True, price=150, effect="restore_mana"),
    ItemBase("potion_cleansing", "potion of cleansing", "potion", "!", 10,
             stackable=True, price=500, effect="cleanse_blight"),
    ItemBase("potion_water", "potion of water", "potion", "!", 10,
             stackable=True, price=10, effect="water"),
    ItemBase("potion_sickness", "potion of sickness", "potion", "!", 10,
             stackable=True, price=10, effect="sickness"),
]

# -- scrolls ----------------------------------------------------------------
_SCROLLS = [
    ItemBase("scroll_identify", "scroll of identify", "scroll", "?", 5,
             stackable=True, price=100, effect="identify"),
    ItemBase("scroll_remove_curse", "scroll of remove curse", "scroll", "?", 5,
             stackable=True, price=120, effect="remove_curse"),
    ItemBase("scroll_magic_mapping", "scroll of magic mapping", "scroll", "?", 5,
             stackable=True, price=150, effect="magic_mapping"),
    ItemBase("scroll_teleport", "scroll of teleportation", "scroll", "?", 5,
             stackable=True, price=120, effect="teleport"),
    ItemBase("scroll_enchant_weapon", "scroll of enchant weapon", "scroll", "?", 5,
             stackable=True, price=200, effect="enchant_weapon"),
    ItemBase("scroll_enchant_armor", "scroll of enchant armor", "scroll", "?", 5,
             stackable=True, price=200, effect="enchant_armor"),
]

# -- food -------------------------------------------------------------------
_FOOD = [
    ItemBase("ration", "iron ration", "food", "%", 100,
             stackable=True, price=30, effect="food"),
]

ITEMS = {b.id: b for b in _WEAPONS + _ARMOUR + _POTIONS + _SCROLLS + _FOOD}

# -- disguise appearance pools ----------------------------------------------
POTION_APPEARANCES = [
    "murky", "fizzy", "smoky", "cloudy", "bubbly", "viscous", "glowing",
    "milky", "oily", "sparkling", "black", "crimson", "azure", "amber",
]
SCROLL_LABELS = [
    "VROOMBA", "ZEK NUR", "OGGROTH", "FIZZ MEK", "QUANTHIS", "BLORNAC",
    "SETHRA", "UMBRIX", "KORVANE", "PLETHIS", "DRONNAK", "YSGARDA",
]


def item_spawn_table(depth: int) -> list:
    """(base_id, weight) list of loot eligible at dungeon level ``depth``.

    Consumables are common at every depth; heavier gear grows more likely
    as you descend."""
    table: list = []
    # Consumables — always available.
    for base in _POTIONS + _SCROLLS + _FOOD:
        weight = 6
        if base.id in ("potion_gain_attributes", "potion_extra_healing"):
            weight = 2  # rarer power items
        if base.id == "potion_cleansing":
            weight = 1  # the most precious item in the game (§9.4)
        table.append((base.id, weight))
    # Weapons / armour — tier gated loosely by depth.
    tiered = [
        ("dagger", 1), ("short_sword", 1), ("leather_armor", 1),
        ("wooden_shield", 1), ("leather_cap", 1), ("leather_boots", 1),
        ("long_sword", 3), ("spear", 3), ("mace", 4), ("ring_mail", 3),
        ("kite_shield", 4), ("iron_helm", 4),
        ("battle_axe", 6), ("chain_mail", 6), ("plate_mail", 9),
    ]
    for base_id, min_depth in tiered:
        if depth >= min_depth:
            weight = max(1, 5 - abs(depth - min_depth))
            table.append((base_id, weight))
    return table
