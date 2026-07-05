# ADOM — Complete Design & Implementation Plan

*A build-oriented specification for reconstructing Ancient Domains of Mystery (Thomas Biskup). Synthesized from the ADOM Wiki (ancardia.fandom.com), the ADOM Manual, and community guidebooks. Values reflect the 1.x / 3.x "Deluxe" era and may vary by patch.*

> **Scope note.** This document specifies every *system, formula, and data model* needed to build a near-duplicate, plus representative data for each content type. ADOM's full content is enormous (600+ monsters, hundreds of items, ~50 artifacts, dozens of spells). Where a list is too large to inline, the exact wiki page to mine is named. Build the engine and schemas from this doc; pour the exhaustive rows in from the wiki tables. Every number here is a target, not gospel — verify against the wiki page cited in each section as you implement.

---

# PART I — FOUNDATIONS

## 1. Overview

- **Genre:** single-character, turn-based, grid roguelike with permadeath and procedural generation.
- **Premise:** the world of **Ancardia** is invaded by **Chaos** through a **Chaos Gate** in the **Drakalor Chain**, opened by the Elder Chaos God **Andor Drakon**. The sage **Khelavaster** found it, failed to close it, and vanished. The player is one of countless heroes who enter the Chain to end the invasion.
- **Objective tiers:** close the Gate (standard win) → ultra endings (ascend as a demigod) → become a (Ultimate) Chaos God.
- **Signature mechanic:** **Corruption** — a slow, near-irreversible mutation toward a nonstandard game-over that punishes dawdling.

## 2. Design Pillars (build priorities)

1. **Permadeath consequence** — one life, one save, deleted on load; every decision is committed.
2. **Corruption pressure clock** — forbids infinite grinding; forces forward momentum.
3. **Divine economy** — alignment + piety + altars + crowning form a second progression track.
4. **Combinatorial builds** — 12 races × 22 classes × 12 star signs × talents × attribute allocation.
5. **Hand-authored world over procedural levels** — fixed sites and NPCs; randomized interiors.
6. **Emergent, light story** — a skeleton the player fills in.

## 3. Core Engine Architecture

### 3.1 Turn / time model (energy system)
ADOM is not round-based; it is **energy/speed-based**.
- Each actor has a **speed** stat. Base normal speed = **100**.
- Actions cost **energy points (EP)**; the standard move/attack costs **1000 EP** (some class powers cost 2500–3500 EP; some are cheaper).
- Each "tick", every actor accrues EP equal to its speed. When an actor has ≥ the cost of its chosen action, it acts and the cost is deducted.
- Net effect: at speed 200 you act twice as often as at speed 100. Speed is therefore one of the most valuable stats in the game (Raven star sign +10, Ring of the Master Cat +16, Boots of Great Speed, Athletics +8 at skill 100).
- **Implementation:** a priority queue / min-heap of actors keyed by "time of next action" (or an incremental EP accumulator loop). Do **not** use a fixed round loop.
- **Wilderness (overworld) movement** uses a much larger base cost (~1000 EP per overworld step, modified by terrain, seven-league boots, etc.).

### 3.2 RNG & dice
- Uses standard dice notation `XdY(+Z)`. Provide a seedable RNG and a `Roll(dice)` helper. `Rnd(n)` = uniform 1..n as used in skill formulas below.
- Damage/effect formulas frequently use `M{a,b}` = max(a,b) and attribute-derived terms. Support these as first-class expression nodes.

### 3.3 Permadeath & saves
- **One canonical save per character.** On load, the save is **deleted**; the game re-saves on quit. Death = save erased, run over.
- Config toggles can disable permadeath (see §5.7). Keep permadeath enforcement in a single save-service gated by that flag.

### 3.4 Monster memory
- Persistent per-*character* (not per-player) knowledge record for each monster type: accumulates observed HP, XP value, speed, special abilities, resistances as the PC kills more of that type. Surface it in a bestiary UI. Store as `Dictionary<MonsterTypeId, MemoryRecord>` on the character.

---

# PART II — THE WORLD

## 4. World & Map Model

