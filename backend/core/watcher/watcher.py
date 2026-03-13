from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver


class DebouncedRunFileHandler(FileSystemEventHandler):
    def __init__(
        self, on_change: Callable[[Path], None], debounce_seconds: float = 0.4
    ):
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self._last_processed: dict[Path, float] = {}

    def _handle_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode(errors="ignore")
        path = Path(src_path)
        if path.suffix != ".run":
            return

        now = time.time()
        previous = self._last_processed.get(path)
        if previous is not None and now - previous < self.debounce_seconds:
            return

        self._last_processed[path] = now
        self.on_change(path)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle_event(event)


def start_watcher(
    path: Path, on_change: Callable[[Path], None], debounce_seconds: float = 0.4
) -> BaseObserver:
    observer = Observer()
    handler = DebouncedRunFileHandler(
        on_change=on_change, debounce_seconds=debounce_seconds
    )
    observer.schedule(handler, str(path), recursive=False)
    observer.start()
    return observer
