import importlib.util
from pathlib import Path
import sys
from types import ModuleType

_cached_module: ModuleType | None = None


def load_original_module(script_path: Path | None = None) -> ModuleType:
    """
    Dynamically loads the original gofile-downloader.py as a module.
    Caches the loaded module for subsequent imports.
    """
    global _cached_module
    if _cached_module is not None:
        return _cached_module

    if script_path is None:
        # Expected to be located in the parent directory of this 'custom' package
        script_path = Path(__file__).resolve().parent.parent / "gofile-downloader.py"

    if not script_path.is_file():
        sys.exit(f"Error: Original gofile-downloader.py not found at {script_path}")

    spec = importlib.util.spec_from_file_location("orig_gofile_downloader", script_path)
    if spec is None or spec.loader is None:
        sys.exit(f"Error: Could not load module spec for {script_path}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules["orig_gofile_downloader"] = mod
    spec.loader.exec_module(mod)

    _cached_module = mod
    return mod
