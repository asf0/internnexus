from __future__ import annotations

import base64
import hashlib
import io
import sys
import time
from types import SimpleNamespace
from types import ModuleType
from unittest.mock import AsyncMock

from cryptography.fernet import Fernet
import pytest

import app.services.users.resume as resume_service
from app.services.users.resume import (
    ResumeProcessingError,
    decrypt_resume_text,
    decrypt_resume_text_dedicated,
    encrypt_resume_text,
    extract_resume_text,
    extract_text_from_pdf,
    read_resume_upload,
    resume_processing_client_message,
)


def test_resume_encryption_writes_with_dedicated_key(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key()
    settings = SimpleNamespace(resume_encryption_key=key.decode(), auth_secret="legacy-secret")
    monkeypatch.setattr(resume_service, "get_settings", lambda: settings)

    ciphertext = encrypt_resume_text("resume text")

    assert decrypt_resume_text_dedicated(ciphertext) == "resume text"
    assert decrypt_resume_text(ciphertext) == "resume text"


def test_resume_decryption_retains_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key()
    auth_secret = "legacy-secret"
    settings = SimpleNamespace(resume_encryption_key=key.decode(), auth_secret=auth_secret)
    monkeypatch.setattr(resume_service, "get_settings", lambda: settings)
    legacy_key = base64.urlsafe_b64encode(hashlib.sha256(auth_secret.encode()).digest())
    ciphertext = Fernet(legacy_key).encrypt(b"legacy resume").decode()

    assert decrypt_resume_text(ciphertext) == "legacy resume"
    with pytest.raises(ResumeProcessingError):
        decrypt_resume_text_dedicated(ciphertext)


def test_resume_encryption_requires_dedicated_key(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(resume_encryption_key="", auth_secret="legacy-secret")
    monkeypatch.setattr(resume_service, "get_settings", lambda: settings)

    with pytest.raises(ResumeProcessingError, match="RESUME_ENCRYPTION_KEY"):
        encrypt_resume_text("resume text")


@pytest.mark.asyncio
async def test_resume_upload_read_is_bounded() -> None:
    upload = AsyncMock()
    upload.read.return_value = b"resume"

    assert await read_resume_upload(upload) == b"resume"
    upload.read.assert_awaited_once_with(resume_service.MAX_RESUME_FILE_BYTES + 1)


@pytest.mark.asyncio
async def test_resume_upload_rejects_size_sentinel() -> None:
    upload = AsyncMock()
    upload.read.return_value = b"x" * (resume_service.MAX_RESUME_FILE_BYTES + 1)

    with pytest.raises(ResumeProcessingError, match="File too large"):
        await read_resume_upload(upload)


def test_pdf_parser_failures_do_not_include_raw_exception_details(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingPdfReader:
        def __init__(self, _file_obj: object) -> None:
            raise RuntimeError("secret parser path /srv/private/resume.pdf")

    pypdf_module = ModuleType("pypdf")
    pypdf_module.PdfReader = FailingPdfReader

    pdfminer_module = ModuleType("pdfminer")
    pdfminer_high_level = ModuleType("pdfminer.high_level")

    def failing_pdfminer_extract(_file_obj: object, **_kwargs: object) -> str:
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


def test_pdf_with_too_many_pages_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    class ManyPagesPdfReader:
        def __init__(self, _file_obj: object) -> None:
            pass

        @property
        def pages(self) -> list:
            return [None] * 100  # 100 pages, exceeds limit of 50

    pypdf_module = ModuleType("pypdf")
    pypdf_module.PdfReader = ManyPagesPdfReader
    monkeypatch.setitem(sys.modules, "pypdf", pypdf_module)

    pdfminer_module = ModuleType("pdfminer")
    pdfminer_high_level = ModuleType("pdfminer.high_level")
    pdfminer_high_level.extract_text = lambda _f: ""
    monkeypatch.setitem(sys.modules, "pdfminer", pdfminer_module)
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", pdfminer_high_level)

    with pytest.raises(ResumeProcessingError, match="too many pages"):
        extract_text_from_pdf(io.BytesIO(b"%PDF fake content"))


def test_pdf_with_oversized_text_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    huge_text = "x" * 2_000_000  # 2MB, exceeds limit of 1MB

    class SinglePagePdfReader:
        def __init__(self, _file_obj: object) -> None:
            pass

        @property
        def pages(self) -> list:
            class Page:
                def extract_text(self) -> str:
                    return huge_text
            return [Page()]

    pypdf_module = ModuleType("pypdf")
    pypdf_module.PdfReader = SinglePagePdfReader
    monkeypatch.setitem(sys.modules, "pypdf", pypdf_module)

    pdfminer_module = ModuleType("pdfminer")
    pdfminer_high_level = ModuleType("pdfminer.high_level")
    pdfminer_high_level.extract_text = lambda _f: ""
    monkeypatch.setitem(sys.modules, "pdfminer", pdfminer_module)
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", pdfminer_high_level)

    with pytest.raises(ResumeProcessingError, match="too long"):
        extract_text_from_pdf(io.BytesIO(b"%PDF fake content"))


def test_pdfminer_fallback_is_limited_to_max_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingPdfReader:
        def __init__(self, _file_obj: object) -> None:
            raise RuntimeError("pypdf cannot parse this fixture")

    pypdf_module = ModuleType("pypdf")
    pypdf_module.PdfReader = FailingPdfReader
    monkeypatch.setitem(sys.modules, "pypdf", pypdf_module)

    captured_kwargs: dict[str, object] = {}
    pdfminer_module = ModuleType("pdfminer")
    pdfminer_high_level = ModuleType("pdfminer.high_level")

    def pdfminer_extract(_file_obj: object, **kwargs: object) -> str:
        captured_kwargs.update(kwargs)
        return "valid resume text"

    pdfminer_high_level.extract_text = pdfminer_extract
    monkeypatch.setitem(sys.modules, "pdfminer", pdfminer_module)
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", pdfminer_high_level)

    assert extract_text_from_pdf(io.BytesIO(b"%PDF fake content")) == "valid resume text"
    assert captured_kwargs["maxpages"] == 50


def test_text_fallback_rejects_oversized_printable_pdf_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingPdfReader:
        def __init__(self, _file_obj: object) -> None:
            raise RuntimeError("pypdf cannot parse this fixture")

    pypdf_module = ModuleType("pypdf")
    pypdf_module.PdfReader = FailingPdfReader
    monkeypatch.setitem(sys.modules, "pypdf", pypdf_module)

    pdfminer_module = ModuleType("pdfminer")
    pdfminer_high_level = ModuleType("pdfminer.high_level")
    pdfminer_high_level.extract_text = lambda _file_obj, **_kwargs: ""
    monkeypatch.setitem(sys.modules, "pdfminer", pdfminer_module)
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", pdfminer_high_level)

    huge_printable_pdf = b"%PDF " + (b"x" * 2_000_000)
    with pytest.raises(ResumeProcessingError, match="too long"):
        extract_text_from_pdf(io.BytesIO(huge_printable_pdf))


def _slow_pdf_worker(_file_content: bytes, _result_queue: object) -> None:
    # Module level so the forkserver start method (the 3.14 default) can
    # pickle the process target; local closures cannot be pickled.
    time.sleep(2)


@pytest.mark.asyncio
async def test_pdf_parse_timeout_is_client_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resume_service, "_PDF_PARSE_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(resume_service, "_pdf_parse_worker", _slow_pdf_worker)

    with pytest.raises(ResumeProcessingError, match="timed out") as exc_info:
        await extract_resume_text("resume.pdf", b"%PDF fake content")

    assert resume_processing_client_message(exc_info.value) == "PDF parsing timed out"
