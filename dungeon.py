"""
Dungeon of Doom
===============
A randomly generated dungeon crawler RPG.
Works on Windows, Mac, and Linux — no external libraries needed.

How to play:
  - Move with the arrow keys (or WASD)
  - Walk into enemies to attack them
  - Pick up items by walking over them — they stay in your bag!
  - Press U to open your inventory and use an item
  - Reach the stairs (>) to descend deeper
  - Defeat the Dungeon Lord on floor 5 to win!
  - Press Q to quit, S to save, L to load

Run with: python dungeon.py
"""

import sys
import os
import random


# ─── Single-keypress input (no Enter needed) ──────────────────────────────────
#
# This part talks directly to the terminal so keys work without pressing Enter.
# I looked up how to do this because the default input() wouldn't work for a game.
# get_key() returns a string for whichever key was pressed:
#
#   "UP", "DOWN", "LEFT", "RIGHT"  ← arrow keys
#   "w", "a", "s", "d"            ← WASD keys
#   "S", "l", "q", "u"            ← save / load / quit / use item

if sys.platform == "win32":
    import msvcrt
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7
    )

    def get_key():
        ch = msvcrt.getwch()
        if ch == chr(224):
            direction = msvcrt.getwch()
            if direction == "H":  return "UP"
            if direction == "P":  return "DOWN"
            if direction == "K":  return "LEFT"
            if direction == "M":  return "RIGHT"
            return ""
        return ch

else:
    import tty
    import termios

    def get_key():
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == chr(27):
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":  return "UP"
                    if ch3 == "B":  return "DOWN"
                    if ch3 == "D":  return "LEFT"
                    if ch3 == "C":  return "RIGHT"
                return ""
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def clear_screen():
    os.system("cls" if sys.platform == "win32" else "clear")


# ─── Colors ──────────────────────────────────────────────────────────────────
# ANSI escape codes let you print colored text in the terminal.

RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"

def fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

COL_WALL      = fg(80,  80,  80)
COL_WALL_DIM  = fg(50,  50,  50)
COL_FLOOR     = fg(40,  40,  40)
COL_PLAYER    = fg(0,   220, 255)
COL_ENEMY     = fg(220, 60,  60)
COL_BOSS      = fg(255, 80,  220)
COL_ITEM      = fg(255, 210, 0)
COL_STAIRS    = fg(80,  255, 120)
COL_HUD       = fg(200, 200, 200)
COL_HUD_DIM   = fg(120, 120, 120)
COL_TITLE     = fg(255, 180, 0)
COL_DEAD      = fg(255, 50,  50)
COL_WIN       = fg(100, 255, 180)
COL_LOG_OLD   = fg(110, 110, 110)
COL_SIDEBAR   = fg(160, 160, 160)
COL_DANGER_1  = fg(255, 220, 0)
COL_DANGER_2  = fg(255, 120, 0)
COL_DANGER_3  = fg(255, 50,  50)

# Message log colors
COL_MSG_DAMAGE  = fg(255, 80,  80)   # player takes damage
COL_MSG_HIT     = fg(100, 220, 255)  # player deals damage
COL_MSG_CRIT    = fg(255, 220, 0)    # critical hit (either side)
COL_MSG_PICKUP  = fg(255, 200, 80)   # item picked up
COL_MSG_LEVEL   = fg(80,  255, 160)  # level up
COL_MSG_HEAL    = fg(80,  220, 120)  # healing
COL_MSG_SYSTEM  = fg(180, 140, 255)  # floor/save/load/smoke messages


# ─── Layout constants ─────────────────────────────────────────────────────────

MAP_W      = 60
MAP_H      = 22
# SIDEBAR_W is how wide the right panel is (in characters)
SIDEBAR_W  = 24
SAVE_FILE  = "save.txt"

WALL   = "#"
FLOOR  = "."
STAIRS = ">"

BOSS_FLOOR = 5


# ─── Item and enemy definitions ───────────────────────────────────────────────

ITEM_DEFS = {
    # Consumables — you can carry multiples of these
    "Health Potion":  {"symbol": "!", "effect": "heal",   "value": 20, "min_floor": 1},
    "Bread":          {"symbol": "%", "effect": "heal",   "value": 8,  "min_floor": 1},
    "Smoke Bomb":     {"symbol": "o", "effect": "smoke",  "value": 4,  "min_floor": 2},
    "Throwing Knife": {"symbol": ")", "effect": "throw",  "value": 10, "min_floor": 1},
    # Weapons — only one can be equipped at a time
    "Rusty Sword":    {"symbol": "/", "effect": "attack", "value": 3,  "min_floor": 1},
    "Short Sword":    {"symbol": "/", "effect": "attack", "value": 5,  "min_floor": 1},
    "Power Crystal":  {"symbol": "*", "effect": "attack", "value": 6,  "min_floor": 2},
    "Steel Sword":    {"symbol": "/", "effect": "attack", "value": 9,  "min_floor": 2},
    "Broadsword":     {"symbol": "/", "effect": "attack", "value": 12, "min_floor": 3},
    "Battle Axe":     {"symbol": "\\","effect": "attack", "value": 14, "min_floor": 3},
    "Cursed Blade":   {"symbol": "†", "effect": "attack", "value": 18, "min_floor": 4},
    "Demon Sword":    {"symbol": "†", "effect": "attack", "value": 22, "min_floor": 5},
    # Shields — same as weapons, only one at a time
    "Iron Shield":    {"symbol": "[", "effect": "defense","value": 2,  "min_floor": 1},
    "Dragon Scale":   {"symbol": "}", "effect": "defense","value": 5,  "min_floor": 4},
}

