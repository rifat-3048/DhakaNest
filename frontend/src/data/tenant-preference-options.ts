import type {
  RentalFurnishingStatus,
  RentalPropertyType,
} from "@/types/tenant-preference";

export const PROPERTY_TYPE_OPTIONS: Array<{
  value: RentalPropertyType;
  label: string;
}> = [
  { value: "apartment", label: "Apartment" },
  { value: "house", label: "House" },
  { value: "sublet", label: "Sublet" },
  { value: "room", label: "Room" },
];

export const FURNISHING_OPTIONS: Array<{
  value: RentalFurnishingStatus;
  label: string;
}> = [
  { value: "unfurnished", label: "Unfurnished" },
  { value: "semi_furnished", label: "Semi-furnished" },
  { value: "furnished", label: "Furnished" },
];

export const AMENITY_OPTIONS = [
  "Lift",
  "Generator",
  "Parking",
  "Balcony",
  "Security Guard",
  "CCTV",
  "Gas Connection",
  "Air Conditioning",
  "Backup Water Supply",
  "Rooftop Access",
] as const;
