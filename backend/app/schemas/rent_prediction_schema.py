from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RentPredictionRequest(BaseModel):
    broad_area: str = Field(
        ...,
        min_length=1,
        examples=["Mirpur"],
    )

    model_micro_area: str = Field(
        ...,
        min_length=1,
        examples=["Section 12"],
    )

    area_sqft: float = Field(
        ...,
        gt=0,
        examples=[1000],
    )

    bedrooms: float = Field(
        ...,
        gt=0,
        examples=[3],
    )

    bathrooms: float = Field(
        ...,
        gt=0,
        examples=[2],
    )

    @field_validator(
        "broad_area",
        "model_micro_area",
    )
    @classmethod
    def normalize_location_text(
        cls,
        value: str,
    ) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                "Location fields cannot be empty."
            )

        return normalized_value


class RentPredictionResponse(BaseModel):
    predicted_rent_bdt: float = Field(
        ...,
        ge=0,
    )

    model_route: Literal[
        "primary",
        "broad_area_fallback",
        "dhaka_wide_fallback",
    ]

    target_strategy: Literal["log1p"]