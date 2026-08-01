/*
 * These labels match the locations currently used by DhakaNest test listings.
 * Expand this centralized list from model metadata before API integration.
 */
export interface AreaOption {
  broadArea: string;
  microAreas: string[];
}

export const DHAKA_LOCATION_OPTIONS: AreaOption[] = [
  { broadArea: "Dhanmondi", microAreas: ["Dhanmondi 27"] },
  { broadArea: "Mohammadpur", microAreas: ["Mohammadia Housing"] },
  { broadArea: "Uttara", microAreas: ["Sector 10"] },
  { broadArea: "Mirpur", microAreas: ["Section 12"] },
];
