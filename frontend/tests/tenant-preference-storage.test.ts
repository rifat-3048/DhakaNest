import assert from "node:assert/strict";
import test from "node:test";

import { migrateStoredValue } from "../src/lib/tenant-preference-storage.ts";

function storedPreference(destination: Record<string, unknown>) {
  return {
    saved_at: "2026-08-26T00:00:00.000Z",
    preferences: {
      important_destinations: [destination],
      minimum_rent_bdt: null,
      maximum_rent_bdt: 30000,
      over_budget_percent: 0,
      property_types: ["apartment"],
      minimum_bedrooms: 2,
      minimum_bathrooms: 1,
      minimum_area_sqft: null,
      maximum_area_sqft: null,
      furnishing_statuses: [],
      desired_move_in_date: null,
      household_size: null,
      must_have_amenities: [],
      nice_to_have_amenities: [],
      priorities: {
        location: 5,
        budget: 5,
        space: 3,
        amenities: 3,
        rent_fairness: 4,
      },
    },
  };
}

test("coordinates serialize and restore correctly", () => {
  const original = storedPreference({
    id: "destination-1",
    destination: "University of Dhaka, Shahbagh, Dhaka, Bangladesh",
    latitude: 23.7338,
    longitude: 90.3929,
    preference: 5,
    max_commute_minutes: 30,
  });
  const restored = migrateStoredValue(
    JSON.parse(JSON.stringify(original)) as unknown,
  );
  const destination = restored?.preferences.important_destinations[0];

  assert.equal(destination?.latitude, 23.7338);
  assert.equal(destination?.longitude, 90.3929);
});

test("old text-only destinations migrate with null coordinates", () => {
  const restored = migrateStoredValue(
    storedPreference({
      id: "destination-1",
      destination: "University of Dhaka",
      preference: 5,
      max_commute_minutes: 30,
    }),
  );
  const destination = restored?.preferences.important_destinations[0];

  assert.equal(destination?.destination, "University of Dhaka");
  assert.equal(destination?.preference, 5);
  assert.equal(destination?.max_commute_minutes, 30);
  assert.equal(destination?.latitude, null);
  assert.equal(destination?.longitude, null);
});
