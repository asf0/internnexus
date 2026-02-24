from typing import Callable, TypeVar

from pipeline.schemas import JobSchema

T = TypeVar("T")


def deduplicate_by_key(items: list[T], key_func: Callable[[T], str]) -> list[T]:
    seen: set[str] = set()
    result: list[T] = []
    for item in items:
        key = key_func(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def deduplicate_jobs(jobs: list[JobSchema]) -> list[JobSchema]:
    from pipeline.pipeline import fingerprint_for

    return deduplicate_by_key(jobs, fingerprint_for)
