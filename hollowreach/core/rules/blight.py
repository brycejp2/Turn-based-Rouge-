"""The Blight clock — the Hollowing's pressure mechanic (original system).

The signature tension of the game.  In the deep places the Hollowing
seeps into the hero, accruing hidden **Blight** every turn at a rate that
climbs with depth.  Cross a threshold and the Hollowing inflicts a
**Warp** (``content/warps.py``): a mutation with jagged upsides and real
costs.  Accumulate enough Warps and the hero is *claimed* — a nonstandard
game over.  Because Blight only builds while you linger in the depths,
grinding is self-defeating: the clock always pushes you forward.

The clock is a global service subscribed to the turn loop (one
``on_turn`` per player action).  Rate modifiers: the Warden omen and high
Appearance slow it; a difficulty flag can switch it off entirely.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...content.warps import (
    WARPS, WARP_IDS, BLIGHT_PER_WARP, MAX_WARPS,
)

# Blight only accrues at or below this dungeon level; shallow floors are safe.
BLIGHT_START_DEPTH = 3


@dataclass
class BlightEvent:
    kind: str              # "warp" | "cured" | "consumed"
    message: str
    warp_id: "str | None" = None


class BlightClock:
    def __init__(self, rng, enabled: bool = True):
        self.enabled = enabled
        # The order Warps arrive is fixed per run but hidden from the player.
        self._order = list(WARP_IDS)
        rng.shuffle(self._order)

    # -- rate ------------------------------------------------------------
    def rate_per_turn(self, pc, depth: int) -> float:
        if not self.enabled or depth < BLIGHT_START_DEPTH:
            return 0.0
        # Tuned so a focused descent to the bottom collects only a handful
        # of Warps, while lingering on a level is punished (§9.2).
        rate = 0.2 + max(0, depth - BLIGHT_START_DEPTH) * 0.12
        rate *= pc.sign.effects.get("blight_mult", 1.0)
        ap = pc.actor.attributes.Ap
        rate *= max(0.5, 1.0 - (ap - 10) * 0.02)   # comely folk resist it
        return max(0.0, rate)

    # -- per-turn advance -------------------------------------------------
    def on_turn(self, pc, depth: int) -> list[BlightEvent]:
        if not self.enabled:
            return []
        gain = self.rate_per_turn(pc, depth)
        if gain <= 0:
            return []
        pc.blight_points += gain
        return self._settle(pc)

    def add_blight(self, pc, amount: float) -> list[BlightEvent]:
        """External Blight source (attack, trap, tainted item)."""
        pc.blight_points += max(0.0, amount)
        return self._settle(pc)

    def _settle(self, pc) -> list[BlightEvent]:
        """Apply/gain Warps until the meter matches the accumulated points."""
        events: list[BlightEvent] = []
        target = int(pc.blight_points // BLIGHT_PER_WARP)
        while len(pc.warps) < target:
            if len(pc.warps) >= MAX_WARPS:
                events.append(BlightEvent(
                    "consumed",
                    "The Hollowing floods the last of you — you are undone. "
                    "You become a hollow thing, and the depths keep it."))
                return events
            warp = self._apply_next_warp(pc)
            events.append(BlightEvent(
                "warp",
                f"The Hollowing warps you: {warp.name} ({warp.note}).",
                warp_id=warp.id))
        return events

    # -- warp application -------------------------------------------------
    def _apply_next_warp(self, pc):
        warp_id = self._order[len(pc.warps)]
        warp = WARPS[warp_id]
        actor = pc.actor
        for key, delta in warp.attr_mods.items():
            actor.attributes.apply_modifier(key, delta)
        actor.warp_dv += warp.dv
        actor.warp_pv += warp.pv
        actor.warp_unarmed_dmg += warp.unarmed_dmg
        pc.warps.append(warp_id)
        self._refresh_specials(pc)
        return warp

    def _remove_last_warp(self, pc):
        if not pc.warps:
            return None
        warp_id = pc.warps.pop()
        warp = WARPS[warp_id]
        actor = pc.actor
        for key, delta in warp.attr_mods.items():
            actor.attributes.apply_modifier(key, -delta)
        actor.warp_dv -= warp.dv
        actor.warp_pv -= warp.pv
        actor.warp_unarmed_dmg -= warp.unarmed_dmg
        self._refresh_specials(pc)
        return warp

    def _refresh_specials(self, pc) -> None:
        specials = set()
        for warp_id in pc.warps:
            specials.update(WARPS[warp_id].specials)
        pc.actor.night_vision = "night_vision" in specials

    # -- cures ------------------------------------------------------------
    def cleanse(self, pc, amount: float) -> list[BlightEvent]:
        """Reduce Blight, shedding Warps whose threshold is no longer met."""
        pc.blight_points = max(0.0, pc.blight_points - amount)
        events: list[BlightEvent] = []
        target = int(pc.blight_points // BLIGHT_PER_WARP)
        while len(pc.warps) > target:
            warp = self._remove_last_warp(pc)
            if warp is None:
                break
            events.append(BlightEvent(
                "cured", f"The {warp.name} fades from you.", warp_id=warp.id))
        return events

    # -- status -----------------------------------------------------------
    def status(self, pc) -> str:
        count = len(pc.warps)
        into = int(pc.blight_points) % BLIGHT_PER_WARP
        return f"Warps:{count}/{MAX_WARPS} ({into}%)"
