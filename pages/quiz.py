from __future__ import annotations

import random

import streamlit as st

from models import Question, QuestionBank, QuizMode, UserProgress
from progress import ProgressManager
from utils import _get_session_dependencies


def _resolve_mode(raw_mode: object) -> QuizMode:
    if isinstance(raw_mode, QuizMode):
        return raw_mode
    if isinstance(raw_mode, str):
        try:
            return QuizMode(raw_mode)
        except ValueError:
            return QuizMode.STANDARD
    return QuizMode.STANDARD


def _initialize_quiz_questions(
    question_bank: QuestionBank,
    progress: UserProgress,
    category: str,
    mode: QuizMode,
) -> list[str]:
    category_questions = sorted(
        question_bank.get_by_category(category), key=lambda question: question.number
    )

    if mode == QuizMode.STANDARD:
        question_ids = [question.id for question in category_questions]
    elif mode == QuizMode.RETRY_WRONG:
        question_ids = progress.get_wrong_ids(category_questions)
        random.shuffle(question_ids)
    elif mode == QuizMode.RETRY_FLAGGED:
        question_ids = progress.get_flagged_ids(category_questions)
        random.shuffle(question_ids)
    else:
        question_ids = [question.id for question in category_questions]

    st.session_state.quiz_questions = question_ids
    return question_ids


def _extract_selected_letter(selected_option: str) -> str:
    if not selected_option:
        return ""
    return selected_option.split(")", maxsplit=1)[0].strip().lower()


def _is_answer_correct(question: Question, selected_letter: str) -> bool:
    if question.correct_answer is None:
        return False

    accepted_answers = {
        answer.strip().lower()
        for answer in question.correct_answer.split(",")
        if answer.strip()
    }
    return selected_letter in accepted_answers


def _save_progress(progress_manager: ProgressManager, progress: UserProgress) -> None:
    progress_manager.save(progress)


def _switch_to_dashboard(progress_manager: ProgressManager, progress: UserProgress) -> None:
    _save_progress(progress_manager, progress)
    st.switch_page("pages/dashboard.py")


def _switch_to_results(progress_manager: ProgressManager, progress: UserProgress) -> None:
    _save_progress(progress_manager, progress)
    st.switch_page("pages/results.py")


def main() -> None:
    deps = _get_session_dependencies()
    if deps is None:
        st.stop()

    question_bank, progress, progress_manager = deps

    selected_category = st.session_state.get("selected_category")
    if not isinstance(selected_category, str) or not selected_category.strip():
        st.switch_page("pages/dashboard.py")
        st.stop()

    mode = _resolve_mode(st.session_state.get("quiz_mode", QuizMode.STANDARD))

    if "current_q_index" not in st.session_state:
        st.session_state.current_q_index = 0
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "last_recorded_answer" not in st.session_state:
        st.session_state.last_recorded_answer = ""
    if "last_was_correct" not in st.session_state:
        st.session_state.last_was_correct = False

    if "quiz_questions" not in st.session_state:
        quiz_question_ids = _initialize_quiz_questions(
            question_bank=question_bank,
            progress=progress,
            category=selected_category,
            mode=mode,
        )
    else:
        quiz_question_ids = st.session_state.quiz_questions

    if not isinstance(quiz_question_ids, list):
        quiz_question_ids = _initialize_quiz_questions(
            question_bank=question_bank,
            progress=progress,
            category=selected_category,
            mode=mode,
        )

    if len(quiz_question_ids) == 0:
        st.info("No questions available for this quiz mode in the selected category.")
        if st.button("⬅️ Back to Dashboard"):
            st.switch_page("pages/dashboard.py")
        st.stop()

    current_q_index = st.session_state.current_q_index
    if current_q_index >= len(quiz_question_ids):
        st.success("Quiz complete for this session.")
        if st.button("Finish Quiz", type="primary"):
            _switch_to_results(progress_manager, progress)
        if st.button("⬅️ Back to Dashboard"):
            _switch_to_dashboard(progress_manager, progress)
        st.stop()

    current_question_id = quiz_question_ids[current_q_index]
    current_question = question_bank.get_by_id(current_question_id)

    if current_question is None:
        st.error("Current question could not be found. Moving to the next one.")
        st.session_state.current_q_index += 1
        st.session_state.submitted = False
        st.rerun()

    assert current_question is not None

    total_questions = len(quiz_question_ids)
    top_cols = st.columns([1, 3, 1])

    with top_cols[0]:
        if st.button("🏠 Quit"):
            _switch_to_dashboard(progress_manager, progress)

    with top_cols[1]:
        st.progress((current_q_index + 1) / total_questions)
        st.caption(
            f"Question {current_q_index + 1} of {total_questions} — {current_question.category}"
        )

    with top_cols[2]:
        progress_entry = progress.entries.get(current_question.id)
        flagged_value = progress_entry.flagged if progress_entry is not None else False
        updated_flagged_value = st.checkbox(
            "🚩 Flag for review",
            value=flagged_value,
            key=f"flag_{current_question.id}",
        )
        if updated_flagged_value != flagged_value:
            progress.toggle_flag(current_question.id)
            _save_progress(progress_manager, progress)

    st.markdown(f"### Q{current_question.number}: {current_question.text}")
    if current_question.has_image_ref:
        st.info("📷 This question references an image that is not available digitally.")

    option_letters = sorted(current_question.options.keys())
    option_labels = [
        f"{letter}) {current_question.options[letter]}" for letter in option_letters
    ]

    selected_option = st.radio(
        "Answer",
        options=option_labels,
        key=f"answer_{current_question.id}",
        label_visibility="collapsed",
    )

    submitted = bool(st.session_state.submitted)

    if not submitted:
        if st.button("Submit Answer", type="primary"):
            selected_letter = _extract_selected_letter(selected_option)

            if current_question.correct_answer is None:
                st.session_state.last_recorded_answer = selected_letter
                st.session_state.last_was_correct = False
                st.session_state.submitted = True
                _save_progress(progress_manager, progress)
                st.rerun()

            is_correct = _is_answer_correct(current_question, selected_letter)
            progress.record_answer(current_question.id, selected_letter, is_correct)
            _save_progress(progress_manager, progress)
            st.session_state.last_recorded_answer = selected_letter
            st.session_state.last_was_correct = is_correct
            st.session_state.submitted = True
            st.rerun()
    else:
        if current_question.correct_answer is None:
            st.info("Practice-only question: no official correct answer for scoring.")
        else:
            selected_letter = st.session_state.get("last_recorded_answer", "")
            is_correct = bool(st.session_state.get("last_was_correct", False))
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(
                    f"❌ Incorrect. Correct answer: {current_question.correct_answer}"
                )

        is_last_question = current_q_index == total_questions - 1
        if is_last_question:
            if st.button("Finish Quiz", type="primary"):
                _switch_to_results(progress_manager, progress)
        else:
            if st.button("Next Question ➡️", type="primary"):
                st.session_state.current_q_index += 1
                st.session_state.submitted = False
                st.session_state.last_recorded_answer = ""
                st.session_state.last_was_correct = False
                st.rerun()


if __name__ == "__main__":
    main()
