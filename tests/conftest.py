from __future__ import annotations

from pathlib import Path

import pytest

from models import ProgressEntry, UserProgress


@pytest.fixture
def fixture_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_md_path(fixture_dir: Path) -> Path:
    return fixture_dir / "sample_questions.md"


@pytest.fixture
def sample_vzor_path(fixture_dir: Path) -> Path:
    return fixture_dir / "sample_vzor.txt"


@pytest.fixture
def tmp_progress_path(tmp_path: Path) -> Path:
    return tmp_path / "progress.json"


@pytest.fixture
def populated_user_progress() -> UserProgress:
    return UserProgress(
        entries={
            "vzor/Aerodynamika/1": ProgressEntry(
                answered=True,
                correct=True,
                attempts=1,
                last_answer="b",
                flagged=False,
            ),
            "vzor/Aerodynamika/2": ProgressEntry(
                answered=True,
                correct=False,
                attempts=2,
                last_answer="c",
                flagged=True,
            ),
            "vzor/Meteorologie/1": ProgressEntry(
                answered=False,
                correct=False,
                attempts=0,
                last_answer="",
                flagged=True,
            ),
        }
    )
