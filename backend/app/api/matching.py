from __future__ import annotations

import io
from typing import Annotated, BinaryIO

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas import MatchResponse, MatchResult
from app.auth import get_current_user
from app.db import get_db
from app.models import Job, User
from app.rate_limiter import limiter
from app.services.embedding_service import EmbeddingService

router = APIRouter()


def extract_text_from_pdf(file: BinaryIO) -> str:
    """Extract text from PDF using pypdf, with fallback to pdfminer."""
    text = ""
    errors = []

    # Try pypdf first
    try:
        from pypdf import PdfReader

        file.seek(0)
        reader = PdfReader(file)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        text = "\n".join(text_parts).strip()
        if text:
            return text
    except Exception as e:
        errors.append(f"pypdf: {str(e)}")

    # Fallback to pdfminer if pypdf fails or returns empty
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract

        file.seek(0)
        text = pdfminer_extract(file)
        if text:
            return text.strip()
    except ImportError:
        errors.append("pdfminer: not installed")
    except Exception as e:
        errors.append(f"pdfminer: {str(e)}")

    # Last resort: try reading as plain text (some "PDFs" are actually text)
    try:
        file.seek(0)
        content = file.read()
        if isinstance(content, bytes):
            # Check if it looks like text
            try:
                decoded = content.decode("utf-8", errors="ignore")
                # Filter out binary garbage
                printable = "".join(c for c in decoded if c.isprintable() or c in "\n\r\t ")
                if len(printable) > 100:
                    return printable.strip()
            except Exception as e:
                errors.append(f"text fallback: {str(e)}")
    except Exception as e:
        errors.append(f"text fallback: {str(e)}")

    # If we got here, all methods failed
    if errors:
        raise ValueError(f"Could not extract text from PDF. Errors: {'; '.join(errors)}")

    return text


@router.post("/match", response_model=MatchResponse)
@limiter.limit("5/minute")
def match_resume(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    max_results: int = 200,
    min_score: float = 0.5,
) -> MatchResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Accept PDF and common document types
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are accepted")

    file_content = file.file.read()

    # Validate file size (max 10MB)
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Validate PDF header if it's supposed to be a PDF
    if filename_lower.endswith(".pdf"):
        if not file_content.startswith(b"%PDF"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file. The file does not have a valid PDF header. "
                "Please ensure you're uploading a real PDF file, not a renamed document.",
            )

    # Handle text files directly
    if filename_lower.endswith(".txt"):
        try:
            resume_text = file_content.decode("utf-8", errors="ignore").strip()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to read text file: {exc}")
    else:
        # Try to extract from PDF
        try:
            resume_text = extract_text_from_pdf(io.BytesIO(file_content))
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse PDF. {str(exc)}. "
                "Please ensure the PDF is not corrupted and is a valid PDF file.",
            )

    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume text is empty")

    try:
        embedder = EmbeddingService()
        resume_embedding = embedder.embed(resume_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {str(exc)}")

    max_results = max(1, min(max_results, 500))
    min_score = max(0.0, min(min_score, 1.0))

    # Cosine similarity using pgvector
    stmt = (
        select(
            Job.id,
            Job.title,
            Job.company,
            Job.location,
            (1 - Job.description_embedding.cosine_distance(resume_embedding)).label("score"),
        )
        .where(Job.is_active == True)  # noqa: E712
        .where(Job.description_embedding.isnot(None))
        .order_by((1 - Job.description_embedding.cosine_distance(resume_embedding)).desc())
        .limit(max_results)
    )

    results = db.execute(stmt).all()
    filtered_results = [row for row in results if row.score is not None and row.score >= min_score]

    matches = [
        MatchResult(
            job_id=row.id,
            score=float(row.score),
            match_percentage=round(float(row.score) * 100, 1),
            title=row.title,
            company=row.company,
            location=row.location,
        )
        for row in filtered_results
    ]

    return MatchResponse(matches=matches, total=len(matches))
