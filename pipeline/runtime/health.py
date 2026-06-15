from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from internnexus_core.embedding import (
    OLLAMA_PROVIDER,
    embedding_provider_label,
    normalize_embedding_provider,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.config import get_settings
from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal
from pipeline.runtime.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    name: str
    healthy: bool
    message: str
    details: dict[str, Any] | None = None


async def check_database(session: AsyncSession | None = None) -> HealthCheckResult:
    should_close = session is None
    if should_close:
        session = AsyncSessionLocal()

    try:
        result = await session.execute(text("SELECT 1"))
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
            await session.close()


async def check_embedding_service() -> HealthCheckResult:
    settings = get_settings()
    provider = normalize_embedding_provider(settings.embedding_provider)

    if provider == OLLAMA_PROVIDER:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.openai_base_url}/api/tags")
                if resp.status_code == 200:
                    return HealthCheckResult(
                        name="Embedding Service (Ollama)",
                        healthy=True,
                        message=f"Ollama server reachable at {settings.openai_base_url}",
                    )
                return HealthCheckResult(
                    name="Embedding Service (Ollama)",
                    healthy=False,
                    message=f"Ollama returned status {resp.status_code}",
                )
        except Exception as e:  # noqa: BLE001  # health check: any Ollama failure means unhealthy
            return HealthCheckResult(
                name="Embedding Service (Ollama)",
                healthy=False,
                message=f"Ollama connection failed: {e}",
            )

    return HealthCheckResult(
        name="Embedding Service",
        healthy=True,
        message=f"Using {embedding_provider_label(provider)} provider",
    )


async def check_job_apis() -> HealthCheckResult:
    settings = get_settings()
    config = get_config()
    timeout = config.health_check.timeout

    results = {}
    async with httpx.AsyncClient(timeout=float(timeout)) as client:
        try:
            resp = await client.get(f"{settings.greenhouse_api_url}/example/jobs")
            results["greenhouse"] = resp.status_code in [200, 404]
        except Exception as e:  # noqa: BLE001  # health check: any API failure means unhealthy
            results["greenhouse"] = False
            logger.debug(f"Greenhouse API check failed: {e}")

        try:
            resp = await client.get(f"{settings.lever_api_url}/bluesight?mode=json")
            results["lever"] = resp.status_code in [200, 404]
        except Exception as e:  # noqa: BLE001  # health check: any API failure means unhealthy
            results["lever"] = False
            logger.debug(f"Lever API check failed: {e}")

    all_healthy = all(results.values())
    failed = [k for k, v in results.items() if not v]

    return HealthCheckResult(
        name="Job APIs",
        healthy=all_healthy,
        message="All APIs reachable" if all_healthy else f"Failed: {', '.join(failed)}",
        details=results,
    )


async def run_health_checks(
    skip_db: bool = False,
    skip_embeddings: bool = False,
    skip_apis: bool = False,
) -> list[HealthCheckResult]:
    checks = []

    if not skip_db:
        checks.append(check_database())
    if not skip_embeddings:
        checks.append(check_embedding_service())
    if not skip_apis:
        checks.append(check_job_apis())

    return await asyncio.gather(*checks)


def print_health_report(results: list[HealthCheckResult]) -> bool:
    all_healthy = True
    for r in results:
        status = "OK" if r.healthy else "FAIL"
        logger.info(f"  [{status}] {r.name}: {r.message}")
        if not r.healthy:
            all_healthy = False

    return all_healthy
