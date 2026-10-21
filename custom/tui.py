from os import name as os_name
import sys
from typing import Sequence


def _get_key_unix() -> str:
    """Reads a single keypress on Unix/Linux."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":  # Escape sequence
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                if ch3 == "A":
                    return "up"
                elif ch3 == "B":
                    return "down"
                elif ch3 == "C":
                    return "right"
                elif ch3 == "D":
                    return "left"
            return "esc"
        elif ch in ("\r", "\n"):
            return "enter"
        elif ch == " ":
            return "space"
        elif ch == "\x03":  # Ctrl+C
            return "ctrl_c"
        elif ch in ("k", "K"):
            return "up"
        elif ch in ("j", "J"):
            return "down"
        elif ch in ("a", "A"):
            return "toggle_all"
        elif ch in ("q", "Q"):
            return "quit"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _get_key_win() -> str:
    """Reads a single keypress on Windows."""
    import msvcrt

    ch = msvcrt.getch()
    if ch in (b"\x00", b"\xe0"):
        ch2 = msvcrt.getch()
        if ch2 == b"H":
            return "up"
        elif ch2 == b"P":
            return "down"
        elif ch2 == b"K":
            return "left"
        elif ch2 == b"M":
            return "right"
        return "unknown"
    elif ch in (b"\r", b"\n"):
        return "enter"
    elif ch == b" ":
        return "space"
    elif ch == b"\x03":
        return "ctrl_c"
    elif ch in (b"k", b"K"):
        return "up"
    elif ch in (b"j", b"J"):
        return "down"
    elif ch in (b"a", b"A"):
        return "toggle_all"
    elif ch in (b"q", b"Q"):
        return "quit"
    elif ch == b"\x1b":
        return "esc"
    return ch.decode("latin1", errors="ignore")


def read_key() -> str:
    """Reads a single key in raw mode across platforms."""
    if os_name == "nt":
        return _get_key_win()
    return _get_key_unix()


def checklist_select(
    items: Sequence[tuple[str, str]],
    title: str = "Select directories to download:",
    default_all: bool = True,
) -> list[str] | None:
    """
    Displays an interactive terminal checklist (TUI) for selecting multiple items.

    :param items: List of tuples (item_id, item_label).
    :param title: Header prompt displayed above the checklist.
    :param default_all: Whether all items should be checked by default.
    :return: List of selected item_ids, or None if cancelled.
    """
    if not items:
        return []

    # Non-interactive / pipe fallback
    if not sys.stdin.isatty():
        sys.stdout.write(f"{title}\n")
        for idx, (_, label) in enumerate(items, 1):
            sys.stdout.write(f"  [{idx}] {label}\n")
        sys.stdout.write(
            "Enter numbers separated by spaces (or press Enter for all): "
        )
        sys.stdout.flush()
        try:
            line = sys.stdin.readline().strip()
            if not line:
                return [item_id for item_id, _ in items]
            indexes = {int(x) for x in line.split() if x.isdigit()}
            return [
                items[i - 1][0]
                for i in sorted(indexes)
                if 1 <= i <= len(items)
            ]
        except (KeyboardInterrupt, EOFError):
            return None

    selected: set[int] = set(range(len(items))) if default_all else set()
    cursor: int = 0
    total = len(items)

    # ANSI Codes
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    CLEAR_LINE = "\033[2K\r"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    previous_lines_count = 0

    try:
        while True:
            # Build screen buffer
            output_lines: list[str] = []
            output_lines.append(f"{BOLD}{CYAN}{title}{RESET}")
            output_lines.append(
                f"  {BOLD}[↑/↓ or j/k]{RESET} Move  "
                f"{BOLD}[Space]{RESET} Toggle  "
                f"{BOLD}[a]{RESET} All/None  "
                f"{BOLD}[Enter]{RESET} Confirm  "
                f"{BOLD}[q/Esc]{RESET} Cancel"
            )
            output_lines.append("")

            for idx, (_, label) in enumerate(items):
                is_checked = idx in selected
                is_cursor = idx == cursor

                check_mark = f"{GREEN}[x]{RESET}" if is_checked else "[ ]"
                pointer = f"{CYAN}>{RESET}" if is_cursor else " "

                if is_cursor:
                    line = f" {pointer} {check_mark} {BOLD}{label}{RESET}"
                else:
                    line = f" {pointer} {check_mark} {label}"
                output_lines.append(line)

            output_lines.append("")
            output_lines.append(f"  ({len(selected)} of {total} selected)")

            # Clear previous render and write new render
            if previous_lines_count > 0:
                # Move cursor up to overwrite
                sys.stdout.write(f"\033[{previous_lines_count}A")

            for line in output_lines:
                sys.stdout.write(f"{CLEAR_LINE}{line}\n")
            sys.stdout.flush()

            previous_lines_count = len(output_lines)

            # Wait for keypress
            key = read_key()

            if key == "up":
                cursor = (cursor - 1) % total
            elif key == "down":
                cursor = (cursor + 1) % total
            elif key == "space":
                if cursor in selected:
                    selected.remove(cursor)
                else:
                    selected.add(cursor)
            elif key == "toggle_all":
                if len(selected) == total:
                    selected.clear()
                else:
                    selected = set(range(total))
            elif key == "enter":
                # Confirm selection
                sys.stdout.write(f"\n{BOLD}Selection confirmed ({len(selected)} items).{RESET}\n")
                sys.stdout.flush()
                return [items[i][0] for i in sorted(selected)]
            elif key in ("esc", "quit", "ctrl_c"):
                sys.stdout.write(f"\nSelection cancelled.\n")
                sys.stdout.flush()
                return None

    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()
