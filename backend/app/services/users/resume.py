from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import logging
import multiprocessing
import re
from queue import Empty
from typing import BinaryIO

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

from app.infra.config import get_settings

_WHITESPACE_RE = re.compile(r"\s+")
logger = logging.getLogger(__name__)

# Resource limits for PDF parsing to prevent crafted-file exhaustion.
_MAX_PDF_PAGES = 50
_MAX_EXTRACTED_TEXT_LENGTH = 1_000_000  # 1MB of text
_PDF_PARSE_TIMEOUT_SECONDS = 10.0
_PDF_WORKER_SHUTDOWN_SECONDS = 1.0
_PDF_RESULT_QUEUE_TIMEOUT_SECONDS = 0.2
MAX_RESUME_FILE_BYTES = 10 * 1024 * 1024
_CANNOT_DECRYPT_EMPTY_RESUME_TEXT = "Cannot decrypt empty resume text"
_FAILED_TO_DECRYPT_STORED_RESUME_TEXT = "Failed to decrypt stored resume text"
_RESUME_TEXT_IS_EMPTY = "Resume text is empty"
_EXTRACTED_TEXT_TOO_LONG = "Extracted text is too long"

_SAFE_RESUME_PROCESSING_MESSAGES = {
    "Cannot encrypt empty resume text",
    _CANNOT_DECRYPT_EMPTY_RESUME_TEXT,
    _FAILED_TO_DECRYPT_STORED_RESUME_TEXT,
    _RESUME_TEXT_IS_EMPTY,
    "Invalid PDF file header",
    "Only PDF and TXT files are accepted",
    "PDF has too many pages (max 50)",
    _EXTRACTED_TEXT_TOO_LONG,
    "PDF parsing timed out",
    "File too large (max 10MB)",
}
_PDF_EXTRACTION_ERROR = "Could not extract text from PDF. Please upload a text-based PDF or TXT file."
_TEXT_DECODE_ERROR = "Failed to decode text file"


class ResumeProcessingError(Exception):
    """Raised when resume parsing or crypto operations fail."""


RESUME_SCHEMA_ERROR_DETAIL = (
    "Resume storage schema is outdated. Run database migrations (uv run alembic upgrade head) and retry."
)


def is_resume_schema_error(exc: ProgrammingError) -> bool:
    """Detect the "user_resumes.content_hash is missing" failure from an unmigrated DB."""
    message = str(getattr(exc, "orig", exc)).lower()
    return "user_resumes" in message and "content_hash" in message


def map_resume_schema_commit_error(exc: SQLAlchemyError) -> HTTPException | None:
    """Translate an unmigrated-schema commit failure into a 503, or None to re-raise."""
    if isinstance(exc, ProgrammingError) and is_resume_schema_error(exc):
        return HTTPException(status_code=503, detail=RESUME_SCHEMA_ERROR_DETAIL)
    return None


async def read_resume_upload(file: UploadFile) -> bytes:
    """Read at most the supported resume size plus one sentinel byte."""
    content = await file.read(MAX_RESUME_FILE_BYTES + 1)
    if len(content) > MAX_RESUME_FILE_BYTES:
        raise ResumeProcessingError("File too large (max 10MB)")
    return content


def resume_processing_client_message(error: ResumeProcessingError) -> str:
    """Return a user-safe message for a resume processing failure."""
    message = str(error)
    if message in _SAFE_RESUME_PROCESSING_MESSAGES:
        return message
    if message.startswith("Could not extract text from PDF."):
        return _PDF_EXTRACTION_ERROR
    if message.startswith(_TEXT_DECODE_ERROR):
        return _TEXT_DECODE_ERROR
    return "Could not process resume. Please upload a valid PDF or TXT file."


def _dedicated_fernet() -> Fernet:
    settings = get_settings()
    if not settings.resume_encryption_key:
        raise ResumeProcessingError("RESUME_ENCRYPTION_KEY is required for resume encryption")
    return Fernet(settings.resume_encryption_key.encode())


def _legacy_fernet() -> Fernet:
    settings = get_settings()
    key_material = hashlib.sha256(settings.auth_secret.encode("utf-8")).digest()
    legacy_key = base64.urlsafe_b64encode(key_material)
    return Fernet(legacy_key)


def _decryption_fernet() -> MultiFernet:
    return MultiFernet([_dedicated_fernet(), _legacy_fernet()])


def encrypt_resume_text(plaintext: str) -> str:
    if not plaintext:
        raise ResumeProcessingError("Cannot encrypt empty resume text")
    token = _dedicated_fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_resume_text(ciphertext: str) -> str:
    if not ciphertext:
        raise ResumeProcessingError(_CANNOT_DECRYPT_EMPTY_RESUME_TEXT)
    try:
        plaintext = _decryption_fernet().decrypt(ciphertext.encode("utf-8"))
    except InvalidToken as exc:
        raise ResumeProcessingError(_FAILED_TO_DECRYPT_STORED_RESUME_TEXT) from exc
    return plaintext.decode("utf-8")


def decrypt_resume_text_dedicated(ciphertext: str) -> str:
    """Decrypt using only the dedicated key for post-rotation verification."""
    if not ciphertext:
        raise ResumeProcessingError(_CANNOT_DECRYPT_EMPTY_RESUME_TEXT)
    try:
        plaintext = _dedicated_fernet().decrypt(ciphertext.encode("utf-8"))
    except InvalidToken as exc:
        raise ResumeProcessingError(_FAILED_TO_DECRYPT_STORED_RESUME_TEXT) from exc
    return plaintext.decode("utf-8")


