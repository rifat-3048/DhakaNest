import assert from "node:assert/strict";
import test from "node:test";

import {
  historicalCandidates,
  historyBudgetSummary,
  historyRunsInBackendOrder,
  historyState,
} from "../src/lib/recommendation-history-display.ts";
import type {
  RankedRecommendationCandidate,
  RecommendationHistoryListResponse,
  RecommendationRunDetail,
  RecommendationRunSummary,
} from "../src/types/recommendation.ts";


function run(id: string, createdAt: string): RecommendationRunSummary {
  return {
    run_id: id,
    created_at: createdAt,
    destination_labels: ["University of Dhaka", "Square Hospital"],
    minimum_rent_bdt: 20_000,
    maximum_rent_bdt: 40_000,
    recommendation_count: 2,
    top_recommendation: {
      listing_id: "listing-one",
      title: "Family Apartment",
      final_suitability_score: 0.754,
      primary_image: null,
    },
  };
}

function history(runs: RecommendationRunSummary[]): RecommendationHistoryListResponse {
  return {
    page: 1,
    page_size: 10,
    total: runs.length,
    total_pages: runs.length ? 1 : 0,
    runs,
  };
}

function candidate(id: string, rank: number): RankedRecommendationCandidate {
  return {
    id,
    rank,
    title: `Listing ${id}`,
    description: null,
    asking_rent_bdt: 25_000,
    property_type: "apartment",
    bedrooms: 2,
    bathrooms: 2,
    area_sqft: 1_000,
    furnishing_status: "semi_furnished",
    amenities: ["Lift"],
    broad_area: "Dhanmondi",
    model_micro_area: "Dhanmondi",
    address: "Dhaka",
    latitude: 23.7,
    longitude: 90.4,
    available_from: null,
    rent_assessment: null,
    primary_image: null,
    images: [],
    commutes: [{
      destination_id: "du",
      destination: "University of Dhaka",
      destination_preference: 5,
      distance_km: 4,
      estimated_duration_minutes: 9,
      max_commute_minutes: 30,
      within_max_commute: true,
      normalized_destination_score: 1,
    }],
    destination_access_score: 1,
    property_similarity_score: 0.8,
    budget_score: 0.7,
    space_score: 0.8,
    amenities_score: 1,
    rent_fairness_score: 0.9,
    final_suitability_score: 0.85,
    recommendation_reasons: [{
      code: "location",
      category: "location",
      text: "Estimated drive to University of Dhaka.",
      strength: "strong",
    }],
  };
}

test("history list preserves backend newest-first order", () => {
  const runs = [
    run("new", "2026-08-28T20:00:00Z"),
    run("old", "2026-08-27T20:00:00Z"),
  ];
  assert.deepEqual(
    historyRunsInBackendOrder(history(runs)).map((item) => item.run_id),
    ["new", "old"],
  );
});

test("history exposes destination labels and recommendation count", () => {
  const item = run("one", "2026-08-28T20:00:00Z");
  assert.deepEqual(item.destination_labels, ["University of Dhaka", "Square Hospital"]);
  assert.equal(item.recommendation_count, 2);
});

test("budget summary handles range and ceiling searches", () => {
  const ranged = run("range", "2026-08-28T20:00:00Z");
  assert.match(historyBudgetSummary(ranged), /20,000.*40,000/);
  assert.match(
    historyBudgetSummary({ ...ranged, minimum_rent_bdt: null }),
    /Up to.*40,000/,
  );
});

test("top match retains title and suitability snapshot", () => {
  const top = run("one", "2026-08-28T20:00:00Z").top_recommendation;
  assert.equal(top?.title, "Family Apartment");
  assert.equal(top?.final_suitability_score, 0.754);
});

test("empty, loading, error, and results states stay distinct", () => {
  assert.equal(historyState(null, false), "loading");
  assert.equal(historyState(null, true), "error");
  assert.equal(historyState(history([]), false), "empty");
  assert.equal(historyState(history([run("one", "2026-08-28T20:00:00Z")]), false), "results");
});

test("historical cards retain stored rank order and snapshot fields", () => {
  const results = [candidate("first", 1), candidate("second", 2)];
  const detail = {
    results,
  } as RecommendationRunDetail;
  const restored = historicalCandidates(detail);
  assert.deepEqual(restored.map((item) => item.id), ["first", "second"]);
  assert.equal(restored[0].final_suitability_score, 0.85);
  assert.equal(restored[0].recommendation_reasons[0].category, "location");
  assert.equal(restored[0].commutes[0].max_commute_minutes, 30);
  assert.equal(restored[0].primary_image, null);
});
