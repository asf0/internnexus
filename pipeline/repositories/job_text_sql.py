"""Shared SQL expressions for job text filtering."""

from __future__ import annotations

from sqlalchemy import func

from pipeline.infra.models import Job


def rowcount(result: object) -> int:
    """Normalize a SQLAlchemy result's ``rowcount`` to an int.

    Async drivers do not all expose ``rowcount`` consistently, so callers
    fall back to 0 when it is missing or ``None``.
    """
    return int(getattr(result, "rowcount", 0) or 0)


def embedding_candidate_text_sql():
    """Return SQL expression approximating embedding text cleanup."""
    return func.trim(
        func.regexp_replace(
            func.replace(
                func.regexp_replace(
                    func.regexp_replace(
                        func.regexp_replace(Job.description_text, r"<[^>]+>", " ", "g"),
                        r"&[a-zA-Z]+;",
                        " ",
                        "g",
                    ),
                    r"```[a-zA-Z0-9_+-]*",
                    " ",
                    "g",
                ),
                "```",
                " ",
            ),
            r"\s+",
            " ",
            "g",
        )
    )
