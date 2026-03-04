from __future__ import annotations

import streamlit as st

from models import Question, QuestionBank, QuizMode, UserProgress
from utils import _get_session_dependencies


def _is_wrong(question: Question, progress: UserProgress) -> bool:
    entry = progress.entries.get(question.id)
    if entry is None:
        return False
    return entry.answered and not entry.correct


def _is_flagged(question: Question, progress: UserProgress) -> bool:
    entry = progress.entries.get(question.id)
    return bool(entry and entry.flagged)


def _get_icon(question: Question, progress: UserProgress) -> str:
    entry = progress.entries.get(question.id)
    if entry is None or not entry.answered:
        icon = "⬜"
    elif entry.correct:
        icon = "✅"
    else:
        icon = "❌"

    if entry is not None and entry.flagged:
        icon = f"{icon}🚩"

    return icon


def _question_preview(question_text: str) -> str:
    compact = " ".join(question_text.split())
    if len(compact) <= 80:
        return compact
    return f"{compact[:80]}..."


def _format_status_line(question: Question, progress: UserProgress) -> str:
    entry = progress.entries.get(question.id)
    answered = bool(entry and entry.answered)
    correct = bool(entry and entry.correct)
    flagged = bool(entry and entry.flagged)

    if not answered:
        answer_status = "Unanswered"
    elif correct:
        answer_status = "Answered • Correct"
    else:
        answer_status = "Answered • Wrong"

    flag_status = "Flagged" if flagged else "Not flagged"
    return f"Status: {answer_status} • {flag_status}"


def _show_question_cards(questions: list[Question], progress: UserProgress) -> None:
    if not questions:
        st.caption("No questions in this view.")
        return

    for question in questions:
        icon = _get_icon(question, progress)
        preview = _question_preview(question.text)
        label = f"{icon} Q{question.number}: {preview}"

        with st.expander(label):
            st.write(question.text)

            entry = progress.entries.get(question.id)
            if entry is not None and entry.answered and entry.last_answer:
                st.write(f"Your answer: {entry.last_answer.upper()}")
            else:
                st.write("Your answer: Not answered")

            if question.correct_answer:
                st.write(f"Correct answer: {question.correct_answer.upper()}")
            else:
                st.write("Correct answer: N/A")

            st.caption(_format_status_line(question, progress))


def _start_retry(selected_category: str, mode: QuizMode) -> None:
    if selected_category == "All Categories":
        st.info("Select a single category to start a retry quiz.")
        return

    st.session_state.selected_category = selected_category
    st.session_state.quiz_mode = mode
    st.session_state.current_q_index = 0
    st.session_state.submitted = False
    st.session_state.last_recorded_answer = ""
    st.session_state.last_was_correct = False
    st.session_state.pop("quiz_questions", None)
    st.switch_page("pages/quiz.py")


def main() -> None:
    deps = _get_session_dependencies()
    if deps is None:
        st.stop()

    question_bank, progress, _ = deps

    st.title("📊 Results")

    category_options = ["All Categories", *question_bank.categories]
    default_category = st.session_state.get("selected_category")
    default_index = 0
    if isinstance(default_category, str) and default_category in question_bank.categories:
        default_index = category_options.index(default_category)

    selected_category = st.selectbox(
        "Category",
        options=category_options,
        index=default_index,
    )

    if selected_category == "All Categories":
        filtered_questions = sorted(
            question_bank.questions,
            key=lambda question: (question.category, question.number),
        )
    else:
        filtered_questions = sorted(
            question_bank.get_by_category(selected_category),
            key=lambda question: (question.category, question.number),
        )

    answered_total = sum(
        1
        for question in question_bank.questions
        if question.id in progress.entries and progress.entries[question.id].answered
    )
    if answered_total == 0:
        st.info("No questions answered yet. Start a quiz from the dashboard!")
        if st.button("🏠 Back to Dashboard"):
            st.switch_page("pages/dashboard.py")
        st.stop()

    correct_questions = [
        question
        for question in filtered_questions
        if question.id in progress.entries and progress.entries[question.id].correct
    ]
    wrong_questions = [
        question
        for question in filtered_questions
        if _is_wrong(question, progress)
    ]
    flagged_questions = [
        question
        for question in filtered_questions
        if _is_flagged(question, progress)
    ]

    stats_cols = st.columns(4)
    stats_cols[0].metric("Total questions", len(filtered_questions))
    stats_cols[1].metric("✅ Correct", len(correct_questions))
    stats_cols[2].metric("❌ Wrong", len(wrong_questions))
    stats_cols[3].metric("🚩 Flagged", len(flagged_questions))

    action_cols = st.columns(2)
    if action_cols[0].button("Retry Wrong ❌", disabled=len(wrong_questions) == 0):
        _start_retry(selected_category, QuizMode.RETRY_WRONG)
    if action_cols[1].button("Retry Flagged 🚩", disabled=len(flagged_questions) == 0):
        _start_retry(selected_category, QuizMode.RETRY_FLAGGED)

    all_tab, wrong_tab, flagged_tab = st.tabs(
        [
            f"All ({len(filtered_questions)})",
            f"❌ Wrong ({len(wrong_questions)})",
            f"🚩 Flagged ({len(flagged_questions)})",
        ]
    )

    with all_tab:
        _show_question_cards(filtered_questions, progress)
    with wrong_tab:
        _show_question_cards(wrong_questions, progress)
    with flagged_tab:
        _show_question_cards(flagged_questions, progress)

    if st.button("🏠 Back to Dashboard"):
        st.switch_page("pages/dashboard.py")


if __name__ == "__main__":
    main()