ENEMY_DEFS = {
    "Goblin":       {"symbol": "g", "hp": 8,  "attack": 3,  "defense": 0, "xp": 5},
    "Orc":          {"symbol": "o", "hp": 15, "attack": 5,  "defense": 1, "xp": 10},
    "Skeleton":     {"symbol": "s", "hp": 10, "attack": 4,  "defense": 0, "xp": 8},
    "Troll":        {"symbol": "T", "hp": 25, "attack": 7,  "defense": 2, "xp": 20},
    "Dungeon Lord": {"symbol": "D", "hp": 80, "attack": 12, "defense": 4, "xp": 100},
}


# ─── Sidebar width helpers ───────────────────────────────────────────────────
#
# I ran into a problem where the sidebar border wouldn't line up because
# color codes count as characters in Python's len() even though they don't
# take up any space on screen. These helpers fix that by stripping the color
# codes before measuring, then padding with spaces to the right width.

def strip_ansi(text):
    """Remove color codes from a string so we can measure its real length."""
    result = ""
    i = 0
    while i < len(text):
        if text[i] == "\033" and i + 1 < len(text) and text[i + 1] == "[":
            i += 2
            while i < len(text) and text[i] != "m":
                i += 1
            i += 1
        else:
            result += text[i]
            i += 1
    return result

def visible_width(text):
    """Return how many characters wide a string looks on screen (ignoring color codes)."""
    return len(strip_ansi(text))

def pad_to(text, width):
    """Add spaces to the end of text until it's exactly `width` characters wide."""
    vw = visible_width(text)
    if vw < width:
        return text + " " * (width - vw)
    if vw > width:
        # Too long — strip color codes and cut it down
        plain = strip_ansi(text)
        return plain[:width]
    return text


# ─── HP / progress bar ────────────────────────────────────────────────────────

def make_bar(current, maximum, bar_len, high_col, mid_col, low_col):
    """Colored block-character progress bar. █ filled, ░ empty."""
    ratio  = max(0, current) / maximum
    filled = int(ratio * bar_len)
    col    = high_col if ratio > 0.6 else (mid_col if ratio > 0.3 else low_col)
    return col + "█" * filled + DIM + "░" * (bar_len - filled) + RESET


# ─── Classes ──────────────────────────────────────────────────────────────────
# Entity is the base class. Player and Enemy both inherit from it.

class Entity:
    """Shared base class for the player and enemies (position, hp, attack, defense)."""

    def __init__(self, x, y, symbol, hp, attack, defense):
        self._x      = x
        self._y      = y
        self.symbol  = symbol
        self.hp      = hp
        self.max_hp  = hp
        self.attack  = attack
        self.defense = defense

    def get_x(self):      return self._x
    def get_y(self):      return self._y
    def set_x(self, x):   self._x = x
    def set_y(self, y):   self._y = y

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        dmg = max(1, amount - self.defense)
        self.hp -= dmg
        return dmg

    def attack_target(self, target):
        return target.take_damage(self.attack + random.randint(0, 2))


class Player(Entity):
    """The player character. Inherits position and combat from Entity."""

    def __init__(self, x, y):
        super().__init__(x, y, symbol="@", hp=30, attack=5, defense=1)
        self._base_atk   = 5
        self._base_def   = 1
        self.xp          = 0
        self.level       = 1
        self.inventory   = {}
        self.weapon      = None
        self.shield      = None
        self.smoke_turns = 0     # how many turns the smoke bomb is still active
        self.floor       = 1
        self.messages    = []
        self.kills       = 0

    def gain_xp(self, amount):
        self.xp += amount
        threshold = self.level * 20
        if self.xp >= threshold:
            self.xp       -= threshold
            self.level    += 1
            self.max_hp   += 5
            self.hp        = min(self.hp + 5, self.max_hp)
            self._base_atk += 1
            self.attack    = self._base_atk
            if self.weapon is not None:
                self.attack += ITEM_DEFS[self.weapon]["value"]
            self.log(f"*** LEVEL UP! Now level {self.level}! ATK+1, MaxHP+5 ***", "level")

    def pick_up(self, name):
        """Add an item to the bag."""
        if name in self.inventory:
            self.inventory[name] += 1
        else:
            self.inventory[name] = 1
        defn = ITEM_DEFS[name]
        if defn["effect"] == "heal" or defn["effect"] == "smoke":
            self.log(f"Picked up {name}. Press U to use.", "pickup")
        else:
            self.log(f"Found {name}. Press U to equip.", "pickup")

    def use_item(self, name):
        """Use an item from the bag. Potions heal immediately; weapons/shields get equipped."""
        if name not in self.inventory or self.inventory[name] == 0:
            return False

        defn = ITEM_DEFS[name]

        if defn["effect"] == "heal":
            healed   = min(defn["value"], self.max_hp - self.hp)
            self.hp += healed
            self.log(f"Used {name}: +{healed} HP.", "heal")
            self._remove_from_bag(name)

        elif defn["effect"] == "smoke":
            self.smoke_turns = defn["value"]
            self.log(f"Smoke Bomb! Enemies confused for {defn['value']} turns.", "system")
            self._remove_from_bag(name)

        elif defn["effect"] == "throw":
            self.log("Use F to throw the knife at the nearest visible enemy.", "system")
            return True

        elif defn["effect"] == "attack":
            if self.weapon is not None:
                old = self.weapon
                self._add_to_bag(old)
                self.log(f"Unequipped {old}.", "system")
            self.weapon = name
            self.attack = self._base_atk + defn["value"]
            self.log(f"Equipped {name}: ATK now {self.attack}.", "pickup")
            self._remove_from_bag(name)

        elif defn["effect"] == "defense":
            if self.shield is not None:
                old = self.shield
                self._add_to_bag(old)
                self.log(f"Unequipped {old}.", "system")
            self.shield  = name
            self.defense = self._base_def + defn["value"]
            self.log(f"Equipped {name}: DEF now {self.defense}.", "pickup")
            self._remove_from_bag(name)

        return True

    def _add_to_bag(self, name):
        if name in self.inventory:
            self.inventory[name] += 1
        else:
            self.inventory[name] = 1

    def _remove_from_bag(self, name):
        self.inventory[name] -= 1
        if self.inventory[name] == 0:
            del self.inventory[name]

    def tick(self):
        """Called every turn to handle effects that last more than one turn."""
        # Cursed Blade drains 1 HP per turn
        if self.weapon == "Cursed Blade" and self.hp > 1:
            self.hp -= 1
            self.log("The Cursed Blade drains your life! -1 HP", "damage")

        # Count down smoke turns
        if self.smoke_turns > 0:
            self.smoke_turns -= 1
            if self.smoke_turns == 0:
                self.log("The smoke clears. Enemies can see you again.", "system")

    def log(self, msg, tag="system"):
        """Add a message to the log. The tag controls what color it shows up as."""
        self.messages.append((msg, tag))
        if len(self.messages) > 5:
            self.messages.pop(0)


