"""Quests (original content, design ref §14).

A small, self-contained quest line the Hearthvale folk hand out.  Each
quest has an **objective** the run tracks automatically and a **reward**
paid when you return to the giver having met it.  Objective kinds:

* ``reach_depth``  — descend to at least dungeon level N.
* ``kill_count``   — slay N monsters (any kind).
* ``kill_type``    — slay N monsters carrying a given type tag.

Rewards are ``{"gold": n, "xp": n, "items": [(base_id, buc), ...]}``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QuestDef:
    id: str
    giver: str
    title: str
    description: str
    objective: dict
    reward: dict
    on_offer: str = ""
    on_complete: str = ""


QUESTS = {
    "cull_the_vermin": QuestDef(
        id="cull_the_vermin", giver="maroc",
        title="Cull the Vermin",
        description="Slay 8 creatures in the Depths.",
        objective={"kind": "kill_count", "count": 8},
        reward={"gold": 120, "xp": 40},
        on_offer="\"The shallows are thick with vermin. Thin them — eight "
                 "should do — and I'll see you paid.\"",
        on_complete="\"Eight and more, by the look of you. Here — you've "
                    "earned it.\""),
    "the_descent": QuestDef(
        id="the_descent", giver="maroc",
        title="Into the Dark",
        description="Descend to dungeon level 5.",
        objective={"kind": "reach_depth", "depth": 5},
        reward={"gold": 200, "xp": 80},
        on_offer="\"If you mean to reach the Gate, you must first learn the "
                 "shallow dark. Get as far as the fifth level and come tell "
                 "me you live.\"",
        on_complete="\"The fifth level and back. Good. The real dark is "
                    "further down — but you're readier for it now.\""),
    "ease_the_hollowing": QuestDef(
        id="ease_the_hollowing", giver="ferelith",
        title="Ease the Hollowing",
        description="Destroy 3 hollowed creatures in the deep.",
        objective={"kind": "kill_type", "type": "hollowed", "count": 3},
        reward={"gold": 100, "xp": 60,
                "items": [("potion_cleansing", "blessed")]},
        on_offer="\"The hollowed are the Hollowing given flesh. Put three of "
                 "them down and I'll bless a draught to wash the taint from "
                 "you.\"",
        on_complete="\"Three of the hollowed, unmade. Take this — blessed "
                    "with all the grace I have. It will cleanse what the deep "
                    "has put in you.\""),
}
