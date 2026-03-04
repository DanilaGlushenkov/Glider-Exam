from __future__ import annotations

import streamlit as st

from models import QuestionBank, UserProgress
from progress import ProgressManager


def _get_session_dependencies() -> tuple[QuestionBank, UserProgress, ProgressManager] | None:
    question_bank = st.session_state.get("question_bank")
    progress = st.session_state.get("progress")
    progress_manager = st.session_state.get("progress_manager")

    if not isinstance(question_bank, QuestionBank):
        st.error("Question bank is not loaded.")
        return None
    if not isinstance(progress, UserProgress):
        st.error("User progress is not loaded.")
        return None
    if not isinstance(progress_manager, ProgressManager):
        st.error("Progress manager is not initialized.")
        return None

    return question_bank, progress, progress_manager