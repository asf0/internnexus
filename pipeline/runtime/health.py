from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.infra.settings import get_settings
from pipeline.infra.db import AsyncSessionLocal
from pipeline.infra.pipeline_config import get_config

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    name: str
    healthy: bool
    message: str
    details: dict[str, Any] | None = None


async def check_database(session: AsyncSession | None = None) -> HealthCheckResult:
    should_close = session is None
    active_session = session if session is not None else AsyncSessionLocal()

    try:
        result = await active_session.execute(text("SELECT 1"))
        row = result.scalar()
        if row == 1:
            return HealthCheckResult(
                name="Database",
                healthy=True,
                message="Database connection successful",
            )
        return HealthCheckResult(
            name="Database",
            healthy=False,
            message="Database query returned unexpected result",
        )
    except Exception as e:  # noqa: BLE001  # health check: any DB failure means unhealthy
        return HealthCheckResult(
            name="Database",
            healthy=False,
            message=f"Database connection failed: {e}",
        )
    finally:
        if should_close:
            await active_session.close()


async def check_embedding_service() -> HealthCheckResult:
    settings = get_settings()
    base_url = settings.openai_base_url.rstrip("/")
    embeddings_url = f"{base_url}/embeddings" if base_url.endswith("/v1") else f"{base_url}/v1/embeddings"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                embeddings_url,
                json={
                    "model": settings.embedding_model,
                    "input": "health check",
                    "dimensions": settings.embedding_dimensions,
                },
            )
            response.raise_for_status()
        payload = response.json()
        items = payload.get("data") if isinstance(payload, dict) else None
        embedding = (
            items[0].get("embedding") if isinstance(items, list) and items and isinstance(items[0], dict) else None
        )
        if not isinstance(embedding, list) or len(embedding) < settings.embedding_dimensions:
            actual = len(embedding) if isinstance(embedding, list) else 0
            raise ValueError(f"expected at least {settings.embedding_dimensions} dimensions, received {actual}")
        # Matryoshka embedding models may return their full native width even
        # when the request asks for fewer dimensions. The runtime embedding
        # client truncates those vectors to the configured width, so the health
        # check must accept the same responses instead of reporting a failure.
        embedding = embedding[: settings.embedding_dimensions]
        return HealthCheckResult(
            name="Embedding Service",
            healthy=True,
            message=f"Embedding endpoint returned {len(embedding)} dimensions",
            details={"url": embeddings_url, "dimensions": len(embedding)},
        )
    except Exception as exc:  # noqa: BLE001  # any API failure means unhealthy
        return HealthCheckResult(
            name="Embedding Service",
            healthy=False,
            message=f"Embedding endpoint check failed: {exc}",
            details={"url": embeddings_url},
        )


async def check_job_apis() -> HealthCheckResult:
    settings = get_settings()
    config = get_config()
    timeout = float(config.health_check.timeout)

    endpoints: dict[str, tuple[str, dict[str, str] | None, set[int]]] = {
        "greenhouse": (f"{settings.greenhouse_api_url.rstrip('/')}/example/jobs", None, {200, 404}),
        "lever": (f"{settings.lever_api_url.rstrip('/')}/bluesight", {"mode": "json"}, {200, 404}),
        "ashby": (f"{settings.ashby_api_url.rstrip('/')}/example", None, {200, 404}),
        "simplify_intern": (settings.simplify_jobs_intern_url, None, {200}),
        "simplify_new_grad": (settings.simplify_jobs_new_grad_url, None, {200}),
    }

    details: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=timeout) as client:
        for name, (url, params, accepted) in endpoints.items():
            try:
                response = await client.get(url, params=params)
                healthy = response.status_code in accepted
                details[name] = {
                    "healthy": healthy,
                    "status_code": response.status_code,
                    "url": url,
                }
            except Exception as exc:  # noqa: BLE001  # health report preserves each service failure
                details[name] = {"healthy": False, "url": url, "error": str(exc)}
                logger.debug("%s health check failed: %s", name, exc)

    failed = [name for name, detail in details.items() if not detail["healthy"]]
    return HealthCheckResult(
        name="Job APIs",
        healthy=not failed,
        message="All APIs reachable" if not failed else f"Failed: {', '.join(failed)}",
        details=details,
    )


async def run_health_checks() -> list[HealthCheckResult]:
    return list(
        await asyncio.gather(
            check_database(),
            check_embedding_service(),
            check_job_apis(),
        )
    )


def print_health_report(results: list[HealthCheckResult]) -> bool:
    all_healthy = True
    for r in results:
        status = "OK" if r.healthy else "FAIL"
        logger.info(f"  [{status}] {r.name}: {r.message}")
        if not r.healthy:
            all_healthy = False

    return all_healthy


async def run_and_report_health() -> bool:
    """Run all checks and log the report, returning overall health."""
    return print_health_report(await run_health_checks())
