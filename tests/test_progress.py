from __future__ import annotations

from pathlib import Path

from models import ResumeState, UserProgress
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


# ---------------------------------------------------------------------------
# Resume methods tests
# ---------------------------------------------------------------------------

def test_save_resume_persists_state(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    manager = ProgressManager(path)
    progress = UserProgress()

    manager.save_resume(progress, "aerodynamika", 7, 30)

    reloaded = manager.load()
    assert "aerodynamika" in reloaded.resume_state
    assert reloaded.resume_state["aerodynamika"].next_question_index == 7
    assert reloaded.resume_state["aerodynamika"].total_questions == 30


def test_get_resume_returns_correct_state(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    manager = ProgressManager(path)
    progress = UserProgress()

    manager.save_resume(progress, "aerodynamika", 5, 20)
    result = manager.get_resume(progress, "aerodynamika")
    assert result is not None
    assert result.next_question_index == 5

    missing = manager.get_resume(progress, "nonexistent")
    assert missing is None


def test_clear_resume_removes_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    manager = ProgressManager(path)
    progress = UserProgress()

    manager.save_resume(progress, "aerodynamika", 5, 20)
    manager.clear_resume(progress, "aerodynamika")

    assert manager.get_resume(progress, "aerodynamika") is None
    reloaded = manager.load()
    assert "aerodynamika" not in reloaded.resume_state


def test_resume_boundary_index_zero(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    manager = ProgressManager(path)
    progress = UserProgress()

    manager.save_resume(progress, "cat", 0, 10)
    result = manager.get_resume(progress, "cat")
    assert result is not None
    assert result.next_question_index == 0


def test_resume_boundary_last_question(tmp_path: Path) -> None:
    """Index == total-1 is valid (last question); stale guard only fires at index >= total."""
    path = tmp_path / "progress.json"
    manager = ProgressManager(path)
    progress = UserProgress()

    manager.save_resume(progress, "cat", 9, 10)
    result = manager.get_resume(progress, "cat")
    assert result is not None
    assert result.next_question_index == 9


def test_resume_stale_guard_index_equals_total(tmp_path: Path) -> None:
    """Index == total_questions should be treated as stale by the quiz startup guard."""
    path = tmp_path / "progress.json"
    manager = ProgressManager(path)
    progress = UserProgress()

    # Store a resume where index equals total (quiz was on last question, then finished)
    manager.save_resume(progress, "cat", 10, 10)  # index 10 >= total 10 -> stale
    result = manager.get_resume(progress, "cat")

    # ProgressManager stores it as-is; stale detection is responsibility of quiz.py startup
    assert result is not None
    assert result.next_question_index >= result.total_questions


def test_resume_survives_round_trip_with_other_data(tmp_path: Path) -> None:
    from models import Question
    path = tmp_path / "progress.json"
    manager = ProgressManager(path)
    progress = UserProgress()

    # Add some answered questions
    q = Question(id="aerodynamika/1", category="aerodynamika", number=1,
                 text="Q?", options={"a": "A", "b": "B"})
    progress.record_answer(q.id, "a", True)

    manager.save_resume(progress, "aerodynamika", 3, 15)
    manager.save(progress)

    reloaded = manager.load()
    assert "aerodynamika/1" in reloaded.entries
    assert "aerodynamika" in reloaded.resume_state
    assert reloaded.resume_state["aerodynamika"].next_question_index == 3
