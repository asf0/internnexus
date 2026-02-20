from __future__ import annotations

import io
import logging
import uuid
from typing import Annotated, BinaryIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import JobResponse, MatchResponse, MatchResult
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import Job, User
from app.rate_limiter import limiter, RATE_LIMITS
from app.services.embedding_service import EmbeddingService
from app.services.match_cache import MatchCacheService, get_match_cache_service

router = APIRouter()
logger = logging.getLogger(__name__)


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
@limiter.limit(RATE_LIMITS["match"])
async def match_resume(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    cache_service: MatchCacheService = Depends(get_match_cache_service),
    min_score: float = 0.5,
    page_size: int = 20,
) -> MatchResponse:
    # Generate unique session_id for this matching request
    session_id = str(uuid.uuid4())

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
        resume_embedding = await embedder.embed(resume_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {str(exc)}")

    # Validate parameters
    min_score = max(0.0, min(min_score, 1.0))
    page_size = max(1, min(page_size, 100))

    # Query ALL active jobs (no limit) for caching
    # Use a high limit as a safety valve (10000)
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
        .limit(10000)
    )

    result = await db.execute(stmt)
    results = result.all()
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

    total_matches = len(matches)

    # Cache the full results (handle Redis failures gracefully)
    cache_success = False
    try:
        cache_success = await cache_service.cache_matches(session_id, matches)
    except Exception as e:
        logger.warning(f"Failed to cache matches for session {session_id}: {e}")
        # Continue without caching - don't fail the request

    # Calculate pagination info
    total_pages = (total_matches + page_size - 1) // page_size if total_matches > 0 else 1

    # Return only the first page of results
    first_page_matches = matches[:page_size]

    return MatchResponse(
        matches=first_page_matches,
        total=total_matches,
        session_id=session_id if cache_success else "",
        page=1,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/match/{session_id}", response_model=MatchResponse)
@limiter.limit(RATE_LIMITS["match"])
async def get_match_page(
    request: Request,
    session_id: str,
    cache_service: MatchCacheService = Depends(get_match_cache_service),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> MatchResponse:
    """Retrieve a specific page of cached match results.

    Args:
        session_id: The match session ID from POST /match
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)

    Returns:
        MatchResponse with paginated matches

    Raises:
        HTTPException 404: If session not found or expired
        HTTPException 400: If pagination params invalid
    """
    # Retrieve paginated matches from cache
    result = await cache_service.get_paginated_matches(session_id, page, page_size)

    # If result is None (session expired/not found), raise HTTPException 404
    if result is None:
        raise HTTPException(status_code=404, detail="Match session not found or expired")

    # Unpack result: matches_data, total_count
    matches_data, total_count = result

    # Convert matches_data (list of dicts) back to MatchResult objects
    matches = [MatchResult(**match_dict) for match_dict in matches_data]

    # Calculate total_pages
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    # Return MatchResponse with all required fields
    return MatchResponse(
        matches=matches,
        total=total_count,
        session_id=session_id,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
