"""Unit tests for pipeline/runtime/classify_step.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pipeline.runtime.config import ClassifyConfig
from pipeline.runtime.classify_step import ClassifyStepResult, run_classify_step


class _FakeClassifier:
    def __init__(self, classifications):
        self.classifications = classifications
        self.close_called = False

    async def classify_batch_with_reasons(self, inputs):
        results = []
        for i, (title, description) in enumerate(inputs):
            if i < len(self.classifications):
                cat, reason = self.classifications[i]
                results.append((cat, reason))
            else:
                results.append((None, "no_classification"))
        return results

    async def close(self):
        self.close_called = True


@pytest.mark.asyncio
async def test_run_classify_step_empty_uncategorized_jobs():
    """When no uncategorized jobs exist, return zeros."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar = MagicMock(return_value=0)
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    mock_db.expunge_all = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    fake_classifier = _FakeClassifier([])

    result = await run_classify_step(
        db=mock_db,
        classifier=fake_classifier,
        commit_batch_size=10,
    )

    assert result == ClassifyStepResult(success_count=0, error_count=0, processed_count=0)
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_run_classify_step_single_batch_under_commit_size():
    """Single batch under commit_batch_size triggers one commit."""
    mock_db = AsyncMock()
    mock_total_result = MagicMock()
    mock_total_result.scalar = MagicMock(return_value=2)
    mock_batch_result = MagicMock()
    mock_batch_result.all = MagicMock(
        return_value=[
            MagicMock(id=1, title="A", description_text="d1"),
            MagicMock(id=2, title="B", description_text="d2"),
        ]
    )
    mock_update_result = MagicMock()
    mock_db.execute.side_effect = [
        mock_total_result,
        mock_batch_result,
        mock_update_result,
        mock_update_result,
    ]
    mock_db.commit = AsyncMock()
    mock_db.expunge_all = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    fake_classifier = _FakeClassifier([("software_engineering", "ok"), ("finance", "ok")])

    result = await run_classify_step(
        db=mock_db,
        classifier=fake_classifier,
        commit_batch_size=10,
    )

    assert result == ClassifyStepResult(success_count=2, error_count=0, processed_count=2)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_classify_step_multi_batch_over_commit_size():
    """Multi-batch over commit_batch_size triggers multiple commits."""
    mock_db = AsyncMock()
    mock_total_result = MagicMock()
    mock_total_result.scalar = MagicMock(return_value=4)
    mock_batch_result_1 = MagicMock()
    mock_batch_result_1.all = MagicMock(
        return_value=[
            MagicMock(id=1, title="A", description_text="d1"),
            MagicMock(id=2, title="B", description_text="d2"),
        ]
    )
    mock_batch_result_2 = MagicMock()
    mock_batch_result_2.all = MagicMock(
        return_value=[
            MagicMock(id=3, title="C", description_text="d3"),
            MagicMock(id=4, title="D", description_text="d4"),
        ]
    )
    mock_update_result = MagicMock()
    mock_db.execute.side_effect = [
        mock_total_result,
        mock_batch_result_1,
        mock_update_result,
        mock_update_result,
        mock_batch_result_2,
        mock_update_result,
        mock_update_result,
    ]
    mock_db.commit = AsyncMock()
    mock_db.expunge_all = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    fake_classifier = _FakeClassifier(
        [
            ("software_engineering", "ok"),
            ("finance", "ok"),
            ("sales", "ok"),
            ("marketing", "ok"),
        ]
    )

    result = await run_classify_step(
        db=mock_db,
        classifier=fake_classifier,
        commit_batch_size=2,
    )

    assert result == ClassifyStepResult(success_count=4, error_count=0, processed_count=4)
    assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_run_classify_step_honors_configured_commit_size():
    config = ClassifyConfig(commit_batch_size=50)
    mock_db = AsyncMock()
    total_result = MagicMock()
    total_result.scalar.return_value = 51
    first_batch = MagicMock()
    first_batch.all.return_value = [
        MagicMock(id=index, title=f"Job {index}", description_text="description") for index in range(1, 51)
    ]
    second_batch = MagicMock()
    second_batch.all.return_value = [
        MagicMock(id=51, title="Job 51", description_text="description"),
    ]
    update_results = [MagicMock() for _ in range(51)]
    mock_db.execute.side_effect = [
        total_result,
        first_batch,
        *update_results[:50],
        second_batch,
        update_results[50],
    ]
    mock_db.commit = AsyncMock()
    mock_db.expunge_all = MagicMock()
    classifier = _FakeClassifier([("software_engineering", "ok")] * 50)

    result = await run_classify_step(
        db=mock_db,
        classifier=classifier,
        commit_batch_size=config.commit_batch_size,
    )

    assert result == ClassifyStepResult(success_count=51, error_count=0, processed_count=51)
    assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_run_classify_step_classifier_returns_none():
    """Classifier returning None counts as error and excludes row from later batches."""
    mock_db = AsyncMock()
    mock_total_result = MagicMock()
    mock_total_result.scalar = MagicMock(return_value=2)
    mock_batch_result = MagicMock()
    mock_batch_result.all = MagicMock(
        return_value=[
            MagicMock(id=1, title="A", description_text="d1"),
            MagicMock(id=2, title="B", description_text="d2"),
        ]
    )
    mock_update_result = MagicMock()
    mock_db.execute.side_effect = [
        mock_total_result,
        mock_batch_result,
        mock_update_result,
        mock_update_result,
    ]
    mock_db.commit = AsyncMock()
    mock_db.expunge_all = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    fake_classifier = _FakeClassifier([(None, "no_match"), ("software_engineering", "ok")])

    result = await run_classify_step(
        db=mock_db,
        classifier=fake_classifier,
        commit_batch_size=10,
    )

    assert result == ClassifyStepResult(success_count=1, error_count=1, processed_count=2)


