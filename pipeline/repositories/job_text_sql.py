"""Shared SQL expressions for job text filtering."""

from __future__ import annotations

from sqlalchemy import func

from pipeline.models import Job


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
