import type {
  RankedRecommendationCandidate,
  RecommendationRouteGeometryResponse,
} from "../types/recommendation.ts";
import type { ImportantDestinationPreference } from "../types/tenant-preference.ts";


export interface MapCoordinate {
  latitude: number;
  longitude: number;
}

export interface RecommendationMapHome extends MapCoordinate {
  id: string;
  rank: number;
  candidate: RankedRecommendationCandidate;
}

export interface RecommendationMapDestination extends MapCoordinate {
  id: string;
  label: string;
  importance: number;
  maxCommuteMinutes: number | null;
}

export function isValidMapCoordinate(
  latitude: unknown,
  longitude: unknown,
): latitude is number {
  return (
    typeof latitude === "number" &&
    typeof longitude === "number" &&
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180
  );
}

export function recommendationMapHomes(
  candidates: RankedRecommendationCandidate[],
): RecommendationMapHome[] {
  return candidates
    .filter((candidate) =>
      isValidMapCoordinate(candidate.latitude, candidate.longitude),
    )
    .map((candidate) => ({
      id: candidate.id,
      rank: candidate.rank,
      latitude: candidate.latitude as number,
      longitude: candidate.longitude as number,
      candidate,
    }));
}

export function recommendationMapDestinations(
  destinations: ImportantDestinationPreference[],
): RecommendationMapDestination[] {
  return destinations
    .filter((destination) =>
      isValidMapCoordinate(destination.latitude, destination.longitude),
    )
    .map((destination) => ({
      id: destination.id,
      label: destination.destination,
      importance: destination.preference ?? 1,
      maxCommuteMinutes: destination.max_commute_minutes,
      latitude: destination.latitude as number,
      longitude: destination.longitude as number,
    }));
}

export function initialRecommendationId(
  candidates: RankedRecommendationCandidate[],
): string | null {
  return candidates.find((candidate) => candidate.rank === 1)?.id ??
    candidates[0]?.id ?? null;
}

export function routeCacheKey(runId: string, listingId: string): string {
  return `${runId}:${listingId}`;
}

export class RecommendationRouteCache {
  private entries = new Map<string, RecommendationRouteGeometryResponse>();

  get(runId: string, listingId: string) {
    return this.entries.get(routeCacheKey(runId, listingId));
  }

  set(response: RecommendationRouteGeometryResponse) {
    this.entries.set(
      routeCacheKey(response.run_id, response.listing_id),
      response,
    );
  }
}

export function isLatestRouteRequest(
  requestNumber: number,
  latestRequestNumber: number,
): boolean {
  return requestNumber === latestRequestNumber;
}
