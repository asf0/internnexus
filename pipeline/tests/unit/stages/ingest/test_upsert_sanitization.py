"""Regression tests for control-character sanitization in the ingest path.

PostgreSQL text columns reject NUL bytes (0x00) outright; job payloads from
source ATSes occasionally contain them and previously failed the whole upsert
batch with CharacterNotInRepertoireError.
"""

from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import sys
from pathlib import Path

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.domain import JobSchema
from pipeline.repositories.job_upsert import build_job_rows
from internnexus_core.text import clean_job_description
from internnexus_core.text import strip_control_chars


class TestStripControlChars:
    def test_removes_nul_bytes(self) -> None:
        assert strip_control_chars("foo\x00bar") == "foobar"

    def test_removes_other_c0_controls_and_del(self) -> None:
        assert strip_control_chars("a\x01b\x08c\x0bd\x1fe\x7ff") == "abcdef"

    def test_preserves_newline_tab_and_carriage_return(self) -> None:
        assert strip_control_chars("line1\nline2\r\n\tindented") == "line1\nline2\r\n\tindented"

    def test_preserves_unicode(self) -> None:
        assert strip_control_chars("日本語 café — résumé") == "日本語 café — résumé"

    def test_none_and_empty_pass_through(self) -> None:
        assert strip_control_chars(None) is None
        assert strip_control_chars("") == ""


class TestJobRowsSanitization:
    def test_rows_contain_no_nul_bytes(self) -> None:
        job = JobSchema(
            source="ashby",
            title="SWE\x00 Intern",
            company="Acme\x00 Corp",
            location="Remote\x00",
            apply_url="https://example.com/apply\x00",
            description_text="A sufficiently long\x00 internship description\x01 for testing.",
        )
        job_rows, _ = build_job_rows([job])
        row = job_rows[0]
        for field in ("title", "company", "location", "apply_url", "description_text"):
            assert "\x00" not in row[field], field
        assert row["title"] == "SWE Intern"
        assert row["description_text"] == "A sufficiently long internship description for testing."

    def test_clean_job_description_strips_nul(self) -> None:
        assert clean_job_description("hello\x00 world") == "hello world"
