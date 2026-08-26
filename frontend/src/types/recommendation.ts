import type {
  FurnishingStatus,
  PropertyType,
  RentAssessment,
  ListingImage,
} from "@/types/listing";
import type { TenantSearchPreferences } from "@/types/tenant-preference";

export type RecommendationReasonCategory =
  | "location"
  | "budget"
  | "space"
  | "amenities"
  | "rent_fairness"
  | "property_match";

export type RecommendationReasonStrength =
  | "strong"
  | "moderate"
  | "informational";

export interface RecommendationReason {
  code: string;
  category: RecommendationReasonCategory;
  text: string;
  strength: RecommendationReasonStrength;
}

export interface RecommendationCommute {
  destination_id: string;
  destination: string;
  destination_preference: number;
  distance_km: number;
  estimated_duration_minutes: number;
  max_commute_minutes: number | null;
  within_max_commute: boolean | null;
  normalized_destination_score: number;
}

export interface RankedRecommendationCandidate {
  id: string;
  title: string | null;
  description: string | null;
  asking_rent_bdt: number | null;
  property_type: PropertyType | null;
  bedrooms: number | null;
  bathrooms: number | null;
  area_sqft: number | null;
  furnishing_status: FurnishingStatus | null;
  amenities: string[];
  broad_area: string | null;
  model_micro_area: string | null;
  address: string | null;
  latitude: number;
  longitude: number;
  available_from: string | null;
  rent_assessment: RentAssessment | null;
  primary_image: ListingImage | null;
  images: ListingImage[];
  commutes: RecommendationCommute[];
  destination_access_score: number;
  property_similarity_score: number;
  budget_score: number;
  space_score: number;
  amenities_score: number;
  rent_fairness_score: number;
  final_suitability_score: number;
  rank: number;
  recommendation_reasons: RecommendationReason[];
}

export interface NormalizedRecommendationWeights {
  location: number;
  budget: number;
  space: number;
  amenities: number;
  rent_fairness: number;
}

export interface RankedRecommendationResponse {
  total_base_eligible: number;
  total_after_hard_filters: number;
  total_routing_complete: number;
  total_after_max_commute: number;
  total_scored_candidates: number;
  total_after_knn: number;
  total_ranked: number;
  normalized_weights: NormalizedRecommendationWeights;
  candidates: RankedRecommendationCandidate[];
  filter_summary: Record<string, number>;
  routing_summary: Record<string, number>;
  scoring_summary: Record<string, number>;
  knn_summary: Record<string, number>;
  wsm_summary: {
    wsm_input_candidate_count: number;
    wsm_ranked_candidate_count: number;
    weight_sum: number;
    scoring_version: string;
  };
  recommendation_run_id: string | null;
  created_at: string | null;
}

export interface RecommendationRunSummary {
  run_id: string;
  created_at: string;
  destination_labels: string[];
  minimum_rent_bdt: number | null;
  maximum_rent_bdt: number;
  recommendation_count: number;
  top_recommendation: {
    listing_id: string;
    title: string | null;
    final_suitability_score: number;
    primary_image: ListingImage | null;
  } | null;
}

export interface RecommendationHistoryListResponse {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  runs: RecommendationRunSummary[];
}

export interface RecommendationRunDetail {
  run_id: string;
  created_at: string;
  request_snapshot: TenantSearchPreferences;
  pipeline_snapshot: {
    scoring_version: string;
    configured_knn_k: number;
    effective_knn_k: number;
    routing_provider: string;
    travel_mode: string;
  };
  counts: {
    base_eligible: number;
    after_hard_filters: number;
    after_max_commute: number;
    after_knn: number;
    ranked: number;
  };
  normalized_weights: NormalizedRecommendationWeights;
  results: RankedRecommendationCandidate[];
  filter_summary: Record<string, number>;
  routing_summary: Record<string, number>;
  scoring_summary: Record<string, number>;
  knn_summary: Record<string, number | string>;
  wsm_summary: Record<string, number | string>;
}
