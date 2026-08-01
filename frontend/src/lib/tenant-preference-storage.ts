import type {
  StoredTenantPreference,
  TenantSearchPreferences,
} from "@/types/tenant-preference";

const STORAGE_KEY = "dhakanest_tenant_search_preferences_v2";
const LEGACY_STORAGE_KEY = "dhakanest_tenant_search_preferences";

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
    return JSON.parse(rawValue) as StoredTenantPreference;
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
