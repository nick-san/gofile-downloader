from pathlib import Path
from .loader import load_original_module
from .downloader import CustomDownloader

orig = load_original_module()


class CustomManager(orig.Manager):
    """
    CustomManager

    Uses CustomDownloader instead of original Downloader for managing download tasks.
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

                password: str | None = (
                    self._password
                    if self._password
                    else line_splitted[1].strip()
                    if len(line_splitted) > 1
                    else self._password
                )
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
