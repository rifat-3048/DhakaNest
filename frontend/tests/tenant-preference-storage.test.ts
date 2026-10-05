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
      preferred_area_sqft: null,
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
  } as {
    saved_at: string;
    preferences: Record<string, unknown> & {
      property_types: string[];
      must_have_amenities: string[];
      nice_to_have_amenities: string[];
      preferred_area_sqft: number | null;
      minimum_area_sqft: number | null;
      maximum_area_sqft: number | null;
    };
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
  assert.equal(destination?.travel_days_per_month, null);
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

test("old room or sublet selections hydrate as the merged tenant option", () => {
  for (const propertyTypes of [["room"], ["sublet"], ["room", "sublet"]]) {
    const stored = storedPreference({
      id: "destination-1",
      destination: "University of Dhaka",
      latitude: 23.7338,
      longitude: 90.3929,
      preference: 5,
      max_commute_minutes: null,
    });
    stored.preferences.property_types = propertyTypes;

    const restored = migrateStoredValue(stored);
    assert.deepEqual(restored?.preferences.property_types, ["room", "sublet"]);
  }
});

test("old amenities move into their new non-overlapping groups", () => {
  const stored = storedPreference({
    id: "destination-1",
    destination: "University of Dhaka",
    latitude: 23.7338,
    longitude: 90.3929,
    preference: 5,
    max_commute_minutes: null,
  });
  stored.preferences.must_have_amenities = ["Lift", "CCTV", "Unknown"];
  stored.preferences.nice_to_have_amenities = ["Parking", "Balcony", "Lift"];

  const restored = migrateStoredValue(stored);
  assert.deepEqual(restored?.preferences.must_have_amenities, ["Lift", "Parking"]);
  assert.deepEqual(restored?.preferences.nice_to_have_amenities, ["Balcony", "CCTV"]);
});

test("v5 single floor size migrates to the v6 preferred target", () => {
  const stored = storedPreference({
    id: "destination-1",
    destination: "University of Dhaka",
    latitude: 23.7338,
    longitude: 90.3929,
    preference: 5,
    max_commute_minutes: null,
  });
  stored.preferences.minimum_area_sqft = 900;
  stored.preferences.maximum_area_sqft = null;

  const restored = migrateStoredValue(stored);
  assert.equal(restored?.preferences.preferred_area_sqft, 900);
  assert.equal(restored?.preferences.minimum_area_sqft, null);
  assert.equal(restored?.preferences.maximum_area_sqft, null);
});

test("older range storage keeps its original min and max semantics", () => {
  const stored = storedPreference({
    id: "destination-1",
    destination: "University of Dhaka",
    latitude: 23.7338,
    longitude: 90.3929,
    preference: 5,
    max_commute_minutes: null,
  });
  stored.preferences.minimum_area_sqft = 900;
  stored.preferences.maximum_area_sqft = 1500;

  const restored = migrateStoredValue(stored, 4);
  assert.equal(restored?.preferences.preferred_area_sqft, null);
  assert.equal(restored?.preferences.minimum_area_sqft, 900);
  assert.equal(restored?.preferences.maximum_area_sqft, 1500);
});

test("v6 preferred floor size persists without legacy bounds", () => {
  const stored = storedPreference({
    id: "destination-1",
    destination: "University of Dhaka",
    latitude: 23.7338,
    longitude: 90.3929,
    preference: 5,
    max_commute_minutes: null,
  });
  stored.preferences.preferred_area_sqft = 1200;

  const restored = migrateStoredValue(stored, 6);
  assert.equal(restored?.preferences.preferred_area_sqft, 1200);
  assert.equal(restored?.preferences.minimum_area_sqft, null);
  assert.equal(restored?.preferences.maximum_area_sqft, null);
  assert.equal(
    restored?.preferences.important_destinations[0].travel_days_per_month,
    null,
  );
});

test("v7 travel frequency persists while v6 migration invents no value", () => {
  const oldStored = storedPreference({
    id: "destination-1",
    destination: "University of Dhaka",
    latitude: 23.7338,
    longitude: 90.3929,
    preference: 5,
    max_commute_minutes: null,
  });
  assert.equal(
    migrateStoredValue(oldStored, 6)?.preferences.important_destinations[0]
      .travel_days_per_month,
    null,
  );

  const currentStored = storedPreference({
    id: "destination-1",
    destination: "University of Dhaka",
    latitude: 23.7338,
    longitude: 90.3929,
    preference: 5,
    max_commute_minutes: null,
    travel_days_per_month: 20,
  });
  assert.equal(
    migrateStoredValue(currentStored, 7)?.preferences.important_destinations[0]
      .travel_days_per_month,
    20,
  );
});