class Enemy(Entity):
    """An enemy monster. Inherits position and combat from Entity."""

    def __init__(self, x, y, kind):
        defn = ENEMY_DEFS[kind]
        super().__init__(x, y, symbol=defn["symbol"], hp=defn["hp"],
                         attack=defn["attack"], defense=defn["defense"])
        self.kind = kind
        self.xp   = defn["xp"]

    def is_boss(self):
        return self.kind == "Dungeon Lord"

    def move_toward(self, px, py, dungeon):
        # Move one step closer to the player's position
        dx = 0 if self._x == px else (1 if px > self._x else -1)
        dy = 0 if self._y == py else (1 if py > self._y else -1)
        candidates = [
            (self._x + dx, self._y + dy),
            (self._x + dx, self._y),
            (self._x,      self._y + dy)
        ]
        for nx, ny in candidates:
            if dungeon.is_walkable(nx, ny):
                self._x = nx
                self._y = ny
                return


class Item:
    """Represents an item sitting on the dungeon floor."""

    def __init__(self, x, y, name):
        self._x   = x
        self._y   = y
        self.name = name

    def get_x(self):  return self._x
    def get_y(self):  return self._y


# ─── Dungeon Generation ───────────────────────────────────────────────────────
# Builds the map by placing random rooms and connecting them with corridors.

