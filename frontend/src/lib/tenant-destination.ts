import type {
  ImportantDestinationPreference,
  PreferenceScore,
} from "@/types/tenant-preference";

export const MIN_DESTINATIONS = 1;
export const MAX_DESTINATIONS = 3;
export const MAX_COMMUTE_MINUTES = 240;
export const MAX_TRAVEL_DAYS_PER_MONTH = 31;

export interface SelectedDestination {
  label: string;
  latitude: number;
  longitude: number;
}

export function createImportantDestination(
  id: string,
): ImportantDestinationPreference {
  return {
    id,
    destination: "",
    latitude: null,
    longitude: null,
    preference: null,
    max_commute_minutes: null,
    travel_days_per_month: null,
  };
}

export function applyDestinationSelection(
  destination: ImportantDestinationPreference,
  selected: SelectedDestination,
): ImportantDestinationPreference {
  return {
    ...destination,
    destination: selected.label,
    latitude: selected.latitude,
    longitude: selected.longitude,
  };
}

export function updateDestinationSearchText(
  destination: ImportantDestinationPreference,
  destinationText: string,
): ImportantDestinationPreference {
  return {
    ...destination,
    destination: destinationText,
    // Edited text is unresolved until the tenant selects another real result.
    latitude: null,
    longitude: null,
  };
}

export function isValidLatitude(value: number | null): value is number {
  return value !== null && Number.isFinite(value) && value >= -90 && value <= 90;
}

export function isValidLongitude(value: number | null): value is number {
  return (
    value !== null && Number.isFinite(value) && value >= -180 && value <= 180
  );
}

export function hasResolvedCoordinates(
  destination: ImportantDestinationPreference,
): boolean {
  return (
    isValidLatitude(destination.latitude) &&
    isValidLongitude(destination.longitude)
  );
}

export function isValidPreferenceScore(
  value: PreferenceScore | null,
): value is PreferenceScore {
  return value !== null && Number.isInteger(value) && value >= 1 && value <= 5;
}

export function isValidOptionalCommute(value: number | null): boolean {
  return (
    value === null ||
    (Number.isFinite(value) &&
      Number.isInteger(value) &&
      value > 0 &&
      value <= MAX_COMMUTE_MINUTES)
  );
}

export function isValidTravelFrequency(value: number | null): boolean {
  return (
    value !== null &&
    Number.isFinite(value) &&
    Number.isInteger(value) &&
    value >= 1 &&
    value <= MAX_TRAVEL_DAYS_PER_MONTH
  );
}

export function canAddDestination(destinationCount: number): boolean {
  return destinationCount < MAX_DESTINATIONS;
}

export function validateImportantDestinations(
  destinations: ImportantDestinationPreference[],
): string | null {
  if (
    destinations.length < MIN_DESTINATIONS ||
    destinations.length > MAX_DESTINATIONS
  ) {
    return "Add between one and three important destinations.";
  }

  if (
    destinations.some(
      (destination) =>
        !destination.destination.trim() || !hasResolvedCoordinates(destination),
    )
  ) {
    return "Search for and select a real result for every destination.";
  }

  if (
    destinations.some(
      (destination) => !isValidPreferenceScore(destination.preference),
    )
  ) {
    return "Select an importance score from 1 to 5 for every destination.";
  }

  if (
    destinations.some(
      (destination) =>
        !isValidOptionalCommute(destination.max_commute_minutes),
    )
  ) {
    return `Optional commute time must be between 1 and ${MAX_COMMUTE_MINUTES} whole minutes.`;
  }

  if (
    destinations.some(
      (destination) => !isValidTravelFrequency(destination.travel_days_per_month),
    )
  ) {
    return "Enter how many days per month you travel to this destination.";
  }

  const normalizedNames = destinations.map((destination) =>
    destination.destination.trim().toLowerCase(),
  );
  if (new Set(normalizedNames).size !== normalizedNames.length) {
    return "Do not add the same destination more than once.";
  }

  return null;
}
