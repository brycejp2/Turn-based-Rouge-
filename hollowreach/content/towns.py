"""Hearthvale — the surface hub and its folk (original content, design ref §4.4).

Hearthvale is the safe village at the mouth of the Sundered Depths: the
run begins here, and a hero can climb back to it between dives to trade,
heal, and take on quests.  This module defines its people — a trader who
runs the shop, and quest-givers who send you into the dark and reward you
for what you bring back.

NPCs are placed by ``core/generation/town.py`` and become non-hostile
:class:`Actor` s the player bumps to interact with.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NpcDef:
    id: str
    name: str
    glyph: str
    role: str                       # "shopkeeper" | "quest_giver" | "folk"
    greeting: list = field(default_factory=list)
    quests: tuple = ()              # quest ids this NPC offers


NPCS = {
    "bram": NpcDef(
        "bram", "Bram the Trader", "T", "shopkeeper",
        greeting=["\"Coin for steel, steel for coin,\" says Bram. "
                  "\"See anything you like?\""]),
    "maroc": NpcDef(
        "maroc", "Elder Maroc", "E", "quest_giver",
        greeting=["Elder Maroc leans on his staff. \"You mean to go down "
                  "there, then. Brave, or a fool — the Depths sort out which.\""],
        quests=("the_descent", "cull_the_vermin")),
    "ferelith": NpcDef(
        "ferelith", "Sister Ferelith", "F", "quest_giver",
        greeting=["Sister Ferelith presses a hand to her heart. \"The "
                  "Hollowing touches everyone who goes deep. Come back to me "
                  "and I'll do what I can.\""],
        quests=("ease_the_hollowing",)),
    "sarn": NpcDef(
        "sarn", "Sarn the Lorekeeper", "S", "folk",
        greeting=["Sarn the Lorekeeper murmurs, \"I opened the Gate and I "
                  "could not close it. Perhaps you will finish what I began.\"",
                  "\"Seal it at the bottom. That is the only ending that "
                  "isn't an ending.\""]),
}

# What Bram stocks. Rolled into concrete items at game start.
SHOP_STOCK = [
    ("potion_healing", 3),
    ("potion_extra_healing", 1),
    ("potion_cleansing", 1),      # the reason to earn gold and come back
    ("scroll_identify", 2),
    ("scroll_remove_curse", 1),
    ("scroll_magic_mapping", 1),
    ("ration", 3),
    ("long_sword", 1),
    ("chain_mail", 1),
    ("kite_shield", 1),
]

SHOP_MARKUP = 1.4      # buy price = value * markup (before haggling)
SELL_FRACTION = 0.4    # sell price = value * this (before haggling)
