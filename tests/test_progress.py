from __future__ import annotations

from pathlib import Path

from models import UserProgress
from progress import ProgressManager


def test_save_then_load_round_trip_preserves_data(
    tmp_progress_path: Path, populated_user_progress: UserProgress
) -> None:
    manager = ProgressManager(tmp_progress_path)

    manager.save(populated_user_progress)
    loaded = manager.load()

    assert loaded == populated_user_progress


def test_load_nonexistent_file_returns_empty_user_progress(tmp_path: Path) -> None:
    missing_path = tmp_path / "does_not_exist.json"
    manager = ProgressManager(missing_path)

    loaded = manager.load()

    assert loaded == UserProgress()
    assert loaded.entries == {}


def test_load_corrupt_json_returns_empty_and_creates_backup(tmp_progress_path: Path) -> None:
    tmp_progress_path.write_text("{not-valid-json", encoding="utf-8")
    manager = ProgressManager(tmp_progress_path)

    loaded = manager.load()

    assert loaded == UserProgress()
    backup_path = tmp_progress_path.with_suffix(".json.bak")
    assert backup_path.exists()


def test_save_creates_file_that_did_not_exist(tmp_progress_path: Path) -> None:
    if tmp_progress_path.exists():
        tmp_progress_path.unlink()

    manager = ProgressManager(tmp_progress_path)
    manager.save(UserProgress())

    assert tmp_progress_path.exists()
