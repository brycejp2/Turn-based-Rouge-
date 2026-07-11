"""Quest state machine and objective tracking (design ref §14).

Quests move offered → active → complete → done.  The run tracks the raw
counters (total kills, kills by monster type, deepest level reached); a
quest records a *baseline* when accepted, so its progress is simply how
far those counters have moved since.  Talking to a giver offers, checks,
or turns in their quests.
"""

from __future__ import annotations

from ...content.quests import QUESTS


def _baseline(pc, quest) -> int:
    obj = quest.objective
    if obj["kind"] == "kill_count":
        return pc.total_kills
    if obj["kind"] == "kill_type":
        return pc.kills_by_type.get(obj["type"], 0)
    return 0


def accept(pc, quest) -> None:
    pc.quests[quest.id] = {"state": "active", "baseline": _baseline(pc, quest)}


def progress(pc, quest) -> tuple:
    """Return (current, needed) toward the objective."""
    obj = quest.objective
    state = pc.quests.get(quest.id)
    base = state["baseline"] if state else 0
    if obj["kind"] == "kill_count":
        return pc.total_kills - base, obj["count"]
    if obj["kind"] == "kill_type":
        return pc.kills_by_type.get(obj["type"], 0) - base, obj["count"]
    if obj["kind"] == "reach_depth":
        return pc.max_depth, obj["depth"]
    return 0, 1


def is_complete(pc, quest) -> bool:
    current, needed = progress(pc, quest)
    return current >= needed


def turn_in(game, quest) -> list:
    """Pay a completed quest's reward; return message lines."""
    from ..generation.loot import make_item
    pc = game.pc
    lines = [quest.on_complete] if quest.on_complete else []
    reward = quest.reward
    if reward.get("gold"):
        pc.gold += reward["gold"]
        lines.append(f"  You receive {reward['gold']} gold.")
    if reward.get("xp"):
        for msg in pc.award_xp(reward["xp"]):
            lines.append("  " + msg)
    for base_id, buc in reward.get("items", []):
        item = make_item(base_id, game.rng, buc=buc, enchant=0)
        pc.inventory.add(item)
        lines.append(f"  You receive {game.id_service.display_name(item)}.")
    pc.quests[quest.id]["state"] = "done"
    pc.update_encumbrance()
    return lines


def talk(game, npc) -> list:
    """Resolve a conversation with a quest-giver; return message lines."""
    from ...content.towns import NPCS
    pc = game.pc
    ndef = NPCS[npc.npc_id]
    lines = list(ndef.greeting)
    for qid in ndef.quests:
        quest = QUESTS[qid]
        state = pc.quests.get(qid, {}).get("state")
        if state is None:
            accept(pc, quest)
            lines.append(f"[New quest: {quest.title}] {quest.on_offer}")
        elif state == "active":
            if is_complete(pc, quest):
                lines.append(f"[Quest complete: {quest.title}]")
                lines.extend(turn_in(game, quest))
            else:
                cur, need = progress(pc, quest)
                lines.append(f"[{quest.title}: {min(cur, need)}/{need}] "
                             f"{quest.description}")
        # state == "done": nothing more to say about it.
    return lines
