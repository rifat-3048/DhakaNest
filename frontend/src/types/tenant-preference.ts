export type RentalPropertyType = "apartment" | "house" | "sublet" | "room";

export type RentalFurnishingStatus =
  | "unfurnished"
  | "semi_furnished"
  | "furnished";

export type BudgetFlexibilityPercent = 0 | 5 | 10;

export type PreferenceScore = 1 | 2 | 3 | 4 | 5;

export interface PreferredMicroArea {
  broad_area: string;
  micro_area: string;
}

export interface ImportantDestinationPreference {
  // Frontend-only identifier used for stable rendering and row deletion.
  id: string;
  destination: string;
  preference: PreferenceScore | null;
  max_commute_minutes: number | null;
}

export interface RecommendationPriorities {
  location: number;
  budget: number;
  space: number;
  amenities: number;
  rent_fairness: number;
}

export interface TenantSearchPreferences {
  preferred_areas: string[];
  preferred_micro_areas: PreferredMicroArea[];
  accept_nearby_areas: boolean;
  important_destinations: ImportantDestinationPreference[];
  minimum_rent_bdt: number | null;
  maximum_rent_bdt: number;
  over_budget_percent: BudgetFlexibilityPercent;
  property_types: RentalPropertyType[];
  minimum_bedrooms: number;
  minimum_bathrooms: number;
  minimum_area_sqft: number | null;
  maximum_area_sqft: number | null;
  furnishing_statuses: RentalFurnishingStatus[];
  desired_move_in_date: string | null;
  household_size: number | null;
  must_have_amenities: string[];
  nice_to_have_amenities: string[];
  priorities: RecommendationPriorities;
}

export interface StoredTenantPreference {
  preferences: TenantSearchPreferences;
  saved_at: string;
}
