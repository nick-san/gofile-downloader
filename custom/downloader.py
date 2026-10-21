from pathlib import Path
from typing import Any
from requests import Response

from .loader import load_original_module
from .prompt import prompt_directory_action

orig = load_original_module()


class CustomDownloader(orig.Downloader):
    """
    CustomDownloader

    Extends the original Downloader to allow interactive selection or exclusion
    of directories when the target download link contains directory structures.
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

    def _get_response(self, **kwargs: Any) -> Response | None:
        """
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

        # Check if this request is fetching metadata for the root content
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

                        # Prompt if there are directories present
                        if dir_children:
                            action, selected_ids = prompt_directory_action(
                                dir_children=dir_children,
                                has_files=bool(file_children),
                            )

                            if action == "cancel":
                                self._cancelled = True
                                self._stop_event.set()
                                data["children"] = {}
                                response.json = lambda: json_data

                            elif action == "exclude":
                                filtered_children = {
                                    k: v for k, v in children.items()
                                    if v.get("type") != "folder"
                                }
                                data["children"] = filtered_children
                                response.json = lambda: json_data

                            elif action == "selected":
                                selected_set = set(selected_ids or [])
                                filtered_children = {
                                    k: v for k, v in children.items()
                                    if v.get("type") != "folder" or v.get("id") in selected_set
                                }
                                data["children"] = filtered_children
                                response.json = lambda: json_data

                            elif action == "all":
                                pass
            except Exception:
                pass

        return response

    def run(self) -> None:
        """
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
