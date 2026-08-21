import type {
  MinimumRoomCount,
  RentalFurnishingStatus,
} from "@/types/tenant-preference";

export const FURNISHING_OPTIONS: Array<{
  value: RentalFurnishingStatus;
  label: string;
}> = [
  { value: "unfurnished", label: "Unfurnished" },
  { value: "semi_furnished", label: "Semi-furnished" },
  { value: "furnished", label: "Furnished" },
];

export const MINIMUM_ROOM_OPTIONS = [
  { label: "1", value: 1 },
  { label: "2", value: 2 },
  { label: "3", value: 3 },
  { label: "4", value: 4 },
  { label: "5", value: 5 },
  { label: "5+", value: 6 },
] as const satisfies ReadonlyArray<{ label: string; value: MinimumRoomCount }>;