class Dungeon:
    """Holds the dungeon map, enemies, and items for one floor."""

    def __init__(self, floor_number=1, player=None):
        self.floor   = floor_number
        self.grid    = []
        for row in range(MAP_H):
            self.grid.append([WALL] * MAP_W)
        self.rooms    = []
        self.enemies  = []
        self.items    = []
        self._generate(player)

    def _generate(self, player=None):
        self._place_rooms()
        self._place_stairs()
        if self.floor == BOSS_FLOOR:
            self._place_boss()
        else:
            self._place_enemies()
        self._place_items(player)

    def _place_rooms(self, attempts=60):
        # Try up to 60 times to place a room. Skip it if it overlaps an existing one.
        for _ in range(attempts):
            w = random.randint(4, 10)
            h = random.randint(3, 6)
            x = random.randint(1, MAP_W - w - 1)
            y = random.randint(1, MAP_H - h - 1)

            overlapping = False
            for room in self.rooms:
                if self._overlaps(x, y, w, h, room[0], room[1], room[2], room[3]):
                    overlapping = True
                    break
            if overlapping:
                continue

            self._carve_room(x, y, w, h)

            # Connect this room to the previous one with an L-shaped corridor
            if len(self.rooms) > 0:
                prev = self.rooms[-1]
                self._carve_corridor(
                    prev[0] + prev[2] // 2,
                    prev[1] + prev[3] // 2,
                    x + w // 2,
                    y + h // 2
                )

            self.rooms.append((x, y, w, h))

    def _overlaps(self, x1, y1, w1, h1, x2, y2, w2, h2):
        return not (x1+w1+1 < x2 or x2+w2+1 < x1 or
                    y1+h1+1 < y2 or y2+h2+1 < y1)

    def _carve_room(self, x, y, w, h):
        for row in range(y, y + h):
            for col in range(x, x + w):
                self.grid[row][col] = FLOOR

    def _carve_corridor(self, x1, y1, x2, y2):
        sx = 1 if x2 >= x1 else -1
        for col in range(x1, x2 + sx, sx):
            self.grid[y1][col] = FLOOR
        sy = 1 if y2 >= y1 else -1
        for row in range(y1, y2 + sy, sy):
            self.grid[row][x2] = FLOOR

    def _center(self, room):
        return room[0] + room[2] // 2, room[1] + room[3] // 2

    def _rand_in_room(self, room):
        return (random.randint(room[0], room[0] + room[2] - 1),
                random.randint(room[1], room[1] + room[3] - 1))

    def _place_stairs(self):
        if len(self.rooms) > 0:
            x, y = self._center(self.rooms[-1])
            self.grid[y][x] = STAIRS

    def _occupied(self):
        """Return a set of all tile positions that already have an enemy on them."""
        return {(e.get_x(), e.get_y()) for e in self.enemies}

    def _find_free_tile(self, rooms, max_tries=20):
        """Find a random empty tile to spawn an enemy on. Returns None if it can't find one."""
        taken = self._occupied()
        for _ in range(max_tries):
            x, y = self._rand_in_room(random.choice(rooms))
            if (x, y) not in taken:
                return x, y
        return None

    def _place_enemies(self):
        kinds = list(ENEMY_DEFS.keys())
        kinds.remove("Dungeon Lord")
        count    = 3 + self.floor * 2
        eligible = self.rooms[1:] if len(self.rooms) > 1 else self.rooms
        for _ in range(count):
            pos = self._find_free_tile(eligible)
            if pos is not None:
                ex, ey = pos
                self.enemies.append(Enemy(ex, ey, random.choice(kinds)))

    def _place_boss(self):
        bx, by = self._center(self.rooms[-1])
        self.enemies.append(Enemy(bx - 2, by, "Dungeon Lord"))
        kinds = list(ENEMY_DEFS.keys())
        kinds.remove("Dungeon Lord")
        if len(self.rooms) > 2:
            eligible = self.rooms[1:-1]
        elif len(self.rooms) > 1:
            eligible = self.rooms[1:]
        else:
            eligible = self.rooms
        for _ in range(4):
            pos = self._find_free_tile(eligible)
            if pos is not None:
                ex, ey = pos
                self.enemies.append(Enemy(ex, ey, random.choice(kinds)))

    def _place_items(self, player=None):
        """
        Place items on this floor. Items with a min_floor higher than the
        current floor are excluded so better loot only appears deeper.

        Weapons and shields the player already owns (equipped or in bag)
        are excluded to avoid useless duplicates.
        """
        # Build the set of gear the player already has
        owned_gear = set()
        if player is not None:
            if player.weapon:
                owned_gear.add(player.weapon)
            if player.shield:
                owned_gear.add(player.shield)
            for name in player.inventory:
                defn = ITEM_DEFS[name]
                if defn["effect"] in ("attack", "defense"):
                    owned_gear.add(name)

        eligible_names = []
        for name in ITEM_DEFS:
            defn = ITEM_DEFS[name]
            if defn["min_floor"] > self.floor:
                continue
            # Skip gear the player already has
            if name in owned_gear:
                continue
            eligible_names.append(name)

        # Fallback: if everything is owned, allow consumables at minimum
        if not eligible_names:
            eligible_names = [n for n in ITEM_DEFS
                              if ITEM_DEFS[n]["effect"] in ("heal", "smoke", "throw")]

        count = 2 + self.floor
        for _ in range(count):
            ix, iy = self._rand_in_room(random.choice(self.rooms))
            self.items.append(Item(ix, iy, random.choice(eligible_names)))

    def is_walkable(self, x, y):
        return 0 <= x < MAP_W and 0 <= y < MAP_H and self.grid[y][x] != WALL

    def tile_at(self, x, y):
        return self.grid[y][x]

    def start_position(self):
        return self._center(self.rooms[0])

    def enemy_at(self, x, y):
        for e in self.enemies:
            if e.get_x() == x and e.get_y() == y:
                return e
        return None

    def item_at(self, x, y):
        for it in self.items:
            if it.get_x() == x and it.get_y() == y:
                return it
        return None

    def wall_tile(self, col, row):
        """
        Pick the right wall character based on which neighbors are also walls.
        This makes walls look like connected lines instead of just a bunch of #'s.
        """
        n = row > 0         and self.grid[row-1][col] == WALL
        s = row < MAP_H - 1 and self.grid[row+1][col] == WALL
        w = col > 0         and self.grid[row][col-1] == WALL
        e = col < MAP_W - 1 and self.grid[row][col+1] == WALL

        key = (n, s, w, e)
        # Each combination of neighbors maps to a different line-drawing character
        BOX = {
            # (N,  S,  W,  E)
            (False,False,False,False): "·",   # isolated — dot
            (True, False,False,False): "│",   # N only
            (False,True, False,False): "│",   # S only
            (True, True, False,False): "│",   # N+S  vertical bar
            (False,False,True, False): "─",   # W only
            (False,False,False,True ): "─",   # E only
            (False,False,True, True ): "─",   # W+E  horizontal bar
            (True, False,True, False): "┘",   # N+W
            (True, False,False,True ): "└",   # N+E
            (False,True, True, False): "┐",   # S+W
            (False,True, False,True ): "┌",   # S+E
            (True, True, True, False): "┤",   # N+S+W
            (True, True, False,True ): "├",   # N+S+E
            (True, False,True, True ): "┴",   # N+W+E
            (False,True, True, True ): "┬",   # S+W+E
            (True, True, True, True ): "┼",   # all four
        }
        ch = BOX.get(key, "·")

        # Walls surrounded on all sides are drawn darker so the rooms stand out
        if all(key):
            return COL_WALL_DIM + ch + RESET
        else:
            return COL_WALL + ch + RESET


# ─── Game Logic ───────────────────────────────────────────────────────────────

