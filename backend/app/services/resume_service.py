from __future__ import annotations

import base64
import hashlib
import io
import logging
import re
from typing import BinaryIO

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

_WHITESPACE_RE = re.compile(r"\s+")
logger = logging.getLogger(__name__)

# Resource limits for PDF parsing to prevent crafted-file exhaustion.
_MAX_PDF_PAGES = 50
_MAX_EXTRACTED_TEXT_LENGTH = 1_000_000  # 1MB of text

_SAFE_RESUME_PROCESSING_MESSAGES = {
    "Cannot encrypt empty resume text",
    "Cannot decrypt empty resume text",
    "Failed to decrypt stored resume text",
    "Resume text is empty",
    "Invalid PDF file header",
    "Only PDF and TXT files are accepted",
    "PDF has too many pages (max 50)",
    "Extracted text is too long",
}
_PDF_EXTRACTION_ERROR = "Could not extract text from PDF. Please upload a text-based PDF or TXT file."
_TEXT_DECODE_ERROR = "Failed to decode text file"


class ResumeProcessingError(Exception):
    """Raised when resume parsing or crypto operations fail."""


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


def _build_fernet() -> Fernet:
    settings = get_settings()
    key_material = hashlib.sha256(settings.auth_secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(key_material)
    return Fernet(key)


def encrypt_resume_text(plaintext: str) -> str:
    if not plaintext:
        raise ResumeProcessingError("Cannot encrypt empty resume text")
    token = _build_fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_resume_text(ciphertext: str) -> str:
    if not ciphertext:
        raise ResumeProcessingError("Cannot decrypt empty resume text")
    try:
        plaintext = _build_fernet().decrypt(ciphertext.encode("utf-8"))
    except InvalidToken as exc:
        raise ResumeProcessingError("Failed to decrypt stored resume text") from exc
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


def extract_text_from_pdf(file_obj: BinaryIO) -> str:
    errors: list[str] = []

    try:
        from pypdf import PdfReader

        file_obj.seek(0)
        reader = PdfReader(file_obj)
        if len(reader.pages) > _MAX_PDF_PAGES:
            raise ResumeProcessingError(f"PDF has too many pages (max {_MAX_PDF_PAGES})")
        text_parts = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(text_parts).strip()
        if text:
            if len(text) > _MAX_EXTRACTED_TEXT_LENGTH:
                raise ResumeProcessingError("Extracted text is too long")
            return text
    except ResumeProcessingError:
        raise
    except Exception as exc:  # noqa: BLE001  # any pypdf failure falls through to next parser
        logger.debug("pypdf failed to extract resume text", exc_info=exc)
        errors.append("pypdf parser failed")

    try:
        from pdfminer.high_level import extract_text as pdfminer_extract

        file_obj.seek(0)
        pdf_bytes = file_obj.read()
        text = (pdfminer_extract(io.BytesIO(pdf_bytes)) or "").strip()
        if text:
            if len(text) > _MAX_EXTRACTED_TEXT_LENGTH:
                raise ResumeProcessingError("Extracted text is too long")
            return text
    except ResumeProcessingError:
        raise
    except ImportError:
        errors.append("pdfminer: not installed")
    except Exception as exc:  # noqa: BLE001  # any pdfminer failure falls through to next parser
        logger.debug("pdfminer failed to extract resume text", exc_info=exc)
        errors.append("pdfminer parser failed")

    try:
        file_obj.seek(0)
        content = file_obj.read()
        if isinstance(content, bytes):
            decoded = _decode_text_bytes(content)
            printable = "".join(c for c in decoded if c.isprintable() or c in "\n\r\t ")
            if len(printable.strip()) > 100:
                return printable.strip()
    except Exception as exc:  # noqa: BLE001  # any text fallback failure is recorded for the final error
        logger.debug("text fallback failed to extract resume text", exc_info=exc)
        errors.append("text fallback failed")

    raise ResumeProcessingError(
        "Could not extract text from PDF. " + "; ".join(errors) if errors else "Unknown parser error"
    )


def extract_resume_text(file_name: str, file_content: bytes) -> str:
    lower = file_name.lower()
    if lower.endswith(".txt"):
        try:
            text = _decode_text_bytes(file_content)
        except Exception as exc:  # noqa: BLE001  # decode failure wrapped as ResumeProcessingError
            logger.debug("Failed to decode text resume", exc_info=exc)
            raise ResumeProcessingError(_TEXT_DECODE_ERROR) from exc
        if not text:
            raise ResumeProcessingError("Resume text is empty")
        return text

    if lower.endswith(".pdf"):
        if not file_content.startswith(b"%PDF"):
            raise ResumeProcessingError("Invalid PDF file header")
        text = extract_text_from_pdf(io.BytesIO(file_content))
        if not text:
            raise ResumeProcessingError("Resume text is empty")
        return text

    raise ResumeProcessingError("Only PDF and TXT files are accepted")
