import type {
  ImportantDestinationPreference,
  StoredTenantPreference,
  TenantSearchPreferences,
} from "@/types/tenant-preference";
import {
  isValidLatitude,
  isValidLongitude,
} from "./tenant-destination.ts";

const STORAGE_KEY = "dhakanest_tenant_search_preferences_v4";
const PREVIOUS_STORAGE_KEYS = [
  "dhakanest_tenant_search_preferences_v3",
  "dhakanest_tenant_search_preferences_v2",
  "dhakanest_tenant_search_preferences",
] as const;
const OBSOLETE_LOCATION_FIELDS = new Set([
  "preferred_areas",
  "preferred_micro_areas",
  "accept_nearby_areas",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function migrateDestination(
  value: unknown,
  index: number,
): ImportantDestinationPreference | null {
  if (!isRecord(value)) return null;

  const latitude =
    typeof value.latitude === "number" ? value.latitude : null;
  const longitude =
    typeof value.longitude === "number" ? value.longitude : null;
  const coordinatesAreValid =
    isValidLatitude(latitude) && isValidLongitude(longitude);
  const preference = value.preference;
  const commute = value.max_commute_minutes;

  return {
    id:
      typeof value.id === "string" && value.id
        ? value.id
        : `destination-${index + 1}`,
    destination:
      typeof value.destination === "string" ? value.destination : "",
    latitude: coordinatesAreValid ? latitude : null,
    longitude: coordinatesAreValid ? longitude : null,
    preference:
      typeof preference === "number" &&
      Number.isInteger(preference) &&
      preference >= 1 &&
      preference <= 5
        ? (preference as ImportantDestinationPreference["preference"])
        : null,
    max_commute_minutes:
      typeof commute === "number" && Number.isFinite(commute) ? commute : null,
  };
}

export function migrateStoredValue(
  value: unknown,
): StoredTenantPreference | null {
  if (!isRecord(value) || !isRecord(value.preferences)) return null;

  const rawPreferences = value.preferences;
  if (
    !Array.isArray(rawPreferences.important_destinations) ||
    !Array.isArray(rawPreferences.property_types) ||
    !Array.isArray(rawPreferences.furnishing_statuses) ||
    !Array.isArray(rawPreferences.must_have_amenities) ||
    !Array.isArray(rawPreferences.nice_to_have_amenities) ||
    !isRecord(rawPreferences.priorities)
  ) {
    return null;
  }

  const importantDestinations = rawPreferences.important_destinations
    .map(migrateDestination)
    .filter(
      (destination): destination is ImportantDestinationPreference =>
        destination !== null,
    );
  if (importantDestinations.length === 0) return null;

  // Copy compatible fields, drop obsolete area choices, and normalize destinations.
  const compatiblePreferences = Object.fromEntries(
    Object.entries(rawPreferences).filter(
      ([fieldName]) => !OBSOLETE_LOCATION_FIELDS.has(fieldName),
    ),
  ) as unknown as TenantSearchPreferences;
  compatiblePreferences.important_destinations = importantDestinations;

  return {
    preferences: compatiblePreferences,
    saved_at:
      typeof value.saved_at === "string"
        ? value.saved_at
        : new Date().toISOString(),
  };
}

function removePreviousStorage(): void {
  for (const key of PREVIOUS_STORAGE_KEYS) {
    sessionStorage.removeItem(key);
  }
}

export function saveTenantPreferences(
  preferences: TenantSearchPreferences,
): StoredTenantPreference {
  if (typeof window === "undefined") {
    throw new Error("Tenant preferences can only be saved in the browser.");
  }

  const storedValue: StoredTenantPreference = {
    preferences,
    saved_at: new Date().toISOString(),
  };
  removePreviousStorage();
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(storedValue));
  return storedValue;
}

export function getSavedTenantPreferences(): StoredTenantPreference | null {
  if (typeof window === "undefined") return null;

  const storedKey = [STORAGE_KEY, ...PREVIOUS_STORAGE_KEYS].find((key) =>
    sessionStorage.getItem(key),
  );
  if (!storedKey) return null;

  const rawValue = sessionStorage.getItem(storedKey);
  if (!rawValue) return null;

  try {
    const storedValue = migrateStoredValue(JSON.parse(rawValue) as unknown);
    if (!storedValue) {
      sessionStorage.removeItem(storedKey);
      return null;
    }

    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(storedValue));
    removePreviousStorage();
    return storedValue;
  } catch {
    sessionStorage.removeItem(storedKey);
    return null;
  }
}

export function clearTenantPreferences(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(STORAGE_KEY);
  removePreviousStorage();
}
