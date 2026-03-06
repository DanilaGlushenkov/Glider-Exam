import streamlit as st

from models import QuestionBank, QuizMode, UserProgress
from progress import ProgressManager
from utils import _get_session_dependencies

CATEGORY_DISPLAY_NAMES = {
    # Unified categories (new format)
    "aerodynamika": "Aerodynamika a mechanika letu",
    "zaklady-letu": "Základy letu",
    "letadla": "Všeobecné znalosti letadel",
    "letove-vykony": "Letové výkony a plánování",
    "meteorologie": "Meteorologie",
    "navigace": "Navigace",
    "predpisy": "Letecké předpisy",
    "provozni-postupy": "Provozní postupy",
    "lidska-vykonnost": "Lidská výkonnost",
    "komunikace": "Komunikace a spojovací předpisy",
    # Legacy categories (backward compat)
    "Aerodynamika": "Aerodynamika",
    "Letadla": "Všeobecné znalosti letadel",
    "Meteorologie": "Meteorologie",
    "Navigace": "Navigace",
    "Predpisy": "Letecké předpisy",
    "SpojPredpisy": "Spojovací předpisy",
}

def _start_quiz(
    category_name: str,
    mode: QuizMode,
    progress_manager: ProgressManager,
    progress: UserProgress,
) -> None:
    progress_manager.clear_resume(progress, category_name)
    st.session_state.selected_category = category_name
    st.session_state.quiz_mode = mode
    st.session_state.current_q_index = 0
    st.session_state.submitted = False
    st.session_state.last_recorded_answer = ""
    st.session_state.last_was_correct = False
    st.switch_page("pages/quiz.py")


def _continue_quiz(category_name: str, resume_index: int) -> None:
    st.session_state.selected_category = category_name
    st.session_state.quiz_mode = QuizMode.STANDARD
    st.session_state.current_q_index = resume_index
    st.session_state.submitted = False
    st.session_state.last_recorded_answer = ""
    st.session_state.last_was_correct = False
    st.switch_page("pages/quiz.py")


def _weakest_category(question_bank: QuestionBank, progress: UserProgress) -> str:
    weakest_name = "N/A"
    lowest_accuracy = 101.0
    for category in question_bank.categories:
        questions = question_bank.get_by_category(category)
        stats = progress.get_category_stats(questions)
        if stats["answered"] == 0:
            continue
        if stats["accuracy"] < lowest_accuracy:
            lowest_accuracy = stats["accuracy"]
            weakest_name = CATEGORY_DISPLAY_NAMES.get(category, category)
    return weakest_name


def main() -> None:
    deps = _get_session_dependencies()
    if deps is None:
        st.stop()

    question_bank, progress, progress_manager = deps

    st.title("🛫 Glider Exam Prep")
    st.caption("Choose a category to continue practicing and track your progress.")

    total_questions = len(question_bank.questions)
    total_answered = sum(
        1
        for question in question_bank.questions
        if question.id in progress.entries and progress.entries[question.id].answered
    )
    total_correct = sum(
        1
        for question in question_bank.questions
        if question.id in progress.entries and progress.entries[question.id].correct
    )
    global_accuracy = (total_correct / total_answered * 100.0) if total_answered > 0 else 0.0

    stat_cols = st.columns(3)
    stat_cols[0].metric("Total Progress", f"{total_answered}/{total_questions}")
    stat_cols[1].metric("Global Accuracy", f"{global_accuracy:.1f}%")
    stat_cols[2].metric("Weakest Category", _weakest_category(question_bank, progress))

    grid_cols = st.columns(2)
    for index, category_name in enumerate(question_bank.categories):
        questions = question_bank.get_by_category(category_name)
        stats = progress.get_category_stats(questions)
        completion = (stats["answered"] / stats["total"]) if stats["total"] > 0 else 0.0

        with grid_cols[index % 2]:
            with st.container(border=True):
                st.subheader(CATEGORY_DISPLAY_NAMES.get(category_name, category_name))
                st.progress(completion)
                st.caption(
                    f"{stats['answered']}/{stats['total']} answered • {stats['accuracy']:.1f}% correct"
                )

                # Determine resume position: explicit save or inferred from progress
                resume = progress_manager.get_resume(progress, category_name)
                resume_index: int | None = None
                resume_total = stats["total"]

                if (
                    resume is not None
                    and resume.next_question_index > 0
                    and resume.next_question_index < resume.total_questions
                ):
                    # Explicit resume from a previous quit / next-question
                    resume_index = resume.next_question_index
                    resume_total = resume.total_questions
                elif stats["answered"] > 0 and stats["answered"] < stats["total"]:
                    # Infer resume: find first unanswered question in order
                    sorted_qs = sorted(questions, key=lambda q: q.number)
                    for idx, q in enumerate(sorted_qs):
                        entry = progress.entries.get(q.id)
                        if entry is None or not entry.answered:
                            if idx > 0:
                                resume_index = idx
                            break

                has_resume = resume_index is not None

                st.divider()

                if has_resume:
                    q_current = resume_index + 1
                    st.caption(f"⏸️ Resumable: Question {q_current}/{resume_total}")

                    if st.button(
                        "Continue ↩️",
                        key=f"continue_{category_name}",
                        type="primary",
                        use_container_width=True,
                    ):
                        _continue_quiz(category_name, resume_index)

                    cols_sub = st.columns(2)
                    with cols_sub[0]:
                        if st.button(
                            "New Quiz 🆕",
                            key=f"new_{category_name}",
                            help="Start over from the beginning",
                            use_container_width=True,
                        ):
                            _start_quiz(
                                category_name,
                                QuizMode.STANDARD,
                                progress_manager,
                                progress,
                            )
                    with cols_sub[1]:
                        if st.button(
                            "Retry Errors ↺",
                            key=f"retry_{category_name}",
                            disabled=stats["wrong"] == 0,
                            use_container_width=True,
                        ):
                            _start_quiz(
                                category_name,
                                QuizMode.RETRY_WRONG,
                                progress_manager,
                                progress,
                            )
                else:
                    cols_std = st.columns(2)
                    with cols_std[0]:
                        if st.button(
                            "New Quiz 🆕",
                            key=f"new_{category_name}",
                            type="primary",
                            use_container_width=True,
                        ):
                            _start_quiz(
                                category_name,
                                QuizMode.STANDARD,
                                progress_manager,
                                progress,
                            )
                    with cols_std[1]:
                        if st.button(
                            "Retry Errors ↺",
                            key=f"retry_{category_name}",
                            disabled=stats["wrong"] == 0,
                            use_container_width=True,
                        ):
                            _start_quiz(
                                category_name,
                                QuizMode.RETRY_WRONG,
                                progress_manager,
                                progress,
                            )

    if st.button("📊 View Results", use_container_width=True):
        st.switch_page("pages/results.py")

    st.caption("Progress is automatically saved to disk.")


if __name__ == "__main__":
    main()