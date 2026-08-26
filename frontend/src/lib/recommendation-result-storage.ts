import { parseRankedRecommendationResponse } from "./recommendation-api.ts";
import type { RankedRecommendationResponse } from "../types/recommendation.ts";


const RESULT_STORAGE_KEY = "dhakanest_latest_ranked_recommendations_v1";

export function saveLatestRecommendationResult(
  response: RankedRecommendationResponse,
): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(RESULT_STORAGE_KEY, JSON.stringify(response));
}

export function getLatestRecommendationResult(): RankedRecommendationResponse | null {
  if (typeof window === "undefined") return null;
  const stored = sessionStorage.getItem(RESULT_STORAGE_KEY);
  if (!stored) return null;
  try {
    return parseRankedRecommendationResponse(JSON.parse(stored) as unknown);
  } catch {
    sessionStorage.removeItem(RESULT_STORAGE_KEY);
    return null;
  }
}
