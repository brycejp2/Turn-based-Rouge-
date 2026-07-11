"""Procedural tile art for the 2D renderer.

Every tile and sprite is drawn from code with pygame primitives — there
are **no external image assets**, which keeps the build self-contained,
tiny, and free of any third-party art.  A :class:`TileAtlas` renders each
terrain type / creature / item once and caches the surface.

The look is a clean, dark "dungeon tile" style: bevelled stone, muted
floors, and sickly Hollowing accents (violet/green) for the Gate and the
corrupted deep.
"""

from __future__ import annotations

import pygame

# -- palette ---------------------------------------------------------------
BG = (12, 12, 16)
PANEL = (20, 20, 26)
PANEL_BORDER = (58, 58, 72)
TEXT = (222, 222, 228)
TEXT_DIM = (120, 122, 134)
TEXT_WARN = (210, 120, 120)
TEXT_GOOD = (150, 200, 140)
ACCENT = (150, 80, 190)          # the Hollowing

FLOOR = (38, 38, 46)
FLOOR_EDGE = (28, 28, 35)
FLOOR_DOT = (50, 50, 60)
CORRIDOR = (32, 32, 40)
WALL_TOP = (78, 74, 88)
WALL_BODY = (46, 44, 55)
WALL_EDGE = (30, 28, 36)
DOOR = (126, 84, 44)
DOOR_DARK = (86, 56, 28)
WATER = (42, 74, 122)
LAVA = (150, 60, 30)
STAIRS = (205, 205, 170)
ALTAR = (185, 185, 196)
FORGE = (150, 92, 60)
HERB = (86, 152, 74)
GATE_RING = (26, 18, 34)
GATE_GLOW = (156, 74, 206)

HERO = (244, 222, 120)

CREATURE_COLORS = {
    "animal": (150, 112, 72),
    "humanoid": (112, 162, 92),
    "undead": (176, 188, 198),
    "demon": (202, 72, 62),
    "giant": (132, 102, 152),
    "hollowed": (150, 86, 190),
    "insect": (150, 150, 70),
    "plant": (90, 150, 70),
}
CREATURE_DEFAULT = (170, 120, 120)

ITEM_COLORS = {
    "potion": (92, 162, 212),
    "scroll": (212, 202, 150),
    "weapon": (186, 186, 196),
    "body_armor": (150, 150, 162),
    "shield": (150, 150, 162),
    "helmet": (150, 150, 162),
    "boots": (150, 150, 162),
    "gauntlets": (150, 150, 162),
    "cloak": (150, 150, 162),
    "girdle": (150, 150, 162),
    "food": (172, 122, 82),
    "ring": (210, 190, 110),
    "spellbook": (156, 100, 200),
}
ITEM_DEFAULT = (200, 200, 120)


def _darken(color, factor=0.5):
    return tuple(max(0, int(c * factor)) for c in color)


def _lighten(color, factor=1.4):
    return tuple(min(255, int(c * factor)) for c in color)


