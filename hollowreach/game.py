"""Game orchestration — wires the subsystems onto the turn scheduler.

The :class:`Game` owns the energy scheduler and drives the plan's core
loop (§3.1): pop the actor whose next-action time is soonest, let it act,
charge the action's EP cost, and requeue it.  The PC's actions come from
the front-end (interactive or demo/AI); monsters use ``core.rules.ai``.

Global clocks that subscribe to the scheduler (calendar/lighting here;
hunger, corruption, piety in later milestones — §17.3) advance off the
same time base, so speed correctly dilates everything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .core.engine.rng import Rng
from .core.engine.scheduler import Scheduler, STANDARD_ACTION_COST
from .core.world import tile as tiles
from .core.world.fov import compute_fov
from .core.generation.dungeon import generate_level
from .core.model.character import build_player, PlayerCharacter
from .core.rules import combat, ai, skills, regen
from .core.rules.calendar import Calendar, sight_radius
from .core.rules.identification import IdentificationService
from .core.rules.consumables import use_consumable
from .core.rules.blight import BlightClock
from .ui.render import MessageLog
from .persistence.save import SaveService
from .content import world


# Directional deltas for movement commands.
DIRECTIONS = {
    "h": (-1, 0), "j": (0, 1), "k": (0, -1), "l": (1, 0),
    "y": (-1, -1), "u": (1, -1), "b": (-1, 1), "n": (1, 1),
    ".": (0, 0),
}


@dataclass
class Game:
    pc: PlayerCharacter
    rng: Rng
    seed: int
    save: SaveService = field(default_factory=SaveService)
    blight_enabled: bool = True   # difficulty toggle (§5.7)

    def __post_init__(self):
        self.calendar = Calendar()
        # Scheduler and calendar share one time base; start mid-morning so
        # the opening level is lit by daylight (§4.1, §4.2).
        self.scheduler = Scheduler(self.calendar.ticks)
        self.log = MessageLog()
        self.levels: dict[int, object] = {}
        self.visible: set = set()
        self.running = True
        self.won = False
        self.depth = 0
        self.id_service = IdentificationService(self.rng)
        self.blight = BlightClock(self.rng, enabled=self.blight_enabled)

    # -- setup ------------------------------------------------------------
    @classmethod
    def new(cls, pc: PlayerCharacter, rng: Rng, seed: int,
            permadeath: bool = True, blight_enabled: bool = True) -> "Game":
        game = cls(pc=pc, rng=rng, seed=seed,
                   save=SaveService(permadeath=permadeath),
                   blight_enabled=blight_enabled)
        game._enter_level(1, going_down=True)
        for line in world.opening_lines(pc.actor.name):
            game.log.add(line)
        game._schedule_all()
        game._update_fov()
        return game

    def _enter_level(self, depth: int, going_down: bool) -> None:
        first_visit = depth not in self.levels
        if first_visit:
            # Deterministic per-depth seed so the world is reproducible.
            level_rng = Rng(self.seed * 1000 + depth)
            self.levels[depth] = generate_level(
                level_rng, depth=depth, is_final=(depth >= world.BOTTOM_DEPTH))
        level = self.levels[depth]
        self.depth = depth

        # Place the PC on the appropriate staircase.
        target = level.stairs_up if going_down else level.stairs_down
        if target is None:
            target = (level.rooms[0].cx, level.rooms[0].cy)
        self.pc.actor.x, self.pc.actor.y = target
        if self.pc.actor not in level.actors:
            level.add_actor(self.pc.actor)

        if first_visit and level.is_final:
            for line in world.gate_arrival_lines():
                self.log.add(line)

    def _schedule_all(self) -> None:
        self.scheduler = Scheduler(self.scheduler.time)
        level = self.levels[self.depth]
        for actor in level.actors:
            if actor.is_alive:
                self.scheduler.add(actor)

    # -- main loop --------------------------------------------------------
    def run_turn(self, player_command) -> None:
        """Advance the scheduler until the PC needs a decision.

        ``player_command`` is a callable returning a command string when
        it's the PC's turn (the front-end supplies input/AI).
        """
        level = self.levels[self.depth]
        while self.running:
            actor = self.scheduler.pop()
            if actor is None:
                self.running = False
                return
            self.calendar.advance_to(self.scheduler.time)

            if actor is self.pc.actor:
                cmd = player_command()
                acted = self._player_act(cmd)
                if self.won:          # sealed the Gate this action
                    return
                if not acted:
                    # Non-time-consuming command (a wall bump, stairs that
                    # aren't there, a failed equip...): put the PC back at
                    # the front without advancing time and RETURN to the
                    # front-end for fresh input. Interactive clients send a
                    # fixed command per keypress — looping here re-asked the
                    # same rejected command forever and froze the game.
                    self.scheduler.add(self.pc.actor, delay_cost=0)
                    return
                self._advance_regen()
                self._advance_blight()
                self._update_fov()
                self.scheduler.reschedule(self.pc.actor, STANDARD_ACTION_COST)
                if not self.pc.actor.is_alive:
                    self._on_death()
                    return
                if not self.running:   # claimed by the Hollowing
                    return
                return  # hand control back to the front-end to redraw
            else:
                self._monster_act(actor, level)
                if not self.running:
                    # The Hollowing claimed the hero mid-monster-turn
                    # (_on_hollowed already ended the run).
                    return
                if not self.pc.actor.is_alive:
                    # A monster landed the killing blow — end the run here,
                    # otherwise the dead PC never pops and monsters loop.
                    self._update_fov()
                    self._on_death()
                    return
                if actor.is_alive:
                    self.scheduler.reschedule(actor, STANDARD_ACTION_COST)

    def _player_act(self, cmd) -> bool:
        pc = self.pc.actor
        level = self.levels[self.depth]

        # Item actions arrive as (verb, payload) tuples from the front-end.
        if isinstance(cmd, tuple):
            verb, arg = cmd
            handler = {
                "pickup": lambda: self.pick_up(),
                "quaff": lambda: self.use_item(arg),
                "read": lambda: self.use_item(arg),
                "equip": lambda: self.equip_item(arg),
                "unequip": lambda: self.unequip_slot(arg),
                "drop": lambda: self.drop_item(arg),
                "cast": lambda: self.cast_spell(*arg),
            }.get(verb)
            return handler() if handler else False

        if cmd in ("Q", "quit"):
            self.running = False
            return False
        if cmd in DIRECTIONS:
            return self._move_or_attack(pc, level, *DIRECTIONS[cmd])
        if cmd == ">":
            return self._descend()
        if cmd == "<":
            return self._ascend()
        # Unknown command: no time passes.
        return False

    # -- item actions (each returns True when it consumes a turn) ---------
    def pick_up(self) -> bool:
        pc = self.pc.actor
        level = self.levels[self.depth]
        item = level.take_top_item(pc.x, pc.y)
        if item is None:
            self.log.add("There is nothing here to pick up.")
            return False
        if self.pc.auto_buc:
            item.buc_known = True   # Priest's Discerning eye (§5.3)
        letter = self.pc.inventory.add(item)
        if letter is None:
            level.add_item(pc.x, pc.y, item)  # put it back
            self.log.add("Your pack is full.")
            return False
        self.pc.update_encumbrance()
        self.log.add(f"{letter} - {self.id_service.display_name(item)}.")
        return True

    def use_item(self, item) -> bool:
        if item is None:
            return False
        if item.base.category == "spellbook":
            return self._study_book(item)
        msg = use_consumable(self, self.pc, item)
        self.log.add(msg)
        if item.quantity > 1:
            item.quantity -= 1
        else:
            self.pc.inventory.remove(item)
        self.pc.update_encumbrance()
        return True

    def _study_book(self, item) -> bool:
        """Read a spellbook to learn/refresh its spell (the book is kept)."""
        from .content.spells import SPELLS
        spell = SPELLS[item.base.teaches]
        newly = self.pc.learn_spell(spell.id, castings=15)
        if newly:
            self.log.add(f"You study the {item.name} and learn {spell.name}.")
        else:
            self.log.add(f"You refresh your grasp of {spell.name}.")
        return True

    def cast_spell(self, spell_id, direction) -> bool:
        """Cast a known spell; returns True if a turn was spent (§8)."""
        from .content.spells import SPELLS
        from .core.rules import magic
        pc, a = self.pc, self.pc.actor
        state = pc.spells.get(spell_id)
        spell = SPELLS.get(spell_id)
        if spell is None or state is None or state["castings"] <= 0:
            self.log.add("You cannot cast that.")
            return False

        cost = self._spell_cost(spell, state)
        if a.pp < cost:
            self.log.add(f"Not enough power to cast {spell.name} "
                         f"({cost} PP needed).")
            return False
        if spell.kind in ("bolt", "ball") and direction in (None, (0, 0)):
            return False   # aimed spell with no target

        a.pp -= cost
        state["castings"] -= 1
        state["casts"] += 1
        if state["casts"] % 20 == 0:      # power grows with practice (§8.2)
            state["power"] += 1
            self.log.add(f"Your command of {spell.name} deepens.")
        magic.resolve(self, spell, direction, state["power"])
        return True

    def _spell_cost(self, spell, state) -> int:
        cost = spell.pp * self.pc.spell_cost_mult
        eff = self.pc.sign.effects
        if spell.element == "fire":
            cost *= eff.get("fire_spell_cost_mult", 1.0)
        if spell.kind in ("bolt", "ball"):
            cost *= eff.get("combat_spell_cost_mult", 1.0)
        cost *= eff.get("neutral_spell_cost_mult", 1.0)
        # Cost climbs as a spell's remaining knowledge dwindles (§8.2).
        cost *= 1 + max(0, 20 - state["castings"]) * 0.05
        return max(1, round(cost))

    def equip_item(self, item) -> bool:
        if item is None:
            return False
        ok, displaced, msg = self.pc.equipment.equip(item)
        self.log.add(msg)
        if ok:
            self.pc.inventory.remove(item)
            if displaced is not None:
                self.pc.inventory.add(displaced)
            self.pc.refresh_combat()   # weapon change updates proficiency too
            self.pc.update_encumbrance()
        return ok

    def unequip_slot(self, slot) -> bool:
        ok, item, msg = self.pc.equipment.unequip(slot)
        self.log.add(msg)
        if ok:
            self.pc.inventory.add(item)
            self.pc.refresh_combat()
            self.pc.update_encumbrance()
        return ok

    def drop_item(self, item) -> bool:
        if item is None:
            return False
        removed = self.pc.inventory.remove(item)
        if removed is None:
            return False
        self.levels[self.depth].add_item(self.pc.actor.x, self.pc.actor.y, removed)
        self.pc.update_encumbrance()
        self.log.add(f"You drop {self.id_service.display_name(removed)}.")
        return True

    def _move_or_attack(self, pc, level, dx, dy) -> bool:
        if dx == 0 and dy == 0:
            return True  # wait a turn
        nx, ny = pc.x + dx, pc.y + dy
        target = level.actor_at(nx, ny)
        if target is not None and target is not pc and target.is_alive:
            result = combat.melee_attack(pc, target, self.rng)
            self.log.add(result.message)
            if result.hit:
                self._train_weapon(pc)
            if result.killed:
                self._reward_kill(target)
            return True
        if level.tile(nx, ny) is tiles.DOOR_CLOSED:
            level.open_door(nx, ny)
            self.log.add("You open the door.")
            return True
        if level.is_walkable(nx, ny):
            pc.x, pc.y = nx, ny
            if level.tile(nx, ny) is tiles.GATE:
                self._try_seal_gate(level)
            else:
                self._describe_floor(level, nx, ny)
            return True
        self.log.add("There's a wall in the way.")
        return False

    def _try_seal_gate(self, level) -> None:
        """Reaching the Gate ends the game — a win if the guardian is dead."""
        if level.boss is not None and level.boss.is_alive:
            self.log.add(world.gate_blocked_line())
            return
        for line in world.victory_lines(self.pc.actor.name):
            self.log.add(line)
        self.won = True
        self.save.on_death(self.pc.actor.name)   # run complete (permadeath)
        self.running = False

    def _describe_floor(self, level, x, y) -> None:
        t = level.tile(x, y)
        pile = level.items_at(x, y)
        if t in (tiles.STAIRS_DOWN, tiles.STAIRS_UP, tiles.ALTAR,
                 tiles.FORGE, tiles.HERB_BUSH):
            self.log.add(f"There is {_article(t.name)} here.")
        if pile:
            names = ", ".join(self.id_service.display_name(i) for i in pile)
            self.log.add(f"You see here: {names}.")

    def _descend(self) -> bool:
        level = self.levels[self.depth]
        if level.tile(self.pc.actor.x, self.pc.actor.y) is not tiles.STAIRS_DOWN:
            self.log.add("There are no stairs down here.")
            return False
        level.remove_actor(self.pc.actor)
        self._enter_level(self.depth + 1, going_down=True)
        self._schedule_all()
        self._update_fov()
        self.log.add(f"You descend to dungeon level {self.depth}.")
        return True

    def _ascend(self) -> bool:
        level = self.levels[self.depth]
        if level.tile(self.pc.actor.x, self.pc.actor.y) is not tiles.STAIRS_UP:
            self.log.add("There are no stairs up here.")
            return False
        if self.depth <= 1:
            self.log.add("You look up toward daylight — but the Gate below "
                         "still stands open. Your task is down, not out.")
            return False
        level.remove_actor(self.pc.actor)
        self._enter_level(self.depth - 1, going_down=False)
        self._schedule_all()
        self._update_fov()
        self.log.add(f"You climb up to dungeon level {self.depth}.")
        return True

    def _monster_act(self, monster, level) -> None:
        result = ai.monster_turn(monster, self.pc.actor, level, self.rng)
        if result is not None and result.message:
            self.log.add(result.message)
        # A corrupting blow feeds the Hollowing (§9.1, §12.2).
        if result is not None and result.hit and self.pc.actor.is_alive:
            from .content.monsters import MONSTERS
            mdef = MONSTERS.get(monster.monster_id)
            if mdef is not None and "corrupting" in mdef.abilities:
                # 15 points per blow: three hits from the hollowed cost a
                # third of a Warp — scary, but it doesn't dwarf the ambient
                # clock the way the old 35 did.
                events = self.blight.add_blight(self.pc, 15)
                self.pc.refresh_combat()
                for event in events:
                    self.log.add(event.message)
                    if event.kind == "consumed":
                        self._on_hollowed()

    def _reward_kill(self, target) -> None:
        from .content.monsters import MONSTERS
        mdef = MONSTERS.get(target.monster_id)
        xp = mdef.xp_value if mdef else 5
        # XP scales with relative speed (§6.1) and with depth — deep spawns
        # are tougher (DV scaling), so they pay accordingly. This keeps the
        # hero's level curve in step with the descent.
        xp = int(xp * (target.speed / max(1, self.pc.actor.speed))
                 * (1 + 0.15 * self.depth))
        self.pc.note_kill(target.monster_id)
        for msg in self.pc.award_xp(max(1, xp)):
            self.log.add(msg)
        self.scheduler.remove(target)
        level = self.levels[self.depth]
        level.remove_actor(target)
        if target is level.boss:   # the guardian falls (§14)
            for line in world.boss_slain_lines():
                self.log.add(line)

    def _train_weapon(self, pc_actor) -> None:
        """Award weapon-proficiency marks (and train combat skills) on a hit."""
        category = self.pc.proficiencies.category_of(self.pc)
        msg = self.pc.proficiencies.award(self.pc, category)
        trained = skills.train_on_use(self.pc, self.rng)
        if msg or trained:
            self.pc.refresh_combat()
        if msg:
            self.log.add(msg)

    def _advance_regen(self) -> None:
        regen.advance_regen(self.pc)

    def _advance_blight(self) -> None:
        """Accrue the Hollowing for this turn and surface any Warps (§9)."""
        events = self.blight.on_turn(self.pc, self.depth)
        if events:
            self.pc.refresh_combat()   # Warps changed attributes
        for event in events:
            self.log.add(event.message)
            if event.kind == "consumed":
                self._on_hollowed()

    def _on_hollowed(self) -> None:
        self.log.add("*** CLAIMED BY THE HOLLOWING — the save is erased. ***")
        self.pc.actor.alive = False
        self.save.on_death(self.pc.actor.name)
        self.running = False

    def _on_death(self) -> None:
        for line in world.death_epitaph(self.pc.actor.name, self.depth):
            self.log.add(line)
        self.log.add("*** PERMADEATH — the save is erased. ***")
        self.save.on_death(self.pc.actor.name)
        self.running = False

    # -- perception -------------------------------------------------------
    def _update_fov(self) -> None:
        level = self.levels[self.depth]
        pc = self.pc.actor
        radius = sight_radius(self.calendar, pc.attributes.Pe)
        if pc.night_vision:
            radius = max(radius, 6)   # voidsight Warp pierces the dark
        self.visible = compute_fov(level, pc.x, pc.y, radius)
        for (x, y) in self.visible:
            level.explored[y][x] = True

    def _visible_to_player(self, actor) -> bool:
        return (actor.x, actor.y) in self.visible


def _article(name: str) -> str:
    return ("an " if name[:1] in "aeiou" else "a ") + name
