import type {
  MinimumRoomCount,
  RecommendationPriorities,
} from "@/types/tenant-preference";
import type {
  PropertyAmenity,
  PropertyType,
} from "@/data/property-options";

// Tenant-facing groups can be simpler than the canonical landlord values.
// The values arrays are sent unchanged to the existing backend contract.
export const TENANT_PROPERTY_TYPE_OPTIONS = [
  { value: "apartment", label: "Apartment", propertyTypes: ["apartment"] },
  { value: "house", label: "House", propertyTypes: ["house"] },
  {
    value: "room_sublet",
    label: "Room / Sublet",
    propertyTypes: ["room", "sublet"],
  },
] as const satisfies ReadonlyArray<{
  value: string;
  label: string;
  propertyTypes: readonly PropertyType[];
}>;

export const MUST_HAVE_AMENITY_OPTIONS = [
  { value: "Lift", label: "Lift" },
  { value: "Generator", label: "Generator" },
  { value: "Security Guard", label: "Security Guard" },
  { value: "Gas Connection", label: "Gas Connection" },
  { value: "Backup Water Supply", label: "Backup Water Supply" },
  { value: "Parking", label: "Parking" },
] as const satisfies ReadonlyArray<{
  value: PropertyAmenity;
  label: string;
}>;

export const NICE_TO_HAVE_AMENITY_OPTIONS = [
  { value: "Balcony", label: "Balcony" },
  { value: "CCTV", label: "CCTV" },
  { value: "Air Conditioning", label: "Air Conditioning" },
  { value: "Rooftop Access", label: "Rooftop Access" },
] as const satisfies ReadonlyArray<{
  value: PropertyAmenity;
  label: string;
}>;

export const MINIMUM_ROOM_OPTIONS = [
  { label: "1", value: 1 },
  { label: "2", value: 2 },
  { label: "3", value: 3 },
  { label: "4", value: 4 },
  { label: "5", value: 5 },
  { label: "5+", value: 6 },
] as const satisfies ReadonlyArray<{ label: string; value: MinimumRoomCount }>;

export const RECOMMENDATION_PRIORITY_OPTIONS = [
  {
    key: "location",
    label: "Destination access",
    description: "How strongly travel needs should affect ranking.",
  },
  {
    key: "budget",
    label: "Monthly budget",
    description: "How strongly rent should affect ranking.",
  },
  {
    key: "space",
    label: "Property size",
    description: "Bedrooms, bathrooms, and floor area.",
  },
  {
    key: "amenities",
    label: "Amenities",
    description: "Importance of selected property features.",
  },
  {
    key: "rent_fairness",
    label: "Rent fairness",
    description: "Importance of model-assessed value.",
  },
] as const satisfies ReadonlyArray<{
  key: keyof RecommendationPriorities;
  label: string;
  description: string;
}>;
