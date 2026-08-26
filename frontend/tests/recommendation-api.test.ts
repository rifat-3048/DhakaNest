import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRankedRecommendationRequest,
  getRecommendationHistory,
  getRecommendationHistoryDetail,
  getRankedRecommendations,
  RecommendationApiError,
} from "../src/lib/recommendation-api.ts";
import { createRecommendationSubmissionKey } from "../src/lib/recommendation-submission.ts";
import type { TenantSearchPreferences } from "../src/types/tenant-preference.ts";


function preferences(): TenantSearchPreferences {
  return {
    important_destinations: [
      {
        id: "destination-1",
        destination: " University of Dhaka ",
        latitude: 23.7338,
        longitude: 90.3929,
        preference: 5,
        max_commute_minutes: 30,
      },
    ],
    minimum_rent_bdt: null,
    maximum_rent_bdt: 30_000,
    over_budget_percent: 5,
    property_types: ["apartment"],
    minimum_bedrooms: 2,
    minimum_bathrooms: 1,
    minimum_area_sqft: null,
    maximum_area_sqft: null,
    furnishing_statuses: [],
    desired_move_in_date: null,
    household_size: 2,
    must_have_amenities: ["Lift"],
    nice_to_have_amenities: ["Parking"],
    priorities: {
      location: 5,
      budget: 4,
      space: 3,
      amenities: 2,
      rent_fairness: 1,
    },
  };
}

function responsePayload(candidates: unknown[] = []) {
  return {
    total_base_eligible: 12,
    total_after_hard_filters: candidates.length,
    total_routing_complete: candidates.length,
    total_after_max_commute: candidates.length,
    total_scored_candidates: candidates.length,
    total_after_knn: candidates.length,
    total_ranked: candidates.length,
    normalized_weights: {
      location: 0.3333,
      budget: 0.2667,
      space: 0.2,
      amenities: 0.1333,
      rent_fairness: 0.0667,
    },
    filter_summary: {},
    routing_summary: {},
    scoring_summary: {},
    knn_summary: {},
    wsm_summary: {
      wsm_input_candidate_count: candidates.length,
      wsm_ranked_candidate_count: candidates.length,
      weight_sum: 15,
      scoring_version: "wsm_v1",
    },
    candidates,
  };
}

test("ranked request serializes exact resolved tenant preference fields", () => {
  const request = buildRankedRecommendationRequest(preferences());
  assert.equal(request.important_destinations[0].destination, "University of Dhaka");
  assert.equal(request.important_destinations[0].latitude, 23.7338);
  assert.equal(request.maximum_rent_bdt, 30_000);
  assert.deepEqual(request.property_types, ["apartment"]);
  assert.deepEqual(request.priorities, preferences().priorities);
});

test("ranked API includes Bearer auth and parses a successful response", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const fetcher: typeof fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return new Response(JSON.stringify(responsePayload()), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  const result = await getRankedRecommendations(preferences(), {
    token: "tenant-token",
    fetcher,
  });
  assert.match(capturedUrl, /\/api\/recommendations\/ranked$/);
  assert.equal(
    (capturedInit?.headers as Record<string, string>).Authorization,
    "Bearer tenant-token",
  );
  assert.equal(result.total_ranked, 0);
  assert.deepEqual(result.candidates, []);
});

test("explicit ranked submission sends its idempotency header", async () => {
  let capturedHeaders: Record<string, string> = {};
  const fetcher: typeof fetch = async (_input, init) => {
    capturedHeaders = init?.headers as Record<string, string>;
    return new Response(JSON.stringify(responsePayload()), { status: 200 });
  };
  await getRankedRecommendations(preferences(), {
    token: "tenant-token",
    idempotencyKey: "submission-uuid-one",
    fetcher,
  });
  assert.equal(capturedHeaders["X-Idempotency-Key"], "submission-uuid-one");
});

test("new explicit submissions generate new keys", () => {
  const keys = ["uuid-one", "uuid-two"];
  assert.equal(createRecommendationSubmissionKey(() => keys.shift()!), "uuid-one");
  assert.equal(createRecommendationSubmissionKey(() => keys.shift()!), "uuid-two");
});

