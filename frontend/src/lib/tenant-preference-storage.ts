import type {
  ImportantDestinationPreference,
  StoredTenantPreference,
  TenantSearchPreferences,
} from "@/types/tenant-preference";
import type { PropertyType } from "../data/property-options.ts";
import {
  MUST_HAVE_AMENITY_OPTIONS,
  NICE_TO_HAVE_AMENITY_OPTIONS,
} from "../data/tenant-preference-options.ts";
import {
  isValidLatitude,
  isValidLongitude,
} from "./tenant-destination.ts";

const STORAGE_KEY = "dhakanest_tenant_search_preferences_v7";
const PREVIOUS_STORAGE_KEYS = [
  "dhakanest_tenant_search_preferences_v6",
  "dhakanest_tenant_search_preferences_v5",
  "dhakanest_tenant_search_preferences_v4",
  "dhakanest_tenant_search_preferences_v3",
  "dhakanest_tenant_search_preferences_v2",
  "dhakanest_tenant_search_preferences",
] as const;
const OBSOLETE_LOCATION_FIELDS = new Set([
  "preferred_areas",
  "preferred_micro_areas",
  "accept_nearby_areas",
]);

const PROPERTY_TYPES = new Set<PropertyType>([
  "apartment",
  "house",
  "room",
  "sublet",
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
  const travelDays = value.travel_days_per_month;

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
    travel_days_per_month:
      typeof travelDays === "number" &&
      Number.isInteger(travelDays) &&
      travelDays >= 1 &&
      travelDays <= 31
        ? travelDays
        : null,
  };
}

function normalizePropertyTypes(values: unknown[]): PropertyType[] {
  const selected = new Set(
    values.filter(
      (value): value is PropertyType =>
        typeof value === "string" && PROPERTY_TYPES.has(value as PropertyType),
    ),
  );
  if (selected.has("room") || selected.has("sublet")) {
    selected.add("room");
    selected.add("sublet");
  }
  return (["apartment", "house", "room", "sublet"] as const).filter((value) =>
    selected.has(value),
  );
}

function normalizeAmenities(
  mustHave: unknown[],
  niceToHave: unknown[],
): Pick<TenantSearchPreferences, "must_have_amenities" | "nice_to_have_amenities"> {
  const selected = [...new Set([...mustHave, ...niceToHave])];
  const selectedValues = new Set(selected);
  return {
    must_have_amenities: MUST_HAVE_AMENITY_OPTIONS
      .map((option) => option.value)
      .filter((value) => selectedValues.has(value)),
    nice_to_have_amenities: NICE_TO_HAVE_AMENITY_OPTIONS
      .map((option) => option.value)
      .filter((value) => selectedValues.has(value)),
  };
}

export function migrateStoredValue(
  value: unknown,
  sourceVersion = 5,
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
  compatiblePreferences.property_types = normalizePropertyTypes(
    rawPreferences.property_types,
  );
  if (compatiblePreferences.property_types.length === 0) return null;

  const amenities = normalizeAmenities(
    rawPreferences.must_have_amenities,
    rawPreferences.nice_to_have_amenities,
  );
  compatiblePreferences.must_have_amenities = amenities.must_have_amenities;
  compatiblePreferences.nice_to_have_amenities = amenities.nice_to_have_amenities;

  const validNumber = (candidate: unknown): candidate is number =>
    typeof candidate === "number" &&
    Number.isFinite(candidate) &&
    candidate > 0 &&
    candidate <= 20_000;
  const oldMinimum = validNumber(rawPreferences.minimum_area_sqft)
    ? rawPreferences.minimum_area_sqft
    : null;
  const oldMaximum = validNumber(rawPreferences.maximum_area_sqft)
    ? rawPreferences.maximum_area_sqft
    : null;
  const savedPreferred = validNumber(rawPreferences.preferred_area_sqft)
    ? rawPreferences.preferred_area_sqft
    : null;

  // v5's single floor-size control wrote its value as a minimum. Only that
  // exact one-sided shape is reinterpreted as a preferred target.
  compatiblePreferences.preferred_area_sqft =
    sourceVersion === 5 && oldMinimum !== null && oldMaximum === null
      ? oldMinimum
      : savedPreferred;

  if (sourceVersion >= 5) {
    compatiblePreferences.minimum_area_sqft = null;
    compatiblePreferences.maximum_area_sqft = null;
  } else {
    // Older range-based browser data keeps its original min/max meaning.
    compatiblePreferences.minimum_area_sqft = oldMinimum;
    compatiblePreferences.maximum_area_sqft = oldMaximum;
  }

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
    const versionMatch = storedKey.match(/_v(\d+)$/);
    const sourceVersion = versionMatch ? Number(versionMatch[1]) : 1;
    const storedValue = migrateStoredValue(
      JSON.parse(rawValue) as unknown,
      sourceVersion,
    );
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
