from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import Question, QuestionBank, QuizMode, UserProgress


def test_question_creation_valid_data() -> None:
    question = Question(
        id="vzor/Aerodynamika/1",
        category="Aerodynamika",
        number=1,
        text="Test question",
        options={"a": "One", "b": "Two", "c": "Three"},
        correct_answer="b",
    )

    assert question.id == "vzor/Aerodynamika/1"
    assert question.correct_answer == "b"


def test_question_validation_error_empty_options() -> None:
    with pytest.raises(ValidationError):
        Question(
            id="vzor/Aerodynamika/2",
            category="Aerodynamika",
            number=2,
            text="Invalid question",
            options={},
            correct_answer="a",
        )


def test_question_validation_error_correct_answer_not_in_options() -> None:
    with pytest.raises(ValidationError):
        Question(
            id="vzor/Aerodynamika/3",
            category="Aerodynamika",
            number=3,
            text="Invalid question",
            options={"a": "One", "b": "Two"},
            correct_answer="d",
        )


def test_question_bank_get_by_category() -> None:
    bank = QuestionBank(
        questions=[
            Question(
                id="vzor/Aerodynamika/1",
                category="Aerodynamika",
                number=1,
                text="Q1",
                options={"a": "A", "b": "B"},
            ),
            Question(
                id="vzor/Meteorologie/1",
                category="Meteorologie",
                number=1,
                text="Q2",
                options={"a": "A", "b": "B"},
            ),
        ]
    )

    aero_questions = bank.get_by_category("Aerodynamika")
    assert len(aero_questions) == 1
    assert aero_questions[0].id == "vzor/Aerodynamika/1"


def test_question_bank_get_by_id_found_and_not_found() -> None:
    q1 = Question(
        id="vzor/Navigace/10",
        category="Navigace",
        number=10,
        text="Q10",
        options={"a": "A", "b": "B"},
    )
    bank = QuestionBank(questions=[q1])

    assert bank.get_by_id("vzor/Navigace/10") == q1
    assert bank.get_by_id("vzor/Navigace/999") is None


def test_user_progress_record_answer() -> None:
    progress = UserProgress()

    progress.record_answer("vzor/Aerodynamika/1", "b", True)
    progress.record_answer("vzor/Aerodynamika/1", "a", False)

    entry = progress.entries["vzor/Aerodynamika/1"]
    assert entry.answered is True
    assert entry.correct is False
    assert entry.attempts == 2
    assert entry.last_answer == "a"


def test_user_progress_toggle_flag() -> None:
    progress = UserProgress()

    progress.toggle_flag("vzor/Aerodynamika/1")
    assert progress.entries["vzor/Aerodynamika/1"].flagged is True

    progress.toggle_flag("vzor/Aerodynamika/1")
    assert progress.entries["vzor/Aerodynamika/1"].flagged is False


def test_user_progress_get_category_stats(populated_user_progress: UserProgress) -> None:
    questions = [
        Question(
            id="vzor/Aerodynamika/1",
            category="Aerodynamika",
            number=1,
            text="Q1",
            options={"a": "A", "b": "B"},
        ),
        Question(
            id="vzor/Aerodynamika/2",
            category="Aerodynamika",
            number=2,
            text="Q2",
            options={"a": "A", "b": "B"},
        ),
        Question(
            id="vzor/Aerodynamika/3",
            category="Aerodynamika",
            number=3,
            text="Q3",
            options={"a": "A", "b": "B"},
        ),
    ]

    stats = populated_user_progress.get_category_stats(questions)
    assert stats["total"] == 3
    assert stats["answered"] == 2
    assert stats["correct"] == 1
    assert stats["wrong"] == 1
    assert stats["flagged"] == 1
    assert stats["accuracy"] == 50.0


def test_user_progress_get_wrong_ids(populated_user_progress: UserProgress) -> None:
    questions = [
        Question(
            id="vzor/Aerodynamika/1",
            category="Aerodynamika",
            number=1,
            text="Q1",
            options={"a": "A", "b": "B"},
        ),
        Question(
            id="vzor/Aerodynamika/2",
            category="Aerodynamika",
            number=2,
            text="Q2",
            options={"a": "A", "b": "B"},
        ),
    ]

    wrong_ids = populated_user_progress.get_wrong_ids(questions)
    assert wrong_ids == ["vzor/Aerodynamika/2"]


def test_user_progress_get_flagged_ids(populated_user_progress: UserProgress) -> None:
    questions = [
        Question(
            id="vzor/Aerodynamika/1",
            category="Aerodynamika",
            number=1,
            text="Q1",
            options={"a": "A", "b": "B"},
        ),
        Question(
            id="vzor/Aerodynamika/2",
            category="Aerodynamika",
            number=2,
            text="Q2",
            options={"a": "A", "b": "B"},
        ),
        Question(
            id="vzor/Meteorologie/1",
            category="Meteorologie",
            number=1,
            text="Q3",
            options={"a": "A", "b": "B"},
        ),
    ]

    flagged_ids = populated_user_progress.get_flagged_ids(questions)
    assert flagged_ids == ["vzor/Aerodynamika/2", "vzor/Meteorologie/1"]


def test_quiz_mode_enum_values() -> None:
    assert QuizMode.STANDARD.value == "standard"
    assert QuizMode.RETRY_WRONG.value == "retry_wrong"
    assert QuizMode.RETRY_FLAGGED.value == "retry_flagged"
