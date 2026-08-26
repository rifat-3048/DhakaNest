import assert from "node:assert/strict";
import test from "node:test";

import {
  canStartRecommendationRequest,
  validateTenantPreferences,
} from "../src/lib/tenant-preference-validation.ts";
import type { TenantSearchPreferences } from "../src/types/tenant-preference.ts";


function validPreferences(): TenantSearchPreferences {
  return {
    important_destinations: [
      {
        id: "destination-1",
        destination: "Square Hospital, Dhaka",
        latitude: 23.7524,
        longitude: 90.3817,
        preference: 5,
        max_commute_minutes: null,
      },
    ],
    minimum_rent_bdt: null,
    maximum_rent_bdt: 40_000,
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
  };
}

test("valid preferences may start recommendation navigation", () => {
  const values = validPreferences();
  assert.deepEqual(validateTenantPreferences(values), {});
  assert.equal(canStartRecommendationRequest(values, false), true);
});

test("invalid budget does not start recommendation navigation", () => {
  const values = validPreferences();
  values.maximum_rent_bdt = 0;
  assert.equal(canStartRecommendationRequest(values, false), false);
  assert.match(validateTenantPreferences(values).maximum_rent_bdt, /valid/i);
});

test("unresolved destination does not start recommendation navigation", () => {
  const values = validPreferences();
  values.important_destinations[0].longitude = null;
  assert.equal(canStartRecommendationRequest(values, false), false);
  assert.match(
    validateTenantPreferences(values).important_destinations,
    /select a real result/i,
  );
});

test("processing state blocks duplicate concurrent submission", () => {
  assert.equal(canStartRecommendationRequest(validPreferences(), true), false);
});
