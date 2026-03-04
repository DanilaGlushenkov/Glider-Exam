from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from models import Question, QuestionBank

H2_PATTERN = re.compile(r"^##\s+(.+?)\s*$")
H2_WITH_ANCHOR = re.compile(r"^##\s+(.+?)\s+\{#(\S+)\}\s*$")
QUESTION_PATTERN = re.compile(r"^\*\*(\d+)\.\*\*\s*(.+?)\s*$")
OPTION_PATTERN = re.compile(r"^\s{2,4}([a-d])\)\s+(.+?)\s*$", re.IGNORECASE)


def _contains_image_ref(text: str) -> bool:
    lowered = text.lower()
    return "obrázk" in lowered or "obr." in lowered


def parse_markdown_questions(markdown_path: str | Path) -> QuestionBank:
    """Parse questions from the unified SPL Markdown format.

    Supports both legacy format (``### Zdroj: vzor/...``) and the new
    unified format (``## Title {#anchor}``).  In the unified format every
    ``## H2 {#anchor}`` heading defines a category whose slug is *anchor*
    and all ``**N.**`` questions underneath belong to it with IDs
    ``{anchor}/{N}``.
    """
    path = Path(markdown_path)
    lines = path.read_text(encoding="utf-8").splitlines()

    questions: list[Question] = []
    categories: list[str] = []
    parse_warnings: list[str] = []
    seen_ids: set[str] = set()

    # Detect format: if any H2 has {#anchor}, use unified mode
    unified_mode = any(H2_WITH_ANCHOR.match(line) for line in lines)

    if unified_mode:
        questions, categories, parse_warnings = _parse_unified(lines)
    else:
        questions, categories, parse_warnings = _parse_legacy(lines)

    return QuestionBank(
        questions=questions,
        categories=categories,
        parse_warnings=parse_warnings,
    )


def _parse_unified(
    lines: list[str],
) -> tuple[list[Question], list[str], list[str]]:
    """Parse the new unified format with ``## Title {#anchor}`` headings."""
    questions: list[Question] = []
    categories: list[str] = []
    parse_warnings: list[str] = []
    seen_ids: set[str] = set()

    current_anchor: str | None = None
    current_number: int | None = None
    current_question_text: str = ""
    current_options: dict[str, str] = {}
    current_option_letter: str | None = None

    def finalize_question() -> None:
        nonlocal current_number, current_question_text, current_options, current_option_letter
        if current_number is None or current_anchor is None:
            current_number = None
            current_question_text = ""
            current_options = {}
            current_option_letter = None
            return

        question_id = f"{current_anchor}/{current_number}"
        option_count = len(current_options)
        if option_count == 0:
            parse_warnings.append(
                f"{question_id}: no options found; likely heading/merged artifact, skipped"
            )
            current_number = None
            current_question_text = ""
            current_options = {}
            current_option_letter = None
            return

        if option_count != 4:
            parse_warnings.append(
                f"{question_id}: unexpected option count {option_count}"
            )

        compact_text = re.sub(r"\s+", " ", current_question_text).strip()

        if question_id in seen_ids:
            parse_warnings.append(f"Duplicate question id detected: {question_id}")
        else:
            seen_ids.add(question_id)
            questions.append(
                Question(
                    id=question_id,
                    category=current_anchor,
                    number=current_number,
                    text=compact_text,
                    options={k: v.strip() for k, v in current_options.items()},
                    has_image_ref=_contains_image_ref(compact_text),
                )
            )
            if current_anchor not in categories:
                categories.append(current_anchor)

        current_number = None
        current_question_text = ""
        current_options = {}
        current_option_letter = None

    for _line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")

        anchor_match = H2_WITH_ANCHOR.match(line)
        if anchor_match:
            finalize_question()
            current_anchor = anchor_match.group(2)
            continue

        # Plain H2 without anchor — skip (e.g. TOC heading)
        if H2_PATTERN.match(line) and not line.startswith("###"):
            finalize_question()
            current_anchor = None
            continue

        if current_anchor is None:
            continue

        question_match = QUESTION_PATTERN.match(line)
        if question_match:
            finalize_question()
            current_number = int(question_match.group(1))
            current_question_text = question_match.group(2).strip()
            current_options = {}
            current_option_letter = None
            continue

        option_match = OPTION_PATTERN.match(line)
        if option_match:
            if current_number is None:
                continue
            option_letter = option_match.group(1).lower()
            option_text = option_match.group(2).strip()
            current_options[option_letter] = option_text
            current_option_letter = option_letter
            continue

        stripped = line.strip()
        if not stripped:
            continue

        if current_number is not None:
            if current_option_letter is not None:
                current_options[current_option_letter] = (
                    f"{current_options[current_option_letter]} {stripped}".strip()
                )
            else:
                current_question_text = f"{current_question_text} {stripped}".strip()

    finalize_question()
    return questions, categories, parse_warnings


