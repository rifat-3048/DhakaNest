// Shared property values keep landlord listings and tenant preferences compatible.
export const PROPERTY_TYPE_OPTIONS = [
  { value: "apartment", label: "Apartment" },
  { value: "house", label: "House" },
  { value: "sublet", label: "Sublet" },
  { value: "room", label: "Room" },
] as const;

export type PropertyType = (typeof PROPERTY_TYPE_OPTIONS)[number]["value"];

export const PROPERTY_AMENITIES = [
  { value: "Lift", label: "Lift" },
  { value: "Generator", label: "Generator" },
  { value: "Parking", label: "Parking" },
  { value: "Balcony", label: "Balcony" },
  { value: "Security Guard", label: "Security Guard" },
  { value: "CCTV", label: "CCTV" },
  { value: "Gas Connection", label: "Gas Connection" },
  { value: "Air Conditioning", label: "Air Conditioning" },
  { value: "Backup Water Supply", label: "Backup Water Supply" },
  { value: "Rooftop Access", label: "Rooftop Access" },
] as const;

export type PropertyAmenity = (typeof PROPERTY_AMENITIES)[number]["value"];

export function isPropertyAmenity(value: string): value is PropertyAmenity {
  return PROPERTY_AMENITIES.some((amenity) => amenity.value === value);
}
