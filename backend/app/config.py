from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB connection string, for example: mongodb://localhost:27017
    mongo_uri: str

    # Name of the MongoDB database used by DhakaNest.
    database_name: str

    # Secret key used to sign JWT access tokens. Keep the real value in .env.
    jwt_secret_key: str

    # JWT signing algorithm. HS256 is a common default for this project.
    jwt_algorithm: str = "HS256"

    # How long a login token stays valid, in minutes.
    access_token_expire_minutes: int = 1440

    # Cloudinary account credentials used for property image storage.
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    # Validation limits for images attached to one rental listing.
    listing_image_max_count: int = 8
    listing_image_max_size_mb: int = 5

    # OSRM's public endpoint is suitable only for light local development use.
    routing_provider: Literal["osrm"] = "osrm"
    routing_base_url: str = "https://router.project-osrm.org"
    routing_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    routing_user_agent: str = "DhakaNest-University-Development/0.1"
    routing_fallback_provider: Literal["osrm"] | None = None
    routing_fallback_base_url: str | None = None
    routing_max_retries: int = Field(default=1, ge=0, le=5)
    routing_retry_backoff_seconds: float = Field(default=0.15, ge=0, le=5)
    routing_matrix_cache_ttl_seconds: int = Field(default=900, ge=1, le=86_400)
    routing_geometry_cache_ttl_seconds: int = Field(default=3_600, ge=1, le=86_400)
    routing_cache_max_entries: int = Field(default=1_000, ge=1, le=100_000)
    routing_cache_coordinate_precision: int = Field(default=6, ge=4, le=7)
    routing_circuit_failure_threshold: int = Field(default=3, ge=1, le=100)
    routing_circuit_open_seconds: float = Field(default=30.0, gt=0, le=3_600)
    routing_health_cache_ttl_seconds: int = Field(default=30, ge=1, le=300)
    recommendation_rate_limit_per_minute: int = Field(default=12, ge=1, le=1_000)
    route_geometry_rate_limit_per_minute: int = Field(default=30, ge=1, le=1_000)

    # Number of content-similar properties retained for later WSM scoring.
    recommendation_knn_k: int = Field(default=10, ge=1)

    @field_validator("routing_fallback_provider", mode="before")
    @classmethod
    def empty_fallback_provider_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("routing_fallback_base_url", mode="before")
    @classmethod
    def empty_fallback_url_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("routing_base_url", "routing_fallback_base_url")
    @classmethod
    def validate_routing_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Routing base URLs must use http or https.")
        if parsed.username or parsed.password:
            raise ValueError("Routing base URLs must not contain credentials.")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_fallback_configuration(self) -> "Settings":
        if self.routing_fallback_provider and not self.routing_fallback_base_url:
            raise ValueError(
                "ROUTING_FALLBACK_BASE_URL is required when a fallback provider is configured."
            )
        if self.routing_fallback_base_url and not self.routing_fallback_provider:
            raise ValueError(
                "ROUTING_FALLBACK_PROVIDER is required when a fallback URL is configured."
            )
        return self

    # This tells pydantic-settings to also read values from a .env file.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Import this single settings object wherever configuration is needed.
settings = Settings()
