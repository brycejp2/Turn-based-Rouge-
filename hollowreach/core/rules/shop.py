"""Buying and selling at Bram's (design ref §11.8).

Prices flex with Charisma and the Haggling skill: a charming, silver-
tongued hero buys cheaper and sells dearer.  Gold lives on the player
(``pc.gold``); the shop keeps a finite, rollable stock, and anything you
sell can be bought back.
"""

from __future__ import annotations

from ...content.towns import SHOP_MARKUP, SELL_FRACTION


def _haggle(pc) -> float:
    """0..~0.5 discount/bonus fraction from Charisma + Haggling."""
    ch = pc.actor.attributes.Ch
    haggling = pc.skills.get("Haggling", 0)
    factor = (ch - 10) * 0.012 + haggling / 400.0
    return max(0.0, min(0.5, factor))


def buy_price(pc, base_price: int) -> int:
    price = base_price * SHOP_MARKUP * (1.0 - _haggle(pc))
    return max(1, round(price))


def sell_price(pc, base_price: int) -> int:
    price = base_price * SELL_FRACTION * (1.0 + _haggle(pc))
    return max(0, round(price))


def buy(game, item) -> tuple:
    pc = game.pc
    price = buy_price(pc, item.base.price)
    if pc.gold < price:
        return False, f"You can't afford the {item.name} ({price} gold)."
    pc.gold -= price
    # Remove this exact instance (Item is value-comparable, so list.remove
    # could drop a different-but-equal copy off the shelf).
    for i, stocked in enumerate(game.shop_stock):
        if stocked is item:
            del game.shop_stock[i]
            break
    pc.inventory.add(item)
    pc.update_encumbrance()
    if game.pc.auto_buc:
        item.buc_known = True
    return True, f"You buy {game.id_service.display_name(item)} for {price} gold."


def sell(game, item) -> tuple:
    pc = game.pc
    price = sell_price(pc, item.base.price)
    removed = pc.inventory.remove(item, quantity=1)   # one from a stack
    if removed is None:
        return False, "You don't have that."
    pc.gold += price
    pc.update_encumbrance()
    game.shop_stock.append(removed)                   # buy it back later
    return True, f"You sell {game.id_service.display_name(removed)} for {price} gold."
