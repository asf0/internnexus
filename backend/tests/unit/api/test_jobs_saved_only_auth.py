from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.jobs import _get_saved_job_ids


@pytest.mark.asyncio
async def test_saved_only_requires_authenticated_user() -> None:
    session = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await _get_saved_job_ids(session, None, saved_only=True)

    assert exc_info.value.status_code == 401
    session.execute.assert_not_awaited()
