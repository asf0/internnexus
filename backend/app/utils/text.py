"""Text processing utilities."""

from __future__ import annotations

import re


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
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Determine text type and apply appropriate limit
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    is_mostly_ascii = len(text) == 0 or (ascii_chars / len(text)) > 0.8

    max_chars = max_chars_ascii if is_mostly_ascii else max_chars_unicode

    return text[:max_chars]