test("a retried ranked action can reuse the exact idempotency key", async () => {
  const captured: string[] = [];
  const fetcher: typeof fetch = async (_input, init) => {
    captured.push(
      (init?.headers as Record<string, string>)["X-Idempotency-Key"],
    );
    return new Response(JSON.stringify(responsePayload()), { status: 200 });
  };
  for (let attempt = 0; attempt < 2; attempt += 1) {
    await getRankedRecommendations(preferences(), {
      token: "tenant-token",
      idempotencyKey: "stable-retry-key",
      fetcher,
    });
  }
  assert.deepEqual(captured, ["stable-retry-key", "stable-retry-key"]);
});

test("history list uses Bearer authentication and pagination", async () => {
  let capturedUrl = "";
  let capturedInit: RequestInit | undefined;
  const fetcher: typeof fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedInit = init;
    return new Response(
      JSON.stringify({ page: 2, page_size: 10, total: 0, total_pages: 0, runs: [] }),
      { status: 200 },
    );
  };
  const result = await getRecommendationHistory(2, 10, {
    token: "tenant-token",
    fetcher,
  });
  assert.match(capturedUrl, /history\?page=2&page_size=10$/);
  assert.equal(
    (capturedInit?.headers as Record<string, string>).Authorization,
    "Bearer tenant-token",
  );
  assert.deepEqual(result.runs, []);
});

test("historical detail uses GET only and never calls ranked POST", async () => {
  let capturedUrl = "";
  let capturedMethod: string | undefined;
  const fetcher: typeof fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedMethod = init?.method;
    return new Response(JSON.stringify({ run_id: "run-one" }), { status: 200 });
  };
  await getRecommendationHistoryDetail("run one", {
    token: "tenant-token",
    fetcher,
  });
  assert.match(capturedUrl, /\/history\/run%20one$/);
  assert.equal(capturedMethod, undefined);
  assert.doesNotMatch(capturedUrl, /\/ranked$/);
});

test("history authentication and API errors remain classified", async () => {
  await assert.rejects(
    getRecommendationHistory(1, 10, { token: null }),
    (error: unknown) =>
      error instanceof RecommendationApiError &&
      error.kind === "authentication",
  );
  const fetcher: typeof fetch = async () =>
    new Response(JSON.stringify({ detail: "History unavailable." }), {
      status: 503,
    });
  await assert.rejects(
    getRecommendationHistoryDetail("run", { token: "token", fetcher }),
    (error: unknown) =>
      error instanceof RecommendationApiError &&
      error.kind === "service_unavailable",
  );
});

test("missing token and 401 or 403 responses are authentication failures", async () => {
  await assert.rejects(
    getRankedRecommendations(preferences(), { token: null }),
    (error: unknown) =>
      error instanceof RecommendationApiError &&
      error.kind === "authentication" &&
      error.status === 401,
  );

  for (const status of [401, 403]) {
    const fetcher: typeof fetch = async () =>
      new Response(JSON.stringify({ detail: "Access denied." }), { status });
    await assert.rejects(
      getRankedRecommendations(preferences(), {
        token: "token",
        fetcher,
      }),
      (error: unknown) =>
        error instanceof RecommendationApiError &&
        error.kind === "authentication" &&
        error.status === status,
    );
  }
});

test("503 remains a service failure rather than an empty result", async () => {
  const fetcher: typeof fetch = async () =>
    new Response(JSON.stringify({ detail: "Routing unavailable." }), {
      status: 503,
    });
  await assert.rejects(
    getRankedRecommendations(preferences(), { token: "token", fetcher }),
    (error: unknown) =>
      error instanceof RecommendationApiError &&
      error.kind === "service_unavailable" &&
      error.status === 503,
  );
});

test("network errors are classified separately", async () => {
  const fetcher: typeof fetch = async () => {
    throw new Error("offline");
  };
  await assert.rejects(
    getRankedRecommendations(preferences(), { token: "token", fetcher }),
    (error: unknown) =>
      error instanceof RecommendationApiError && error.kind === "network",
  );
});

test("unresolved destinations stop the request before fetch", async () => {
  const unresolved = preferences();
  unresolved.important_destinations[0].latitude = null;
  let calls = 0;
  const fetcher: typeof fetch = async () => {
    calls += 1;
    return new Response(JSON.stringify(responsePayload()), { status: 200 });
  };
  await assert.rejects(
    getRankedRecommendations(unresolved, { token: "token", fetcher }),
    RecommendationApiError,
  );
  assert.equal(calls, 0);
});
