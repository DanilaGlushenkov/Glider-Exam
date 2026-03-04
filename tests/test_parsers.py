from __future__ import annotations

from parsers.answer_key_parser import parse_answer_keys
from parsers.markdown_parser import parse_markdown_questions


def test_parse_markdown_questions_returns_expected_count(sample_md_path) -> None:
    bank = parse_markdown_questions(sample_md_path)
    assert len(bank.questions) == 15


def test_parsed_questions_have_expected_fields(sample_md_path) -> None:
    bank = parse_markdown_questions(sample_md_path)

    first = bank.get_by_id("vzor/Aerodynamika/1")
    assert first is not None
    assert first.category == "Aerodynamika"
    assert first.number == 1
    assert first.text.startswith("Podle standardní atmosféry")
    assert first.options["a"] == "roste"
    assert first.options["d"] == "nejprve roste a pak klesá"


def test_image_reference_detection(sample_md_path) -> None:
    bank = parse_markdown_questions(sample_md_path)
    question = bank.get_by_id("vzor/Aerodynamika/5")

    assert question is not None
    assert question.has_image_ref is True


def test_questions_with_less_than_four_options_generate_warnings(sample_md_path) -> None:
    bank = parse_markdown_questions(sample_md_path)

    warning_ids = [warning for warning in bank.parse_warnings if "unexpected option count" in warning]
    assert any("vzor/Aerodynamika/4" in warning for warning in warning_ids)
    assert any("vzor/Aerodynamika/5" in warning for warning in warning_ids)


def test_parse_answer_keys_returns_expected_count(sample_vzor_path) -> None:
    answer_map = parse_answer_keys(sample_vzor_path)
    assert len(answer_map) == 15


def test_answer_keys_map_to_correct_ids(sample_vzor_path) -> None:
    answer_map = parse_answer_keys(sample_vzor_path)

    assert answer_map["vzor/Aerodynamika/1"] == "b"
    assert answer_map["vzor/Meteorologie/3"] == "b"
    assert answer_map["vzor/Navigace/5"] == "a"


def test_integration_all_sample_questions_have_answer_keys(sample_md_path, sample_vzor_path) -> None:
    bank = parse_markdown_questions(sample_md_path)
    answer_map = parse_answer_keys(sample_vzor_path)

    missing = [question.id for question in bank.questions if question.id not in answer_map]
    assert missing == []
