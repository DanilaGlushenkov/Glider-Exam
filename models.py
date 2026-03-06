"""Data models for the Glider Exam quiz app."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, PrivateAttr, model_validator


class QuizMode(str, Enum):
    STANDARD = "standard"
    RETRY_WRONG = "retry_wrong"
    RETRY_FLAGGED = "retry_flagged"


class Question(BaseModel):
    """A single exam question."""
    id: str  # e.g. "vzor/Aerodynamika/42"
    category: str  # e.g. "Aerodynamika"
    number: int  # local question number within source
    text: str
    options: dict[str, str]  # {"a": "...", "b": "...", ...}
    correct_answer: str | None = None  # letter(s) of correct answer, e.g. "b" or "a,c"
    has_image_ref: bool = False  # True if question references an image

    @model_validator(mode="after")
    def validate_options(self) -> "Question":
        if not self.options:
            raise ValueError(f"Question {self.id} has no options")
        if self.correct_answer:
            for ans in self.correct_answer.split(","):
                ans = ans.strip()
                if ans and ans not in self.options:
                    # Data quality issue: answer key references missing option.
                    # Clear invalid answer instead of crashing.
                    import logging
                    logging.getLogger(__name__).warning(
                        "Question %s: correct answer '%s' not in options %s — clearing answer",
                        self.id, ans, list(self.options.keys()),
                    )
                    self.correct_answer = None
                    break
        return self


class QuestionBank(BaseModel):
    """Collection of all questions grouped by category."""
    questions: list[Question] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)
    _question_index: dict[str, Question] | None = PrivateAttr(default=None)

    @property
    def question_index(self) -> dict[str, Question]:
        if self._question_index is None:
            self._question_index = {question.id: question for question in self.questions}
        return self._question_index

    def get_by_category(self, category: str) -> list[Question]:
        return [q for q in self.questions if q.category == category]

    def get_by_id(self, question_id: str) -> Question | None:
        return self.question_index.get(question_id)


class ProgressEntry(BaseModel):
    """Progress for a single question."""
    answered: bool = False
    correct: bool = False
    attempts: int = 0
    last_answer: str = ""
    flagged: bool = False


class ResumeState(BaseModel):
    """Persisted quiz position for a category (STANDARD mode only)."""
    next_question_index: int
    total_questions: int


class UserProgress(BaseModel):
    """All user progress, keyed by question ID."""
    entries: dict[str, ProgressEntry] = Field(default_factory=dict)
    resume_state: dict[str, ResumeState] = Field(default_factory=dict)

    def record_answer(self, question_id: str, answer: str, is_correct: bool) -> None:
        entry = self.entries.get(question_id, ProgressEntry())
        entry.answered = True
        entry.correct = is_correct
        entry.attempts += 1
        entry.last_answer = answer
        self.entries[question_id] = entry

    def toggle_flag(self, question_id: str) -> None:
        entry = self.entries.get(question_id, ProgressEntry())
        entry.flagged = not entry.flagged
        self.entries[question_id] = entry

    def get_category_stats(self, questions: list[Question]) -> dict:
        total = len(questions)
        answered = sum(1 for q in questions if q.id in self.entries and self.entries[q.id].answered)
        correct = sum(1 for q in questions if q.id in self.entries and self.entries[q.id].correct)
        wrong = answered - correct
        flagged = sum(1 for q in questions if q.id in self.entries and self.entries[q.id].flagged)
        accuracy = (correct / answered * 100) if answered > 0 else 0.0
        return {
            "total": total,
            "answered": answered,
            "correct": correct,
            "wrong": wrong,
            "flagged": flagged,
            "accuracy": accuracy,
        }

    def get_wrong_ids(self, questions: list[Question]) -> list[str]:
        return [q.id for q in questions if q.id in self.entries and self.entries[q.id].answered and not self.entries[q.id].correct]

    def get_flagged_ids(self, questions: list[Question]) -> list[str]:
        return [q.id for q in questions if q.id in self.entries and self.entries[q.id].flagged]
