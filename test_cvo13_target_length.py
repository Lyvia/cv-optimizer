"""
test_cvo13_target_length.py — Regression tests for CVO-13's target-length
option: optimize_cv() must support an explicit 1-page/2-page budget on top
of the original "match original length" default.

Zero-cost: no LLM call, no mocking needed -- this only inspects the prompt
text PromptBuilder builds (run with: python -m pytest test_cvo13_target_length.py -v).
"""

from src.prompts import PromptBuilder
from src.styles import WORDS_PER_PAGE_ESTIMATE

SAMPLE_CV = "John Doe\n" + ("Experienced engineer. " * 30)


def test_default_keeps_length_relative_to_original():
    pb = PromptBuilder()
    word_count = len(SAMPLE_CV.split())

    prompt = pb.optimize_cv(SAMPLE_CV, "")

    assert f"close to the original CV (~{word_count} words)" in prompt
    assert "MUST fit within" not in prompt


def test_target_pages_one_uses_absolute_word_budget():
    pb = PromptBuilder()

    prompt = pb.optimize_cv(SAMPLE_CV, "", target_pages=1)

    assert f"MUST fit within 1 A4 page (~{WORDS_PER_PAGE_ESTIMATE} words total" in prompt
    assert "close to the original CV" not in prompt


def test_target_pages_two_doubles_the_budget_and_uses_plural():
    pb = PromptBuilder()

    prompt = pb.optimize_cv(SAMPLE_CV, "", target_pages=2)

    assert f"MUST fit within 2 A4 pages (~{2 * WORDS_PER_PAGE_ESTIMATE} words total" in prompt


def test_target_pages_applies_with_a_job_description_too():
    pb = PromptBuilder()

    prompt = pb.optimize_cv(SAMPLE_CV, "Senior Engineer role", target_pages=1)

    assert f"MUST fit within 1 A4 page (~{WORDS_PER_PAGE_ESTIMATE} words total" in prompt
    assert "Senior Engineer role" in prompt
