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
  travel_days_per_month?: number | null;
  estimated_monthly_travel_cost_bdt?: number | null;
}

export type TravelCostBasis = "rent_plus_travel" | "rent_only_legacy";

export interface TravelCostMetadata {
  cost_per_km_bdt: number;
  round_trip_multiplier: number;
  distance_basis: "osrm_road_distance";
  frequency_unit: "days_per_month";
  calculation_version: "travel_cost_v1";
}

export interface LandlordContact {
  owner_name: string | null;
  email: string | null;
  phone_number: string | null;
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
  latitude: number | null;
  longitude: number | null;
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
  landlord_contact?: LandlordContact | null;
  travel_cost_basis?: TravelCostBasis;
  estimated_monthly_travel_cost_bdt?: number | null;
  estimated_monthly_spend_bdt?: number | null;
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
  travel_cost_summary?: TravelCostMetadata | null;
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
    travel_cost?: TravelCostMetadata | null;
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
  travel_cost_summary?: TravelCostMetadata | null;
}

export interface RouteGeometryLineString {
  type: "LineString";
  coordinates: number[][];
}

export interface DestinationRouteGeometry {
  destination_id: string;
  destination: string;
  geometry: RouteGeometryLineString;
}

export interface RecommendationRouteGeometryResponse {
  run_id: string;
  listing_id: string;
  provider: string;
  travel_mode: "driving";
  routes: DestinationRouteGeometry[];
  unavailable_destination_ids: string[];
}