def normalize_resume_text(text: str) -> str:
    normalized = _WHITESPACE_RE.sub(" ", text).strip()
    return normalized


def compute_hash(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _decode_text_bytes(file_content: bytes) -> str:
    return file_content.decode("utf-8", errors="ignore").strip()


def _checked_extracted_text(text: str) -> str:
    if len(text) > _MAX_EXTRACTED_TEXT_LENGTH:
        raise ResumeProcessingError(_EXTRACTED_TEXT_TOO_LONG)
    return text


def _extract_with_pypdf(file_obj: BinaryIO, errors: list[str]) -> str | None:
    try:
        from pypdf import PdfReader

        file_obj.seek(0)
        reader = PdfReader(file_obj)
        if len(reader.pages) > _MAX_PDF_PAGES:
            raise ResumeProcessingError(f"PDF has too many pages (max {_MAX_PDF_PAGES})")
        text_parts = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(text_parts).strip()
        if text:
            return _checked_extracted_text(text)
    except ResumeProcessingError:
        raise
    except Exception as exc:  # noqa: BLE001  # any pypdf failure falls through to next parser
        logger.debug("pypdf failed to extract resume text", exc_info=exc)
        errors.append("pypdf parser failed")
    return None


def _extract_with_pdfminer(file_obj: BinaryIO, errors: list[str]) -> str | None:
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract

        file_obj.seek(0)
        pdf_bytes = file_obj.read()
        text = (pdfminer_extract(io.BytesIO(pdf_bytes), maxpages=_MAX_PDF_PAGES) or "").strip()
        if text:
            return _checked_extracted_text(text)
    except ResumeProcessingError:
        raise
    except ImportError:
        errors.append("pdfminer: not installed")
    except Exception as exc:  # noqa: BLE001  # any pdfminer failure falls through to next parser
        logger.debug("pdfminer failed to extract resume text", exc_info=exc)
        errors.append("pdfminer parser failed")
    return None


def _extract_with_text_fallback(file_obj: BinaryIO, errors: list[str]) -> str | None:
    try:
        file_obj.seek(0)
        content = file_obj.read()
        if isinstance(content, bytes):
            decoded = _decode_text_bytes(content)
            printable = "".join(c for c in decoded if c.isprintable() or c in "\n\r\t ")
            if len(printable.strip()) > 100:
                return _checked_extracted_text(printable.strip())
    except ResumeProcessingError:
        raise
    except Exception as exc:  # noqa: BLE001  # any text fallback failure is recorded for the final error
        logger.debug("text fallback failed to extract resume text", exc_info=exc)
        errors.append("text fallback failed")
    return None


def extract_text_from_pdf(file_obj: BinaryIO) -> str:
    errors: list[str] = []

    for extractor in (_extract_with_pypdf, _extract_with_pdfminer, _extract_with_text_fallback):
        text = extractor(file_obj, errors)
        if text:
            return text

    raise ResumeProcessingError(
        "Could not extract text from PDF. " + "; ".join(errors) if errors else "Unknown parser error"
    )


def _pdf_parse_worker(file_content: bytes, result_queue: multiprocessing.Queue) -> None:
    try:
        text = extract_text_from_pdf(io.BytesIO(file_content))
    except ResumeProcessingError as exc:
        result_queue.put(("resume_error", str(exc)))
    except Exception:  # noqa: BLE001  # raw parser errors are intentionally hidden from clients
        logger.exception("Unexpected PDF parser worker failure")
        result_queue.put(("error", _PDF_EXTRACTION_ERROR))
    else:
        result_queue.put(("ok", text))


async def _extract_text_from_pdf_with_budget(file_content: bytes) -> str:
    """Extract PDF text in a child process so parser timeouts are enforceable."""
    context = multiprocessing.get_context()
    result_queue = context.Queue(maxsize=1)
    process = context.Process(target=_pdf_parse_worker, args=(file_content, result_queue))
    process.start()
    await asyncio.to_thread(process.join, _PDF_PARSE_TIMEOUT_SECONDS)

    try:
        if process.is_alive():
            process.terminate()
            process.join(_PDF_WORKER_SHUTDOWN_SECONDS)
            if process.is_alive() and hasattr(process, "kill"):
                process.kill()
                process.join(_PDF_WORKER_SHUTDOWN_SECONDS)
            raise ResumeProcessingError("PDF parsing timed out")

        try:
            status, payload = result_queue.get(timeout=_PDF_RESULT_QUEUE_TIMEOUT_SECONDS)
        except Empty as exc:
            raise ResumeProcessingError(_PDF_EXTRACTION_ERROR) from exc

        if status == "ok":
            return str(payload)
        raise ResumeProcessingError(str(payload))
    finally:
        result_queue.close()
        result_queue.join_thread()


async def extract_resume_text(file_name: str, file_content: bytes) -> str:
    lower = file_name.lower()
    if lower.endswith(".txt"):
        try:
            text = _decode_text_bytes(file_content)
        except Exception as exc:  # noqa: BLE001  # decode failure wrapped as ResumeProcessingError
            logger.debug("Failed to decode text resume", exc_info=exc)
            raise ResumeProcessingError(_TEXT_DECODE_ERROR) from exc
        if not text:
            raise ResumeProcessingError(_RESUME_TEXT_IS_EMPTY)
        return text

    if lower.endswith(".pdf"):
        if not file_content.startswith(b"%PDF"):
            raise ResumeProcessingError("Invalid PDF file header")
        text = await _extract_text_from_pdf_with_budget(file_content)
        if not text:
            raise ResumeProcessingError(_RESUME_TEXT_IS_EMPTY)
        return text

    raise ResumeProcessingError("Only PDF and TXT files are accepted")
