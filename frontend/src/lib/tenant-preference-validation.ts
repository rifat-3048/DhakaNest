import { validateImportantDestinations } from "./tenant-destination.ts";
import type { TenantSearchPreferences } from "../types/tenant-preference.ts";
import type { PropertyAmenity } from "../data/property-options.ts";
import {
  MUST_HAVE_AMENITY_OPTIONS,
  NICE_TO_HAVE_AMENITY_OPTIONS,
} from "../data/tenant-preference-options.ts";

const MUST_HAVE_AMENITIES = new Set<PropertyAmenity>(
  MUST_HAVE_AMENITY_OPTIONS.map((option) => option.value),
);
const NICE_TO_HAVE_AMENITIES = new Set<PropertyAmenity>(
  NICE_TO_HAVE_AMENITY_OPTIONS.map((option) => option.value),
);


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
    values.preferred_area_sqft !== null &&
    (!Number.isFinite(values.preferred_area_sqft) ||
      values.preferred_area_sqft <= 0 ||
      values.preferred_area_sqft > 20_000)
  ) {
    errors.preferred_area_sqft =
      "Enter a preferred floor size between 1 and 20,000 sq ft.";
  }
  if (
    values.must_have_amenities.some((amenity) => !MUST_HAVE_AMENITIES.has(amenity)) ||
    values.nice_to_have_amenities.some(
      (amenity) => !NICE_TO_HAVE_AMENITIES.has(amenity),
    )
  ) {
    errors.amenities = "Select amenities from their correct groups.";
  }
  return errors;
}

export function canStartRecommendationRequest(
  values: TenantSearchPreferences,
  isProcessing: boolean,
): boolean {
  return !isProcessing && Object.keys(validateTenantPreferences(values)).length === 0;
}
