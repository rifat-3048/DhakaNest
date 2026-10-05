import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  FURNISHING_OPTIONS,
  PROPERTY_AMENITIES,
  PROPERTY_TYPE_OPTIONS,
} from "../src/data/property-options.ts";
import {
  MINIMUM_ROOM_OPTIONS,
  MUST_HAVE_AMENITY_OPTIONS,
  NICE_TO_HAVE_AMENITY_OPTIONS,
  RECOMMENDATION_PRIORITY_OPTIONS,
  TENANT_PROPERTY_TYPE_OPTIONS,
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

test("shared listing property and furnishing options remain canonical", () => {
  assert.deepEqual(
    PROPERTY_TYPE_OPTIONS.map((option) => option.value),
    ["apartment", "house", "sublet", "room"],
  );
  assert.deepEqual(
    FURNISHING_OPTIONS.map((option) => option.value),
    ["unfurnished", "semi_furnished", "furnished"],
  );
});

test("tenant property choices map the merged room and sublet option", () => {
  assert.deepEqual(
    TENANT_PROPERTY_TYPE_OPTIONS.map((option) => ({
      label: option.label,
      propertyTypes: [...option.propertyTypes],
    })),
    [
      { label: "Apartment", propertyTypes: ["apartment"] },
      { label: "House", propertyTypes: ["house"] },
      { label: "Room / Sublet", propertyTypes: ["room", "sublet"] },
    ],
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

test("must-have and nice-to-have amenities are distinct canonical groups", () => {
  const mustHave = MUST_HAVE_AMENITY_OPTIONS.map((option) => option.value);
  const niceToHave = NICE_TO_HAVE_AMENITY_OPTIONS.map((option) => option.value);

  assert.deepEqual(mustHave, [
    "Lift",
    "Generator",
    "Security Guard",
    "Gas Connection",
    "Backup Water Supply",
    "Parking",
  ]);
  assert.deepEqual(niceToHave, [
    "Balcony",
    "CCTV",
    "Air Conditioning",
    "Rooftop Access",
  ]);
  assert.deepEqual(mustHave.filter((amenity) => niceToHave.includes(amenity as never)), []);
  assert.deepEqual(
    [...mustHave, ...niceToHave].sort(),
    PROPERTY_AMENITIES.map((option) => option.value).sort(),
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

test("active tenant UI presents one preferred floor-size target", () => {
  const formSource = readFileSync(
    new URL("../src/components/tenant/TenantPreferenceForm.tsx", import.meta.url),
    "utf8",
  );
  const summarySource = readFileSync(
    new URL("../src/components/tenant/PreferenceSummary.tsx", import.meta.url),
    "utf8",
  );

  assert.match(formSource, /label="Preferred floor size"/);
  assert.match(formSource, /Nearby sizes can still be recommended\./);
  assert.doesNotMatch(formSource, /label="Minimum floor/);
  assert.doesNotMatch(formSource, /label="Maximum floor/);
  assert.match(summarySource, /label="Preferred floor size"/);
});

test("destination editor and preference summary expose travel frequency clearly", () => {
  const editorSource = readFileSync(
    new URL("../src/components/tenant/ImportantDestinationsEditor.tsx", import.meta.url),
    "utf8",
  );
  const summarySource = readFileSync(
    new URL("../src/components/tenant/PreferenceSummary.tsx", import.meta.url),
    "utf8",
  );
  assert.match(editorSource, /How many days per month do you travel here\?/);
  assert.match(editorSource, /Used to estimate your monthly travel cost\./);
  assert.match(summarySource, /Travel frequency:/);
  assert.match(summarySource, /days\/month/);
});
