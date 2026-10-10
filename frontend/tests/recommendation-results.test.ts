import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  candidatesInBackendOrder,
  recommendationDetailsPath,
  recommendationContactValue,
  recommendationImage,
  recommendationResultState,
  suitabilityPercent,
} from "../src/lib/recommendation-display.ts";
import type {
  RankedRecommendationCandidate,
  RankedRecommendationResponse,
} from "../src/types/recommendation.ts";


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
    commutes: [
      {
        destination_id: "destination-1",
        destination: "University of Dhaka",
        destination_preference: 5,
        distance_km: 4,
        estimated_duration_minutes: 9.4,
        max_commute_minutes: null,
        within_max_commute: null,
        normalized_destination_score: 0.8,
      },
    ],
    destination_access_score: 0.8,
    property_similarity_score: 0.7,
    budget_score: 0.75,
    space_score: 0.9,
    amenities_score: 1,
    rent_fairness_score: 0.84,
    final_suitability_score: 0.8124,
    recommendation_reasons: [
      {
        code: "location_estimated_drive",
        category: "location",
        strength: "strong",
        text: "Estimated 9.4-minute drive to University of Dhaka.",
      },
    ],
  };
}

function response(candidates: RankedRecommendationCandidate[]): RankedRecommendationResponse {
  return {
    total_base_eligible: 12,
    total_after_hard_filters: candidates.length,
    total_routing_complete: candidates.length,
    total_after_max_commute: candidates.length,
    total_scored_candidates: candidates.length,
    total_after_knn: candidates.length,
    total_ranked: candidates.length,
    normalized_weights: {
      location: 0.2,
      budget: 0.2,
      space: 0.2,
      amenities: 0.2,
      rent_fairness: 0.2,
    },
    filter_summary: {},
    routing_summary: {},
    scoring_summary: {},
    knn_summary: {},
    wsm_summary: {
      wsm_input_candidate_count: candidates.length,
      wsm_ranked_candidate_count: candidates.length,
      weight_sum: 5,
      scoring_version: "wsm_v1",
    },
    recommendation_run_id: null,
    created_at: null,
    candidates,
  };
}

test("results preserve backend rank order without frontend sorting", () => {
  const candidates = [candidate("first", 1), candidate("second", 2)];
  assert.deepEqual(
    candidatesInBackendOrder(response(candidates)).map((item) => item.id),
    ["first", "second"],
  );
});

test("suitability formats backend score without recalculating ranking", () => {
  assert.equal(suitabilityPercent(0.8124), 81);
  assert.equal(suitabilityPercent(2), 100);
  assert.equal(suitabilityPercent(-1), 0);
});

test("cards and details display stored affordability and travel breakdown fields", () => {
  const cardSource = readFileSync(
    new URL("../src/components/tenant/RecommendationCard.tsx", import.meta.url),
    "utf8",
  );
  const detailsSource = readFileSync(
    new URL("../src/components/tenant/RecommendationDetails.tsx", import.meta.url),
    "utf8",
  );
  for (const label of [
    "Monthly rent",
    "Estimated travel cost",
    "Estimated monthly spend",
  ]) {
    assert.match(cardSource, new RegExp(label));
  }
  assert.match(detailsSource, /Estimated monthly travel/);
  assert.match(detailsSource, /km one way/);
  assert.match(detailsSource, /one round trip per travel day/);
  assert.match(detailsSource, /academic cost assumption/);
});

test("recommendation cards display landlord contacts with safe fallbacks", () => {
  const cardSource = readFileSync(
    new URL("../src/components/tenant/RecommendationCard.tsx", import.meta.url),
    "utf8",
  );
  for (const label of [
    "Owner Contact Information",
    "Owner Name",
    "Email",
    "Phone Number",
  ]) {
    assert.match(cardSource, new RegExp(label));
  }
  assert.equal(recommendationContactValue(" Mohammad Rahim "), "Mohammad Rahim");
  assert.equal(recommendationContactValue(null), "Not provided");
  assert.equal(recommendationContactValue("   "), "Not provided");
});

test("missing images return placeholder state", () => {
  assert.equal(recommendationImage(candidate("missing", 1)), null);
});

test("primary or first valid real listing image is selected", () => {
  const listing = candidate("image", 1);
  listing.images = [
    {
      image_id: "first",
      url: "https://res.cloudinary.com/pqec5b01/image/upload/example.webp",
      public_id: "example",
      width: 1200,
      height: 800,
      format: "webp",
      bytes: 1000,
      original_filename: "home.webp",
      is_primary: false,
      sort_order: 0,
      uploaded_at: "2026-08-26T00:00:00Z",
    },
  ];
  assert.equal(recommendationImage(listing)?.image_id, "first");
  listing.primary_image = { ...listing.images[0], image_id: "primary" };
  assert.equal(recommendationImage(listing)?.image_id, "primary");
});

test("zero results and provider failure remain distinct states", () => {
  assert.equal(recommendationResultState(response([]), null), "empty");
  assert.equal(
    recommendationResultState(null, "service_unavailable"),
    "service_error",
  );
  assert.equal(recommendationResultState(null, "network"), "service_error");
});

test("details link identifies the selected listing", () => {
  assert.equal(
    recommendationDetailsPath("listing id"),
    "/tenant/recommendations/listing%20id",
  );
});

test("all destination commute data remains available for rendering", () => {
  const listing = candidate("commutes", 1);
  listing.commutes.push({
    ...listing.commutes[0],
    destination_id: "destination-2",
    destination: "Square Hospital",
    max_commute_minutes: 30,
    within_max_commute: true,
  });
  assert.equal(listing.commutes.length, 2);
  assert.equal(listing.commutes[0].max_commute_minutes, null);
  assert.equal(listing.commutes[1].max_commute_minutes, 30);
});
