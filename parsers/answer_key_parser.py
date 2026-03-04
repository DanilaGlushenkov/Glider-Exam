from __future__ import annotations

import re
import unicodedata
from pathlib import Path

ANSWER_PATTERN = re.compile(
    r"^\s*(\d+)[\.)]\s*([a-d](?:\s*,\s*[a-d])*)\s*$",
    re.IGNORECASE,
)
PDF_MARKER_PATTERN = re.compile(r"^\s*([A-Za-z]+)\.pdf\s*$")


def _normalize_ocr_text(text: str) -> str:
    collapsed = re.sub(r"\s+", "", text).lower()
    return "".join(
        ch
        for ch in unicodedata.normalize("NFD", collapsed)
        if unicodedata.category(ch) != "Mn"
    )


def _is_answer_header(raw_line: str) -> bool:
    stripped = raw_line.strip()
    if not stripped or len(stripped) > 80:
        return False
    if re.match(r"^\d+[\.)]", stripped):
        return False

    normalized = _normalize_ocr_text(stripped)
    if not normalized:
        return False

    has_keyword = "vyhodnoceni" in normalized or "reseni" in normalized
    has_context = (
        "otazek" in normalized
        or "testovych" in normalized
        or normalized in {"vyhodnoceni", "reseni"}
        or ("spravne" in normalized and "reseni" in normalized)
    )
    return has_keyword and has_context


def parse_answer_keys(answer_file_path: str | Path) -> dict[str, str]:
    lines = Path(answer_file_path).read_text(encoding="utf-8").splitlines()

    current_source: str | None = None
    in_answer_block = False
    answer_map: dict[str, str] = {}

    for raw_line in lines:
        pdf_match = PDF_MARKER_PATTERN.match(raw_line.strip())
        if pdf_match:
            current_source = pdf_match.group(1)
            in_answer_block = False
            continue

        if current_source is None:
            continue

        if _is_answer_header(raw_line):
            in_answer_block = True
            continue

        if not in_answer_block:
            continue

        answer_match = ANSWER_PATTERN.match(raw_line)
        if not answer_match:
            continue

        question_number = int(answer_match.group(1))
        normalized_answers = ",".join(
            part.strip().lower() for part in answer_match.group(2).split(",")
        )
        question_id = f"vzor/{current_source}/{question_number}"
        answer_map[question_id] = normalized_answers

    return answer_map


def load_json_answer_keys(json_path: str | Path) -> dict[str, str]:
    """Load unified answer keys from a JSON file.

    Returns a mapping of ``{question_id: answer_letters}``.
    Falls back to an empty dict if the file is missing or malformed.
    """
    import json
    import logging

    logger = logging.getLogger(__name__)
    path = Path(json_path)

    if not path.exists():
        logger.warning("Answer key file not found: %s", path)
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning("Answer key file is not a JSON object: %s", path)
            return {}
        return {str(k): str(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load answer keys from %s: %s", path, exc)
        return {}
