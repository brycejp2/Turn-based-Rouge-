"""Potion and scroll effects (design ref §11.7).

Each consumable's ``effect`` id maps to a handler here.  Handlers take the
running ``game`` (for the level, log, rng and identification service), the
``pc`` and the ``item``, apply the effect — scaled by BUC where it matters
— and return a message.  Using a consumable identifies its type
(use-ID).  The caller is responsible for decrementing the stack.
"""

from __future__ import annotations

from ..model.item import BLESSED, CURSED
from ..model.attributes import ATTRIBUTE_KEYS


def use_consumable(game, pc, item) -> str:
    """Dispatch to the right handler and identify the type on use."""
    effect = item.base.effect
    handler = _EFFECTS.get(effect)
    if handler is None:
        return f"Nothing happens."
    msg = handler(game, pc, item)
    newly = game.id_service.identify_type(item.base)
    item.reveal()
    if newly:
        msg += f" (It was {game.id_service.display_name(item, quantity=False)}.)"
    return msg


# -- potions -----------------------------------------------------------------
def _heal(game, pc, item) -> str:
    a = pc.actor
    amount = game.rng.roll("2d8") + a.char_level
    if item.buc == BLESSED:
        amount = int(amount * 1.5)
    elif item.buc == CURSED:
        amount = max(1, amount // 2)
    a.heal(amount)
    return f"You feel better. (+{amount} HP)"


def _extra_heal(game, pc, item) -> str:
    a = pc.actor
    amount = game.rng.roll("4d8") + a.char_level * 2
    if item.buc == BLESSED:
        amount = int(amount * 1.5)
        a.max_hp += 2  # blessed extra healing tempers you
    elif item.buc == CURSED:
        amount = max(1, amount // 2)
    a.heal(amount)
    return f"Vitality floods through you. (+{amount} HP)"


def _gain_attributes(game, pc, item) -> str:
    attrs = pc.actor.attributes
    if item.buc == BLESSED:
        for key in ATTRIBUTE_KEYS:
            attrs.apply_modifier(key, 1)
        return "Power surges through every fibre! (+1 to all attributes)"
    key = game.rng.choice(ATTRIBUTE_KEYS)
    if item.buc == CURSED:
        attrs.apply_modifier(key, -1)
        return f"You feel diminished. (-1 {key})"
    attrs.apply_modifier(key, 1)
    return f"You feel more capable. (+1 {key})"


def _boost(attr_key, label):
    def handler(game, pc, item) -> str:
        delta = 2 if item.buc == BLESSED else 1
        if item.buc == CURSED:
            pc.actor.attributes.apply_modifier(attr_key, -1)
            return f"Your {label} wanes. (-1 {attr_key})"
        pc.actor.attributes.apply_modifier(attr_key, delta)
        return f"Your {label} grows. (+{delta} {attr_key})"
    return handler


def _restore_mana(game, pc, item) -> str:
    a = pc.actor
    amount = game.rng.roll("2d6") + a.char_level
    if item.buc == BLESSED:
        amount = int(amount * 1.5)
        a.max_pp += 1
    a.restore_pp(amount)
    return f"Arcane energy returns. (+{amount} PP)"


def _water(game, pc, item) -> str:
    if item.buc == BLESSED:
        return "You drink some holy water. It is refreshing."
    return "You drink some water."


def _sickness(game, pc, item) -> str:
    a = pc.actor
    dmg = game.rng.roll("2d4")
    a.take_damage(dmg)
    return f"That was foul — you retch. (-{dmg} HP)"


# -- scrolls -----------------------------------------------------------------
def _identify(game, pc, item) -> str:
    targets = [it for _l, it in pc.inventory.listing()
               if it is not item and not it.identified]
    if not targets:
        return "The scroll's runes fade. Nothing here to identify."
    if item.buc == BLESSED:
        for it in targets:
            it.reveal()
            game.id_service.identify_type(it.base)
        return f"You identify your entire pack ({len(targets)} items)."
    target = targets[0]
    target.reveal()
    game.id_service.identify_type(target.base)
    return f"It is {game.id_service.display_name(target)}."


def _remove_curse(game, pc, item) -> str:
    from ..model.item import UNCURSED
    if item.buc == BLESSED:
        pool = [it for _s, it in pc.equipment.worn_items()] + \
               [it for _l, it in pc.inventory.listing()]
    else:
        pool = [it for _s, it in pc.equipment.worn_items()]
    cleaned = 0
    for it in pool:
        if it.buc == CURSED:
            it.buc = UNCURSED
            it.buc_known = True
            cleaned += 1
    if cleaned:
        return f"A holy light cleanses {cleaned} item(s) of their curse."
    return "A holy light washes over you, but nothing was cursed."


def _magic_mapping(game, pc, item) -> str:
    level = game.levels[game.depth]
    for y in range(level.height):
        for x in range(level.width):
            level.explored[y][x] = True
    return "The layout of the level floods into your mind."


def _teleport(game, pc, item) -> str:
    level = game.levels[game.depth]
    for _ in range(200):
        x = game.rng.randint(1, level.width - 2)
        y = game.rng.randint(1, level.height - 2)
        if level.is_walkable(x, y) and level.actor_at(x, y) is None:
            pc.actor.x, pc.actor.y = x, y
            game._update_fov()
            return "The world lurches — you are somewhere else."
    return "The scroll fizzles."


def _enchant_weapon(game, pc, item) -> str:
    weapon = pc.equipment.weapon()
    if weapon is None:
        return "Your hands tingle, but you wield no weapon."
    amount = 2 if item.buc == BLESSED else 1
    if item.buc == CURSED:
        weapon.enchant -= 1
        weapon.reveal()
        pc.equipment.recompute(pc.actor)
        return f"Your {weapon.name} dims. (-1)"
    weapon.enchant += amount
    weapon.reveal()
    pc.equipment.recompute(pc.actor)
    return f"Your {weapon.name} glows sharper! (+{amount})"


def _enchant_armor(game, pc, item) -> str:
    worn = [it for s, it in pc.equipment.worn_items() if s != "weapon"]
    if not worn:
        return "Your skin tingles, but you wear no armour."
    target = max(worn, key=lambda it: it.base.pv)
    amount = 2 if item.buc == BLESSED else 1
    if item.buc == CURSED:
        target.enchant -= 1
        target.reveal()
        pc.equipment.recompute(pc.actor)
        return f"Your {target.name} corrodes. (-1)"
    target.enchant += amount
    target.reveal()
    pc.equipment.recompute(pc.actor)
    return f"Your {target.name} hardens! (+{amount})"


def _food(game, pc, item) -> str:
    return "You eat the ration. It is filling."


_EFFECTS = {
    "heal": _heal,
    "extra_heal": _extra_heal,
    "gain_attributes": _gain_attributes,
    "boost_strength": _boost("St", "strength"),
    "boost_toughness": _boost("To", "toughness"),
    "restore_mana": _restore_mana,
    "water": _water,
    "sickness": _sickness,
    "identify": _identify,
    "remove_curse": _remove_curse,
    "magic_mapping": _magic_mapping,
    "teleport": _teleport,
    "enchant_weapon": _enchant_weapon,
    "enchant_armor": _enchant_armor,
    "food": _food,
}
