"""Typed, fail-closed configuration for the DataSense control plane."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DATASENSE_",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    public_base_url: str = "http://localhost:8080"
    allowed_hosts: str = "localhost,127.0.0.1"
    cors_origins: str = "http://localhost:3000"
    trusted_proxy_cidrs: str = ""

    database_url: str = "sqlite:///./datasense-enterprise.db"
    redis_url: str | None = None
    outbox_worker_database_url: str | None = None
    outbox_webhook_url: str | None = None
    outbox_webhook_token_file: Path | None = None
    outbox_poll_interval_seconds: float = Field(default=2.0, ge=0.1, le=60.0)
    outbox_batch_size: int = Field(default=25, ge=1, le=500)
    outbox_lease_seconds: int = Field(default=60, ge=5, le=3600)
    outbox_max_attempts: int = Field(default=8, ge=1, le=100)

    jwt_issuer: str = "http://localhost:8080"
    jwt_audience: str = "datasense-desktop"
    jwt_private_key_pem_file: Path | None = None
    jwt_public_key_pem_file: Path | None = None
    access_token_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    auth_code_ttl_seconds: int = Field(default=90, ge=30, le=300)
    saml_transaction_ttl_seconds: int = Field(default=300, ge=60, le=900)

    saml_clock_skew_seconds: int = Field(default=120, ge=0, le=300)
    saml_sp_x509_cert_pem_file: Path | None = None
    saml_sp_private_key_pem_file: Path | None = None
    saml_require_signed_assertions: bool = True
    saml_allow_idp_initiated: bool = False
    saml_encrypted_assertion_required: bool = True

    audit_hmac_key_file: Path | None = None
    log_level: str = "INFO"
    disable_docs_in_production: bool = True

    @field_validator("public_base_url", "jwt_issuer")
    @classmethod
    def require_https_outside_dev(cls, value: str, info):
        environment = info.data.get("environment", "development")
        if environment in {"staging", "production"} and not value.startswith("https://"):
            raise ValueError("HTTPS is mandatory outside development/test")
        return value.rstrip("/")

    def required_secret(self, name: str, file_path: Path | None) -> str:
        if file_path is None:
            raise RuntimeError(f"{name} must be injected through a mounted secret file")
        try:
            value = file_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"cannot read {name} secret") from exc
        if not value:
            raise RuntimeError(f"{name} secret is empty")
        return value

    def assert_worker_safe(self) -> None:
        """Validate the separate worker deployment only when its entrypoint starts."""
        if not self.outbox_worker_database_url:
            raise RuntimeError("outbox worker requires a dedicated database URL")
        if not self.outbox_webhook_url or not self.outbox_webhook_url.startswith("https://"):
            raise RuntimeError("outbox worker requires an HTTPS webhook URL")
        self.required_secret("Outbox webhook token", self.outbox_webhook_token_file)

    def assert_production_safe(self) -> None:
        if self.environment != "production":
            return
        if not self.redis_url:
            raise RuntimeError("production requires Redis for atomic TTL and replay protection")
        for name, path in (
            ("JWT private key", self.jwt_private_key_pem_file),
            ("JWT public key", self.jwt_public_key_pem_file),
            ("Audit HMAC key", self.audit_hmac_key_file),
            ("SAML SP certificate", self.saml_sp_x509_cert_pem_file),
            ("SAML SP private key", self.saml_sp_private_key_pem_file),
        ):
            self.required_secret(name, path)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.assert_production_safe()
    return settings
