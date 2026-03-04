"""Glider Exam Prep — Streamlit entry point."""
from pathlib import Path

import streamlit as st

from models import QuestionBank, UserProgress
from parsers.answer_key_parser import parse_answer_keys
from parsers.markdown_parser import parse_markdown_questions
from progress import ProgressManager

# --- Page Config (must be first st command) ---
st.set_page_config(
    page_title="Glider Exam Prep",
    page_icon="🛫",
    layout="wide",
)

# --- Paths ---
BASE_DIR = Path(__file__).parent
MD_PATH = BASE_DIR / "SPL_Otazky.md"
VZOR_PATH = BASE_DIR / "extracted_vzor.txt"
PROGRESS_PATH = BASE_DIR / "progress.json"


@st.cache_data(show_spinner="Loading question bank...")
def load_question_bank() -> dict:
    """Parse questions and match answer keys. Cached across reruns."""
    bank = parse_markdown_questions(MD_PATH)
    answer_keys = parse_answer_keys(VZOR_PATH)

    merged_questions = [
        question.model_copy(
            update={"correct_answer": answer_keys.get(question.id, question.correct_answer)}
        )
        for question in bank.questions
    ]
    merged_bank = bank.model_copy(update={"questions": merged_questions})

    # Return as dict for Streamlit cache serialization
    return merged_bank.model_dump()


def init_session_state() -> None:
    """Initialize session state variables on first run."""
    # Question bank (cached)
    if "question_bank" not in st.session_state:
        bank_data = load_question_bank()
        st.session_state.question_bank = QuestionBank.model_validate(bank_data)
    
    # Progress manager
    if "progress_manager" not in st.session_state:
        st.session_state.progress_manager = ProgressManager(PROGRESS_PATH)
    
    # User progress
    if "progress" not in st.session_state:
        st.session_state.progress = st.session_state.progress_manager.load()
    
    # Quiz state defaults
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = ""
    if "quiz_mode" not in st.session_state:
        from models import QuizMode
        st.session_state.quiz_mode = QuizMode.STANDARD
    if "current_q_index" not in st.session_state:
        st.session_state.current_q_index = 0
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "last_recorded_answer" not in st.session_state:
        st.session_state.last_recorded_answer = ""
    if "last_was_correct" not in st.session_state:
        st.session_state.last_was_correct = False


# --- Initialize ---
init_session_state()

# --- Multipage Navigation ---
pages = [
    st.Page("pages/dashboard.py", title="Dashboard", icon="🏠", default=True),
    st.Page("pages/quiz.py", title="Quiz", icon="📝"),
    st.Page("pages/results.py", title="Results", icon="📊"),
]

nav = st.navigation(pages)
nav.run()
