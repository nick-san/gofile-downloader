#! /usr/bin/env python3

from pathlib import Path
import sys

from custom.loader import load_original_module
from custom.manager import CustomManager


def main() -> None:
    orig = load_original_module()
    url_or_file: str | None = None
    password: str | None = None
    argc: int = len(sys.argv)

    if argc > 1:
        url_or_file = sys.argv[1]

        if argc > 2:
            password = sys.argv[2]

        manager: CustomManager = CustomManager(url_or_file=url_or_file, password=password)
        manager.run()
    else:
        orig.die(
            f"Usage:"
            f"{orig.NEW_LINE}"
            f"python {Path(__file__).name} https://gofile.io/d/contentid"
            f"{orig.NEW_LINE}"
            f"python {Path(__file__).name} https://gofile.io/d/contentid password"
        )


if __name__ == "__main__":
    main()
