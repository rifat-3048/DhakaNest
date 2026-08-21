import type {
  StoredTenantPreference,
  TenantSearchPreferences,
} from "@/types/tenant-preference";

const STORAGE_KEY = "dhakanest_tenant_search_preferences_v3";
const PREVIOUS_STORAGE_KEYS = [
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

function migrateStoredValue(value: unknown): StoredTenantPreference | null {
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

  // Copy compatible fields only, silently dropping the old area preferences.
  const compatiblePreferences = Object.fromEntries(
    Object.entries(rawPreferences).filter(
      ([fieldName]) => !OBSOLETE_LOCATION_FIELDS.has(fieldName),
    ),
  ) as unknown as TenantSearchPreferences;

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
