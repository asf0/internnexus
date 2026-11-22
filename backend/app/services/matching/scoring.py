"""Hybrid match scoring.

The final score blends a semantic (vector) score with three cheap signals derived
from the resume text. Weights are sourced from settings and fall back to the same
defaults when unset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from app.infra.config import get_settings

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#\.\-]{1,}")
_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "that",
    "this",
    "from",
    "you",
    "your",
    "are",
    "was",
    "were",
    "have",
    "has",
    "will",
    "our",
    "not",
    "all",
    "any",
}


def match_weights() -> tuple[float, float, float, float]:
    """Return (semantic, skill_title, work_mode, recency) weights from settings."""
    settings = get_settings()
    return (
        settings.match_weight_semantic,
        settings.match_weight_skill_title,
        settings.match_weight_work_mode,
        settings.match_weight_recency,
    )


@dataclass
class ResumeSignals:
    tokens: set[str]
    prefers_remote: bool
    prefers_hybrid: bool
    prefers_onsite: bool


def clamp_01(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, float(value)))


def tokenize(text: str, limit: int = 300) -> set[str]:
    if not text:
        return set()
    tokens = {
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if token and token.lower() not in _STOPWORDS and len(token) > 2
    }
    if len(tokens) <= limit:
        return tokens
    return set(sorted(tokens)[:limit])


def extract_resume_signals(resume_text: str) -> ResumeSignals:
    lowered = resume_text.lower()
    return ResumeSignals(
        tokens=tokenize(resume_text, limit=500),
        prefers_remote="remote" in lowered,
        prefers_hybrid="hybrid" in lowered,
        prefers_onsite=("on-site" in lowered or "onsite" in lowered or "on site" in lowered),
    )


def overlap_ratio(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, min(len(a), len(b)))


def skill_title_score(
    resume_tokens: set[str],
    title: str,
    description_text: str | None,
) -> float:
    title_tokens = tokenize(title, limit=60)
    description_tokens = tokenize(description_text or "", limit=300)
    title_overlap = overlap_ratio(resume_tokens, title_tokens)
    description_overlap = overlap_ratio(resume_tokens, description_tokens)
    return clamp_01(0.65 * title_overlap + 0.35 * description_overlap)


def work_mode_score(work_mode: str | None, signals: ResumeSignals) -> float:
    raw_mode = work_mode
    mode = str(raw_mode or "").strip().lower()
    explicit_preference = signals.prefers_remote or signals.prefers_hybrid or signals.prefers_onsite
    if not explicit_preference:
        return 0.5
    if not mode:
        return 0.5
    if signals.prefers_remote:
        if mode == "remote":
            return 1.0
        if mode == "hybrid":
            return 0.7
        return 0.2
    if signals.prefers_hybrid:
        if mode == "hybrid":
            return 1.0
        if mode == "remote":
            return 0.7
        return 0.4
    if signals.prefers_onsite:
        if mode in {"on-site", "onsite", "on site"}:
            return 1.0
        if mode == "hybrid":
            return 0.7
        return 0.3
    return 0.5


def recency_score(posted_at: datetime | None) -> float:
    if posted_at is None:
        return 0.4
    now = datetime.now(timezone.utc)
    posted_utc = posted_at if posted_at.tzinfo is not None else posted_at.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - posted_utc).total_seconds() / 86400.0)
    # Linear decay to 0 at 120 days.
    return clamp_01(1.0 - (age_days / 120.0))


def hybrid_match_score(
    *,
    semantic_score: float,
    skill_title_score: float,
    work_mode_score: float,
    recency_score: float,
) -> float:
    weight_semantic, weight_skill_title, weight_work_mode, weight_recency = match_weights()
    return clamp_01(
        (weight_semantic * clamp_01(semantic_score))
        + (weight_skill_title * clamp_01(skill_title_score))
        + (weight_work_mode * clamp_01(work_mode_score))
        + (weight_recency * clamp_01(recency_score))
    )


def explain_match(
    *,
    semantic_score: float,
    skill_title_score: float,
    work_mode_score: float,
    recency_score: float,
    final_score: float,
) -> dict[str, float]:
    return {
        "semantic": round(clamp_01(semantic_score), 4),
        "skill_title": round(clamp_01(skill_title_score), 4),
        "work_mode": round(clamp_01(work_mode_score), 4),
        "recency": round(clamp_01(recency_score), 4),
        "final": round(clamp_01(final_score), 4),
    }
