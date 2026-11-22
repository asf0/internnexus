from __future__ import annotations

from enum import Enum

from app.schemas.admin import AdminJobResponse, AdminUserResponse
from app.schemas.jobs import JobResponse, JobSummaryResponse
from app.schemas.matching import MatchResult
from app.models import Job, User
from app.services.jobs.sanitize import sanitize_description

_JOB_SOURCE_MISSING = "Job source is missing"


def enum_to_str(value: Enum | str | None) -> str | None:
    if value is None:
        return None
    return value.value if isinstance(value, Enum) else value


def _job_common_fields(job: Job, source: str) -> dict:
    """Job fields shared by the response, summary, and admin projections."""
    return {
        "id": job.id,
        "source": source,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "city": job.city,
        "state": job.state,
        "country": job.country,
        "apply_url": job.apply_url,
        "job_category": job.job_category,
        "job_type": enum_to_str(job.job_type),
        "work_mode": enum_to_str(job.work_mode),
        "posted_at": job.posted_at,
        "is_active": job.is_active,
    }


def _job_source_or_raise(job: Job) -> str:
    source = enum_to_str(job.source)
    if source is None:
        raise ValueError(_JOB_SOURCE_MISSING)
    return source


def job_to_response(
    job: Job, *, description_html: str | None = None, description_truncated: bool | None = None
) -> JobResponse:
    if description_html is None or description_truncated is None:
        description_html, description_truncated = sanitize_description(job.description_text)

    return JobResponse(
        **_job_common_fields(job, _job_source_or_raise(job)),
        description_html=description_html,
        description_truncated=description_truncated,
    )


def job_to_summary(job: Job) -> JobSummaryResponse:
    return JobSummaryResponse(**_job_common_fields(job, _job_source_or_raise(job)))


def job_to_match_result(
    job: Job,
    *,
    score: float,
    score_breakdown: dict[str, float] | None,
) -> MatchResult:
    description_html, description_truncated = sanitize_description(job.description_text)
    return MatchResult(
        job_id=job.id,
        score=float(score),
        match_percentage=round(float(score) * 100, 1),
        title=job.title,
        company=job.company,
        location=job.location,
        apply_url=job.apply_url,
        description_html=description_html,
        description_truncated=description_truncated,
        city=job.city,
        state=job.state,
        country=job.country,
        job_category=job.job_category,
        job_type=enum_to_str(job.job_type),
        work_mode=enum_to_str(job.work_mode),
        posted_at=job.posted_at,
        score_breakdown=score_breakdown,
    )


def job_to_admin_response(job: Job, *, click_count: int = 0) -> AdminJobResponse:
    description_html, description_truncated = sanitize_description(job.description_text)
    return AdminJobResponse(
        **_job_common_fields(job, _job_source_or_raise(job)),
        description_html=description_html,
        description_truncated=description_truncated,
        click_count=click_count,
        created_at=job.last_seen,
    )


def user_to_admin_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=not user.is_deleted,
        created_at=user.created_at,
        has_password=user.hashed_password is not None,
        admin_role=enum_to_str(user.admin.role) if user.admin else None,
        provider=user.accounts[0].provider if user.accounts else None,
        notes=user.notes,
    )