class TileAtlas:
    def __init__(self, size: int = 24):
        self.size = size
        self._cache: dict = {}
        self._glyph_font = pygame.font.Font(None, int(size * 0.9))

    def get(self, key: str, drawer) -> pygame.Surface:
        surf = self._cache.get(key)
        if surf is None:
            surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            drawer(surf)
            self._cache[key] = surf
        return surf

    # -- terrain ---------------------------------------------------------
    def terrain(self, tile) -> pygame.Surface:
        return self.get(f"terrain:{tile.key}", lambda s: self._draw_terrain(s, tile))

    def _draw_terrain(self, s, tile):
        n = self.size
        key = tile.key
        if key == "wall":
            s.fill(WALL_BODY)
            pygame.draw.rect(s, WALL_TOP, (0, 0, n, max(2, n // 5)))
            pygame.draw.rect(s, WALL_EDGE, (0, 0, n, n), 1)
        elif key in ("floor", "corridor"):
            s.fill(FLOOR if key == "floor" else CORRIDOR)
            pygame.draw.rect(s, FLOOR_EDGE, (0, 0, n, n), 1)
            for (px, py) in ((n // 4, n // 3), (2 * n // 3, 3 * n // 4)):
                s.set_at((px, py), FLOOR_DOT)
        elif key in ("door_closed", "door_open"):
            s.fill(FLOOR)
            if key == "door_closed":
                pygame.draw.rect(s, DOOR, (n // 6, 1, 2 * n // 3, n - 2))
                pygame.draw.rect(s, DOOR_DARK, (n // 6, 1, 2 * n // 3, n - 2), 1)
                pygame.draw.circle(s, DOOR_DARK, (2 * n // 3, n // 2), 2)
            else:
                pygame.draw.rect(s, DOOR, (1, 1, n // 5, n - 2))
                pygame.draw.rect(s, DOOR, (n - n // 5 - 1, 1, n // 5, n - 2))
        elif key in ("stairs_down", "stairs_up"):
            s.fill(FLOOR)
            up = key == "stairs_up"
            for i in range(3):
                w = n - 6 - i * 4
                x = 3 + i * 2
                y = (n - 6 - i * 3) if up else (4 + i * 3)
                pygame.draw.rect(s, STAIRS, (x, y, w, 3))
        elif key == "water":
            s.fill(WATER)
            pygame.draw.arc(s, _lighten(WATER), (2, n // 3, n - 4, n // 3), 3.3, 6.1, 2)
        elif key == "lava":
            s.fill(LAVA)
            pygame.draw.circle(s, _lighten(LAVA, 1.5), (n // 2, n // 2), n // 5)
        elif key == "gate":
            s.fill(GATE_RING)
            pygame.draw.circle(s, GATE_GLOW, (n // 2, n // 2), n // 2 - 2)
            pygame.draw.circle(s, GATE_RING, (n // 2, n // 2), n // 3)
            pygame.draw.circle(s, _lighten(GATE_GLOW), (n // 2, n // 2), n // 6)
        elif key == "altar":
            s.fill(FLOOR)
            pygame.draw.rect(s, ALTAR, (n // 5, n // 3, 3 * n // 5, n // 2))
            pygame.draw.rect(s, _darken(ALTAR), (n // 5, n // 3, 3 * n // 5, n // 2), 1)
        elif key == "forge":
            s.fill(FLOOR)
            pygame.draw.rect(s, FORGE, (n // 5, n // 4, 3 * n // 5, n // 2))
            pygame.draw.circle(s, _lighten(LAVA, 1.4), (n // 2, n // 2), 2)
        elif key == "herb_bush":
            s.fill(FLOOR)
            for dx in (-3, 0, 3):
                pygame.draw.circle(s, HERB, (n // 2 + dx, n // 2 + 2), 4)
        else:
            s.fill(FLOOR)

    # -- entities --------------------------------------------------------
    def hero(self) -> pygame.Surface:
        return self.get("hero", self._draw_hero)

    def _draw_hero(self, s):
        n = self.size
        pygame.draw.circle(s, _darken(HERO, 0.6), (n // 2, n // 2), n // 2 - 2)
        pygame.draw.circle(s, HERO, (n // 2, n // 2), n // 2 - 3)
        # simple figure
        pygame.draw.circle(s, _darken(HERO, 0.35), (n // 2, n // 2 - 3), max(2, n // 8))
        pygame.draw.rect(s, _darken(HERO, 0.35),
                         (n // 2 - 2, n // 2, 4, n // 3))

    def creature(self, glyph: str, category: str) -> pygame.Surface:
        color = CREATURE_COLORS.get(category, CREATURE_DEFAULT)
        return self.get(f"mon:{glyph}:{category}",
                        lambda s: self._draw_creature(s, glyph, color))

    def _draw_creature(self, s, glyph, color):
        n = self.size
        pygame.draw.rect(s, _darken(color, 0.55), (2, 2, n - 4, n - 4),
                         border_radius=n // 4)
        pygame.draw.rect(s, color, (3, 3, n - 6, n - 6), 2, border_radius=n // 4)
        glyph_img = self._glyph_font.render(glyph, True, _lighten(color, 1.6))
        s.blit(glyph_img, glyph_img.get_rect(center=(n // 2, n // 2 + 1)))

    def npc(self, glyph: str) -> pygame.Surface:
        return self.get(f"npc:{glyph}", lambda s: self._draw_npc(s, glyph))

    def _draw_npc(self, s, glyph):
        n = self.size
        friendly = (110, 180, 210)
        pygame.draw.rect(s, _darken(friendly, 0.5), (2, 2, n - 4, n - 4),
                         border_radius=n // 5)
        pygame.draw.rect(s, friendly, (3, 3, n - 6, n - 6), 2, border_radius=n // 5)
        img = self._glyph_font.render(glyph, True, _lighten(friendly, 1.5))
        s.blit(img, img.get_rect(center=(n // 2, n // 2 + 1)))

    def boss(self, glyph: str) -> pygame.Surface:
        return self.get(f"boss:{glyph}", lambda s: self._draw_boss(s, glyph))

    def _draw_boss(self, s, glyph):
        n = self.size
        pygame.draw.rect(s, _darken(ACCENT, 0.5), (1, 1, n - 2, n - 2),
                         border_radius=n // 5)
        pygame.draw.rect(s, GATE_GLOW, (1, 1, n - 2, n - 2), 2, border_radius=n // 5)
        glyph_img = self._glyph_font.render(glyph, True, (255, 230, 255))
        s.blit(glyph_img, glyph_img.get_rect(center=(n // 2, n // 2 + 1)))

    def item(self, glyph: str, category: str) -> pygame.Surface:
        color = ITEM_COLORS.get(category, ITEM_DEFAULT)
        return self.get(f"item:{category}",
                        lambda s: self._draw_item(s, category, color))

    def _draw_item(self, s, category, color):
        n = self.size
        cx = n // 2
        if category == "potion":
            pygame.draw.rect(s, color, (cx - 2, 4, 4, 4))          # neck
            pygame.draw.circle(s, color, (cx, n - 8), n // 4)       # flask
            pygame.draw.circle(s, _lighten(color), (cx - 2, n - 10), 2)
        elif category == "scroll":
            pygame.draw.rect(s, color, (5, 6, n - 10, n - 12), border_radius=2)
            pygame.draw.line(s, _darken(color), (8, n // 2), (n - 8, n // 2), 1)
            pygame.draw.line(s, _darken(color), (8, n // 2 + 3), (n - 8, n // 2 + 3), 1)
        elif category == "weapon":
            pygame.draw.line(s, color, (6, n - 6), (n - 7, 6), 2)   # blade
            pygame.draw.line(s, _darken(color, 0.7), (5, n - 8), (10, n - 3), 3)  # hilt
        elif category == "food":
            pygame.draw.circle(s, color, (cx, cx), n // 4)
        elif category == "ring":
            pygame.draw.circle(s, color, (cx, cx), n // 4, 2)
        elif category == "spellbook":
            pygame.draw.rect(s, color, (5, 5, n - 10, n - 9), border_radius=2)
            pygame.draw.rect(s, _darken(color), (5, 5, n - 10, n - 9), 1,
                             border_radius=2)
            pygame.draw.line(s, _lighten(color), (cx, 7), (cx, n - 7), 1)
        else:  # armour and the rest → a shield
            pygame.draw.polygon(s, color, [(cx, 4), (n - 5, 8),
                                           (cx, n - 4), (5, 8)])
            pygame.draw.polygon(s, _darken(color), [(cx, 4), (n - 5, 8),
                                                    (cx, n - 4), (5, 8)], 1)
