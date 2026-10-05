import type {
  FurnishingStatus,
  PropertyAmenity,
  PropertyType,
} from "@/data/property-options";

export type RentalPropertyType = PropertyType;
export type RentalFurnishingStatus = FurnishingStatus;

export type BudgetFlexibilityPercent = 0 | 5 | 10;

export type PreferenceScore = 1 | 2 | 3 | 4 | 5;
export type MinimumRoomCount = 1 | 2 | 3 | 4 | 5 | 6;

export interface ImportantDestinationPreference {
  // Frontend-only identifier used for stable rendering and row deletion.
  id: string;
  destination: string;
  latitude: number | null;
  longitude: number | null;
  preference: PreferenceScore | null;
  max_commute_minutes: number | null;
  travel_days_per_month: number | null;
}

export interface RecommendationPriorities {
  location: number;
  budget: number;
  space: number;
  amenities: number;
  rent_fairness: number;
}

export interface TenantSearchPreferences {
  important_destinations: ImportantDestinationPreference[];
  minimum_rent_bdt: number | null;
  maximum_rent_bdt: number;
  over_budget_percent: BudgetFlexibilityPercent;
  property_types: RentalPropertyType[];
  minimum_bedrooms: MinimumRoomCount;
  minimum_bathrooms: MinimumRoomCount;
  preferred_area_sqft: number | null;
  minimum_area_sqft: number | null;
  maximum_area_sqft: number | null;
  furnishing_statuses: RentalFurnishingStatus[];
  desired_move_in_date: string | null;
  household_size: number | null;
  must_have_amenities: PropertyAmenity[];
  nice_to_have_amenities: PropertyAmenity[];
  priorities: RecommendationPriorities;
}

export interface StoredTenantPreference {
  preferences: TenantSearchPreferences;
  saved_at: string;
}
