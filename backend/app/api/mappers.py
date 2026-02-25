from __future__ import annotations

from enum import Enum

from app.api.admin_schemas import AdminJobResponse, AdminUserResponse
from app.api.schemas import JobResponse, MatchResult
from app.models import Job, User


def enum_to_str(value: Enum | str | None) -> str | None:
    if value is None:
        return None
    return value.value if isinstance(value, Enum) else value


def job_to_response(job: Job) -> JobResponse:
    source = enum_to_str(job.source)
    if source is None:
        raise ValueError("Job source is missing")

    return JobResponse(
        id=job.id,
        source=source,
        title=job.title,
        company=job.company,
        location=job.location,
        city=job.city,
        state=job.state,
        country=job.country,
        apply_url=job.apply_url,
        description_text=job.description_text,
        job_category=job.job_category,
        job_type=enum_to_str(job.job_type),
        work_mode=enum_to_str(job.work_mode),
        posted_at=job.posted_at,
        is_active=job.is_active,
    )


def job_to_match_result(
    job: Job,
    *,
    score: float,
    score_breakdown: dict[str, float] | None,
) -> MatchResult:
    return MatchResult(
        job_id=job.id,
        score=float(score),
        match_percentage=round(float(score) * 100, 1),
        title=job.title,
        company=job.company,
        location=job.location,
        apply_url=job.apply_url,
        description_text=job.description_text,
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
    source = enum_to_str(job.source)
    if source is None:
        raise ValueError("Job source is missing")

    return AdminJobResponse(
        id=job.id,
        source=source,
        title=job.title,
        company=job.company,
        location=job.location,
        city=job.city,
        state=job.state,
        country=job.country,
        apply_url=job.apply_url,
        description_text=job.description_text,
        job_category=job.job_category,
        job_type=enum_to_str(job.job_type),
        work_mode=enum_to_str(job.work_mode),
        posted_at=job.posted_at,
        is_active=job.is_active,
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
    )
