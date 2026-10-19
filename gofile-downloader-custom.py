#! /usr/bin/env python3

import importlib.util
from pathlib import Path
import sys
from typing import Any
from requests import Response

# ---------------------------------------------------------------------------
# Dynamically load the original gofile-downloader.py from the same directory
# ---------------------------------------------------------------------------
ORIG_SCRIPT_PATH = Path(__file__).resolve().parent / "gofile-downloader.py"
if not ORIG_SCRIPT_PATH.is_file():
    sys.exit(f"Error: Original script not found at {ORIG_SCRIPT_PATH}")

spec = importlib.util.spec_from_file_location("orig_gofile_downloader", ORIG_SCRIPT_PATH)
if spec is None or spec.loader is None:
    sys.exit(f"Error: Could not load spec for {ORIG_SCRIPT_PATH}")

orig = importlib.util.module_from_spec(spec)
sys.modules["orig_gofile_downloader"] = orig
spec.loader.exec_module(orig)


class CustomDownloader(orig.Downloader):
    """
    CustomDownloader

    Extends the original Downloader to prompt the user for action when
    the target download link contains directory(ies) in addition to other contents.
    """

    def __init__(
        self,
        root_dir: Path,
        interactive: bool,
        max_workers: int,
        number_retries,
        timeout: float,
        chunk_size: int,
        stop_event,
        session,
        url: str,
        password: str | None = None,
        prompt_on_directories: bool = True,
    ) -> None:
        super().__init__(
            root_dir,
            interactive,
            max_workers,
            number_retries,
            timeout,
            chunk_size,
            stop_event,
            session,
            url,
            password,
        )
        self._prompt_on_directories: bool = prompt_on_directories
        self._cancelled: bool = False

    def _prompt_directory_action(self, dir_children: list[dict[str, Any]]) -> str:
        """
        _prompt_directory_action

        Prompts user when the download link contains directory(ies) in addition to other contents.

        :param dir_children: list of directory child entries.
        :return: 'exclude', 'all', or 'cancel'.
        """
        dir_names: list[str] = [str(c.get("name", "Unknown")) for c in dir_children]
        orig._print(
            f"{orig.NEW_LINE}"
            f"======================================================================{orig.NEW_LINE}"
            f"Notice: The link contains directory(ies) in addition to other contents:{orig.NEW_LINE}"
        )
        for name in dir_names:
            orig._print(f"  - {name}{orig.NEW_LINE}")
        orig._print(
            f"----------------------------------------------------------------------{orig.NEW_LINE}"
            f"[1] Exclude directories and download other contents only{orig.NEW_LINE}"
            f"    (そのディレクトリを除外して、それ以外のコンテンツをダウンロード){orig.NEW_LINE}"
            f"[2] Download everything including directories{orig.NEW_LINE}"
            f"    (ディレクトリを含めてすべてダウンロード){orig.NEW_LINE}"
            f"[3] Cancel{orig.NEW_LINE}"
            f"    (キャンセル){orig.NEW_LINE}"
            f"======================================================================{orig.NEW_LINE}"
        )

        while True:
            try:
                choice: str = input("Select an option [1/2/3]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                orig._print(f"{orig.NEW_LINE}")
                return "cancel"

            if choice in ("1", "exclude", "e"):
                return "exclude"
            elif choice in ("2", "all", "a"):
                return "all"
            elif choice in ("3", "cancel", "c", "q", "quit"):
                return "cancel"
            else:
                orig._print(f"Invalid option '{choice}'. Please enter 1, 2, or 3.{orig.NEW_LINE}")

    def _get_response(self, **kwargs: Any) -> Response | None:
        """
        _get_response

        Intercepts the API response for the root content folder to check
        for directory children and prompt the user if needed.
        """
        response: Response | None = super()._get_response(**kwargs)
        if not response or not self._prompt_on_directories:
            return response

        url: str = str(kwargs.get("url", ""))

        try:
            content_id: str = self._url.split("/")[-1]
        except Exception:
            return response

        # Check if this request is fetching the metadata of the root content
        if f"/contents/{content_id}?" in url or url.endswith(f"/contents/{content_id}"):
            try:
                json_data: dict[str, Any] = response.json()
                if json_data.get("status") == "ok":
                    data: dict[str, Any] = json_data.get("data", {})
                    if data.get("type") == "folder":
                        children: dict[str, Any] = data.get("children", {})
                        dir_children: list[dict[str, Any]] = [
                            c for c in children.values() if c.get("type") == "folder"
                        ]
                        file_children: list[dict[str, Any]] = [
                            c for c in children.values() if c.get("type") != "folder"
                        ]

                        if dir_children and file_children:
                            choice: str = self._prompt_directory_action(dir_children)
                            if choice == "cancel":
                                self._cancelled = True
                                self._stop_event.set()
                                # Clear children so no files or directories are registered
                                data["children"] = {}
                                response.json = lambda: json_data
                            elif choice == "exclude":
                                # Filter out folder children so only files are registered and downloaded
                                filtered_children = {
                                    k: v for k, v in children.items() if v.get("type") != "folder"
                                }
                                data["children"] = filtered_children
                                response.json = lambda: json_data
                            elif choice == "all":
                                # Keep everything as-is
                                pass
            except Exception:
                pass

        return response

    def run(self) -> None:
        """
        run

        Custom run method to handle graceful exit without error messages when cancelled.
        """
        try:
            if not self._url.split("/")[-2] == "d":
                orig._print(f"The url probably doesn't have an id in it: {self._url}.{orig.NEW_LINE}")
                return
            content_id: str = self._url.split("/")[-1]
        except IndexError:
            orig._print(f"{self._url} doesn't seem a valid url.{orig.NEW_LINE}")
            return

        _password: str | None = orig.sha256(self._password.encode()).hexdigest() if self._password else None
        content_dir: Path = self._root_dir / content_id

        self._create_dirs(content_dir)

        self._build_content_tree_structure(content_dir, content_id, _password)

        if self._cancelled:
            self._remove_dir(content_dir)
            orig._print(f"Download cancelled.{orig.NEW_LINE}")
            return

        if content_dir.exists() and not any(content_dir.iterdir()) and not self._files_info:
            orig._print(f"Empty directory for url: {self._url}, nothing done.{orig.NEW_LINE}")
            self._remove_dir(content_dir)
            return

        if self._interactive:
            self._do_interactive(content_dir)

        self._threaded_downloads()


class CustomManager(orig.Manager):
    """
    CustomManager

    Uses CustomDownloader instead of Downloader for managing download tasks.
    """

    def _parse_url_or_file(self) -> None:
        source: str = self._url_or_file.strip()
        filepath: Path = Path(source).expanduser()
        url: str | None = self._normalize_http_url(source)

        if not filepath.is_file() and not url:
            orig.die(f"{source} is either a valid url or local url file.")

        if not filepath.is_file() and url:
            downloader: CustomDownloader = CustomDownloader(
                self._root_dir,
                self._interactive,
                self._max_workers,
                self._number_retries,
                self._timeout,
                self._chunk_size,
                self._stop_event,
                self._session,
                url,
                self._password,
                prompt_on_directories=True,
            )

            downloader.run()
            return

        with open(filepath, "r") as f:
            lines: list[str] = f.readlines()

        max_workers: int = self._max_workers if self._max_workers <= 10 else 10

        with orig.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for line in lines:
                if self._stop_event.is_set():
                    return

                line_splitted: list[str] = line.split(" ")
                source = line_splitted[0].strip()
                url = self._normalize_http_url(source)

                if not url:
                    orig._print(f"{source} is not a valid url.")
                    continue

                password: str | None = self._password if self._password else line_splitted[1].strip() \
                    if len(line_splitted) > 1 else self._password
                downloader: CustomDownloader = CustomDownloader(
                    self._root_dir,
                    False,
                    self._max_workers,
                    self._number_retries,
                    self._timeout,
                    self._chunk_size,
                    self._stop_event,
                    self._session,
                    url,
                    password,
                    prompt_on_directories=False,
                )

                executor.submit(downloader.run)


if __name__ == "__main__":
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
