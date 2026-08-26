import assert from "node:assert/strict";
import test from "node:test";

import {
  FURNISHING_OPTIONS,
  PROPERTY_AMENITIES,
  PROPERTY_TYPE_OPTIONS,
} from "../src/data/property-options.ts";
import {
  MINIMUM_ROOM_OPTIONS,
  RECOMMENDATION_PRIORITY_OPTIONS,
} from "../src/data/tenant-preference-options.ts";

test("bedroom and bathroom selectors use the exact shared room thresholds", () => {
  assert.deepEqual(
    MINIMUM_ROOM_OPTIONS.map(({ label, value }) => [label, value]),
    [
      ["1", 1],
      ["2", 2],
      ["3", 3],
      ["4", 4],
      ["5", 5],
      ["5+", 6],
    ],
  );
});

test("tenant property and furnishing options match listing canonical values", () => {
  assert.deepEqual(
    PROPERTY_TYPE_OPTIONS.map((option) => option.value),
    ["apartment", "house", "sublet", "room"],
  );
  assert.deepEqual(
    FURNISHING_OPTIONS.map((option) => option.value),
    ["unfurnished", "semi_furnished", "furnished"],
  );
});

test("tenant amenity choices are the canonical listing values", () => {
  assert.deepEqual(
    PROPERTY_AMENITIES.map((option) => option.value),
    [
      "Lift",
      "Generator",
      "Parking",
      "Balcony",
      "Security Guard",
      "CCTV",
      "Gas Connection",
      "Air Conditioning",
      "Backup Water Supply",
      "Rooftop Access",
    ],
  );
});

test("ranking priorities contain only future scoring criteria", () => {
  const priorityKeys = RECOMMENDATION_PRIORITY_OPTIONS.map((option) => option.key);
  assert.deepEqual(priorityKeys, [
    "location",
    "budget",
    "space",
    "amenities",
    "rent_fairness",
  ]);
  assert.equal(priorityKeys.includes("household_size" as never), false);
  assert.equal(priorityKeys.includes("residential_area" as never), false);
});
