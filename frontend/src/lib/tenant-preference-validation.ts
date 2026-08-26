import { validateImportantDestinations } from "./tenant-destination.ts";
import type { TenantSearchPreferences } from "../types/tenant-preference.ts";


export function validateTenantPreferences(
  values: TenantSearchPreferences,
): Record<string, string> {
  const errors: Record<string, string> = {};
  const destinationError = validateImportantDestinations(
    values.important_destinations,
  );
  if (destinationError) errors.important_destinations = destinationError;
  if (!Number.isFinite(values.maximum_rent_bdt) || values.maximum_rent_bdt <= 0) {
    errors.maximum_rent_bdt = "Enter a valid maximum monthly rent.";
  }
  if (
    values.minimum_rent_bdt !== null &&
    values.minimum_rent_bdt > values.maximum_rent_bdt
  ) {
    errors.minimum_rent_bdt = "Minimum rent cannot exceed maximum rent.";
  }
  if (values.property_types.length === 0) {
    errors.property_types = "Select at least one property type.";
  }
  if (values.minimum_bedrooms < 1) {
    errors.minimum_bedrooms = "Select at least one bedroom.";
  }
  if (values.minimum_bathrooms < 1) {
    errors.minimum_bathrooms = "Select at least one bathroom.";
  }
  if (
    values.minimum_area_sqft !== null &&
    values.maximum_area_sqft !== null &&
    values.minimum_area_sqft > values.maximum_area_sqft
  ) {
    errors.minimum_area_sqft = "Minimum area cannot exceed maximum area.";
  }
  if (
    values.must_have_amenities.some((amenity) =>
      values.nice_to_have_amenities.includes(amenity),
    )
  ) {
    errors.amenities = "An amenity cannot be both must-have and nice-to-have.";
  }
  return errors;
}

export function canStartRecommendationRequest(
  values: TenantSearchPreferences,
  isProcessing: boolean,
): boolean {
  return !isProcessing && Object.keys(validateTenantPreferences(values)).length === 0;
}
