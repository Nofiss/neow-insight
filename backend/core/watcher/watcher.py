from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver


class DebouncedRunFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        history_path: Path,
        current_run_path: Path,
        on_change: Callable[[Path], None],
        debounce_seconds: float = 0.4,
    ):
        self.history_path = history_path.resolve(strict=False)
        self.current_run_path = current_run_path.resolve(strict=False)
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self._last_processed: dict[Path, float] = {}

    def _is_supported_run_file(self, path: Path) -> bool:
        resolved = path.resolve(strict=False)
        if resolved == self.current_run_path:
            return True
        return resolved.parent == self.history_path and resolved.suffix == ".run"

    def _handle_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode(errors="ignore")
        path = Path(src_path)
        if not self._is_supported_run_file(path):
            return

        resolved_path = path.resolve(strict=False)

        now = time.time()
        previous = self._last_processed.get(resolved_path)
        if previous is not None and now - previous < self.debounce_seconds:
            return

        self._last_processed[resolved_path] = now
        self.on_change(resolved_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle_event(event)


def start_watcher(
    history_path: Path,
    current_run_path: Path,
    on_change: Callable[[Path], None],
    debounce_seconds: float = 0.4,
) -> BaseObserver:
    observer = Observer()
    handler = DebouncedRunFileHandler(
        history_path=history_path,
        current_run_path=current_run_path,
        on_change=on_change,
        debounce_seconds=debounce_seconds,
    )
    watch_roots = {
        history_path.resolve(strict=False),
        current_run_path.parent.resolve(strict=False),
    }
    for root in watch_roots:
        if root.exists() and root.is_dir():
            observer.schedule(handler, str(root), recursive=False)
    observer.start()
    return observer