### 4.1 Geography
- The game world is the **Drakalor Chain**: a mountain-ringed valley, entered via a pass in the NE corner (the PC's start). All play happens here except the Chaos Plane (ultra endings).
- **Overworld (wilderness):** a tiled map connecting all sites. Movement consumes time/food. **Sight range depends on time of day**: full by day (≈06:00–20:00), reduced to ~2 tiles on the overworld / ~5 in wilderness at night; further modified by Perception, torches, Farsight, terrain.
- Some dungeons spawn in the NW and require a **climbing set** to reach.

### 4.2 Calendar & time
- 360-day year, **12 months of 30 days**, each named for a **star sign**. The game begins on day 1 of the month of the **Unicorn**. Track Ancardian month/day/hour; expose via a status command. Day/date/birthday produce minor luck and stat effects.

### 4.3 Level generation
- **Two site classes:**
  - **Fixed sites** (towns, story dungeons): hand-authored layouts, fixed NPCs and features, fixed depth/role.
  - **Random dungeons**: fixed *depth bands and difficulty* but randomized overworld placement and randomized interior each generation. Once generated, a level is **persistent** for the rest of the game (except the Infinite Dungeon, which regenerates each entry).
- **Dungeon level (DL)** drives monster/item danger. Item and monster spawn tables are keyed to DL.
- **Level features** injected by generator: rooms, corridors, caverns, water, lava, **altars**, **forges**, **herb bushes**, shops, traps, stairs, special vaults.
- **Cavernous levels** favor high monster generation (good for altar farming).

### 4.4 Locations catalog (build the world graph from this)
**Towns / hubs**
- **Terinyo** — start village; quest-givers (elder **Rynt**, druid **Guth'Alak**, sheriff **Tywat Pare**), food shop, the fool **Yggaz**. No hostiles.
- **Lawenilothehl** (Outlaw/"BVL") — general shop, key salesman **Yergius** (thief trainer/guild), beggars.
- **Dwarftown** — pivotal mid-game hub; ruled by **Thrundarr** (main quest-giver); shopkeeper **Waldenbrook**; altar; smith; Arena. Sells nearly everything.
- **High Mountain Village (HMV)** — reached via the Small Cave/UD; shop; ratling guardians.
- **Borderland Settlement** — has an altar useful for sacrifices.

**Early dungeons**
- **Small Cave (SMC)** — tutorial-ish; leads to UD/HMV; monsters ~2× your level; guaranteed waterproof blanket.
- **Unremarkable Cave (UCa)** — easy 3 levels, sometimes altars.
- **Village Dungeon (VD, 7 levels)** — healer **Jharod** (VD:4), mad carpenter **Yrrigs** (VD:7).
- **Druid Dungeon (DD, 7 levels)** — black druid **Keethrax** (DD:7).
- **Puppy Cave / "doggie" quest cave** — often a vault; corpse retrieval quest.
- **Infinite Dungeon (ID)** — arbitrarily deep, regenerates each entry; safe grinding, poor loot.

**Mid/late & special zones**
- **Pyramid** (mummy lord, Ankh, wrappings), **Tomb of the High Kings** (Ring of the High Kings; no-teleport), **Darkforge** (Kherab; shield of raw steel; wand of teleportation), **Tower of Eternal Flames (ToEF)** — *mandatory*, holds the **Fire Orb**; **Ice Queen Domain**, **Rift** (needs Climbing 100 + Willpower; water-breathing item), **Assassins' Guild** (no-teleport), **Casino** (biggest item source), **Library of Nilthrias** (spellbooks; corruption cure), **Minotaur Maze** (7 levels, traps, false levels), **Quickling Tree** (needs 2 specific corruptions; Boots of Great Speed), **Ultimate Dungeon** (endgame; Ultimate Balor; Scroll of Omnipotence).

**Caverns of Chaos (CoC)** — the spine. See §13.4.

---

# PART III — THE CHARACTER

## 5. Character Model

### 5.1 Attributes (9)
`Strength (St), Learning (Le), Willpower (Wi), Dexterity (Dx), Toughness (To), Charisma (Ch), Appearance (Ap), Mana (Ma), Perception (Pe).`

**Mechanics**
- Each attribute has: **base value**, a hidden **potential** (hard cap for training; modified values may exceed potential via boosts), and **modified/total value** = base + semi-permanent modifiers (equipment, corruptions, orc daylight penalty) + temporary boosts. Modified value clamps to **1–99**.
- **Training/abuse:** actions raise/lower a hidden training counter; the game periodically rolls to raise/lower the base. Herbs (morgia → To/Wi/Dx; moss of mareilon → St; etc.) are the reliable herb-based trainers; **Garth** in Dwarftown trains via gold.
- **Potentials** are set at creation (point-buy sets a floor ≥1 above the bought value) and can be raised by potions of potential / gain attributes.
- 10 = average. Most breakpoints land by ~30–32; mid-30s+ only matters in the very late game.

**Key thresholds / effects (implement as rules):**
| Attribute | Primary effects | Notable breakpoints |
|---|---|---|
| Strength | melee damage, carry capacity, kicking | high St needed for heavy armor/carry |
| Toughness | **max HP** (biggest driver), bonus PV `(To-18)/2` capped +20 | herb-train to ~24–26 early |
| Dexterity | DV `(Dx-12)/2 + (Dx-9)/2`, to-hit, missiles, #attacks | ranged builds want high |
| Learning | spell learning, **skill gain rate**, XP bonus `+Le/1000 per xp` | 10 → Literacy; 15/20 → extra skill increases |
| Willpower | spell/mindcraft power, HP/PP, resist confusion/paralysis, **ball-spell diameter** `Wi/8` | 32→diameter 4, 48→6, 64→8 |
| Mana | **max PP** (biggest driver), resist drain | ≥6 PP-gain threshold; **≥18 → bonus talent** |
| Perception | sight range, wand charge visibility, traps | 6 → see wand charges; 10 → vision |
| Charisma | shop prices, companion orders | mostly a dump stat |
| Appearance | women's shop discount, reduces corruption gain / boosts corruption *removal* | mostly a dump stat |

### 5.2 Races (12)
Race sets: **level-up XP multiplier, max age (aging-attack vulnerability), HP & PP regen rates, starting alignment, attribute modifiers & potentials, starting skills/equipment, shop relations, food quirks, unique abilities.**

**XP multipliers** (higher = slower leveling): Gnome ×0.75, Hurthling ×0.8, Human ×0.86, others ~×1.0, **Troll ×2.5**.

| Race | Cost* | Attr tendencies | Lifespan | Regen | Signature traits |
|---|---|---|---|---|---|
| **Human** | 0 | balanced, fast learner | 50–120y | avg/avg | jack-of-all-trades; good shop relations |
| **Troll** | high | +++St/To, ---Le/Ma/Wi | short | **fastest HP**, poor PP | strongest/toughest; ×2.5 XP; starts 2H weapons L2; illiterate barbarians |
| **High Elf** | mid | +Le/Ma/Dx, -To | ~1000y | slow HP, **fast PP** | great casters/archers; good starting elven gear |
| **Gray Elf** | high | ++Le/Ma, --To | longest | slow HP, fast PP | best mana-wielders; snobbish shop relations |
| **Dark Elf** | mid | +Dx/Ma, -To | ~1200y | slow HP, fast PP | starts Alertness; hand crossbow; hated by dwarves; spider affinity (eats spider corpses) |
| **Mist Elf** | highest | ++Ma, very frail | very long | fast PP | expert-only; unique crowning gift (Staff of Creation); shopkeepers hate them |
| **Dwarf** | mid | +To/St, -Dx | ~150y | avg | **Mithril Skin** talent (+3 PV, dwarf-only); finds secret doors; gods love gold → fast piety; guaranteed dwarf shopkeeper |
| **Gnome** | low | +Dx/Le | long | avg | ×0.75 XP; faster crossbow marks; toughness edge over elves |
| **Hurthling** | low | +Dx, -St | mid-long | avg | starts thrown-rock/club L4; **cooked-food sacrifice bonus** (fast piety); cursed starting ring; shoe penalty (-Dx); ⅔ marks for slings/thrown |
| **Orc** | low | +St/To, -Le/Ma | 36–47y (short!) | +HP, -PP | daylight Dx penalty; bad shop prices from dwarves/elves; aging kills them fast |
| **Drakeling** | mid | balanced, +To | mid | avg | **acid spit** (ranged, scales w/ level); heat problems in ToEF |
| **Ratling** | mid | +Dx | mid-long | HP ~1/35t, PP ~1/55t | sociable → good trades; hated by mist elves/drakelings |

*Cost = relative "expense"/power in char-gen point terms (flavor guidance).

All PCs start with **Climbing, First Aid, Haggling, Listening**; plus **Literacy** if not Barbarian/Beastfighter and Le ≥ 10. Pull exact per-race attribute modifier tables and starting skill/equipment lists from the wiki **Races** pages.

### 5.3 Classes (22)
`Fighter, Paladin, Ranger, Thief, Assassin, Wizard, Priest, Bard, Monk, Healer, Weaponsmith, Archer, Merchant, Farmer, Mindcrafter, Barbarian, Druid, Necromancer, Elementalist, Beastfighter, Duelist, Chaos Knight.`

Class sets: **starting skills, starting piety** (Druid/Priest 1500, Paladin 1200, others 200), **starting alignment tendencies, spellcasting aptitude, melee/ranged to-hit progression, weapon-mark rate, item/spellbook drop rates, and 7 class powers.**

**Class powers** unlock at **levels 6, 12, 18, 25, 32, 40, 50** — a fixed set per class (only Bard's are randomized). Types: one-time bonus, per-level recurring bonus, permanent passive/intrinsic, or an activatable ability (often high-EP). Examples to model the system:

- **Weaponsmith:** L6 melt metal → ingots; L12 forge 4× faster; L18 +4 St; L25 auto-recognize metals; (higher) further smithing mastery.
- **Mindcrafter:** L6 fast confusion recovery; L12 sense enemy count on level; L18 +1d6 PP/level; L25 +5 Wi; L32 block some Chaos corruption; L40 +3d5 PP/level (cumulative); L50 halve undead-contact damage.
- **Monk:** L6 circular kick (2500 EP); scaling unarmed AC (DV `+lvl*2/3` unarmored); L32 power doesn't affect large monsters.
- **Healer:** doubles then triples HP regeneration at L6/L12; extremely resilient.
- **Necromancer:** Shadow Touch (drain HP, else PP, unarmed; pulls alignment chaotic); can command undead; guaranteed to find every spellbook (incl. Wish).
- **Merchant:** specializes in one item class (potions/rings/scrolls/wands) → auto-IDs that class on sight; throws gold as missiles (only way to missile doppelgangers).
- **Priest:** starts Detect Item Status (auto-BUC); strong clerical casting; easy deity.
- **Chaos Knight:** starts chaotic + 3 random corruptions + high-PV chaos armor; *thrives on* corruption; changing alignment inflicts ongoing damage; unique NPC dialogue; unique chaos-god ending.

Class archetype roles (for balance): full arcane (Wizard/Necromancer/Elementalist), full clerical (Priest/Druid), hybrid divine-warrior (Paladin), ranged (Archer/Ranger), pure melee (Fighter/Barbarian/Duelist/Healer), unarmed (Monk/Beastfighter), skill/utility & hard-mode (Thief/Assassin/Bard/Merchant/Farmer/Weaponsmith/Mindcrafter), challenge (Chaos Knight). Pull each class's exact starting-skill set and full class-power list from the wiki **Class power** and per-class pages.

### 5.4 Star signs (12)
Assigned by birthday (choosable in paid versions). The month of your sign slightly favors you; you're extra-lucky on your birthday. Order by month:

| Month | Sign | Themes / representative effect |
|---|---|---|
| 1 | **Raven** | +10 Speed, +2 Pe, stronger companions, faster messengers, harder to trick |
| 2 | **Book** | +3 Le, +500 initial alignment (lawful lean), +1 free skill/level, better spell learning |
| 3 | **Wand** | neutral-magic lean, spells 10% cheaper (neutral casters), leadership |
| 4 | **Unicorn** | grace/purity; **corruption modifier** (−19% at L, −37% at L+, +30% at C−); widely considered weak |
| 5 | **Salamander** | **fire immunity** + 50% extra cold damage; fire magic cheaper; great for casters |
| 6 | **Dragon** | combat magic 10% cheaper; ferocity/combat lean |
| 7 | **Sword** | −20% melee weapon-mark cost; combat/tactics |
| 8 | **Falcon** | grants **Survival** + a **free talent**; nobility |
| 9 | **Cup** | good general skillset boosts |
| 10 | **Candle** | **strong HP regen** + a **free talent**; beginner-recommended |
| 11 | **Wolf** | +Wi lean |
| 12 | **Tree** | **+PV, +To, +Wi (large)** — early-survival powerhouse |

(Candle, Raven, Tree are generally strongest; Salamander for casters.) Pull exact numeric effects per sign from the wiki **Star sign** pages.

### 5.5 Talents
- Chosen at creation and periodically on level-up; form **dependency chains** (a talent may require an attribute, a prior talent, or a skill).
- **Key lines to implement first:**
  - **Aura chain:** Potent → Strong → Mighty aura (unlocks caster talents).
  - **Learner chain:** Good Learner (+8% XP, Le 10) → Great Learner (+15% XP, Le 16).
  - **Book learner/caster** chains (cheaper/better book casting).
  - **Candle** (HP regen), **Tree** (+1 PV, +2 To, +5 Wi), **Tough**, **Very/Extremely Hardy** (HP).
  - **Heir** line (Charming → Boon to the Family → Heir): grants a class-specific **Heir gift** item (huge for Bard/Thief/Monk/Healer/Beastfighter).
  - **Melee Weapon Master** (deep, late), **Treasure Hunter** (Alert → …), **Silver Tongue** (−20% shop prices), **Mithril Skin** (dwarf-only, +3 PV).
- Model talents as data: `{ id, name, requirements[], effects[], line, tier }`. Pull the full talent tree from the wiki **Talents** page.

### 5.6 Gender, age, cosmetics
- **Gender:** men +1 St; women +1 Dx and up to 50% shop discount (scales with Appearance). Also affects some flavor.
- **Age** (race-dependent range) modifies starting attributes and sets aging-attack vulnerability. Cosmetics (hair/eyes/complexion/height) are flavor; **weight** has tiny effects (Quickling Tree entry, ice-breaking).

### 5.7 Character creation flow & difficulty config
Order: **Race → Class → Gender → Star Sign → Attributes → Talents → Name.** Age/history/birth-messages auto-generated.
- **Attribute entry:** point-buy (Deluxe) *or* the classic "opening question" system (answer scenario questions that nudge stats). Point-buy: each attribute has a per-point cost (Mana costs 4/pt); min/max from race×class×sign×gender×age.
- **Config toggles:** Disable Corruption, Disable Hunger, Monster Lethality (scaler), Disable Permadeath, Treasure Rate. Gate the corresponding subsystems behind these flags.

---

# PART IV — PROGRESSION

## 6. Experience, Skills, Weapon Marks

### 6.1 Experience & leveling
- Kills grant XP; **XP to next level** scales by race×class multipliers.
- **XP per kill** depends on relative speed: `Exp = base_exp * (monster_speed / PC_speed)` — so slowing yourself or speeding the enemy before the kill nets more XP.
- **Learning bonus:** `+Le/1000` bonus XP per XP gained; Good/Great Learner talents add more.
- On level-up: raise HP/PP (race/class/To/Ma driven), gain class powers at the 7 breakpoints, and pick skill increases (≥3 skills, more with high Le / Book sign).

### 6.2 Skills (45)
All PCs get **Climbing, First Aid, Haggling, Listening** (+Literacy conditionally). Skills advance **passively on use** and **actively on level-up**. A skill has a **level (0–100)** and a **potential cap**; **Yergius/Garth-style training** can raise the cap and the dice/rate. The **80/100 rule** doubles/triples check attempts at skill 80/100. Wishable except **Alertness** and **Healing** (wishing those instead gives Perception / full heal).

**Full skill list & function (implement each as a check or passive):**
Alchemy (brew potions; 1 recipe/10 pts, gain-attributes at 100), Alertness (dodge combat magic; +DV +1/+2/+4 at 75/90/100; sense traps/invisible), Appraising (rough item value), Archery (missile to-hit/damage), Athletics (+speed, up to +8 at 100), Backstabbing (bonus vs unaware; huge with invisibility), Bridge Building, Climbing (100 needed for the Rift), Concentration (spell casting; regen PP; get to 100 for casters), Cooking (preserve/cook corpses; doubles sacrifice value), Courage, Detect Item Status (auto-BUC), Detect Traps, Disarm Traps, Dodge (+DV), Find Weakness (crit chance), First Aid (stop bleeding, minor heal), Fletchery (make ammo), Food Preservation, Gardening (grow herbs), Gemology, Haggling (shop discount), **Healing** (HP regen + First-Aid-like; near-mandatory), Herbalism (safe herb picking; blessed herbs; herb-train stats), Law (identify lawful/chaotic acts), Listening (detect nearby monsters; trains Pe), Literacy (read scrolls/books), Metallurgy, Mining (dig), Music (bard; taming), Necromancy (undead; trains Mana), Pick Locks, Pick Pockets, Smithing (improve gear at forges), Stealth, Survival (food in wilderness), Swimming, Tactics (combat stance depth), Two-Weapon Combat, Ventriloquism (confuse single monster w/o alerting others — great vs shopkeepers), Woodcraft (fell trees faster).

**Starting-skill formulas** (representative — cumulative across race+class): `Climbing = Rnd(Dx)+Rnd(10)+20`, `First Aid = Rnd(Le)+Rnd(10)+15`, `Haggling = Rnd(Ch)+Rnd(10)+15`, `Listening = Rnd(Pe)+Rnd(10)+20`, `Literacy ≈ Le*4` (if eligible). Each class supplies its own set (e.g. Healer: `Healing = Rnd(30)+50`, `Herbalism = Rnd(40)+40`, `First Aid = Rnd(30)+40`, `Literacy = Rnd(50)+50`). **Skill cost model:** base cost reduced ~50% by race/class aptitude (both = even cheaper "double-trained"); cost rises with skill level and if skill ≫ character level. Pull the complete class×skill starting matrix and per-skill detail from the wiki **Skill** / darktwinge skill dump.

### 6.3 Weapon marks (weapon skills)
- Separate from general skills: proficiency per **weapon category** (swords, axes, polearms, whips, daggers, staves, 2-handed, unarmed; plus missile categories: bows, crossbows, slings, thrown rocks, thrown, etc.).
- Accrue **marks** by using that category; at thresholds you advance a **weapon skill level** (better to-hit, damage, DV, and **extra attacks**). Some races/classes need fewer marks (Gnome crossbow ¾, Hurthling slings/thrown ⅔, Sword sign −20% melee marks).
- **Tactics** setting (very defensive → berserk) shifts the DV/to-hit tradeoff and interacts with marks.

---

# PART V — COMBAT

## 7. Combat System

### 7.1 Resolution order per attack
1. Determine attacker action & **EP** availability (§3.1).
2. **To-hit** roll: attacker's melee/missile bonus (level progression + weapon skill + Dx + St + tactics + item bonuses) vs defender **DV**.
3. If hit, **PV** reduces damage; roll damage dice (weapon `XdY` + St bonus + weapon-skill + slaying/elemental + criticals).
4. Apply special on-hit effects (poison, drain, corruption, elemental, etc.).

### 7.2 Defensive values (formulas)
- **DV (avoid):** driven by Dx: `DV += (Dx-12)/2 + (Dx-9)/2`; −3 if Drunk; +shield/armor DV; +Dodge; +Alertness (1/2/4 at 75/90/100); +Tactics (defensive); Monk unarmored `+lvl*2/3`, Beastfighter `+lvl/3`; Mindcrafter Mental Shield `+(Level+Wi)/5`; +invisibility; ~half DV bonus when wielding staves.
- **PV (soak):** driven by To: `PV += (To-18)/2` (max +20); +1 if Blessed (level-scaled: +2 at L25, +3 at L50); +armor PV; Dwarf Mithril Skin +3; purity items. At PV < 4, kicking walls/statues hurts.

### 7.3 Damage, criticals, tactics
- Base weapon damage `XdY` + strength bonus + weapon-skill bonus. **Find Weakness** and certain items/rings raise crit rate; **Slaying** weapons auto-crit a monster type.
- **Tactics** slider (Coward … Normal … Berserk) trades to-hit/damage against DV — expose as a runtime setting.

### 7.4 Attack modes
- **Melee:** 1H/2H; **Two-Weapon Combat** for dual-wield (penalties reduced by skill).
- **Missile:** requires ammo & launcher (bow/crossbow/sling) or thrown; Archery skill + Dx + Perception. Always keep a ranged option.
- **Unarmed:** Monks/Beastfighters scale hugely; thorns/hooves corruptions add unarmed damage.

### 7.5 Elements, resistances, immunities
- Damage types: **fire, cold, shock/lightning, acid, poison**, plus physical, and special (death ray, petrification, paralysis, aging, stat-drain).
- **Resistance ≠ immunity:** resistance reduces damage; a Death Ray while merely resistant still hurts. Two resistances = immunities in effect (**petrification, sleep**).
- Intrinsics gained from **eating corpses** (e.g., fire beetle 50% → fire resist; red dragon/wyrm → guaranteed fire resist), items, pools, or **crowning** (permanent elemental immunity). Fire vs cold-based creatures and undead is a key tactical axis.

---

# PART VI — MAGIC

## 8. Magic System

### 8.1 Two traditions, one engine
- **Arcane** (Wizard/Necromancer/Elementalist) and **Clerical** (Priest/Druid/Paladin) cast the *same* spells under different names (e.g., Magic Missile = "Minor Punishment"; Lightning Bolt = "Divine Wrath"). Same effects, different flavor + drop-table bias.
- All magic is fueled by **mana** (the attribute) → **Power Points (PP)**. Max PP driven mainly by Mana, plus Willpower, race, class, level.

### 8.2 Spell knowledge & spell power
- **Spell Knowledge** = number of remaining castings for a spell. Each cast decreases it; at 0 you can't cast until you re-read a spellbook. **PP cost rises as knowledge drops** (noticeable below ~100, steep below ~20).
- **Spell Power** (effectiveness) increases the more you cast a spell; casting X times → +1 power.
- **Learning** from books: success depends on Le, Concentration, class aptitude, Book sign, Book-learner talents. **Failure effects** (weighted by class; casters rarely suffer): status (blind/confused/stunned), HP loss up to base cost, forced teleport (or confusion), −1 To, pit opens under you, or the **spellbook explodes** (fire damage).

### 8.3 Spell list (base PP cost, reading turns)
Bolt spells fire in 8 directions (some **bounce** off walls; can hit you). Ball spells hit an area; diameter from `Wi/8`. Touch spells target adjacent/self.

| Spell (arcane) | PP | Notes |
|---|---|---|
| Light | 3 | utility |
| Darkness | 4 | utility |
| Cure Light Wounds | 5 | most PP-efficient heal |
| Slow Poison | 6 | |
| Slow Monster | 7 | debuff |
| Bless | 8 | buff (damages undead) |
| Burning Hands | 8 | short-range fire |
| Calm Monster | 8 | |
| Cure Disease | 8 | |
| Destroy Undead | 8 | |
| Magic Lock | 8 | |
| **Magic Missile** | 8 | **bounces; nothing resists it; won't destroy floor items** |
| Stun Ray | 8 | |
| Cure Serious Wounds | 10 | |
| Disarm Trap | 10 | |
| **Fire Bolt** | 10 | special dmg vs ice/water; can cook corpses |
| Invisibility | 10 | buff |
| Know Alignment | 10 | |
| Neutralize Poison | 10 | |
| Strength of Atlas | 10 | carry buff |
| **Frost Bolt** | 12 | special dmg vs fire; freezes water → ice bridge |
| Knock | 12 | |
| Lightning Bolt | 12 | bounces |
| … | … | Acid Bolt, Acid Ball, Fireball, **Improved Fireball** (thrown like a missile), Ice Ball/Lightning Ball, Web, Petrification, Death Ray, Teleport, Teleport Control, Farsight, Magic Map, Identify/Greater Identify, Remove Curse (50 PP), Heal, Create Item, Summon Monsters, Mystic Shovel, Revelation, **Wish** (extremely expensive; drains a random stat −10) |

Pull the complete spell table with exact damage dice, radius formulas, and clerical names from the wiki **Spells** page.

### 8.4 Cost modifiers
- Cheaper: Wizard/Priest class powers, Silvernight (alignment day), Dragon sign (combat magic −10%), Salamander (fire −20%), Wand (all −10% for neutral casters), Mana-battery corruption (−20% teleport). Costlier: low spell knowledge, high DL/corruption (teleport).

### 8.5 Mindcraft (Mindcrafter's psionics)
- A separate, PP-like resource path keyed to **Willpower**; no spellbooks — abilities unlock via class powers/levels. Powers: Confusion Blast/Wave, Mind Blast/Wave/Greater, Telekinetic Blast/Greater, Mental Shield (+DV), Eyes of the Mind, Regeneration, Teleport Self/Other, Greater Mental Wave. Effective vs most living things (undead/constructs resist).

---

# PART VII — CHAOS & THE DIVINE

## 9. Corruption System (signature)

### 9.1 Sources
Being hit by a chaos creature's **corrupting attack**, corruption **traps**, eating **corrupted corpses**, drinking **potion of raw chaos**, using a **staff of corruption dissemination**, carrying/equipping **chaos artifacts**, and **background corruption** (proximity to the Gate).

### 9.2 Background corruption model
- Begins below **CoC D:9** (and most DL ≥ 10 levels). Roughly every few turns (more often deeper) the PC gains **1 corruption point (CP)**, adjusted by Appearance and other factors. At **D:45+** the PC gains **3 CP** at a time. Accumulated CP crossing thresholds → a **new corruption** (mutation).
- **Alignment modifies rate:** L+ slower, N= medium, C− faster. **Doomed** increases the rate. **Purity items** (bracers/robe of purity; artifacts like Aylas Holy Scarf) reduce/eliminate background corruption (protection level 5+ ≈ immune, except Chaos Plane / special caves). Salamander/Unicorn/Appearance modifiers apply.

### 9.3 Corruption effects
~18 progressive corruption "stages"; each mutation has stat and ability effects, often mixed. Beyond certain **counts**, aggregate bonuses to St/Dx/To/Ma and a **Willpower penalty** apply (scaled by alignment). Representative corruptions (implement as a weighted table; each is a data record with modifiers + special behavior):

| Corruption | Effect |
|---|---|
| Tough scales | PV +8, Dx −6, Ap −4 |
| 12 eyes | Pe +6, Ap −6 |
| Exhale sulphur | Ch −4; gain **acid spit** |
| Apish (cumulative) | St +3, Le −1, Wi −1, Ch −2, Ap −3 — recurs & stacks over time |
| Fast-healing tissue | improved regeneration |
| Thorns | 3d3 unarmed dmg, Dx −2, Ap −3 |
| Hooves | +8 kick dmg, Dx −6 |
| **Poison Hands** | poison foes in melee, **but** food you touch → cursed, potions → poison (negate with thick gauntlets) |
| **Mana battery** | wands you touch drain to 0 (raises Mana); teleport −20% |
| Very light | 1/10 weight, St −6, To −6, Dx +4, Ap −6 *(Quickling Tree key #1)* |
| Extremely thin | 1/2 weight, DV +6 *(Quickling Tree key #2)* |
| … | plus antennae, tail, teeth/claws, unholy aura (terror), see-in-dark, water breathing, chaotic speech, etc. |

**End state:** enough corruptions → "**writhing mass of primal chaos**" → nonstandard game-over. (The chaotic ending *requires* being nearly fully corrupted.)

### 9.4 Removal
- **Potion of cure corruption** removes ~**0.75 corruption per blessed potion** (always bless these). Scroll of corruption removal (cursed = *adds* corruption — dangerous). **Thrown** potions of cure corruption badly hurt chaos beings. NPC cures (Jharod cures the carpenter; Guth'Alak gives a cure potion). These items are the most precious in the game — make them rare.

## 10. Religion & Divine Economy

### 10.1 Alignment
- Three groups **Lawful / Neutral / Chaotic**; **11 sub-shades**. Internal score ≈ **−10000…+6000** (read via scroll of balance). Dynamic: actions shift it (Law skill identifies act nature). Lawful ≈ "good."
- **Extreme alignment** L+ / N= / C− is required for full crowning. C− corrupts faster; L+ slower.
- Alignment **gates content**: chaotic PCs can't get Healing from Jharod, the Trident from Khelavaster, cure potions from Guth'Alak, or Hawkslayer companion; some NPCs (Yergius, Gaab'Baay) gate quests by alignment.

### 10.2 Piety
- Hidden favor **per god** (one deity per alignment for the PC's race). Starts positive with your god, 0 with others. **Starting piety:** Druid/Priest 1500, Paladin 1200, others 200.
- **Gains:** sacrifice on **co-aligned altar** — gold (**~0.32 piety/gp**; dwarves ~0.48), items (usually worth less than selling then sacrificing the gold), **food/corpses** (corpse ≈ 370 gp value; **cooking doubles**; Hurthling cooked-food bonus), and **live monster sacrifice** (≈ **1400 gp** of piety — best early). Herbs cap (~10 stomafillia before "NO MORE VEGETABLES").
- **Decay:** −1% of piety every **220 turns**, floored at max(99, class/alignment starting piety). Keep sacrificing.
- **Retribution:** misuse (converting an altar, cross-aligned offering, sacrificing a gift, kicking/shattering an altar = −10000 piety) → cursing, equipment-to-dust, dooming, damage bolts, hostile summons.

### 10.3 Altars
- **Marble (white)** = lawful; **granite (light grey)** = neutral; **obsidian (dark grey)** = chaotic. Deal only with your alignment's altar (or convert it). Dropping items on a co-aligned altar reveals **BUC** for free. Blessing water on a co-aligned altar → **holy water**.

### 10.4 Prayer
- Costs piety; effect chosen by a **precedence list** by need: crowning > heal/food > uncurse > remove status > etc. Repeated prayers get costlier (like any favor). Praying while angering one god pleases the others (exploitable to max piety).

### 10.5 Crowning
- Requires **extreme alignment** + very high piety (≈ **30000** "extremely close"; effective cost ~10000). Prayer at that state → **Champion of {Order/Balance/Chaos}**.
- **Gifts:** permanent **Blessed**; an **alignment amulet**; a **class- or race-specific artifact**; one **permanent elemental immunity** (message says which); +1 To, +2 Ch, +1 Ma; halved prayer cost; artifact food-cost drops to 0.25/turn (so a crowned PC wears 3 artifacts free).
- **Precrowning/Postcrowning** (non-extreme / any alignment resp.): additional random artifacts (needs char level ≥ 8 + 3 artifacts already generated; escalating piety cost 50k, 150k, 300k…).
- **Chaotic crowning** also inflicts **2–3 corruptions**. Changing alignment after crowning → **fallen Champion** (deity turns hostile).

---

# PART VIII — ITEMS

## 11. Item System

### 11.1 Slots & categories
- **Equip slots:** head (helmet), body armor, shield, gauntlets, cloak, girdle, boots, neck (necklace/amulet), bracers, ring ×2, melee weapon (1–2 hands), missile weapon, tool slot, plus the missile/ammo slot.
- **Categories:** helmets, body armor, shields, gauntlets, cloaks, girdles, boots, necklaces, bracers, melee weapons, missile weapons, missiles/ammo, tools, instruments, rings, wands, potions, scrolls, books & **spellbooks**, food, herbs, gems, gold, corpses/statues, and **artifacts** (per-slot artifact variants exist).

### 11.2 BUC (Blessed / Uncursed / Cursed)
- Every instance has hidden **BUC**; **10% chance blessed, 10% cursed** at generation.
- **Cursed:** worse effect; **can't be unequipped** (except missile slot); some restrict other slots (cursed gauntlets lock rings; cursed girdle locks body armor). A few are useful cursed (cursed potion of invisibility → blinds enemies when thrown).
- **Blessed:** stronger, more damage-resistant. Some items scale dramatically (blessed potion of gain attributes = +1 to *all* 9 stats vs one random; blessed scroll of uncursing cleans whole inventory).
- **Change BUC:** holy water dip → blessed; unholy water → cursed; scroll of uncursing (uncursed = one item, blessed = all); Remove Curse spell/prayer; blessed scroll of repair can bump a *broken* item up one BUC step.

### 11.3 Materials, quality, affixes
- Material tiers (weakest→strongest, roughly): iron/leather → mithril → adamantium → eternium; plus **crystal**, and **dragon scale** (grants the dragon's elemental immunity). Heavier-than-expected items may be a rare material.
- Weapons/armor carry modifiers `[DV, PV]` and `(to-hit, XdY+dmg)`; e.g., eternium plate ≈ `[-1,+13]`, eternium tower shield ≈ `[+13,+4]`.
- **Prefix/suffix** system on armor/weapons/missiles (e.g., "of {element} slaying", "trapped", "of protection") — a large combinatorial affix space. Model as `basetype + prefix? + suffix?`.

### 11.4 Identification
- Items start unidentified (general info only). ID methods: use-ID (weapons/armor), scroll of identify, shops, **Detect Item Status** (BUC only), Merchant class specialty, altar-drop (BUC), potion/scroll of ID, casting Identify. Appraising gives a rough value; shop buy-price hints at quality.

### 11.5 Artifacts
- **Unique, indestructible** (can't be improved either), except a few (map fragments, si). Sources: **crowning/pre/postcrowning**, specific **quests**, greater vaults, shops, Casino, Merchant Guild, surges of power, random drops.
- **Food cost:** +0.5 satiation/turn each (0.25 if crowned) → uncrowned can wear 1 free, crowned 3.
- Some **autocurse** on equip (Black Torc, Moon Sickle, Boots of Great Speed) and/or **corrupt/doom** the wearer. Destroy only via sacrifice or the Demented Ratling.
- Example guaranteed/quest artifacts: **Sword of Nonnak, Elemental Gauntlets** (Portal quest), **Moon Sickle** (guarded by stone golem), **Black Torc** (Keethrax), **Trident of the Red Rooster** (Khelavaster, lawful), **Ring of the Master Cat** (Cat Lord: +16 Dx, +16 Speed, crits, Fate Smiles), **Ring of the High Kings**. Pull the full artifact roster (~50+, with per-class crowning-gift tables) from the wiki **Artifact** pages.

### 11.6 Item powers & intrinsics
- **Intrinsics** (permanent unless removed): elemental resist/immunity, **teleportitis** (random teleport) vs **teleport control**, **invisibility** / **see invisible**, **water breathing**, **Fate Smiles**/Luck, **Cursed**/**Doomed** (nudge all rolls against you; Doomed also ups corruption & blocks divine help), petrification/sleep resist.
- Sources: worn items (only while equipped), eaten corpses, pools (risky), karma.
- **Item powers:** slaying, purity, terror (enemies flee), +HP/PP regen, blood-drinking weapons (grow stats), etc.

### 11.7 Notable consumables
- **Potions** (unID'd by color): boost-{stat}, gain attributes, cure corruption, extra/ healing, troll blood (HP regen ↓time), raw mana (PP regen), holy/unholy water, invisibility, exchange, potential-{stat}, booze, raw chaos (dangerous), water, etc. Cooking/dipping/alchemy interactions matter.
- **Scrolls:** identify, uncursing, corruption removal, magic mapping, teleport, defense/protection, repair, balance, chaos resistance, danger, ill fate, entropy (used in the chaos-god ending), etc.
- **Herbs:** morgia (To/Wi/Dx), moss of mareilon (St), stomafillia (food/sacrifice), spenseweed (heal), curaria, alraunia, pepper petal, demon daisy — regrow if picked correctly with Herbalism.
- **Corpses:** satiation + chance of intrinsics or harm; some cause **cursing/dooming** if eaten (Cute Dog, dwarven child, unicorn, etc.).

### 11.8 Economy & shops
- Shops have finite random stock; you can buy back what you sell. **Prices** scale with Charisma/Appearance/gender, **race relations** (dwarves gouge orcs/dark elves), and **Haggling**/Silver Tongue. **Casino** = biggest item source. Never anger a shopkeeper (they're deadly; Ventriloquism helps).

---

# PART IX — MONSTERS

## 12. Monster System

### 12.1 Stats & types
- Per-monster: HP, DV/PV, speed, attacks (dice), XP value, alignment, size, type tags, special abilities, corpse effect, drops. Base monster **DV** ≈ table value + `0.7*level`, +4 invisible, −6 enraged, +items, +3 if it drank a boost potion; special cases (Shopkeeper DV ≈ DL+15; Royal guardian ≈ DL/2 + PC level + 15).
- **Monster types** (for slaying weapons & vulnerabilities): humanoid, demon, undead, animal, insect/bug, construct/golem, dragon, jelly/ooze, elemental, plant, giant, etc. A monster can have multiple types (golem = construct humanoid).
- **Sizes** (hidden): tiny/small/medium/large — bigger = ~2× harder to corrupt per size, heavier corpses/statues; some powers only affect ≤ certain size.

### 12.2 Special abilities (implement as on-hit / passive components)
Poisoning, **corrupting**, penetrating (ignore PV), paralyzing, sickness, sleep, **aging** (deadly to short-lived races), slowing, confusing, **stat-drain** melee; **elemental breath** (fire common; cold/acid rarer; lightning = air creatures) treated as a bolt for resistance; **missile use**; **equipment annihilation** (eyes of destruction/annihilators destroy a random *equipped* non-artifact); sleep **song** (harpies/jackalweres); plus phasing, digging, teleport-self, **stealing**, suicide/explode (vortices), web-spinning, floor-item destruction, mimicking, power adjustment, ignore-traps/water/webs.

### 12.3 Breeding vs summoning
- **Breeders** produce more of themselves — by **duplicating** (splits HP in half) or **spawning** (full-HP copy, no HP loss). Breeders **never gain XP**. Can be **sterilized** (scroll of vermin control / prayer). Classic danger: rats, giant rats, etc. **Gremlins** breed only when splashed with water.
- **Summoners** conjure *other* monster types; can't be sterilized.

### 12.4 Monster XP-leveling & the "uberjackal" effect
- The more of a monster type you kill, the **higher-level the next spawn** of that type (rarer types level after fewer kills; min 5; rats/jackals level fast → over-farming weak monsters breeds dangerous versions). Breeders exempt. Feed the monster memory from these kills.

### 12.5 Notable / unique monsters & bosses
- Uniques (single-spawn, fixed location): Keethrax, Yrrigs, Jharod, Thrundarr, Khelavaster, Waldenbrook, Cat Lord (D:35), the elemental **Orb Guardians**, minotaur emperor, **Andor Drakon** (D:50, demonic humanoid), **Ultimate Balor**, plus a large **boss-monster** roster (~147). Pull the full monster list (~600) and unique list from the wiki **Monsters** / **Monster stats** pages.

---

# PART X — CONTENT & FLOW

## 13. Locations (detailed)

### 13.1 Towns — see §4.4. Key NPC functions: quest-givers, shops, trainers (Yergius: thief skills; Garth: attributes/skills for gold), healer (Jharod / Kranf Niest), smith, Arena (fight for gold/XP).

### 13.2 Early loop
Terinyo (quests, food) → Small Cave → Unremarkable/UD → HMV shop → Village or Druid Dungeon → Puppy Cave → down into CoC.

### 13.3 Special zones — Pyramid, Tomb of the High Kings, Darkforge, ToEF (**mandatory**, Fire Orb), Ice Queen Domain, Rift, Assassins' Guild, Casino, Library of Nilthrias, Minotaur Maze, Quickling Tree, Ultimate Dungeon (see §4.4).

### 13.4 Caverns of Chaos (the spine)
- **50 levels + side branches**; the only dungeon with **sub-dungeons**. Persistent once generated. Selected guaranteed features (verify exact DLs on the wiki):
  - **D:1–2:** optional Shortcut level; a second down-stair may lead to the **Halls of the Dwarves** (2 levels, over-DL danger, quest target) or the **Animated Forest** (Thrundarr quest — do **not** enter early or you forfeit the quest).
  - **Dwarftown** (around D:11–13): Thrundarr, Waldenbrook, altar, smith, Arena. Hands out **Thrundarr's quests** and the **Portal quest**.
  - **Moon Sickle** artifact (stone golem) between Dwarftown and ~D:21.
  - **Khelavaster** on the **down-stairs of D:16**: reveals the Orb quest; if saved (needs Ankh + scrolls), unlocks **ultra endings** and gives spellbooks of Teleport & Identify (+ Trident for lawful).
  - **Graveyard** ~D:17 (undead, lich). **Griffyard / Portal quest** tomb: master necromancer + **Griff Bloodax** → **Sword of Nonnak**, **Elemental Gauntlets**; completing it makes Thrundarr open the **dwarven portal** to the lower CoC (+ wand of digging/fireballs, potions of extra healing).
  - **Water Temple** ~D:19–22 (disconnected — dig in; no teleport): **Water Orb**.
  - **Banshee level** ~D:22–24 (deadly scream; counter with beeswax/deafness/wedding ring). After D:24 the level numbering reverses.
  - **Air / Earth / Mana Temples** in CoC sub-dungeons (Unreal Caves for Mana). **Fire Temple** is in **ToEF:4** (outside CoC).
  - **D:48:** five **elemental anomalies** (each guarded by an elemental grue / chaos wizard). Throw each Orb into its matching anomaly to convert the stairs to a down-stair (commits you).
  - **D:50:** the **Chaos Gate**. Two levers in hidden N/S passages, each guarded by a **balor**; **Fistanarius** + 10 balors can reopen levers you leave line-of-sight of. Close both (permanently) to halt corruption, then exit.

## 14. Quests & Main Storyline

### 14.1 Early branching (mutually exclusive) — Terinyo
- **Save the Carpenter** (Rynt): lead Yrrigs from VD:7 up to Jharod (VD:4). Rewards: Village Dungeon access, **Healing skill** (via Jharod), Bridge Building, hatchet, oil of rust removal. *(The path to Healing for classes/races lacking it.)*
- **Kill the Black Druid** (Guth'Alak): descend DD:7, kill **Keethrax**. Rewards: Druid Dungeon access, **Herbalism**, cold magic (Frost Bolt book + wand of cold), **Black Torc**, **potion of cure corruption**. *(Chaotic-restricted; Keethrax is a hard fight.)*
- Plus: sheriff **Tywat Pare** (vs Kranach the raider), the **doggie/Blup** corpse-retrieval quests.

### 14.2 Main quest chain
1. Descend CoC to **Dwarftown**; get **Thrundarr's quests** (report beyond Animated Forest / Dwarven Halls; kill a specific monster) and the **Portal quest** (Griffyard).
2. Meet **Khelavaster** on D:16 → learn the **five Orbs** objective (optionally *save* him for ultra-ending eligibility).
3. Collect the **5 Elemental Orbs**: Water (CoC ~D:20), Fire (ToEF:4), Air, Earth, Mana (CoC sub-dungeons).
4. Complete the **Portal quest** so Thrundarr opens the portal to lower CoC.
5. **D:48:** throw each Orb into its anomaly (side effects: fire scours the level, mana drains your PP).
6. **D:50:** close both Gate levers (kill/trap the balors) → corruption halts.
7. Exit CoC and leave the Drakalor Chain → **win**.
   - **Orbs as gear:** each Orb equips in the tool slot for +10 to a stat (Water→Wi, Fire→St, Air→Dx, Earth→To, Mana→Ma), but handling them corrupts.

### 14.3 Side quests (samples)
Rolf's quest (antediluvian dwarven map fragments; Bergbringer), Sharad-Waador (blue dragon caves), Ice Queen, Gaab'Baay (farmers), the Cat Lord (never kill a cat → Ring of the Master Cat), Tome of Donors, Assassins'/Thieves' guild lines. Pull the full quest list from the wiki **Quests** page.

## 15. Endings

1. **Standard win** — close the Gate, leave the Chain.
2. **Chaos God (Chaos Knight)** — like standard but the PC needn't leave; different text/score.
3. **Ordinary Chaos God** — a **C−** Champion enters the Gate with the **Sceptre of Chaos** (or Trident), reads a **scroll of entropy** next to Andor Drakon to kill him, then flees the collapsing CoC.
4. **Ultra endings (Avatar of Order / Balance)** — a Champion of any alignment (Balance requires the Atoner arc: be chaotic, get the Medal/Crown of Chaos, then convert and obtain the **Trident of the Red Rooster**) enters the Gate with the **Trident** equipped and slays Andor Drakon in melee → ascend as an **Avatar**.
5. **Ultimate Dungeon / Scroll of Omnipotence** — post-win megaquest (Minotaur Maze, deliberately fail the Rolf quest, lure an NPC across the map) → **Ultimate Balor**.

Only ways to *lose*: **die** (permadeath) or **quit**.

---

# PART XI — DESIGN & BUILD

## 16. Systems-Interaction & Difficulty Design
The game's tension comes from coupling, not any single system:
- **Permadeath** amplifies every choice.
- **Corruption** blocks safe grinding → pushes you toward **altars/piety** for fast power.
- **Piety** decays and punishes abuse → couples to **alignment**.
- **Alignment** changes **corruption rate** and gates **quests/endings** → your moral and survival tracks are one track.
- **Build** sets your relationship to all of the above (fragile immortal elf caster vs corruption-resistant dwarf priest piety-engine).
- **Hunger + day/night + travel cost** make the world itself a spent resource.
- **The endings are the difficulty ladder** (close-the-gate → ascension) on one codebase.

## 17. Implementation Blueprint (.NET-oriented)

### 17.1 Recommended module layout
- **Core.Engine:** energy scheduler (min-heap), RNG, turn loop, action/effect pipeline.
- **Core.Model:** Actor (PC & monsters), Attributes, Skills, Inventory, Corruption, Piety, StatusEffects.
- **Core.World:** overworld graph, Level, tile map, FOV/lighting (time-of-day), pathfinding.
- **Core.Generation:** fixed-site loader + random-level generators (rooms/caverns/vaults/features).
- **Core.Rules:** combat resolver, spell/mindcraft resolver, corruption clock, piety ledger, hunger clock, identification, BUC, affix system.
- **Content (data):** JSON/SQLite tables for races, classes, class powers, star signs, talents, skills, spells, corruptions, items, affixes, artifacts, monsters, monster abilities, locations, quests.
- **UI:** ASCII/tile renderer, message log, inventory/char screens, bestiary (monster memory).
- **Persistence:** single-save service enforcing permadeath.

### 17.2 Core data schemas (sketch)
```
RaceDef      { id, attrMods{9}, attrPotentials{9}, xpMult, ageRange, hpRegen, ppRegen,
               startAlignment, startSkills[], startEquip[], shopRelations{}, foodRules[],
               abilities[] (acidSpit, mithrilSkinEligible, …) }

ClassDef     { id, startSkills[], startPiety, casterType (arcane|clerical|none|mind),
               meleeToHitCurve, rangedToHitCurve, weaponMarkRate, itemDropBias,
               classPowers[7] { level, kind, payload }, crowningGiftTable[] }

StarSignDef  { id, month, effects[] (attrMods, speed, corruptionMod, freeTalent, fireImmunity…) }

TalentDef    { id, requirements[], effects[], line, tier }

SkillDef     { id, attr, startFormula, potentialCap, checkType, on80, on100, wishable }

SpellDef     { id, arcaneName, clericalName, basePP, readTurns, kind (bolt|ball|touch|self|other),
               radiusFormula, damageFormula, bounces, destroysFloorItems, resistTag }

CorruptionDef{ id, weight, minCorruptCount, statMods{}, special[] (poisonHands, manaBattery,
               acidSpit, quicklingKey, cumulative…) }

ItemBaseDef  { id, slot, category, material, baseDV, basePV, dmgDice, weight, buc?,
               powers[], allowedPrefixes[], allowedSuffixes[] }
AffixDef     { id, kind (prefix|suffix), slotFilter, modifiers[] }
ArtifactDef  { id, baseSlot, powers[], autocurse?, corrupts?, dooms?, foodCost,
               source (crowning|quest|vault|…), classCrowningFor[] }

MonsterDef   { id, hp, dv, pv, speed, attacks[], xpValue, alignment, size, types[],
               abilities[], corpseEffect, drops[], breeder?, summoner?, unique?,
               killsToLevel, spawnDL }

LocationDef  { id, kind (town|fixedDungeon|randomDungeon), depthBand, dlRange, features[],
               fixedNpcs[], connections[], generationRules }

QuestDef     { id, giver, prereqs[], mutualExclusions[], steps[], rewards[], alignmentGate }
```

### 17.3 Global services (subscribe to the turn scheduler)
`HungerClock`, `BackgroundCorruptionClock` (depth-aware: off < DL10, 1CP below CoC D:9, 3CP at D:45+), `PietyLedger` (per-deity, −1%/220 turns, floor rules), `MonsterLevelingTracker` (uberjackal), `IdentificationService`, `LightingService` (time-of-day FOV).

### 17.4 Suggested milestone order
1. Grid, FOV, energy scheduler, one random level, move/attack, permadeath save.
2. Attributes/HP/PP, DV/PV/to-hit/damage, tactics, one race+class.
3. Inventory, BUC, equip slots, identification, basic items + potions/scrolls.
4. Skills + weapon marks + leveling + class powers.
5. Magic (PP, spell knowledge/power, spell list) + mindcraft.
6. Overworld graph + fixed towns/NPCs + shops + quests (Terinyo branch).
7. Altars/piety/alignment/prayer/crowning.
8. Corruption clock + corruption table + removal.
9. CoC spine + Orbs + Gate + standard ending.
10. Remaining races/classes/monsters/artifacts/special zones + ultra endings.

## 18. Content-Enumeration Appendix (mine these wiki pages directly)
Because the following are too large to inline, port them as data tables from the ADOM Wiki:
- **Races** (per-race attribute mod & potential tables, starting equipment). 12 pages.
- **Class power** (all 22 classes × 7 powers) and per-class starting skills.
- **Skill** (45 skills, exact per-class start formulas, cost curves).
- **Spells** (full table: damage dice, radius, clerical names, rarity).
- **Corruptions** (complete list + exact stat mods + aggregate thresholds).
- **Artifact** (~50+ artifacts + per-class crowning-gift tables).
- **Items** (base types, materials `[DV,PV]/(hit,dmg)` stats, prefixes/suffixes, potions/scrolls/wands/herbs lists).
- **Monsters / Monster stats / Monster abilities** (~600 monsters, ability tags, corpse effects, boss list).
- **Locations / Caverns of chaos** (exact guaranteed features & DLs, sub-dungeons).
- **Quests** (full quest list, givers, rewards, gates).
- **Star sign / Talents** (exact numeric effects & full talent tree).

---

*Everything above is a design/reimplementation synthesis of publicly documented ADOM mechanics (ADOM Wiki, ADOM Manual, community guidebooks). Numbers are edition-dependent — treat the cited wiki page as the source of truth per system, and verify against your target ADOM version.*
