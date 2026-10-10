import type {
  RankedRecommendationCandidate,
  RankedRecommendationResponse,
} from "../types/recommendation.ts";
import type { ListingImage } from "../types/listing.ts";


export function suitabilityPercent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
}

export function recommendationContactValue(
  value: string | null | undefined,
): string {
  const cleaned = value?.trim();
  return cleaned || "Not provided";
}

export function candidatesInBackendOrder(
  response: RankedRecommendationResponse,
): RankedRecommendationCandidate[] {
  return [...response.candidates];
}

function validImage(image: ListingImage | null | undefined): image is ListingImage {
  return Boolean(image?.url && /^https:\/\//.test(image.url));
}

export function recommendationImage(
  candidate: RankedRecommendationCandidate,
): ListingImage | null {
  if (validImage(candidate.primary_image)) return candidate.primary_image;
  const sorted = [...candidate.images].sort(
    (first, second) => first.sort_order - second.sort_order,
  );
  return sorted.find(validImage) ?? null;
}

export function recommendationDetailsPath(listingId: string): string {
  return `/tenant/recommendations/${encodeURIComponent(listingId)}`;
}

export function recommendationResultState(
  response: RankedRecommendationResponse | null,
  errorKind: string | null,
): "results" | "empty" | "service_error" | "error" | "idle" {
  if (errorKind === "service_unavailable" || errorKind === "network") {
    return "service_error";
  }
  if (errorKind) return "error";
  if (!response) return "idle";
  return response.candidates.length === 0 ? "empty" : "results";
}
