import type {
  MinimumRoomCount,
  RecommendationPriorities,
} from "@/types/tenant-preference";

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
