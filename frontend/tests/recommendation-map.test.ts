import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { getRecommendationRouteGeometry } from "../src/lib/recommendation-api.ts";
import {
  initialRecommendationId,
  isLatestRouteRequest,
  isValidMapCoordinate,
  recommendationMapDestinations,
  recommendationMapHomes,
  RecommendationRouteCache,
  routeCacheKey,
} from "../src/lib/recommendation-map.ts";
import type {
  RankedRecommendationCandidate,
  RecommendationRouteGeometryResponse,
} from "../src/types/recommendation.ts";
import type { ImportantDestinationPreference } from "../src/types/tenant-preference.ts";


function candidate(id: string, rank: number): RankedRecommendationCandidate {
  return {
    id,
    rank,
    title: `Home ${id}`,
    description: null,
    asking_rent_bdt: 28_000,
    property_type: "apartment",
    bedrooms: 3,
    bathrooms: 2,
    area_sqft: 1_250,
    furnishing_status: "semi_furnished",
    amenities: ["Lift"],
    broad_area: "Dhanmondi",
    model_micro_area: "Road 8A",
    address: "Dhaka",
    latitude: 23.7465,
    longitude: 90.376,
    available_from: null,
    rent_assessment: null,
    primary_image: null,
    images: [],
    commutes: [{
      destination_id: "du",
      destination: "University of Dhaka",
      destination_preference: 5,
      distance_km: 4,
      estimated_duration_minutes: 6.7,
      max_commute_minutes: 30,
      within_max_commute: true,
      normalized_destination_score: 0.9,
    }],
    destination_access_score: 0.9,
    property_similarity_score: 0.8,
    budget_score: 0.7,
    space_score: 0.9,
    amenities_score: 1,
    rent_fairness_score: 0.8,
    final_suitability_score: 0.75,
    recommendation_reasons: [],
  };
}

function destinations(): ImportantDestinationPreference[] {
  return [{
    id: "du",
    destination: "University of Dhaka",
    latitude: 23.7338,
    longitude: 90.3929,
    preference: 5,
    max_commute_minutes: 30,
  }];
}

function route(listingId = "home-1"): RecommendationRouteGeometryResponse {
  return {
    run_id: "run-1",
    listing_id: listingId,
    provider: "osrm",
    travel_mode: "driving",
    routes: [{
      destination_id: "du",
      destination: "University of Dhaka",
      geometry: {
        type: "LineString",
        coordinates: [[90.376, 23.7465], [90.3929, 23.7338]],
      },
    }],
    unavailable_destination_ids: [],
  };
}

test("home markers use recommendation coordinates and rank labels", () => {
  const homes = recommendationMapHomes([candidate("home-1", 1)]);
  assert.deepEqual(
    { id: homes[0].id, rank: homes[0].rank, lat: homes[0].latitude, lon: homes[0].longitude },
    { id: "home-1", rank: 1, lat: 23.7465, lon: 90.376 },
  );
});

test("destination markers retain label importance and commute maximum", () => {
  const marker = recommendationMapDestinations(destinations())[0];
  assert.equal(marker.label, "University of Dhaka");
  assert.equal(marker.importance, 5);
  assert.equal(marker.maxCommuteMinutes, 30);
});

test("rank one is selected initially even when array order differs", () => {
  assert.equal(
    initialRecommendationId([candidate("two", 2), candidate("one", 1)]),
    "one",
  );
});

test("first backend item is fallback when rank one is absent", () => {
  assert.equal(initialRecommendationId([candidate("three", 3)]), "three");
});

test("missing or invalid listing coordinates are skipped without crashing", () => {
  const missing = candidate("missing", 1);
  missing.latitude = null;
  const invalid = candidate("invalid", 2);
  invalid.longitude = 181;
  assert.deepEqual(recommendationMapHomes([missing, invalid]), []);
  assert.equal(isValidMapCoordinate(23.7, 90.4), true);
  assert.equal(isValidMapCoordinate(Number.NaN, 90.4), false);
});

test("missing destination coordinates do not remove valid destinations", () => {
  const values = destinations();
  values.push({ ...values[0], id: "missing", latitude: null });
  assert.deepEqual(
    recommendationMapDestinations(values).map((item) => item.id),
    ["du"],
  );
});

test("map conversion preserves authoritative rank and suitability", () => {
  const listing = candidate("stable", 4);
  const mapped = recommendationMapHomes([listing])[0].candidate;
  assert.equal(mapped.rank, 4);
  assert.equal(mapped.final_suitability_score, 0.75);
});

test("map conversion preserves stored commute metrics", () => {
  const mapped = recommendationMapHomes([candidate("stable", 1)])[0].candidate;
  assert.equal(mapped.commutes[0].estimated_duration_minutes, 6.7);
  assert.equal(mapped.commutes[0].distance_km, 4);
});

test("geometry response has no power to replace commute metrics", () => {
  const listing = candidate("stable", 1);
  const before = structuredClone(listing.commutes);
  route();
  assert.deepEqual(listing.commutes, before);
});

