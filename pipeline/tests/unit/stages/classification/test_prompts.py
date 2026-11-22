"""Prompt constraints for keeping model outputs inside the job taxonomy."""

from __future__ import annotations

from pipeline.stages.classification.prompts import (
    _build_batch_classification_prompts,
    _build_classification_prompts,
)


def test_single_prompt_requires_job_function_not_industry() -> None:
    system_prompt, _ = _build_classification_prompts("Store Manager", "Retail operations")

    assert "Classify the job function, not its industry or workplace" in system_prompt
    assert "retail" in system_prompt


def test_batch_prompt_requires_job_function_not_industry() -> None:
    system_prompt, _ = _build_batch_classification_prompts([("Auto Technician", "Repairs vehicles")])

    assert "Classify the job function, not its industry or workplace" in system_prompt
