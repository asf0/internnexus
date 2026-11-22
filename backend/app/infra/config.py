from __future__ import annotations

from cryptography.fernet import Fernet
from pydantic import Field, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from internnexus_core.config import PostgresSettingsMixin, make_settings_loader

from app.infra.paths import ENV_FILE


class Settings(PostgresSettingsMixin):
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_statement_cache_size: int | None = None

    # Embedding configuration
    embedding_model: str
    embedding_dimensions: int = 1024
    openai_base_url: str
    embedding_timeout_seconds: float = 180.0

    # Auth/JWT configuration
    auth_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    app_name: str = "InternNexus API"

    # A provider is enabled only when its complete client ID/secret pair exists.
    gh_client_id: str = ""
    gh_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Redis configuration (optional; in-memory TTL cache is used when empty)
    redis_url: str = ""

    # Proxy trust for rate limiting and IP tracking behind tunnels/load balancers
    trust_proxy_headers: bool = False
    trusted_proxy_ips: str = ""

    # Resume encryption (Fernet key, base64-encoded)
    # When set, new resumes are encrypted with this key while legacy blobs
    # encrypted with the AUTH_SECRET-derived key remain decryptable.
    resume_encryption_key: str = ""

    # Dedicated HMAC key for pseudonymizing client IPs in click analytics.
    # Falls back to auth_secret when unset so that rotating the JWT signing
    # secret does not break correlation of historical IP hashes.
    ip_hash_secret: str = ""

    # Private frontend endpoint used after public job-detail writes commit.
    frontend_internal_url: str = ""
    job_cache_revalidation_secret: str = ""

    # Disabled by default. Exposes process-local cache benchmark counters only
    # to an authenticated loopback endpoint.
    benchmark_counters_enabled: bool = False
    benchmark_counters_secret: str = ""

    # Hybrid match scoring weights. The four weights are combined per candidate
    # in hybrid_match_score and must sum to ~1.0 (validated below).
    # Semantic (resume<->job embedding cosine) dominates; the rest are tie-breakers:
    # skill/title keyword overlap, work-mode preference fit, and posting recency.
    match_weight_semantic: float = Field(default=0.70, ge=0.0, le=1.0, allow_inf_nan=False)
    match_weight_skill_title: float = Field(default=0.15, ge=0.0, le=1.0, allow_inf_nan=False)
    match_weight_work_mode: float = Field(default=0.08, ge=0.0, le=1.0, allow_inf_nan=False)
    match_weight_recency: float = Field(default=0.07, ge=0.0, le=1.0, allow_inf_nan=False)
    # Number of nearest-neighbour candidates pulled for re-ranking, and the
    # fallback result count used when no candidate clears the score threshold.
    match_rerank_pool: int = Field(default=1000, ge=1)
    match_fallback_count: int = Field(default=20, ge=1)

    # Retention window for the mcp_invocations analytics table. Rows older than
    # this are removed by the `app.prune_analytics` maintenance command.
    mcp_invocation_retention_days: int = 90

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("embedding_dimensions")
    @classmethod
    def validate_embedding_dimensions(cls, value: int) -> int:
        if value != 1024:
            raise ValueError(
                "EMBEDDING_DIMENSIONS must equal 1024 (the column dimension). "
                f"Got {value}. To use a different dimension, create a migration "
                "to ALTER the vector columns first."
            )
        return value

    @field_validator("db_pool_size")
    @classmethod
    def validate_pool_size(cls, value: int) -> int:
        if not 1 <= value <= 50:
            raise ValueError("db_pool_size must be between 1 and 50")
        return value

    @field_validator("db_max_overflow")
    @classmethod
    def validate_pool_overflow(cls, value: int) -> int:
        if not 0 <= value <= 50:
            raise ValueError("db_max_overflow must be between 0 and 50")
        return value

    @field_validator("jwt_expiration_hours")
    @classmethod
    def validate_jwt_expiration(cls, value: int) -> int:
        if value < 1:
            raise ValueError("jwt_expiration_hours must be at least 1")
        return value

    @field_validator("auth_secret")
    @classmethod
    def validate_auth_secret_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("auth_secret must be at least 32 characters for security")
        return v

    @field_validator("resume_encryption_key")
    @classmethod
    def validate_resume_encryption_key(cls, v: str) -> str:
        if not v:
            return v
        try:
            Fernet(v.encode())
        except Exception as exc:
            raise ValueError(
                "RESUME_ENCRYPTION_KEY must be a valid Fernet key "
                "(base64-encoded 32-byte key). Generate with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            ) from exc
        return v

    @property
    def resolved_ip_hash_secret(self) -> str:
        """HMAC key for IP pseudonymization; falls back to auth_secret when unset."""
        return self.ip_hash_secret or self.auth_secret

    @model_validator(mode="after")
    def validate_match_weights_sum(self) -> "Settings":
        total = (
            self.match_weight_semantic
            + self.match_weight_skill_title
            + self.match_weight_work_mode
            + self.match_weight_recency
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                "Match scoring weights (MATCH_WEIGHT_SEMANTIC, MATCH_WEIGHT_SKILL_TITLE, "
                f"MATCH_WEIGHT_WORK_MODE, MATCH_WEIGHT_RECENCY) must sum to 1.0; got {total}"
            )
        return self

    @model_validator(mode="after")
    def validate_oauth_provider_pairs(self) -> "Settings":
        providers = (
            ("GitHub", self.gh_client_id, self.gh_client_secret),
            ("Google", self.google_client_id, self.google_client_secret),
        )
        incomplete = [
            name
            for name, client_id, client_secret in providers
            if bool(client_id.strip()) != bool(client_secret.strip())
        ]
        if incomplete:
            names = ", ".join(incomplete)
            raise ValueError(
                f"OAuth providers require complete client ID/secret pairs: {names}"
            )
        return self


get_settings = make_settings_loader(Settings)
