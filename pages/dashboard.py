import streamlit as st

from models import QuestionBank, QuizMode, UserProgress
from utils import _get_session_dependencies

CATEGORY_DISPLAY_NAMES = {
    "Aerodynamika": "Aerodynamika",
    "Letadla": "Všeobecné znalosti letadel",
    "Meteorologie": "Meteorologie",
    "Navigace": "Navigace",
    "Predpisy": "Letecké předpisy",
    "SpojPredpisy": "Spojovací předpisy",
}

def _start_quiz(category_name: str, mode: QuizMode) -> None:
    st.session_state.selected_category = category_name
    st.session_state.quiz_mode = mode
    st.session_state.current_q_index = 0
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

    question_bank, progress, _ = deps

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

                button_cols = st.columns(2)
                if button_cols[0].button("Start Quiz ▶️", key=f"start_{category_name}"):
                    _start_quiz(category_name, QuizMode.STANDARD)
                if button_cols[1].button(
                    "Retry Errors ↺",
                    key=f"retry_{category_name}",
                    disabled=stats["wrong"] == 0,
                ):
                    _start_quiz(category_name, QuizMode.RETRY_WRONG)

    if st.button("📊 View Results", use_container_width=True):
        st.switch_page("pages/results.py")

    st.caption("Progress is automatically saved to disk.")


if __name__ == "__main__":
    main()