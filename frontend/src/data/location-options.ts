/*
 * This is the tenant frontend's single source of truth for location choices.
 * Keep every label aligned with the canonical rental dataset/model spelling.
 */
export interface AreaOption {
  broadArea: string;
  microAreas: string[];
}

export const DHAKA_LOCATION_OPTIONS: AreaOption[] = [
  {
    broadArea: "Dhanmondi",
    microAreas: [
      "Dhanmondi 1",
      "Dhanmondi 2",
      "Dhanmondi 3",
      "Dhanmondi 4",
      "Dhanmondi 5",
      "Dhanmondi 6",
      "Dhanmondi 7",
      "Dhanmondi 8",
      "Dhanmondi 9",
      "Dhanmondi 10",
      "Dhanmondi 11",
      "Dhanmondi 12",
      "Dhanmondi 15",
      "Dhanmondi 27",
      "Dhanmondi 32",
    ],
  },
  {
    broadArea: "Mohammadpur",
    microAreas: [
      "Mohammadia Housing",
      "Mohammadpur Housing",
      "Japan Garden City",
      "Bashbari",
      "Chandrima Model Town",
      "Bosila",
      "Tajmahal Road",
      "Nurjahan Road",
    ],
  },
  {
    broadArea: "Uttara",
    microAreas: [
      "Sector 1",
      "Sector 3",
      "Sector 4",
      "Sector 5",
      "Sector 6",
      "Sector 7",
      "Sector 9",
      "Sector 10",
      "Sector 11",
      "Sector 12",
      "Sector 13",
      "Sector 14",
      "Sector 15",
      "Sector 16",
      "Sector 17",
      "Sector 18",
    ],
  },
  {
    broadArea: "Mirpur",
    microAreas: [
      "Section 1",
      "Section 2",
      "Section 6",
      "Section 10",
      "Section 11",
      "Section 12",
      "Section 13",
      "Section 14",
      "Pallabi",
      "Kazipara",
      "Shewrapara",
    ],
  },
];