test("route cache reuses a selected run and listing response", () => {
  const cache = new RecommendationRouteCache();
  const response = route();
  cache.set(response);
  assert.equal(cache.get("run-1", "home-1"), response);
});

test("route cache isolates different selected listings", () => {
  const cache = new RecommendationRouteCache();
  cache.set(route("home-1"));
  assert.equal(cache.get("run-1", "home-2"), undefined);
  assert.notEqual(routeCacheKey("run-1", "home-1"), routeCacheKey("run-1", "home-2"));
});

test("stale route responses cannot become the latest selection", () => {
  assert.equal(isLatestRouteRequest(1, 3), false);
  assert.equal(isLatestRouteRequest(3, 3), true);
});

test("partial route geometry remains renderable", () => {
  const response = route();
  response.unavailable_destination_ids = ["hospital"];
  assert.equal(response.routes.length, 1);
  assert.deepEqual(response.unavailable_destination_ids, ["hospital"]);
});

test("route API is an authenticated GET scoped by run and listing", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const fetcher: typeof fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return new Response(JSON.stringify(route("listing id")), { status: 200 });
  };
  await getRecommendationRouteGeometry("run id", "listing id", {
    token: "tenant-token",
    fetcher,
  });
  assert.match(capturedUrl, /history\/run%20id\/listings\/listing%20id\/route-geometry$/);
  assert.equal(capturedInit?.method, undefined);
  assert.equal(
    (capturedInit?.headers as Record<string, string>).Authorization,
    "Bearer tenant-token",
  );
  assert.doesNotMatch(capturedUrl, /ranked/);
});

test("route API failures remain separate from recommendation empty state", async () => {
  const fetcher: typeof fetch = async () =>
    new Response(JSON.stringify({ detail: "Route unavailable" }), { status: 503 });
  await assert.rejects(
    getRecommendationRouteGeometry("run", "listing", {
      token: "token",
      fetcher,
    }),
    (error: unknown) => error instanceof Error && error.message === "Route unavailable",
  );
});

test("map is dynamically imported with server rendering disabled", () => {
  const source = readFileSync(
    new URL("../src/components/tenant/RecommendationMapPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /dynamic\(\(\) => import\("\.\/RecommendationMap"\)/);
  assert.match(source, /ssr: false/);
});

test("card and marker selection share listing ID state", () => {
  const explorer = readFileSync(
    new URL("../src/components/tenant/RecommendationExplorer.tsx", import.meta.url),
    "utf8",
  );
  assert.match(explorer, /setSelectedId\(listingId\)/);
  assert.match(explorer, /onSelectHome={selectFromMap}/);
  assert.match(explorer, /onSelect=\{\(\) => selectFromCard\(candidate\.id\)\}/);
  assert.match(explorer, /scrollIntoView/);
});

test("only selected listing identity drives route requests", () => {
  const panel = readFileSync(
    new URL("../src/components/tenant/RecommendationMapPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.match(panel, /getRecommendationRouteGeometry\(runId, selectedHomeId/);
  assert.doesNotMatch(
    panel,
    /homes\.map\([\s\S]*getRecommendationRouteGeometry/,
  );
});

test("historical map uses snapshot results and run ID without ranked POST", () => {
  const historical = readFileSync(
    new URL("../src/components/tenant/HistoricalRecommendationResults.tsx", import.meta.url),
    "utf8",
  );
  assert.match(historical, /candidates=\{historicalCandidates\(detail\)\}/);
  assert.match(historical, /runId=\{detail\.run_id\}/);
  assert.doesNotMatch(historical, /getRankedRecommendations/);
});

test("historical cards remain rendered through the shared explorer", () => {
  const explorer = readFileSync(
    new URL("../src/components/tenant/RecommendationExplorer.tsx", import.meta.url),
    "utf8",
  );
  assert.match(explorer, /<RecommendationCard/);
  assert.match(explorer, /detailsHref=\{historical \? null : undefined\}/);
});

test("map retains required OpenStreetMap attribution", () => {
  const source = readFileSync(
    new URL("../src/components/tenant/RecommendationMap.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /OpenStreetMap contributors/);
  assert.doesNotMatch(source, /Mapbox|Google Maps/);
});

test("legacy snapshots without home coordinates show map-unavailable text", () => {
  const panel = readFileSync(
    new URL("../src/components/tenant/RecommendationMapPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.match(panel, /Map location unavailable for this historical result/);
});

test("selected panel labels stored estimates as traffic-free estimates", () => {
  const panel = readFileSync(
    new URL("../src/components/tenant/RecommendationMapPanel.tsx", import.meta.url),
    "utf8",
  );
  assert.match(panel, /Estimated drive:/);
  assert.match(panel, /Road distance:/);
  assert.doesNotMatch(panel, /Live commute|Current traffic|Real-time/);
});

test("marker interaction sends the snapshot listing ID back to explorer", () => {
  const map = readFileSync(
    new URL("../src/components/tenant/RecommendationMap.tsx", import.meta.url),
    "utf8",
  );
  assert.match(map, /click: \(\) => onSelectHome\(home\.id\)/);
  assert.doesNotMatch(map, /onSelectHome\(candidate\.title/);
});
