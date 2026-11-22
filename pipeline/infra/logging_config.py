"""Shared logging setup for pipeline CLI entry points."""

from __future__ import annotations

import logging

# httpx logs every request at INFO ("HTTP Request: GET ... 200 OK"), which
# drowns out our own progress logs across ingest, classification, and
# embedding - all of which go through httpx. Keep it at WARNING so only
# actual problems surface.
_NOISY_THIRD_PARTY_LOGGERS = ("httpx", "httpcore")


def configure_logging(
    format: str = "%(asctime)s [%(levelname)s] %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
    level: int = logging.INFO,
) -> None:
    """Configure root logging and quiet noisy third-party request loggers."""
    logging.basicConfig(level=level, format=format, datefmt=datefmt)
    for name in _NOISY_THIRD_PARTY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
