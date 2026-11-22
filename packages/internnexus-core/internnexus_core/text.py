"""Text processing utilities."""

from __future__ import annotations

import hashlib
import html
import re

_CONTROL_CHARS = re.compile(r"[\x00\x01-\x08\x0b\x0c\x0e-\x1f\x7f]")
_INLINE_STYLE = re.compile(r' style="[^"]*"')


def clean_job_description(text: str) -> str:
    """Decode entities, drop inline styles, and strip control chars.

    Shared by persistence and snapshot hashing so the two never drift.
    """
    if not text:
        return text
    return strip_control_chars(_INLINE_STYLE.sub("", html.unescape(text))) or ""


def strip_control_chars(text: str | None) -> str | None:
    """Remove NUL and other non-printable C0 control chars (keeps \\n, \\r, \\t).

    PostgreSQL text columns reject 0x00 outright; the remaining C0 controls
    are junk in job text.
    """
    if text is None:
        return None
    return _CONTROL_CHARS.sub("", text)


def clean_text_for_embedding(
    text: str,
    max_chars_ascii: int = 6000,
    max_chars_unicode: int = 2000,
) -> str:
    """Clean and truncate text for embedding.

    Removes HTML tags, HTML entities, and normalizes whitespace.
    Uses higher limit for ASCII text (English) and lower limit for
    non-ASCII text (Japanese, Chinese, etc.) which uses more tokens per char.

    Args:
        text: Raw text to clean
        max_chars_ascii: Maximum characters for mostly-ASCII text
        max_chars_unicode: Maximum characters for mostly-Unicode text

    Returns:
        Cleaned and truncated text
    """
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove HTML entities
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    # Remove markdown code fence markers while keeping code content
    text = re.sub(r"```[a-zA-Z0-9_+-]*", " ", text)
    text = text.replace("```", " ")
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Determine text type and apply appropriate limit
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    is_mostly_ascii = len(text) == 0 or (ascii_chars / len(text)) > 0.8

    max_chars = max_chars_ascii if is_mostly_ascii else max_chars_unicode

    return text[:max_chars]


def embedding_input_hash(text: str) -> str:
    """Return a stable digest of the exact text sent to the embedding provider."""
    cleaned = clean_text_for_embedding(text)
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
