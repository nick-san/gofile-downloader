from typing import Any
from .tui import checklist_select
from .loader import load_original_module


def prompt_directory_action(
    dir_children: list[dict[str, Any]],
    has_files: bool = True,
) -> tuple[str, list[str] | None]:
    """
    Prompts the user when directory(ies) are present in the target download link.

    :param dir_children: List of child items that are directories.
    :param has_files: Whether there are other contents (files) at the root level.
    :return: A tuple of (action, selected_directory_ids), where action is one of:
             'exclude', 'selected', 'all', 'cancel'.
    """
    orig = load_original_module()
    dir_count = len(dir_children)

    if dir_count == 0:
        return "all", None

    # Case 1: Exactly 1 directory
    if dir_count == 1:
        dir_name = dir_children[0].get("name", "Unknown")
        orig._print(
            f"{orig.NEW_LINE}"
            f"======================================================================{orig.NEW_LINE}"
            f"Notice: The link contains 1 directory in addition to other contents:{orig.NEW_LINE}"
            f"  - {dir_name}{orig.NEW_LINE}"
            f"----------------------------------------------------------------------{orig.NEW_LINE}"
            f"[1] Exclude directory and download other contents only{orig.NEW_LINE}"
            f"    (そのディレクトリを除外して、それ以外のコンテンツをダウンロード){orig.NEW_LINE}"
            f"[2] Download everything including directory{orig.NEW_LINE}"
            f"    (ディレクトリを含めてすべてダウンロード){orig.NEW_LINE}"
            f"[3] Cancel{orig.NEW_LINE}"
            f"    (キャンセル){orig.NEW_LINE}"
            f"======================================================================{orig.NEW_LINE}"
        )

        while True:
            try:
                choice = input("Select an option [1/2/3]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                orig._print(f"{orig.NEW_LINE}")
                return "cancel", None

            if choice in ("1", "exclude", "e"):
                return "exclude", None
            elif choice in ("2", "all", "a"):
                return "all", None
            elif choice in ("3", "cancel", "c", "q", "quit"):
                return "cancel", None
            else:
                orig._print(f"Invalid option '{choice}'. Please enter 1, 2, or 3.{orig.NEW_LINE}")

    # Case 2: Multiple directories (2 or more)
    dir_items = [
        (c.get("id", str(idx)), c.get("name", f"Directory {idx}"))
        for idx, c in enumerate(dir_children, 1)
    ]

    orig._print(
        f"{orig.NEW_LINE}"
        f"======================================================================{orig.NEW_LINE}"
        f"Notice: The link contains {dir_count} directories.{orig.NEW_LINE}"
        f"Directories found:{orig.NEW_LINE}"
    )
    for _, name in dir_items:
        orig._print(f"  - {name}{orig.NEW_LINE}")
    orig._print(
        f"----------------------------------------------------------------------{orig.NEW_LINE}"
    )

    if has_files:
        orig._print(
            f"[1] Exclude all directories and download other contents only{orig.NEW_LINE}"
            f"    (すべてのディレクトリを除外して、それ以外のコンテンツをダウンロード){orig.NEW_LINE}"
            f"[2] Select directories to download [TUI Checklist]{orig.NEW_LINE}"
            f"    (ダウンロードするディレクトリをチェックリストで選択){orig.NEW_LINE}"
            f"[3] Download everything including all directories{orig.NEW_LINE}"
            f"    (すべてのディレクトリを含めてダウンロード){orig.NEW_LINE}"
            f"[4] Cancel{orig.NEW_LINE}"
            f"    (キャンセル){orig.NEW_LINE}"
            f"======================================================================{orig.NEW_LINE}"
        )
        while True:
            try:
                choice = input("Select an option [1/2/3/4]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                orig._print(f"{orig.NEW_LINE}")
                return "cancel", None

            if choice in ("1", "exclude", "e"):
                return "exclude", None
            elif choice in ("2", "select", "s"):
                selected_ids = checklist_select(
                    dir_items,
                    title="Select directories to download:",
                    default_all=True,
                )
                if selected_ids is None:
                    return "cancel", None
                return "selected", selected_ids
            elif choice in ("3", "all", "a"):
                return "all", None
            elif choice in ("4", "cancel", "c", "q", "quit"):
                return "cancel", None
            else:
                orig._print(f"Invalid option '{choice}'. Please enter 1, 2, 3, or 4.{orig.NEW_LINE}")
    else:
        orig._print(
            f"[1] Select directories to download [TUI Checklist]{orig.NEW_LINE}"
            f"    (ダウンロードするディレクトリをチェックリストで選択){orig.NEW_LINE}"
            f"[2] Download everything including all directories{orig.NEW_LINE}"
            f"    (すべてのディレクトリを含めてダウンロード){orig.NEW_LINE}"
            f"[3] Cancel{orig.NEW_LINE}"
            f"    (キャンセル){orig.NEW_LINE}"
            f"======================================================================{orig.NEW_LINE}"
        )
        while True:
            try:
                choice = input("Select an option [1/2/3]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                orig._print(f"{orig.NEW_LINE}")
                return "cancel", None

            if choice in ("1", "select", "s"):
                selected_ids = checklist_select(
                    dir_items,
                    title="Select directories to download:",
                    default_all=True,
                )
                if selected_ids is None:
                    return "cancel", None
                return "selected", selected_ids
            elif choice in ("2", "all", "a"):
                return "all", None
            elif choice in ("3", "cancel", "c", "q", "quit"):
                return "cancel", None
            else:
                orig._print(f"Invalid option '{choice}'. Please enter 1, 2, or 3.{orig.NEW_LINE}")
