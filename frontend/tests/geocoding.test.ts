import assert from "node:assert/strict";
import test from "node:test";

import { normalizeGeocodingResponse } from "../src/lib/geocoding.ts";

test("provider results normalize to the internal destination shape", () => {
  const results = normalizeGeocodingResponse([
    {
      place_id: 123,
      osm_id: 456,
      osm_type: "relation",
      display_name: "University of Dhaka, Shahbagh, Dhaka, Bangladesh",
      lat: "23.7338",
      lon: "90.3929",
    },
  ]);

  assert.deepEqual(results, [
    {
      id: "relation-456",
      label: "University of Dhaka, Shahbagh, Dhaka, Bangladesh",
      latitude: 23.7338,
      longitude: 90.3929,
    },
  ]);
});

test("malformed provider results are ignored", () => {
  const results = normalizeGeocodingResponse([
    { display_name: "Missing coordinates" },
    { display_name: "Invalid latitude", lat: "91", lon: "90.4" },
    null,
  ]);

  assert.deepEqual(results, []);
});
