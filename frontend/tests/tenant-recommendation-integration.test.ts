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
        travel_days_per_month: 20,
      },
    ],
    minimum_rent_bdt: null,
    maximum_rent_bdt: 40_000,
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

test("every destination requires 1 to 31 travel days for a new search", () => {
  for (const value of [null, 0, 32]) {
    const values = validPreferences();
    values.important_destinations[0].travel_days_per_month = value;
    assert.match(
      validateTenantPreferences(values).important_destinations,
      /days per month/i,
    );
  }
  for (const value of [1, 31]) {
    const values = validPreferences();
    values.important_destinations[0].travel_days_per_month = value;
    assert.equal(validateTenantPreferences(values).important_destinations, undefined);
  }
});

test("preferred floor size must be positive and within listing limits", () => {
  const values = validPreferences();
  values.preferred_area_sqft = 0;
  assert.match(
    validateTenantPreferences(values).preferred_area_sqft,
    /floor size/i,
  );
  values.preferred_area_sqft = 20_001;
  assert.match(
    validateTenantPreferences(values).preferred_area_sqft,
    /20,000/i,
  );
});

test("amenities must stay in their tenant-facing groups", () => {
  const values = validPreferences();
  values.must_have_amenities = ["CCTV"];
  assert.match(validateTenantPreferences(values).amenities, /correct groups/i);
});
