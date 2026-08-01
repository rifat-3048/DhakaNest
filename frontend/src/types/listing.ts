export type ListingStatus =
  | "draft"
  | "pending_review"
  | "revision_requested"
  | "approved"
  | "rejected"
  | "rented";

export type PropertyType = "apartment" | "house" | "sublet" | "room";

export type FurnishingStatus =
  | "unfurnished"
  | "semi_furnished"
  | "furnished";

export type FairnessStatus =
  | "significantly_below_estimated_range"
  | "below_estimated_range"
  | "fairly_priced"
  | "above_estimated_range"
  | "significantly_above_estimated_range";

export interface ListingImage {
  image_id: string;
  url: string;
  public_id: string;
  asset_id?: string | null;
  width: number;
  height: number;
  format: string;
  bytes: number;
  original_filename: string;
  is_primary: boolean;
  sort_order: number;
  uploaded_at: string;
}

export interface RentAssessment {
  asking_rent_bdt: number;
  predicted_rent_bdt: number;
  estimated_lower_bdt: number;
  estimated_upper_bdt: number;
  difference_bdt: number;
  difference_percent: number;
  fairness_status: FairnessStatus;
  model_route: "primary" | "broad_area_fallback" | "dhaka_wide_fallback";
  model_version: string;
  target_strategy: "log1p";
  checked_at: string;
  checked_by: string;
  input_snapshot?: {
    broad_area: string;
    model_micro_area: string;
    area_sqft: number;
    bedrooms: number;
    bathrooms: number;
    asking_rent_bdt: number;
  };
}

export interface AdminReview {
  decision: "approve" | "request_revision" | "reject";
  notes: string | null;
  reviewed_by: string;
  reviewed_at: string;
}

export interface RentalListing {
  id: string;
  landlord_id: string;
  title: string;
  description: string;
  property_type: PropertyType;
  furnishing_status: FurnishingStatus;
  broad_area: string;
  model_micro_area: string;
  address: string;
  area_sqft: number;
  bedrooms: number;
  bathrooms: number;
  asking_rent_bdt: number;
  amenities: string[];
  available_from: string | null;
  images: ListingImage[];
  status: ListingStatus;
  is_available: boolean;
  rent_assessment: RentAssessment | null;
  admin_review: AdminReview | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ListingFormValues {
  title: string;
  description: string;
  property_type: PropertyType;
  furnishing_status: FurnishingStatus;
  broad_area: string;
  model_micro_area: string;
  address: string;
  area_sqft: number;
  bedrooms: number;
  bathrooms: number;
  asking_rent_bdt: number;
  amenities: string[];
  available_from: string | null;
}

export type ListingCreatePayload = ListingFormValues;
export type ListingUpdatePayload = Partial<ListingFormValues>;

export interface ListingMutationResponse {
  message: string;
  listing: RentalListing;
}

export interface LandlordListingsResponse {
  count: number;
  listings: RentalListing[];
}

export interface ListingImageUploadResponse {
  message: string;
  uploaded_images: ListingImage[];
  listing: RentalListing;
}

export type AdminDecision = "approve" | "request_revision" | "reject";

export interface AdminDecisionPayload {
  decision: AdminDecision;
  notes: string | null;
}

export interface AdminPendingListingsResponse {
  count: number;
  listings: RentalListing[];
}

export interface AdminActionResponse {
  message?: string;
  listing?: RentalListing;
  rent_assessment?: RentAssessment;
}

export type AdminListingFilter =
  | "all"
  | "pending_review"
  | "approved"
  | "revision_requested"
  | "rejected";

export interface AdminListingSummary {
  all_listings: number;
  pending_review: number;
  approved: number;
  revision_requested: number;
  rejected: number;
  fairness_check_required: number;
  fairness_checked: number;
  above_estimated_range: number;
}

export interface AdminListingsResponse {
  count: number;
  skip: number;
  limit: number;
  active_status: AdminListingFilter;
  summary: AdminListingSummary;
  listings: RentalListing[];
}

export interface AdminListingsQuery {
  status?: AdminListingFilter;
  search?: string;
  skip?: number;
  limit?: number;
}
