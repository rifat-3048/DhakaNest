"""Validation schemas for landlord listings and admin review actions."""

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ListingStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    RENTED = "rented"


class FairnessStatus(str, Enum):
    SIGNIFICANTLY_BELOW = "significantly_below_estimated_range"
    BELOW = "below_estimated_range"
    FAIR = "fairly_priced"
    ABOVE = "above_estimated_range"
    SIGNIFICANTLY_ABOVE = "significantly_above_estimated_range"


class ListingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=5, max_length=150)
    description: str = Field(..., min_length=10, max_length=3000)
    property_type: Literal["apartment", "house", "sublet", "room"] = "apartment"
    furnishing_status: Literal[
        "unfurnished", "semi_furnished", "furnished"
    ] = "unfurnished"
    broad_area: str = Field(..., min_length=1, max_length=100, examples=["Mirpur"])
    model_micro_area: str = Field(
        ..., min_length=1, max_length=150, examples=["Section 12"]
    )
    address: str = Field(..., min_length=5, max_length=500)
    area_sqft: float = Field(..., gt=0, le=20_000)
    bedrooms: int = Field(..., gt=0, le=20)
    bathrooms: int = Field(..., gt=0, le=20)
    asking_rent_bdt: float = Field(..., gt=0, le=10_000_000)
    amenities: list[str] = Field(default_factory=list, max_length=30)
    available_from: date | None = None

    @field_validator(
        "title", "description", "broad_area", "model_micro_area", "address"
    )
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("Text fields cannot be empty.")
        return cleaned

    @field_validator("amenities")
    @classmethod
    def clean_amenities(cls, values: list[str]) -> list[str]:
        cleaned_values = [
            " ".join(value.strip().split())
            for value in values
            if " ".join(value.strip().split())
        ]
        return list(dict.fromkeys(cleaned_values))


class ListingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=5, max_length=150)
    description: str | None = Field(default=None, min_length=10, max_length=3000)
    property_type: Literal["apartment", "house", "sublet", "room"] | None = None
    furnishing_status: Literal[
        "unfurnished", "semi_furnished", "furnished"
    ] | None = None
    broad_area: str | None = Field(default=None, min_length=1, max_length=100)
    model_micro_area: str | None = Field(default=None, min_length=1, max_length=150)
    address: str | None = Field(default=None, min_length=5, max_length=500)
    area_sqft: float | None = Field(default=None, gt=0, le=20_000)
    bedrooms: int | None = Field(default=None, gt=0, le=20)
    bathrooms: int | None = Field(default=None, gt=0, le=20)
    asking_rent_bdt: float | None = Field(default=None, gt=0, le=10_000_000)
    amenities: list[str] | None = Field(default=None, max_length=30)
    available_from: date | None = None

    @field_validator(
        "title", "description", "broad_area", "model_micro_area", "address"
    )
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("Text fields cannot be empty.")
        return cleaned

    @field_validator("amenities")
    @classmethod
    def clean_optional_amenities(
        cls, values: list[str] | None
    ) -> list[str] | None:
        if values is None:
            return None
        cleaned_values = [
            " ".join(value.strip().split())
            for value in values
            if " ".join(value.strip().split())
        ]
        return list(dict.fromkeys(cleaned_values))

    @model_validator(mode="after")
    def require_at_least_one_update(self) -> "ListingUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be updated.")
        return self


class ImageReorderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_ids: list[str] = Field(..., min_length=1, max_length=8)


class AdminDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "request_revision", "reject"]
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class RentAssessmentResponse(BaseModel):
    listing_id: str
    asking_rent_bdt: float
    predicted_rent_bdt: float
    estimated_lower_bdt: float
    estimated_upper_bdt: float
    difference_bdt: float
    difference_percent: float
    fairness_status: FairnessStatus
    model_route: Literal[
        "primary", "broad_area_fallback", "dhaka_wide_fallback"
    ]
    model_version: str
    target_strategy: Literal["log1p"]
    checked_at: datetime
    checked_by: str
