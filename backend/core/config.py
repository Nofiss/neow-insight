from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Settings:
    db_path: Path
    saves_path: Path
    run_history_path: Path
    current_run_path: Path
    log_level: str
    api_host: str
    api_port: int
    enable_watcher: bool
    watcher_debounce_seconds: float
    llm_enabled: bool
    llm_provider: str
    llm_base_url: str
    llm_recommendation_model: str
    llm_vision_model: str
    llm_timeout_ms: int


def _default_saves_path() -> Path:
    if Path.home().drive:
        return (
            Path.home()
            / "AppData"
            / "Roaming"
            / "SlayTheSpire2"
            / "steam"
            / "76561198110552884"
            / "profile1"
            / "saves"
        )
    return Path.home() / "SlayTheSpire2" / "saves"


def _resolve_storage_paths(
    storage_data: dict, workspace_root: Path, default_saves_path: Path
) -> tuple[Path, Path, Path]:
    saves_value = (
        storage_data.get("saves_path") if isinstance(storage_data, dict) else None
    )
    history_value = (
        storage_data.get("run_history_path") if isinstance(storage_data, dict) else None
    )

    if isinstance(saves_value, str) and saves_value.strip():
        saves_path = _resolve_path(saves_value, workspace_root, default_saves_path)
    elif isinstance(history_value, str) and history_value.strip():
        run_history_path = _resolve_path(
            history_value, workspace_root, default_saves_path / "history"
        )
        saves_path = run_history_path.parent
    else:
        saves_path = default_saves_path

    run_history_path = _resolve_path(
        history_value
        if isinstance(history_value, str) and history_value.strip()
        else None,
        workspace_root,
        saves_path / "history",
    )
    current_run_path = saves_path / "current_run.save"
    return saves_path, run_history_path, current_run_path


def _load_settings_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as settings_file:
            data = tomllib.load(settings_file)
            if isinstance(data, dict):
                return data
    except OSError:
        return {}
    except tomllib.TOMLDecodeError:
        return {}
    return {}


def _resolve_path(value: str | None, workspace_root: Path, fallback: Path) -> Path:
    if not value:
        return fallback
    parsed = Path(value)
    if parsed.is_absolute():
        return parsed
    return workspace_root / parsed


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    backend_root = Path(__file__).resolve().parents[1]
    workspace_root = backend_root.parent
    settings_file_path = workspace_root / "settings.toml"
    file_data = _load_settings_file(settings_file_path)
    api_data = file_data.get("api", {}) if isinstance(file_data, dict) else {}
    storage_data = file_data.get("storage", {}) if isinstance(file_data, dict) else {}
    watcher_data = file_data.get("watcher", {}) if isinstance(file_data, dict) else {}
    llm_data = file_data.get("llm", {}) if isinstance(file_data, dict) else {}

    default_db_path = workspace_root / "data" / "neow_insight.db"
    default_saves_path = _default_saves_path()

    db_path = _resolve_path(
        storage_data.get("db_path") if isinstance(storage_data, dict) else None,
        workspace_root,
        default_db_path,
    )
    saves_path, run_history_path, current_run_path = _resolve_storage_paths(
        storage_data if isinstance(storage_data, dict) else {},
        workspace_root,
        default_saves_path,
    )

    api_host = api_data.get("host") if isinstance(api_data, dict) else None
    api_port = api_data.get("port") if isinstance(api_data, dict) else None
    log_level = api_data.get("log_level") if isinstance(api_data, dict) else None

    enable_watcher = (
        watcher_data.get("enabled") if isinstance(watcher_data, dict) else None
    )
    watcher_debounce_seconds = (
        watcher_data.get("debounce_seconds") if isinstance(watcher_data, dict) else None
    )
    llm_enabled = llm_data.get("enabled") if isinstance(llm_data, dict) else None
    llm_provider = llm_data.get("provider") if isinstance(llm_data, dict) else None
    llm_base_url = llm_data.get("base_url") if isinstance(llm_data, dict) else None
    llm_model = llm_data.get("model") if isinstance(llm_data, dict) else None
    llm_recommendation_model = (
        llm_data.get("recommendation_model") if isinstance(llm_data, dict) else None
    )
    llm_vision_model = (
        llm_data.get("vision_model") if isinstance(llm_data, dict) else None
    )
    llm_timeout_ms = llm_data.get("timeout_ms") if isinstance(llm_data, dict) else None

    normalized_legacy_model = (
        llm_model.strip() if isinstance(llm_model, str) and llm_model.strip() else None
    )
    normalized_recommendation_model = (
        llm_recommendation_model.strip()
        if isinstance(llm_recommendation_model, str)
        and llm_recommendation_model.strip()
        else None
    )
    normalized_vision_model = (
        llm_vision_model.strip()
        if isinstance(llm_vision_model, str) and llm_vision_model.strip()
        else None
    )

    return Settings(
        db_path=db_path,
        saves_path=saves_path,
        run_history_path=run_history_path,
        current_run_path=current_run_path,
        log_level=log_level if isinstance(log_level, str) and log_level else "INFO",
        api_host=api_host if isinstance(api_host, str) and api_host else "127.0.0.1",
        api_port=int(api_port) if isinstance(api_port, int | str) else 8000,
        enable_watcher=bool(enable_watcher)
        if isinstance(enable_watcher, bool)
        else False,
        watcher_debounce_seconds=(
            float(watcher_debounce_seconds)
            if isinstance(watcher_debounce_seconds, int | float | str)
            else 0.4
        ),
        llm_enabled=bool(llm_enabled) if isinstance(llm_enabled, bool) else False,
        llm_provider=(
            llm_provider.strip().lower()
            if isinstance(llm_provider, str) and llm_provider.strip()
            else "ollama"
        ),
        llm_base_url=(
            llm_base_url.strip()
            if isinstance(llm_base_url, str) and llm_base_url.strip()
            else "http://127.0.0.1:11434"
        ),
        llm_recommendation_model=(
            normalized_recommendation_model
            or normalized_legacy_model
            or "gemma3:latest"
        ),
        llm_vision_model=(
            normalized_vision_model or normalized_legacy_model or "gemma3:latest"
        ),
        llm_timeout_ms=(
            max(int(float(llm_timeout_ms)), 1)
            if isinstance(llm_timeout_ms, int | float | str)
            else 1500
        ),
    )