class Game:
    """Runs the game — creates the dungeon, tracks the player, and handles each turn."""

    def __init__(self):
        self.dungeon  = Dungeon(floor_number=1)
        sx, sy        = self.dungeon.start_position()
        self.player   = Player(sx, sy)
        self._won     = False
        self.player.log("Welcome to Dungeon of Doom!", "system")
        self.player.log("Walk into enemies to attack. Press U to use items.", "system")

    def move_player(self, dx, dy):
        nx = self.player.get_x() + dx
        ny = self.player.get_y() + dy

        enemy = self.dungeon.enemy_at(nx, ny)
        if enemy:
            # 15% chance of a critical hit that deals double damage
            crit = random.random() < 0.15
            raw_dmg = self.player.attack + random.randint(0, 2)
            if crit:
                raw_dmg *= 2
            dmg = max(1, raw_dmg - enemy.defense)
            enemy.hp -= dmg
            if crit:
                self.player.log(f"CRITICAL HIT on {enemy.kind} for {dmg}! ({enemy.hp}/{enemy.max_hp} HP)", "crit")
            else:
                self.player.log(f"You hit {enemy.kind} for {dmg}! ({enemy.hp}/{enemy.max_hp} HP)", "hit")
            if not enemy.is_alive():
                self.player.log(f"{enemy.kind} slain! +{enemy.xp} XP", "hit")
                self.player.gain_xp(enemy.xp)
                self.player.kills += 1
                self.dungeon.enemies.remove(enemy)
                if enemy.is_boss():
                    self._won = True
                    return
            self.player.tick()
            self._enemy_turn()
            return

        if self.dungeon.is_walkable(nx, ny):
            self.player.set_x(nx)
            self.player.set_y(ny)

            item = self.dungeon.item_at(nx, ny)
            if item:
                self.player.pick_up(item.name)
                self.dungeon.items.remove(item)

            if self.dungeon.tile_at(nx, ny) == STAIRS:
                self._descend()
                return

            self.player.tick()
            self._enemy_turn()

    def open_inventory(self):
        """Show the inventory screen and let the player use an item."""
        player = self.player

        while True:
            clear_screen()
            print(COL_TITLE + BOLD + "  ╔══════════════════════════╗")
            print("  ║     I N V E N T O R Y    ║")
            print("  ╚══════════════════════════╝" + RESET)
            print()

            # Show what the player currently has equipped
            wpn = player.weapon if player.weapon else "(none)"
            shd = player.shield if player.shield else "(none)"
            print(COL_HUD + f"  Weapon : " + (COL_ITEM if player.weapon else COL_HUD_DIM) + wpn + RESET)
            print(COL_HUD + f"  Shield : " + (COL_ITEM if player.shield else COL_HUD_DIM) + shd + RESET)

            # Show smoke bomb status if active
            if player.smoke_turns > 0:
                print(COL_DANGER_1 + f"  Smoke  : {player.smoke_turns} turns remaining" + RESET)

            print()
            print(COL_HUD + "  BAG:" + RESET)
            print()

            item_names = list(player.inventory.keys())

            if len(item_names) == 0:
                print(COL_HUD_DIM + "  (empty)" + RESET)
                print()
                print(COL_HUD_DIM + "  Press any key to close." + RESET)
                get_key()
                return

            for i in range(len(item_names)):
                name  = item_names[i]
                count = player.inventory[name]
                sym   = ITEM_DEFS[name]["symbol"]
                eff   = ITEM_DEFS[name]["effect"]

                if eff == "heal":
                    tag = "(potion)"
                elif eff == "smoke":
                    tag = "(consumable)"
                elif eff == "attack":
                    tag = f"(weapon +{ITEM_DEFS[name]['value']} ATK)"
                else:
                    tag = f"(shield +{ITEM_DEFS[name]['value']} DEF)"

                # Warn about the Cursed Blade
                warning = ""
                if name == "Cursed Blade":
                    warning = COL_DEAD + " ⚠ drains 1 HP/turn" + RESET

                print(COL_ITEM + f"  [{i + 1}] {sym} {name} x{count}  "
                      + COL_HUD_DIM + tag + warning + RESET)

            print()
            print(COL_HUD_DIM + f"  Press 1-{len(item_names)} to use, Q to close." + RESET)

            key = get_key()

            if key in ("q", "Q", chr(27), ""):
                return

            if key.isdigit():
                index = int(key) - 1
                if 0 <= index < len(item_names):
                    player.use_item(item_names[index])

    def throw_knife(self):
        """Throw a knife at the nearest visible enemy. Uses one Throwing Knife."""
        player = self.player
        if "Throwing Knife" not in player.inventory:
            player.log("No Throwing Knives! Find one first.", "system")
            return

        px, py = player.get_x(), player.get_y()

        # Find the closest visible enemy
        best_enemy = None
        best_dist  = 999
        for e in self.dungeon.enemies:
            ex, ey = e.get_x(), e.get_y()
            dist = abs(ex - px) + abs(ey - py)
            if dist < best_dist:
                best_dist  = dist
                best_enemy = e

        if best_enemy is None:
            player.log("No visible enemies to target.", "system")
            return

        # Use up one knife
        player._remove_from_bag("Throwing Knife")

        # Knives deal 10 damage and ignore the enemy's defense
        crit = random.random() < 0.15
        dmg  = ITEM_DEFS["Throwing Knife"]["value"] * (2 if crit else 1)
        best_enemy.hp -= dmg

        if crit:
            player.log(f"CRITICAL THROW! Knife hits {best_enemy.kind} for {dmg}!", "crit")
        else:
            player.log(f"Knife hits {best_enemy.kind} for {dmg}! ({best_enemy.hp}/{best_enemy.max_hp} HP)", "hit")

        if not best_enemy.is_alive():
            player.log(f"{best_enemy.kind} slain! +{best_enemy.xp} XP", "hit")
            player.gain_xp(best_enemy.xp)
            player.kills += 1
            self.dungeon.enemies.remove(best_enemy)
            if best_enemy.is_boss():
                self._won = True
                return

        player.tick()
        self._enemy_turn()

    def _enemy_turn(self):
        """Run every enemy's turn — they either attack or move toward the player."""
        px = self.player.get_x()
        py = self.player.get_y()
        smoked = self.player.smoke_turns > 0

        for enemy in list(self.dungeon.enemies):
            dist = abs(enemy.get_x() - px) + abs(enemy.get_y() - py)
            if dist == 1:
                # Enemies that are right next to you still attack even through smoke
                crit = random.random() < 0.15
                raw_dmg = enemy.attack + random.randint(0, 2)
                if crit:
                    raw_dmg *= 2
                dmg = max(1, raw_dmg - self.player.defense)
                self.player.hp -= dmg
                if crit:
                    self.player.log(
                        f"CRITICAL! {enemy.kind} hits you for {dmg}! "
                        f"({self.player.hp}/{self.player.max_hp} HP)", "crit"
                    )
                else:
                    self.player.log(
                        f"{enemy.kind} hits you for {dmg}! "
                        f"({self.player.hp}/{self.player.max_hp} HP)", "damage"
                    )
            elif dist <= 8 and not smoked:
                # If smoke is active, enemies lose track of you and stop chasing
                enemy.move_toward(px, py, self.dungeon)

    def _descend(self):
        self.player.floor += 1
        if self.player.floor == BOSS_FLOOR:
            self.player.log("You sense something ancient and terrible below...", "system")
        else:
            self.player.log(f"Floor {self.player.floor}. Darker still...", "system")
        self.dungeon = Dungeon(floor_number=self.player.floor, player=self.player)
        sx, sy = self.dungeon.start_position()
        self.player.set_x(sx)
        self.player.set_y(sy)

    def is_game_over(self):
        return not self.player.is_alive()

    def is_won(self):
        return self._won

    def save(self):
        # Save the player's stats and inventory to a text file.
        # The dungeon itself isn't saved — it gets regenerated when you load.
        p = self.player
        with open(SAVE_FILE, "w") as f:
            f.write(f"floor={p.floor}\n")
            f.write(f"hp={p.hp}\n")
            f.write(f"max_hp={p.max_hp}\n")
            f.write(f"attack={p.attack}\n")
            f.write(f"defense={p.defense}\n")
            f.write(f"base_atk={p._base_atk}\n")
            f.write(f"base_def={p._base_def}\n")
            f.write(f"xp={p.xp}\n")
            f.write(f"level={p.level}\n")
            f.write(f"kills={p.kills}\n")
            f.write(f"weapon={p.weapon if p.weapon else 'none'}\n")
            f.write(f"shield={p.shield if p.shield else 'none'}\n")
            # Save each inventory item on its own line
            for name, count in p.inventory.items():
                f.write(f"item={name}={count}\n")
        self.player.log("Game saved!", "system")

    def load(self):
        if not os.path.exists(SAVE_FILE):
            self.player.log("No save file found.", "system")
            return

        # Read the save file into a dictionary
        data = {}
        inventory = {}
        with open(SAVE_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("item="):
                    # inventory lines look like: item=Health Potion=2
                    parts = line[5:].rsplit("=", 1)
                    inventory[parts[0]] = int(parts[1])
                elif "=" in line:
                    key, val = line.split("=", 1)
                    data[key] = val

        # Rebuild the player from the saved stats
        new_player = Player(0, 0)
        new_player.floor     = int(data["floor"])
        new_player.hp        = int(data["hp"])
        new_player.max_hp    = int(data["max_hp"])
        new_player.attack    = int(data["attack"])
        new_player.defense   = int(data["defense"])
        new_player._base_atk = int(data["base_atk"])
        new_player._base_def = int(data["base_def"])
        new_player.xp        = int(data["xp"])
        new_player.level     = int(data["level"])
        new_player.kills     = int(data["kills"])
        new_player.weapon    = None if data["weapon"] == "none" else data["weapon"]
        new_player.shield    = None if data["shield"] == "none" else data["shield"]
        new_player.inventory = inventory

        # Generate a fresh dungeon for the saved floor
        # (enemies and items will be different, but the floor number is correct)
        new_dungeon = Dungeon(floor_number=new_player.floor, player=new_player)
        sx, sy = new_dungeon.start_position()
        new_player.set_x(sx)
        new_player.set_y(sy)

        self.player  = new_player
        self.dungeon = new_dungeon
        self._won    = False
        self.player.log("Game loaded! (new dungeon layout for this floor)", "system")


# ─── Rendering ────────────────────────────────────────────────────────────────

def danger_color(floor):
    if floor >= BOSS_FLOOR: return COL_DANGER_3
    elif floor >= 3:        return COL_DANGER_2
    elif floor >= 2:        return COL_DANGER_1
    else:                   return COL_HUD


def render(game):
    """Draw the map, sidebar, and message log to the terminal."""
    dungeon = game.dungeon
    player  = game.player

    # Build lookup dictionaries so we can quickly check if a tile has an enemy or item
    enemy_pos = {}
    for e in dungeon.enemies:
        enemy_pos[(e.get_x(), e.get_y())] = e

    item_pos = {}
    for it in dungeon.items:
        item_pos[(it.get_x(), it.get_y())] = it

    # Build the sidebar content line by line

    raw_sidebar = []   # each entry is one line of sidebar text, padded to the right width

    def sb(colored_text):
        """Pad and store one sidebar line."""
        raw_sidebar.append(pad_to(colored_text, SIDEBAR_W))

    def sb_div():
        """Add a full-width divider line."""
        raw_sidebar.append(COL_SIDEBAR + "─" * SIDEBAR_W + RESET)

    # Floor + danger stars
    dcol  = danger_color(player.floor)
    stars = "★" * player.floor + "☆" * (BOSS_FLOOR - player.floor)
    sb(dcol + BOLD + f" FLOOR {player.floor}  {stars}" + RESET)
    sb_div()

    # Stats
    sb(COL_HUD + f" Lvl {player.level}   ATK {player.attack}  DEF {player.defense}" + RESET)
    hp_bar = make_bar(player.hp, player.max_hp, 10,
                      fg(60, 220, 80), fg(255, 200, 0), fg(220, 50, 50))
    sb(COL_HUD + f" HP {hp_bar} {player.hp}/{player.max_hp}" + RESET)
    xp_bar = make_bar(player.xp, player.level * 20, 10,
                      fg(120, 100, 255), fg(120, 100, 255), fg(120, 100, 255))
    sb(COL_HUD + f" XP {xp_bar} {player.xp}/{player.level * 20}" + RESET)

    # Smoke bomb status
    if player.smoke_turns > 0:
        sb(COL_DANGER_1 + f" Smoke: {player.smoke_turns} turns left" + RESET)

    sb_div()

    # Equipped gear
    sb(COL_HUD_DIM + " EQUIPPED" + RESET)
    wpn_text = player.weapon if player.weapon else "(no weapon)"
    shd_text = player.shield if player.shield else "(no shield)"
    wpn_col  = COL_ITEM if player.weapon else COL_HUD_DIM
    shd_col  = COL_ITEM if player.shield else COL_HUD_DIM
    sb(wpn_col + f" / {wpn_text}" + RESET)
    sb(shd_col + f" [ {shd_text}" + RESET)
    sb_div()

    # Nearby enemies (within distance 6)
    px = player.get_x()
    py = player.get_y()
    nearby = []
    for e in dungeon.enemies:
        dist = abs(e.get_x() - px) + abs(e.get_y() - py)
        if dist <= 6:
            nearby.append((dist, e))

    # Sort enemies by distance (closest first) using a basic bubble sort
    for a in range(len(nearby)):
        for b in range(a + 1, len(nearby)):
            if nearby[b][0] < nearby[a][0]:
                nearby[a], nearby[b] = nearby[b], nearby[a]

    if len(nearby) > 0:
        sb(COL_HUD_DIM + " NEARBY" + RESET)
        shown = 0
        for dist, e in nearby:
            if shown >= 2:
                break
            ecol     = COL_BOSS if e.is_boss() else COL_ENEMY
            ebar     = make_bar(e.hp, e.max_hp, 8,
                                fg(200, 80, 80), fg(200, 80, 80), fg(220, 50, 50))
            name_str = f" {e.symbol} {e.kind}"
            # Truncate to fit, leaving room for the bar
            if len(name_str) > SIDEBAR_W - 1:
                name_str = name_str[:SIDEBAR_W - 1]
            sb(ecol + name_str + RESET)
            hp_str = f" {e.hp}/{e.max_hp}"
            sb(f"  {ebar}" + COL_HUD_DIM + hp_str + RESET)
            shown += 1
    else:
        sb(COL_HUD_DIM + " No enemies nearby" + RESET)

    sb_div()

    # Bag
    sb(COL_HUD_DIM + " BAG" + RESET)
    if len(player.inventory) == 0:
        sb(COL_HUD_DIM + "  (empty)" + RESET)
    else:
        for name in player.inventory:
            sym  = ITEM_DEFS[name]["symbol"]
            line = f" {sym} {name} x{player.inventory[name]}"
            if len(line) > SIDEBAR_W - 1:
                line = line[:SIDEBAR_W - 1]
            sb(COL_ITEM + line + RESET)

    sb_div()
    sb(DIM + " Arrows/WASD: Move" + RESET)
    sb(DIM + " U:Use  F:Throw  S:Save  L:Load" + RESET)
    sb(DIM + " Q:Quit" + RESET)

    # Make sure the sidebar has the same number of rows as the map
    while len(raw_sidebar) < MAP_H:
        raw_sidebar.append(" " * SIDEBAR_W)

    # Now combine the map and sidebar into one output, row by row

    lines = []

    # Title row
    title      = danger_color(player.floor) + BOLD + " DUNGEON OF DOOM" + RESET
    kills_text = COL_HUD_DIM + f"  kills: {player.kills}" + RESET
    lines.append(title + kills_text)

    # Top border
    lines.append(
        COL_SIDEBAR + "─" * MAP_W + "┬" + "─" * SIDEBAR_W + "┐" + RESET
    )

    # Draw each row of the map, then attach the matching sidebar line
    for row in range(MAP_H):
        map_line = ""
        for col in range(MAP_W):
            if col == player.get_x() and row == player.get_y():
                map_line += COL_PLAYER + BOLD + "@" + RESET
            elif (col, row) in enemy_pos:
                e = enemy_pos[(col, row)]
                col_e = COL_BOSS if e.is_boss() else COL_ENEMY
                map_line += col_e + BOLD + e.symbol + RESET
            elif (col, row) in item_pos:
                sym = ITEM_DEFS[item_pos[(col, row)].name]["symbol"]
                map_line += COL_ITEM + BOLD + sym + RESET
            else:
                tile = dungeon.tile_at(col, row)
                if tile == WALL:
                    map_line += dungeon.wall_tile(col, row)
                elif tile == STAIRS:
                    map_line += COL_STAIRS + BOLD + ">" + RESET
                else:
                    map_line += COL_FLOOR + "·" + RESET

        side = raw_sidebar[row] if row < len(raw_sidebar) else " " * SIDEBAR_W
        lines.append(map_line + COL_SIDEBAR + "│" + RESET + side + COL_SIDEBAR + "│" + RESET)

    # Bottom border
    lines.append(
        COL_SIDEBAR + "─" * MAP_W + "┴" + "─" * SIDEBAR_W + "┘" + RESET
    )

    # Print the last few messages, coloring them based on what kind of event they are
    TAG_COLORS = {
        "hit":    COL_MSG_HIT,
        "damage": COL_MSG_DAMAGE,
        "crit":   COL_MSG_CRIT,
        "pickup": COL_MSG_PICKUP,
        "level":  COL_MSG_LEVEL,
        "heal":   COL_MSG_HEAL,
        "system": COL_MSG_SYSTEM,
    }
    recent = player.messages[-4:]
    for i, (msg, tag) in enumerate(recent):
        if i == len(recent) - 1:
            color = TAG_COLORS.get(tag, COL_HUD)   # newest message is full color
        else:
            color = COL_LOG_OLD                      # older messages are dimmed
        lines.append(color + "  " + msg + RESET)
    for _ in range(4 - len(recent)):
        lines.append("")

    clear_screen()
    print("\n".join(lines))


# ─── Screens ──────────────────────────────────────────────────────────────────

def show_title():
    clear_screen()
    print(COL_TITLE + BOLD)
    print("  ╔══════════════════════════════════════╗")
    print("  ║                                      ║")
    print("  ║        D U N G E O N                 ║")
    print("  ║              O F                     ║")
    print("  ║                  D O O M             ║")
    print("  ║                                      ║")
    print("  ╚══════════════════════════════════════╝")
    print(RESET + COL_HUD)
    print("  Descend five floors. Defeat the Dungeon Lord. Survive.")
    print()
    print(COL_HUD_DIM + "  Controls:" + RESET)
    print("    Arrow keys / WASD   Move and attack")
    print("    U                   Open inventory / use items")
    print("    F                   Throw knife at nearest visible enemy")
    print("    S / L               Save / Load")
    print("    Q                   Quit")
    print()
    print(COL_HUD_DIM + "  Items:" + RESET)
    print(f"    {COL_ITEM}!{COL_HUD} Health Potion  "
          f"{COL_ITEM}%{COL_HUD} Bread  "
          f"{COL_ITEM}o{COL_HUD} Smoke Bomb")
    print(f"    {COL_ITEM}/ * f †{COL_HUD} Weapons  "
          f"  {COL_ITEM}[ }}{COL_HUD} Shields")
    print()
    print(COL_HUD_DIM + "  Press any key to begin..." + RESET)
    get_key()


def show_death(player):
    clear_screen()
    print(COL_DEAD + BOLD)
    print("  ╔══════════════════════════════════════╗")
    print("  ║                                      ║")
    print("  ║          Y O U   D I E D             ║")
    print("  ║                                      ║")
    print("  ╚══════════════════════════════════════╝")
    print(RESET)
    print(COL_HUD + f"  Floor reached : {player.floor}")
    print(f"  Level         : {player.level}")
    print(f"  Enemies slain : {player.kills}" + RESET)
    print()
    print(COL_HUD_DIM + "  Press any key to exit..." + RESET)
    get_key()


def show_win(player):
    clear_screen()
    print(COL_WIN + BOLD)
    print("  ╔══════════════════════════════════════╗")
    print("  ║                                      ║")
    print("  ║      V I C T O R Y !                 ║")
    print("  ║                                      ║")
    print("  ║  The Dungeon Lord has been defeated!  ║")
    print("  ║                                      ║")
    print("  ╚══════════════════════════════════════╝")
    print(RESET)
    print(COL_HUD + f"  Final level   : {player.level}")
    print(f"  Enemies slain : {player.kills}" + RESET)
    print()
    print(COL_HUD_DIM + "  Press any key to exit..." + RESET)
    get_key()


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    show_title()
    game = Game()

    while True:
        render(game)

        if game.is_won():
            show_win(game.player)
            break

        if game.is_game_over():
            show_death(game.player)
            break

        key = get_key()

        if   key in ("w", "UP"):    game.move_player(0, -1)
        elif key in ("s", "DOWN"):  game.move_player(0,  1)
        elif key in ("a", "LEFT"):  game.move_player(-1, 0)
        elif key in ("d", "RIGHT"): game.move_player(1,  0)
        elif key in ("u", "U"):     game.open_inventory()
        elif key in ("f", "F"):     game.throw_knife()
        elif key == "S":            game.save()
        elif key in ("l", "L"):     game.load()
        elif key in ("q", "Q"):     break


if __name__ == "__main__":
    main()
