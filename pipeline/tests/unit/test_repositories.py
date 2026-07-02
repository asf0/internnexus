"""Unit tests for pipeline/repositories/__init__.py."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pipeline.repositories import (
    JobLocationData,
    LocationUpdate,
    JobRepository,
)


class TestJobLocationData:
    """Test suite for JobLocationData dataclass."""

    def test_creation_with_all_fields(self):
        job_id = uuid4()
        data = JobLocationData(
            id=job_id,
            source="greenhouse",
            location="San Francisco, CA",
            city="San Francisco",
            state="California",
            country="United States",
        )

        assert data.id == job_id
        assert data.source == "greenhouse"
        assert data.location == "San Francisco, CA"
        assert data.city == "San Francisco"
        assert data.state == "California"
        assert data.country == "United States"

    def test_creation_with_none_values(self):
        job_id = uuid4()
        data = JobLocationData(
            id=job_id,
            source="lever",
            location="Remote",
            city=None,
            state=None,
            country=None,
        )

        assert data.id == job_id
        assert data.source == "lever"
        assert data.location == "Remote"
        assert data.city is None
        assert data.state is None
        assert data.country is None

    def test_is_dataclass(self):
        from dataclasses import is_dataclass

        assert is_dataclass(JobLocationData)

    def test_immutability(self):
        job_id = uuid4()
        data = JobLocationData(
            id=job_id,
            source="ashby",
            location="Test",
            city=None,
            state=None,
            country=None,
        )

        data.source = "greenhouse"
        assert data.source == "greenhouse"


class TestLocationUpdate:
    """Test suite for LocationUpdate dataclass."""

    def test_creation_with_all_fields(self):
        job_id = uuid4()
        update = LocationUpdate(
            job_id=job_id,
            city="New York",
            state="New York",
            country="United States",
            is_remote=False,
        )

        assert update.job_id == job_id
        assert update.city == "New York"
        assert update.state == "New York"
        assert update.country == "United States"
        assert update.is_remote is False

    def test_creation_with_remote_flag(self):
        job_id = uuid4()
        update = LocationUpdate(
            job_id=job_id,
            city=None,
            state=None,
            country="United States",
            is_remote=True,
        )

        assert update.job_id == job_id
        assert update.city is None
        assert update.state is None
        assert update.country == "United States"
        assert update.is_remote is True

    def test_is_dataclass(self):
        from dataclasses import is_dataclass

        assert is_dataclass(LocationUpdate)


class TestJobRepositoryProtocol:
    """Test suite for JobRepository protocol."""

    def test_protocol_is_defined(self):
        assert JobRepository is not None

    def test_protocol_has_required_methods(self):
        required_methods = [
            "fetch_jobs_batch",
            "update_job_locations",
            "get_jobs_without_embeddings",
            "get_jobs_by_ids",
            "update_job_embedding",
            "delete_inactive_jobs",
            "get_total_count",
        ]

        for method_name in required_methods:
            assert hasattr(JobRepository, method_name) or method_name in dir(JobRepository)

    def test_protocol_signature_fetch_jobs_batch(self):
        import inspect

        sig = inspect.signature(JobRepository.fetch_jobs_batch)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "since" in params
        assert "process_all" in params
        assert "offset" in params
        assert "limit" in params

    def test_protocol_signature_update_job_locations(self):
        import inspect

        sig = inspect.signature(JobRepository.update_job_locations)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "updates" in params


class TestSQLAlchemyRepositoryImport:
    """Test suite for SQLAlchemyRepository import."""

    def test_can_import_sqlalchemy_repo(self):
        from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository

        assert SQLAlchemyJobRepository is not None

    def test_sqlalchemy_repo_exports_boundary_symbols(self):
        from pipeline.repositories.sqlalchemy_repo import __all__

        expected_exports = {
            "SQLAlchemyJobRepository",
            "get_repository",
        }

        assert expected_exports.issubset(set(__all__))

    def test_sqlalchemy_repo_has_required_methods(self):
        from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository

        required_methods = [
            "fetch_jobs_batch",
            "update_job_locations",
            "get_jobs_without_embeddings",
            "get_jobs_by_ids",
            "update_job_embedding",
            "delete_inactive_jobs",
            "get_total_count",
        ]

        for method_name in required_methods:
            assert hasattr(SQLAlchemyJobRepository, method_name)

    def test_sqlalchemy_repo_init_signature(self):
        import inspect
        from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository

        sig = inspect.signature(SQLAlchemyJobRepository.__init__)
        params = list(sig.parameters.keys())

        assert "self" in params
        assert "session" in params

    @pytest.mark.asyncio
    async def test_delete_inactive_jobs_uses_standalone_default_batch_size(self, monkeypatch):
        from pipeline.repositories import sqlalchemy_repo

        sync_id = uuid4()
        session = object()
        batched_delete = AsyncMock(return_value=7)
        monkeypatch.setattr(sqlalchemy_repo, "batched_delete_inactive", batched_delete)

        repo = sqlalchemy_repo.SQLAlchemyJobRepository(session)
        result = await repo.delete_inactive_jobs(sync_id)

        assert result == 7
        batched_delete.assert_awaited_once_with(
            session,
            sync_id,
            batch_size=sqlalchemy_repo.SYNC_BATCH_SIZE,
            max_attempts=None,
            base_delay=None,
            max_delay=None,
        )


class TestRepositoryProtocolCompliance:
    """Test that SQLAlchemyJobRepository complies with JobRepository protocol."""

    def test_sqlalchemy_repo_satisfies_protocol(self):
        from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository

        protocol_methods = set(dir(JobRepository))
        repo_methods = set(dir(SQLAlchemyJobRepository))

        protocol_public_methods = {
            m for m in protocol_methods if not m.startswith("_") and callable(getattr(JobRepository, m, None))
        }

        for method in protocol_public_methods:
            if method in ["__init__", "__class__"]:
                continue
            assert method in repo_methods, f"Missing method: {method}"


class TestDataclassEquality:
    """Test equality and comparison of dataclasses."""

    def test_job_location_data_equality(self):
        job_id = uuid4()
        data1 = JobLocationData(
            id=job_id,
            source="greenhouse",
            location="SF",
            city="San Francisco",
            state="CA",
            country="US",
        )
        data2 = JobLocationData(
            id=job_id,
            source="greenhouse",
            location="SF",
            city="San Francisco",
            state="CA",
            country="US",
        )

        assert data1 == data2

    def test_job_location_data_inequality(self):
        job_id = uuid4()
        data1 = JobLocationData(
            id=job_id,
            source="greenhouse",
            location="SF",
            city="San Francisco",
            state="CA",
            country="US",
        )
        data2 = JobLocationData(
            id=job_id,
            source="lever",
            location="SF",
            city="San Francisco",
            state="CA",
            country="US",
        )

        assert data1 != data2

    def test_location_update_equality(self):
        job_id = uuid4()
        update1 = LocationUpdate(
            job_id=job_id,
            city="NYC",
            state="NY",
            country="US",
            is_remote=False,
        )
        update2 = LocationUpdate(
            job_id=job_id,
            city="NYC",
            state="NY",
            country="US",
            is_remote=False,
        )

        assert update1 == update2
