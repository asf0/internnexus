import pytest
from pydantic import ValidationError

from app.api.jobs import JobListQuery, MAX_PAGINATION_OFFSET


def test_job_list_offset_limit_depends_on_page_and_page_size():
    assert JobListQuery(page=2000, page_size=20).page == 2000
    with pytest.raises(ValidationError):
        JobListQuery(page=2000, page_size=100)


def test_job_list_offset_limit_allows_the_exact_boundary():
    query = JobListQuery(page=(MAX_PAGINATION_OFFSET // 100) + 1, page_size=100)
    assert (query.page - 1) * query.page_size == MAX_PAGINATION_OFFSET
