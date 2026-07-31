from app.ml.predictor import predict_monthly_rent


def main() -> None:
    primary_result = predict_monthly_rent(
        broad_area="Mirpur",
        model_micro_area="Section 12",
        area_sqft=1000,
        bedrooms=3,
        bathrooms=2,
    )

    broad_fallback_result = predict_monthly_rent(
        broad_area="Mirpur",
        model_micro_area="UNSEEN_MICRO_AREA",
        area_sqft=1000,
        bedrooms=3,
        bathrooms=2,
    )

    dhaka_fallback_result = predict_monthly_rent(
        broad_area="UNSEEN_BROAD_AREA",
        model_micro_area="UNSEEN_MICRO_AREA",
        area_sqft=1000,
        bedrooms=3,
        bathrooms=2,
    )

    print("Primary route:")
    print(primary_result)

    print("\nBroad-area fallback:")
    print(broad_fallback_result)

    print("\nDhaka-wide fallback:")
    print(dhaka_fallback_result)

    assert primary_result["model_route"] == "primary"
    assert (
        broad_fallback_result["model_route"]
        == "broad_area_fallback"
    )
    assert (
        dhaka_fallback_result["model_route"]
        == "dhaka_wide_fallback"
    )

    print("\nAll production model routing tests passed.")


if __name__ == "__main__":
    main()