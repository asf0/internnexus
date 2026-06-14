"""Unit tests for core job enums."""

from __future__ import annotations

from internnexus_core.jobs import JobSource, JobType, WorkMode


class TestJobSource:
    def test_expected_values(self):
        assert JobSource.greenhouse.value == "greenhouse"
        assert JobSource.lever.value == "lever"
        assert JobSource.ashby.value == "ashby"
        assert JobSource.manual.value == "manual"

    def test_count(self):
        assert len(JobSource) == 4

    def test_value_construction(self):
        assert JobSource("greenhouse") is JobSource.greenhouse

    def test_no_scraper_sources(self):
        for scraper in ("linkedin_scrape", "indeed_scrape"):
            with pytest.raises(ValueError):
                JobSource(scraper)


class TestJobType:
    def test_expected_values(self):
        assert JobType.internship.value == "internship"
        assert JobType.full_time.value == "full_time"
        assert JobType.part_time.value == "part_time"

    def test_count(self):
        assert len(JobType) == 3


class TestWorkMode:
    def test_expected_values(self):
        assert WorkMode.remote.value == "remote"
        assert WorkMode.hybrid.value == "hybrid"
        assert WorkMode.on_site.value == "on_site"

    def test_count(self):
        assert len(WorkMode) == 3


class TestEnumConsistency:
    def test_all_values_are_strings(self):
        for enum_cls in (JobSource, JobType, WorkMode):
            for member in enum_cls:
                assert isinstance(member.value, str)

    def test_no_duplicate_values(self):
        for enum_cls in (JobSource, JobType, WorkMode):
            values = [m.value for m in enum_cls]
            assert len(values) == len(set(values))


import pytest
