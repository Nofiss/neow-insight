from __future__ import annotations

from pathlib import Path

from core.watcher.watcher import DebouncedRunFileHandler


class _FakeEvent:
    def __init__(self, path: Path, *, is_directory: bool = False) -> None:
        self.src_path = str(path)
        self.is_directory = is_directory


def test_handler_accepts_history_run_files(tmp_path: Path):
    saves_path = tmp_path / "saves"
    history_path = saves_path / "history"
    history_path.mkdir(parents=True)
    current_run_path = saves_path / "current_run.save"
    observed: list[Path] = []

    handler = DebouncedRunFileHandler(
        history_path=history_path,
        current_run_path=current_run_path,
        on_change=observed.append,
        debounce_seconds=0,
    )

    run_file = history_path / "test.run"
    handler.on_created(_FakeEvent(run_file))

    assert observed == [run_file.resolve(strict=False)]


def test_handler_accepts_current_run_save(tmp_path: Path):
    saves_path = tmp_path / "saves"
    history_path = saves_path / "history"
    history_path.mkdir(parents=True)
    current_run_path = saves_path / "current_run.save"
    observed: list[Path] = []

    handler = DebouncedRunFileHandler(
        history_path=history_path,
        current_run_path=current_run_path,
        on_change=observed.append,
        debounce_seconds=0,
    )

    handler.on_modified(_FakeEvent(current_run_path))

    assert observed == [current_run_path.resolve(strict=False)]


def test_handler_ignores_non_supported_files(tmp_path: Path):
    saves_path = tmp_path / "saves"
    history_path = saves_path / "history"
    history_path.mkdir(parents=True)
    current_run_path = saves_path / "current_run.save"
    observed: list[Path] = []

    handler = DebouncedRunFileHandler(
        history_path=history_path,
        current_run_path=current_run_path,
        on_change=observed.append,
        debounce_seconds=0,
    )

    handler.on_created(_FakeEvent(saves_path / "notes.txt"))
    handler.on_created(_FakeEvent(history_path / "test.save"))

    assert observed == []
