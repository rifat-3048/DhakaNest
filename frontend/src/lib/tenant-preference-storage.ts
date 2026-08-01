import { DHAKA_LOCATION_OPTIONS } from "@/data/location-options";
import type {
  StoredTenantPreference,
  TenantSearchPreferences,
} from "@/types/tenant-preference";

const STORAGE_KEY = "dhakanest_tenant_search_preferences_v2";
const LEGACY_STORAGE_KEY = "dhakanest_tenant_search_preferences";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function sanitizeStoredValue(value: unknown): StoredTenantPreference | null {
  if (!isRecord(value) || !isRecord(value.preferences)) return null;

  const rawPreferences = value.preferences;
  if (
    !Array.isArray(rawPreferences.important_destinations) ||
    !isRecord(rawPreferences.priorities)
  ) {
    return null;
  }

  const microAreasByBroadArea = new Map<string, ReadonlySet<string>>(
    DHAKA_LOCATION_OPTIONS.map((option) => [
      option.broadArea,
      new Set<string>(option.microAreas),
    ]),
  );
  const rawBroadAreas = Array.isArray(rawPreferences.preferred_areas)
    ? rawPreferences.preferred_areas
    : [];
  const preferredAreas = Array.from(
    new Set(
      rawBroadAreas.filter(
        (area): area is string =>
          typeof area === "string" && microAreasByBroadArea.has(area),
      ),
    ),
  ).slice(0, 3);
  const selectedBroadAreas = new Set(preferredAreas);
  const rawMicroAreas = Array.isArray(rawPreferences.preferred_micro_areas)
    ? rawPreferences.preferred_micro_areas
    : [];
  const preferredMicroAreas = rawMicroAreas.filter((location) => {
    if (!isRecord(location)) return false;
    const broadArea = location.broad_area;
    const microArea = location.micro_area;
    return (
      typeof broadArea === "string" &&
      typeof microArea === "string" &&
      selectedBroadAreas.has(broadArea) &&
      Boolean(microAreasByBroadArea.get(broadArea)?.has(microArea))
    );
  }) as TenantSearchPreferences["preferred_micro_areas"];

  return {
    preferences: {
      ...(rawPreferences as unknown as TenantSearchPreferences),
      preferred_areas: preferredAreas,
      preferred_micro_areas: preferredMicroAreas,
    },
    saved_at:
      typeof value.saved_at === "string"
        ? value.saved_at
        : new Date().toISOString(),
  };
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
  sessionStorage.removeItem(LEGACY_STORAGE_KEY);
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(storedValue));
  return storedValue;
}

export function getSavedTenantPreferences(): StoredTenantPreference | null {
  if (typeof window === "undefined") return null;
  const rawValue = sessionStorage.getItem(STORAGE_KEY);
  if (!rawValue) return null;

  try {
    const storedValue = sanitizeStoredValue(JSON.parse(rawValue) as unknown);
    if (!storedValue) sessionStorage.removeItem(STORAGE_KEY);
    return storedValue;
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function clearTenantPreferences(): void {
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem(LEGACY_STORAGE_KEY);
  }
}
