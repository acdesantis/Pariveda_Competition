"""
ARCADE LAUNCHER
===============
Choose a game and play!

Run with: python main.py
"""

import sys
import os


# ─── Single-keypress input ────────────────────────────────────────────────────

if sys.platform == "win32":
    import msvcrt
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7
    )

    def get_key():
        ch = msvcrt.getwch()
        if ch == chr(224):
            d = msvcrt.getwch()
            if d == "H": return "UP"
            if d == "P": return "DOWN"
            if d == "K": return "LEFT"
            if d == "M": return "RIGHT"
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
                    if ch3 == "A": return "UP"
                    if ch3 == "B": return "DOWN"
                    if ch3 == "D": return "LEFT"
                    if ch3 == "C": return "RIGHT"
                return ""
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def clear_screen():
    os.system("cls" if sys.platform == "win32" else "clear")


# ─── Colors ───────────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"

def fg(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

COL_TITLE    = fg(255, 180, 0)
COL_HUD      = fg(200, 200, 200)
COL_HUD_DIM  = fg(120, 120, 120)
COL_SELECT   = fg(0,   220, 255)    # highlighted selection
COL_DUNGEON  = fg(255, 120, 50)     # dungeon game color
COL_BORDER   = fg(80,  80,  120)


# ─── Game registry ────────────────────────────────────────────────────────────
#
# To add a new game later, just add an entry here and create the matching file.
# Each entry needs:
#   "title"    — display name shown in the menu
#   "subtitle" — one-line description
#   "color"    — the color used to highlight this game's entry
#   "module"   — the Python filename (without .py)
#   "function" — the function inside that file to call to start the game

GAMES = [
    {
        "title":    "Dungeon of Doom",
        "subtitle": "Descend 5 floors. Defeat the Dungeon Lord.",
        "color":    COL_DUNGEON,
        "module":   "dungeon",
        "function": "main",
    },
]


# ─── Launcher screen ──────────────────────────────────────────────────────────

def show_launcher(selected):
    """
    Draw the launcher menu. `selected` is the index of the currently
    highlighted game (0 = first game, 1 = second, etc.).
    """
    clear_screen()

    print(COL_TITLE + BOLD)
    print("  ╔══════════════════════════════════════════╗")
    print("  ║                                          ║")
    print("  ║        T E R M I N A L   A R C A D E    ║")
    print("  ║                                          ║")
    print("  ╚══════════════════════════════════════════╝")
    print(RESET)
    print(COL_HUD_DIM + "  Use arrow keys to select, Enter to play, Q to quit." + RESET)
    print()

    for i in range(len(GAMES)):
        game = GAMES[i]

        if i == selected:
            # Highlighted entry — show with arrow and bright color
            marker = COL_SELECT + BOLD + "  ▶  " + RESET
            title  = game["color"] + BOLD + game["title"] + RESET
            sub    = COL_HUD + "     " + game["subtitle"] + RESET
        else:
            # Unselected entry — dimmer
            marker = "     "
            title  = COL_HUD_DIM + game["title"] + RESET
            sub    = COL_HUD_DIM + "     " + game["subtitle"] + RESET

        print(marker + title)
        print(sub)
        print()

    print(COL_HUD_DIM + "  " + "─" * 42 + RESET)
    print(COL_HUD_DIM + "  All games run in this terminal window." + RESET)
    print(COL_HUD_DIM + "  Press Q at any time inside a game to return here." + RESET)


def launch_game(index):
    """
    Import the selected game's module and call its entry function.
    Using __import__ lets us load the file by name as a string,
    which is cleaner than a big if/elif chain.
    """
    game   = GAMES[index]
    module = __import__(game["module"])          # e.g. import dungeon
    fn     = getattr(module, game["function"])   # e.g. dungeon.main
    fn()                                          # run it


# ─── Main launcher loop ───────────────────────────────────────────────────────

def main():
    selected = 0

    while True:
        show_launcher(selected)

        key = get_key()

        if key in ("UP", "w"):
            # Move selection up, wrap around
            selected = selected - 1
            if selected < 0:
                selected = len(GAMES) - 1

        elif key in ("DOWN", "s"):
            # Move selection down, wrap around
            selected = selected + 1
            if selected >= len(GAMES):
                selected = 0

        elif key in ("\r", "\n", "d", "RIGHT"):
            # Enter or right arrow — launch the selected game
            launch_game(selected)
            # When the game returns (player quit), come back to menu

        elif key in ("q", "Q"):
            # Quit the launcher entirely
            clear_screen()
            print(COL_HUD + "  Thanks for playing. Goodbye!" + RESET)
            print()
            break

        # Any other key is ignored — just redraw the menu


if __name__ == "__main__":
    main()
