import assert from "node:assert/strict";
import test from "node:test";

import {
  applyDestinationSelection,
  canAddDestination,
  createImportantDestination,
  updateDestinationSearchText,
  validateImportantDestinations,
} from "../src/lib/tenant-destination.ts";
import type { ImportantDestinationPreference } from "../src/types/tenant-preference.ts";

function validDestination(): ImportantDestinationPreference {
  return {
    ...createImportantDestination("destination-1"),
    destination: "University of Dhaka, Shahbagh, Dhaka, Bangladesh",
    latitude: 23.7338,
    longitude: 90.3929,
    preference: 5,
    max_commute_minutes: 30,
  };
}

test("a selected destination with valid coordinates passes validation", () => {
  assert.equal(validateImportantDestinations([validDestination()]), null);
});

test("typed text without coordinates fails validation", () => {
  const destination = validDestination();
  destination.latitude = null;
  destination.longitude = null;

  assert.match(
    validateImportantDestinations([destination]) ?? "",
    /select a real result/i,
  );
});

test("invalid latitude fails validation", () => {
  const destination = validDestination();
  destination.latitude = 91;
  assert.notEqual(validateImportantDestinations([destination]), null);
});

test("invalid longitude fails validation", () => {
  const destination = validDestination();
  destination.longitude = 181;
  assert.notEqual(validateImportantDestinations([destination]), null);
});

test("missing importance fails validation", () => {
  const destination = validDestination();
  destination.preference = null;
  assert.match(
    validateImportantDestinations([destination]) ?? "",
    /importance/i,
  );
});

test("optional commute may be null", () => {
  const destination = validDestination();
  destination.max_commute_minutes = null;
  assert.equal(validateImportantDestinations([destination]), null);
});

test("zero and negative commute values fail validation", () => {
  const zeroCommute = validDestination();
  zeroCommute.max_commute_minutes = 0;
  const negativeCommute = validDestination();
  negativeCommute.max_commute_minutes = -10;

  assert.match(validateImportantDestinations([zeroCommute]) ?? "", /commute/i);
  assert.match(
    validateImportantDestinations([negativeCommute]) ?? "",
    /commute/i,
  );
});

test("selecting a result stores its label and coordinates", () => {
  const selected = applyDestinationSelection(
    createImportantDestination("destination-1"),
    {
      label: "Square Hospital, Panthapath, Dhaka, Bangladesh",
      latitude: 23.7524,
      longitude: 90.3817,
    },
  );

  assert.equal(
    selected.destination,
    "Square Hospital, Panthapath, Dhaka, Bangladesh",
  );
  assert.equal(selected.latitude, 23.7524);
  assert.equal(selected.longitude, 90.3817);
});

test("editing selected text clears stale coordinates", () => {
  const edited = updateDestinationSearchText(
    validDestination(),
    "University of Dhaka edited",
  );

  assert.equal(edited.latitude, null);
  assert.equal(edited.longitude, null);
});

test("the editor allows no more than three destinations", () => {
  assert.equal(canAddDestination(2), true);
  assert.equal(canAddDestination(3), false);
});

test("at least one fully resolved destination is required", () => {
  assert.notEqual(validateImportantDestinations([]), null);
  assert.notEqual(
    validateImportantDestinations([createImportantDestination("empty")]),
    null,
  );
});