@pytest.mark.asyncio
async def test_run_classify_step_limit_truncates():
    """Limit parameter truncates total jobs processed."""
    mock_db = AsyncMock()
    mock_total_result = MagicMock()
    mock_total_result.scalar = MagicMock(return_value=10)
    mock_batch_result = MagicMock()
    mock_batch_result.all = MagicMock(
        return_value=[
            MagicMock(id=1, title="A", description_text="d1"),
            MagicMock(id=2, title="B", description_text="d2"),
        ]
    )
    mock_update_result = MagicMock()
    mock_db.execute.side_effect = [
        mock_total_result,
        mock_batch_result,
        mock_update_result,
        mock_update_result,
    ]
    mock_db.commit = AsyncMock()
    mock_db.expunge_all = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    fake_classifier = _FakeClassifier([("software_engineering", "ok"), ("finance", "ok")])

    result = await run_classify_step(
        db=mock_db,
        classifier=fake_classifier,
        commit_batch_size=10,
        limit=2,
    )

    assert result == ClassifyStepResult(success_count=2, error_count=0, processed_count=2)


@pytest.mark.asyncio
async def test_run_classify_step_exhausted_rows_after_exclusion():
    """When all uncategorized rows are excluded, loop stops cleanly."""
    mock_db = AsyncMock()
    mock_total_result = MagicMock()
    mock_total_result.scalar = MagicMock(return_value=3)
    mock_batch_result = MagicMock()
    mock_batch_result.all = MagicMock(
        return_value=[
            MagicMock(id=1, title="A", description_text="d1"),
            MagicMock(id=2, title="B", description_text="d2"),
        ]
    )
    mock_empty_result = MagicMock()
    mock_empty_result.all = MagicMock(return_value=[])
    mock_db.execute.side_effect = [
        mock_total_result,
        mock_batch_result,
        mock_empty_result,
    ]
    mock_db.commit = AsyncMock()
    mock_db.expunge_all = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    fake_classifier = _FakeClassifier([(None, "no_match"), (None, "no_match")])

    result = await run_classify_step(
        db=mock_db,
        classifier=fake_classifier,
        commit_batch_size=10,
    )

    assert result == ClassifyStepResult(success_count=0, error_count=2, processed_count=2)
    assert mock_db.execute.call_count == 3


@pytest.mark.asyncio
async def test_run_classify_step_does_not_close_classifier():
    """Classifier lifecycle remains the caller's responsibility."""
    mock_db = AsyncMock()
    mock_total_result = MagicMock()
    mock_total_result.scalar = MagicMock(return_value=1)
    mock_batch_result = MagicMock()
    mock_batch_result.all = MagicMock(
        return_value=[
            MagicMock(id=1, title="A", description_text="d1"),
        ]
    )
    mock_update_result = MagicMock()
    mock_db.execute.side_effect = [
        mock_total_result,
        mock_batch_result,
        mock_update_result,
    ]
    mock_db.commit = AsyncMock()
    mock_db.expunge_all = MagicMock()

    fake_classifier = _FakeClassifier([("software_engineering", "ok")])

    await run_classify_step(
        db=mock_db,
        classifier=fake_classifier,
        commit_batch_size=10,
    )

    assert fake_classifier.close_called is False
