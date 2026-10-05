import { validateImportantDestinations } from "./tenant-destination.ts";
import { API_BASE_URL } from "./api-config.ts";
import type {
  RankedRecommendationResponse,
  RecommendationHistoryListResponse,
  RecommendationRouteGeometryResponse,
  RecommendationRunDetail,
} from "../types/recommendation.ts";
import type { TenantSearchPreferences } from "../types/tenant-preference.ts";


const TOKEN_KEY = "dhakanest_access_token";

export type RecommendationErrorKind =
  | "authentication"
  | "rate_limited"
  | "service_unavailable"
  | "network"
  | "request";

export class RecommendationApiError extends Error {
  status: number;
  kind: RecommendationErrorKind;

  constructor(message: string, status: number, kind: RecommendationErrorKind) {
    super(message);
    this.name = "RecommendationApiError";
    this.status = status;
    this.kind = kind;
  }
}

export function buildRankedRecommendationRequest(
  preferences: TenantSearchPreferences,
) {
  const destinationError = validateImportantDestinations(
    preferences.important_destinations,
  );
  if (destinationError) {
    throw new RecommendationApiError(destinationError, 422, "request");
  }

  return {
    ...preferences,
    // Preferred area is a soft target. Legacy bounds stay clear for new UI requests.
    preferred_area_sqft: preferences.preferred_area_sqft,
    minimum_area_sqft: null,
    maximum_area_sqft: null,
    important_destinations: preferences.important_destinations.map(
      (destination) => ({
        id: destination.id,
        destination: destination.destination.trim(),
        latitude: destination.latitude as number,
        longitude: destination.longitude as number,
        preference: destination.preference as number,
        max_commute_minutes: destination.max_commute_minutes,
        travel_days_per_month: destination.travel_days_per_month,
      }),
    ),
  };
}

function errorKind(status: number): RecommendationErrorKind {
  if (status === 401 || status === 403) return "authentication";
  if (status === 429) return "rate_limited";
  if (status === 503) return "service_unavailable";
  return "request";
}

function errorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" && item !== null && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : String(item),
        )
        .join(" ");
    }
  }
  return fallback;
}

export function parseRankedRecommendationResponse(
  payload: unknown,
): RankedRecommendationResponse {
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("candidates" in payload) ||
    !Array.isArray((payload as { candidates?: unknown }).candidates) ||
    !("normalized_weights" in payload) ||
    typeof (payload as { total_ranked?: unknown }).total_ranked !== "number"
  ) {
    throw new RecommendationApiError(
      "The recommendation response was not in the expected format.",
      500,
      "request",
    );
  }
  return payload as RankedRecommendationResponse;
}

interface RankedRequestOptions {
  token?: string | null;
  idempotencyKey?: string | null;
  signal?: AbortSignal;
  fetcher?: typeof fetch;
}

interface AuthenticatedRequestOptions {
  token?: string | null;
  signal?: AbortSignal;
  fetcher?: typeof fetch;
}

function storedToken(optionToken?: string | null): string | null {
  return optionToken ??
    (typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY));
}

async function authenticatedGet<T>(
  path: string,
  options: AuthenticatedRequestOptions = {},
): Promise<T> {
  const token = storedToken(options.token);
  if (!token) {
    throw new RecommendationApiError(
      "You are not authenticated.", 401, "authentication",
    );
  }
  let response: Response;
  try {
    response = await (options.fetcher ?? fetch)(`${API_BASE_URL}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new RecommendationApiError(
      "Cannot connect to the recommendation service.", 0, "network",
    );
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new RecommendationApiError(
      errorMessage(payload, "The recommendation history request failed."),
      response.status,
      errorKind(response.status),
    );
  }
  return payload as T;
}

export async function getRankedRecommendations(
  preferences: TenantSearchPreferences,
  options: RankedRequestOptions = {},
): Promise<RankedRecommendationResponse> {
  const token = storedToken(options.token);
  if (!token) {
    throw new RecommendationApiError(
      "You are not authenticated.",
      401,
      "authentication",
    );
  }

  const requestBody = buildRankedRecommendationRequest(preferences);
  let response: Response;
  try {
    response = await (options.fetcher ?? fetch)(
      `${API_BASE_URL}/api/recommendations/ranked`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          ...(options.idempotencyKey
            ? { "X-Idempotency-Key": options.idempotencyKey }
            : {}),
        },
        body: JSON.stringify(requestBody),
        signal: options.signal,
      },
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new RecommendationApiError(
      "Cannot connect to the recommendation service.",
      0,
      "network",
    );
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new RecommendationApiError(
      errorMessage(payload, "The recommendation request failed."),
      response.status,
      errorKind(response.status),
    );
  }
  return parseRankedRecommendationResponse(payload);
}

export function getRecommendationHistory(
  page = 1,
  pageSize = 10,
  options: AuthenticatedRequestOptions = {},
): Promise<RecommendationHistoryListResponse> {
  return authenticatedGet(
    `/api/recommendations/history?page=${page}&page_size=${pageSize}`,
    options,
  );
}

export function getRecommendationHistoryDetail(
  runId: string,
  options: AuthenticatedRequestOptions = {},
): Promise<RecommendationRunDetail> {
  return authenticatedGet(
    `/api/recommendations/history/${encodeURIComponent(runId)}`,
    options,
  );
}

export function getRecommendationRouteGeometry(
  runId: string,
  listingId: string,
  options: AuthenticatedRequestOptions = {},
): Promise<RecommendationRouteGeometryResponse> {
  return authenticatedGet(
    `/api/recommendations/history/${encodeURIComponent(runId)}/listings/${encodeURIComponent(listingId)}/route-geometry`,
    options,
  );
}
