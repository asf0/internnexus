from __future__ import annotations

import io
import sys
from types import ModuleType

import pytest

from app.services.resume_service import (
    ResumeProcessingError,
    extract_text_from_pdf,
    resume_processing_client_message,
)


def test_pdf_parser_failures_do_not_include_raw_exception_details(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingPdfReader:
        def __init__(self, _file_obj: object) -> None:
            raise RuntimeError("secret parser path /srv/private/resume.pdf")

    pypdf_module = ModuleType("pypdf")
    pypdf_module.PdfReader = FailingPdfReader

    pdfminer_module = ModuleType("pdfminer")
    pdfminer_high_level = ModuleType("pdfminer.high_level")

    def failing_pdfminer_extract(_file_obj: object) -> str:
        raise RuntimeError("database host internal-db.local")

    pdfminer_high_level.extract_text = failing_pdfminer_extract

    monkeypatch.setitem(sys.modules, "pypdf", pypdf_module)
    monkeypatch.setitem(sys.modules, "pdfminer", pdfminer_module)
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", pdfminer_high_level)

    with pytest.raises(ResumeProcessingError) as exc_info:
        extract_text_from_pdf(io.BytesIO(b"%PDF short invalid content"))

    raw_message = str(exc_info.value)
    client_message = resume_processing_client_message(exc_info.value)

    assert "secret parser path" not in raw_message
    assert "internal-db.local" not in raw_message
    assert "secret parser path" not in client_message
    assert "internal-db.local" not in client_message
    assert client_message == "Could not extract text from PDF. Please upload a text-based PDF or TXT file."


def test_unknown_resume_processing_error_maps_to_generic_client_message() -> None:
    error = ResumeProcessingError("Unexpected parser stack trace: /private/tmp/file.pdf")

    assert resume_processing_client_message(error) == "Could not process resume. Please upload a valid PDF or TXT file."