def _parse_legacy(
    lines: list[str],
) -> tuple[list[Question], list[str], list[str]]:
    """Parse the legacy format with ``### Zdroj: vzor/...`` sub-headers."""
    questions: list[Question] = []
    categories: list[str] = []
    parse_warnings: list[str] = []
    seen_ids: set[str] = set()

    H3_SOURCE_PATTERN = re.compile(r"^###\s+Zdroj:\s*(.+?)\s*$")

    current_source: str | None = None
    current_source_short: str | None = None
    in_vzor_source = False

    current_number: int | None = None
    current_question_text: str = ""
    current_options: dict[str, str] = {}
    current_option_letter: str | None = None

    def _source_name_from_h3(source: str) -> str:
        source_path = source.strip().split()[0]
        return Path(source_path).stem

    def finalize_question() -> None:
        nonlocal current_number, current_question_text, current_options, current_option_letter
        if current_number is None:
            return
        if not current_source_short:
            parse_warnings.append(
                f"Question {current_number}: missing source context; skipped"
            )
            current_number = None
            current_question_text = ""
            current_options = {}
            current_option_letter = None
            return

        question_id = f"vzor/{current_source_short}/{current_number}"
        option_count = len(current_options)
        if option_count == 0:
            parse_warnings.append(
                f"{question_id}: no options found; likely heading/merged artifact, skipped"
            )
            current_number = None
            current_question_text = ""
            current_options = {}
            current_option_letter = None
            return

        if option_count < 4 or option_count > 4:
            parse_warnings.append(
                f"{question_id}: unexpected option count {option_count}"
            )

        compact_text = re.sub(r"\s+", " ", current_question_text).strip()
        if re.search(r"\b\d+\.[A-Za-zÁ-Žá-ž]", compact_text):
            parse_warnings.append(
                f"{question_id}: possible merged question line in text"
            )

        if question_id in seen_ids:
            parse_warnings.append(f"Duplicate question id detected: {question_id}")
        else:
            seen_ids.add(question_id)
            questions.append(
                Question(
                    id=question_id,
                    category=current_source_short,
                    number=current_number,
                    text=compact_text,
                    options={k: v.strip() for k, v in current_options.items()},
                    has_image_ref=_contains_image_ref(compact_text),
                )
            )
            if current_source_short not in categories:
                categories.append(current_source_short)

        current_number = None
        current_question_text = ""
        current_options = {}
        current_option_letter = None

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")

        h2_match = H2_PATTERN.match(line)
        if h2_match and not line.startswith("###"):
            finalize_question()
            continue

        h3_match = H3_SOURCE_PATTERN.match(line)
        if h3_match:
            finalize_question()
            source_value = h3_match.group(1).strip()
            current_source = source_value
            in_vzor_source = source_value.startswith("vzor/")
            current_source_short = (
                _source_name_from_h3(source_value) if in_vzor_source else None
            )
            continue

        if not in_vzor_source:
            continue

        question_match = QUESTION_PATTERN.match(line)
        if question_match:
            finalize_question()
            current_number = int(question_match.group(1))
            current_question_text = question_match.group(2).strip()
            current_options = {}
            current_option_letter = None
            continue

        option_match = OPTION_PATTERN.match(line)
        if option_match:
            if current_number is None:
                parse_warnings.append(
                    f"Line {line_number}: option outside question context "
                    f"in source {current_source}"
                )
                continue
            option_letter = option_match.group(1).lower()
            option_text = option_match.group(2).strip()
            current_options[option_letter] = option_text
            current_option_letter = option_letter
            continue

        stripped = line.strip()
        if not stripped:
            continue

        if current_number is not None:
            if current_option_letter is not None:
                current_options[current_option_letter] = (
                    f"{current_options[current_option_letter]} {stripped}".strip()
                )
            else:
                current_question_text = f"{current_question_text} {stripped}".strip()

    finalize_question()

    if not questions:
        parse_warnings.append("No questions found in markdown input")

    return questions, categories, parse_warnings


def iter_questions_by_source(question_bank: QuestionBank, source: str) -> Iterable[Question]:
    return (q for q in question_bank.questions if q.category == source)
