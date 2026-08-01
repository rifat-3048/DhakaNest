"use client";

import { useEffect, useMemo, useState } from "react";

import ImportantDestinationsEditor from "@/components/tenant/ImportantDestinationsEditor";
import PreferenceSection from "@/components/tenant/PreferenceSection";
import PreferenceSummary from "@/components/tenant/PreferenceSummary";
import PrioritySelector from "@/components/tenant/PrioritySelector";
import {
  DHAKA_LOCATION_OPTIONS,
  type AreaOption,
} from "@/data/location-options";
import {
  AMENITY_OPTIONS,
  FURNISHING_OPTIONS,
  PROPERTY_TYPE_OPTIONS,
} from "@/data/tenant-preference-options";
import {
  clearTenantPreferences,
  getSavedTenantPreferences,
  saveTenantPreferences,
} from "@/lib/tenant-preference-storage";
import type {
  BudgetFlexibilityPercent,
  RecommendationPriorities,
  PreferredMicroArea,
  TenantSearchPreferences,
} from "@/types/tenant-preference";

function createInitialPreferences(): TenantSearchPreferences {
  return {
    preferred_areas: [],
    preferred_micro_areas: [],
    accept_nearby_areas: true,
    important_destinations: [
      {
        id: "destination-1",
        destination: "",
        preference: null,
        max_commute_minutes: null,
      },
    ],
    minimum_rent_bdt: null,
    maximum_rent_bdt: 30000,
    over_budget_percent: 0,
    property_types: ["apartment"],
    minimum_bedrooms: 2,
    minimum_bathrooms: 1,
    minimum_area_sqft: null,
    maximum_area_sqft: null,
    furnishing_statuses: [],
    desired_move_in_date: null,
    household_size: null,
    must_have_amenities: [],
    nice_to_have_amenities: [],
    priorities: {
      location: 5,
      budget: 5,
      space: 3,
      amenities: 3,
      rent_fairness: 4,
    },
  };
}

const fieldClass =
  "mt-2 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100";

function toggleArrayValue<T extends string>(values: T[], value: T): T[] {
  return values.includes(value)
    ? values.filter((item) => item !== value)
    : [...values, value];
}

function nullableNumber(value: string): number | null {
  if (value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function validatePreferences(
  values: TenantSearchPreferences,
): Record<string, string> {
  const nextErrors: Record<string, string> = {};

  if (values.preferred_areas.length === 0) {
    nextErrors.preferred_areas = "Select at least one preferred area.";
  } else if (values.preferred_areas.length > 3) {
    nextErrors.preferred_areas = "Select no more than three preferred areas.";
  }
  if (
    values.important_destinations.length < 1 ||
    values.important_destinations.length > 3
  ) {
    nextErrors.important_destinations =
      "Add between one and three important destinations.";
  } else {
    const incompleteDestination = values.important_destinations.find(
      (destination) =>
        !destination.destination.trim() || destination.preference === null,
    );
    const invalidCommuteTime = values.important_destinations.find(
      (destination) =>
        destination.max_commute_minutes !== null &&
        (destination.max_commute_minutes < 1 ||
          destination.max_commute_minutes > 240),
    );
    const normalizedNames = values.important_destinations.map((destination) =>
      destination.destination.trim().toLowerCase(),
    );

    if (incompleteDestination) {
      nextErrors.important_destinations =
        "Enter a name and select an importance score for every destination.";
    } else if (invalidCommuteTime) {
      nextErrors.important_destinations =
        "Optional commute time must be between 1 and 240 minutes.";
    } else if (new Set(normalizedNames).size !== normalizedNames.length) {
      nextErrors.important_destinations =
        "Do not add the same destination more than once.";
    }
  }
  if (!Number.isFinite(values.maximum_rent_bdt) || values.maximum_rent_bdt <= 0) {
    nextErrors.maximum_rent_bdt = "Enter a valid maximum monthly rent.";
  }
  if (
    values.minimum_rent_bdt !== null &&
    values.minimum_rent_bdt > values.maximum_rent_bdt
  ) {
    nextErrors.minimum_rent_bdt = "Minimum rent cannot exceed maximum rent.";
  }
  if (values.property_types.length === 0) {
    nextErrors.property_types = "Select at least one property type.";
  }
  if (values.minimum_bedrooms < 1) {
    nextErrors.minimum_bedrooms = "Select at least one bedroom.";
  }
  if (values.minimum_bathrooms < 1) {
    nextErrors.minimum_bathrooms = "Select at least one bathroom.";
  }
  if (
    values.minimum_area_sqft !== null &&
    values.maximum_area_sqft !== null &&
    values.minimum_area_sqft > values.maximum_area_sqft
  ) {
    nextErrors.minimum_area_sqft = "Minimum area cannot exceed maximum area.";
  }

  const hasDuplicateAmenity = values.must_have_amenities.some((amenity) =>
    values.nice_to_have_amenities.includes(amenity),
  );
  if (hasDuplicateAmenity) {
    nextErrors.amenities =
      "An amenity cannot be both must-have and nice-to-have.";
  }

  return nextErrors;
}

export default function TenantPreferenceForm() {
  const [preferences, setPreferences] =
    useState<TenantSearchPreferences>(createInitialPreferences);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [broadAreaSearch, setBroadAreaSearch] = useState("");

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      const saved = getSavedTenantPreferences();
      if (saved) setPreferences(saved.preferences);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, []);

  const selectedLocationGroups = useMemo(
    () =>
      DHAKA_LOCATION_OPTIONS.filter((option) =>
        preferences.preferred_areas.includes(option.broadArea),
      ),
    [preferences.preferred_areas],
  );

  const normalizedBroadAreaSearch = broadAreaSearch.trim().toLowerCase();
  const broadAreaSearchHasMatch = useMemo(
    () =>
      !normalizedBroadAreaSearch ||
      DHAKA_LOCATION_OPTIONS.some((option) =>
        option.broadArea.toLowerCase().includes(normalizedBroadAreaSearch),
      ),
    [normalizedBroadAreaSearch],
  );
  const visibleLocationOptions = useMemo(
    () =>
      DHAKA_LOCATION_OPTIONS.filter(
        (option) =>
          preferences.preferred_areas.includes(option.broadArea) ||
          option.broadArea.toLowerCase().includes(normalizedBroadAreaSearch),
      ),
    [normalizedBroadAreaSearch, preferences.preferred_areas],
  );

  function updatePreferences(
    update: (current: TenantSearchPreferences) => TenantSearchPreferences,
  ) {
    setPreferences(update);
    setSuccessMessage(null);
  }

  function togglePreferredArea(broadArea: string) {
    updatePreferences((current) => {
      const isSelected = current.preferred_areas.includes(broadArea);
      if (!isSelected && current.preferred_areas.length >= 3) return current;
      return {
        ...current,
        preferred_areas: toggleArrayValue(current.preferred_areas, broadArea),
        preferred_micro_areas: isSelected
          ? current.preferred_micro_areas.filter(
              (microArea) => microArea.broad_area !== broadArea,
            )
          : current.preferred_micro_areas,
      };
    });
  }

  function togglePreferredMicroArea(broadArea: string, microArea: string) {
    updatePreferences((current) => {
      const alreadySelected = current.preferred_micro_areas.some(
        (selected) =>
          selected.broad_area === broadArea && selected.micro_area === microArea,
      );
      const selectedValue: PreferredMicroArea = {
        broad_area: broadArea,
        micro_area: microArea,
      };
      return {
        ...current,
        preferred_micro_areas: alreadySelected
          ? current.preferred_micro_areas.filter(
              (selected) =>
                !(
                  selected.broad_area === broadArea &&
                  selected.micro_area === microArea
                ),
            )
          : [...current.preferred_micro_areas, selectedValue],
      };
    });
  }

  function handleFindRecommendedHomes() {
    setIsProcessing(true);
    setSuccessMessage(null);
    const validationErrors = validatePreferences(preferences);
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      window.scrollTo({ top: 0, behavior: "smooth" });
      setIsProcessing(false);
      return;
    }

    const stored = saveTenantPreferences(preferences);
    console.log("Tenant recommendation payload:", stored);
    setSuccessMessage(
      "Your search preferences are ready. The recommendation engine will use this information when it is connected.",
    );
    setIsProcessing(false);
  }

  function handleReset() {
    if (!window.confirm("Reset all tenant search preferences?")) return;
    clearTenantPreferences();
    setPreferences(createInitialPreferences());
    setErrors({});
    setSuccessMessage(null);
  }

  return (
    <div className="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:px-6 lg:px-8 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start">
      <div className="space-y-6">
        {Object.keys(errors).length > 0 && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4" role="alert">
            <p className="font-semibold text-red-900">Check your preferences</p>
            <p className="mt-1 text-sm text-red-700">
              Correct the highlighted sections before saving your search.
            </p>
          </div>
        )}

        <PreferenceSection
          number={1}
          title="Preferred location"
          description="Choose up to three broad areas, select optional micro-areas, and add your important destinations."
        >
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-sm font-semibold text-slate-900">
              Preferred areas <span className="text-red-600">*</span>
            </h3>
            <span className="text-xs font-semibold text-emerald-700">
              {preferences.preferred_areas.length}/3 selected
            </span>
          </div>
          <ErrorText message={errors.preferred_areas} />

          <label htmlFor="broad-area-search" className="mt-4 block">
            <span className="text-sm font-medium text-slate-700">
              Search broad areas
            </span>
            <input
              id="broad-area-search"
              type="search"
              value={broadAreaSearch}
              placeholder="Search broad areas"
              onChange={(event) => setBroadAreaSearch(event.target.value)}
              className={fieldClass}
            />
          </label>

          {!broadAreaSearchHasMatch && (
            <p className="mt-3 text-sm text-slate-500">
              No areas match your search
            </p>
          )}

          <div className="mt-4 max-h-80 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {visibleLocationOptions.map((option) => {
                const checked = preferences.preferred_areas.includes(
                  option.broadArea,
                );
                const disabled =
                  !checked && preferences.preferred_areas.length >= 3;
                return (
                  <CheckboxChoice
                    key={option.broadArea}
                    label={option.broadArea}
                    checked={checked}
                    disabled={disabled}
                    onChange={() => togglePreferredArea(option.broadArea)}
                  />
                );
              })}
            </div>
          </div>

          <div className="mt-8">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Preferred micro-areas{" "}
                  <span className="font-normal text-slate-500">(Optional)</span>
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  Micro-areas are grouped under the broad areas you selected.
                </p>
              </div>
              <span className="text-xs font-semibold text-emerald-700">
                {preferences.preferred_micro_areas.length} selected
              </span>
            </div>

            {selectedLocationGroups.length === 0 ? (
              <div className="mt-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-500">
                Select at least one preferred broad area to see its micro-areas.
              </div>
            ) : (
              <div className="mt-4 space-y-5">
                {selectedLocationGroups.map((location) => (
                  <MicroAreaGroup
                    key={location.broadArea}
                    location={location}
                    selectedMicroAreas={preferences.preferred_micro_areas}
                    onToggle={togglePreferredMicroArea}
                  />
                ))}
              </div>
            )}
          </div>

          <label className="mt-8 flex cursor-pointer items-start gap-3 rounded-lg border border-slate-200 p-4">
            <input
              type="checkbox"
              checked={preferences.accept_nearby_areas}
              onChange={(event) =>
                updatePreferences((current) => ({
                  ...current,
                  accept_nearby_areas: event.target.checked,
                }))
              }
              className="mt-0.5 h-4 w-4 accent-emerald-700"
            />
            <span>
              <span className="block text-sm font-semibold text-slate-900">
                Accept nearby areas
              </span>
              <span className="mt-1 block text-xs text-slate-500">
                Allow nearby locations when exact-area choices are limited.
              </span>
            </span>
          </label>

          <div className="mt-8 border-t border-slate-200 pt-8">
            <ImportantDestinationsEditor
              destinations={preferences.important_destinations}
              errorMessage={errors.important_destinations}
              onChange={(importantDestinations) =>
                updatePreferences((current) => ({
                  ...current,
                  important_destinations: importantDestinations,
                }))
              }
            />
          </div>
        </PreferenceSection>

        <PreferenceSection
          number={2}
          title="Monthly budget"
          description="Set a comfortable rent range and controlled flexibility."
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <NumberField
              label="Minimum monthly rent"
              requirement="Optional"
              prefix="BDT"
              min={0}
              step={500}
              value={preferences.minimum_rent_bdt}
              onChange={(value) =>
                updatePreferences((current) => ({
                  ...current,
                  minimum_rent_bdt: value,
                }))
              }
            />
            <NumberField
              label="Maximum monthly rent"
              requirement="Required"
              prefix="BDT"
              min={1}
              step={500}
              value={preferences.maximum_rent_bdt || null}
              onChange={(value) =>
                updatePreferences((current) => ({
                  ...current,
                  maximum_rent_bdt: value ?? 0,
                }))
              }
            />
          </div>
          <ErrorText message={errors.minimum_rent_bdt ?? errors.maximum_rent_bdt} />
          <label className="mt-5 block">
            <FieldHeading label="Over-budget flexibility" requirement="Required" />
            <select
              value={preferences.over_budget_percent}
              onChange={(event) =>
                updatePreferences((current) => ({
                  ...current,
                  over_budget_percent: Number(
                    event.target.value,
                  ) as BudgetFlexibilityPercent,
                }))
              }
              className={fieldClass}
            >
              <option value={0}>No flexibility</option>
              <option value={5}>Up to 5% over budget</option>
              <option value={10}>Up to 10% over budget</option>
            </select>
          </label>
        </PreferenceSection>

        <PreferenceSection
          number={3}
          title="Property requirements"
          description="Choose the property formats and minimum space you need."
        >
          <FieldHeading
            label="Property types"
            requirement="Required"
            detail={`${preferences.property_types.length} selected`}
          />
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {PROPERTY_TYPE_OPTIONS.map((option) => (
              <CheckboxChoice
                key={option.value}
                label={option.label}
                checked={preferences.property_types.includes(option.value)}
                onChange={() =>
                  updatePreferences((current) => ({
                    ...current,
                    property_types: toggleArrayValue(
                      current.property_types,
                      option.value,
                    ),
                  }))
                }
              />
            ))}
          </div>
          <ErrorText message={errors.property_types} />

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <SelectNumberField
              label="Minimum bedrooms"
              value={preferences.minimum_bedrooms}
              maximum={6}
              onChange={(value) =>
                updatePreferences((current) => ({
                  ...current,
                  minimum_bedrooms: value,
                }))
              }
            />
            <SelectNumberField
              label="Minimum bathrooms"
              value={preferences.minimum_bathrooms}
              maximum={5}
              onChange={(value) =>
                updatePreferences((current) => ({
                  ...current,
                  minimum_bathrooms: value,
                }))
              }
            />
          </div>
          <ErrorText message={errors.minimum_bedrooms ?? errors.minimum_bathrooms} />

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <NumberField
              label="Minimum floor area"
              requirement="Optional"
              suffix="sq ft"
              min={1}
              value={preferences.minimum_area_sqft}
              onChange={(value) =>
                updatePreferences((current) => ({
                  ...current,
                  minimum_area_sqft: value,
                }))
              }
            />
            <NumberField
              label="Maximum floor area"
              requirement="Optional"
              suffix="sq ft"
              min={1}
              value={preferences.maximum_area_sqft}
              onChange={(value) =>
                updatePreferences((current) => ({
                  ...current,
                  maximum_area_sqft: value,
                }))
              }
            />
          </div>
          <ErrorText message={errors.minimum_area_sqft} />

          <div className="mt-6">
            <FieldHeading
              label="Furnishing preferences"
              requirement="Optional"
              detail={
                preferences.furnishing_statuses.length
                  ? `${preferences.furnishing_statuses.length} selected`
                  : "No restriction"
              }
            />
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              {FURNISHING_OPTIONS.map((option) => (
                <CheckboxChoice
                  key={option.value}
                  label={option.label}
                  checked={preferences.furnishing_statuses.includes(option.value)}
                  onChange={() =>
                    updatePreferences((current) => ({
                      ...current,
                      furnishing_statuses: toggleArrayValue(
                        current.furnishing_statuses,
                        option.value,
                      ),
                    }))
                  }
                />
              ))}
            </div>
          </div>
        </PreferenceSection>

        <PreferenceSection
          number={4}
          title="Move-in information"
          description="Optional timing and household details help explain matches."
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <label>
              <FieldHeading label="Desired move-in date" requirement="Optional" />
              <input
                type="date"
                value={preferences.desired_move_in_date ?? ""}
                onChange={(event) =>
                  updatePreferences((current) => ({
                    ...current,
                    desired_move_in_date: event.target.value || null,
                  }))
                }
                className={fieldClass}
              />
            </label>
            <NumberField
              label="Household size"
              requirement="Optional"
              suffix="people"
              min={1}
              value={preferences.household_size}
              onChange={(value) =>
                updatePreferences((current) => ({
                  ...current,
                  household_size: value,
                }))
              }
            />
          </div>
        </PreferenceSection>

        <PreferenceSection
          number={5}
          title="Amenities"
          description="Separate requirements from features that simply improve a match."
        >
          <div className="grid gap-6 lg:grid-cols-2">
            <AmenityGroup
              title="Must-have amenities"
              description="Missing items may exclude a listing."
              selected={preferences.must_have_amenities}
              onToggle={(amenity) =>
                updatePreferences((current) => ({
                  ...current,
                  must_have_amenities: toggleArrayValue(
                    current.must_have_amenities,
                    amenity,
                  ),
                }))
              }
            />
            <AmenityGroup
              title="Nice-to-have amenities"
              description="These improve ranking without excluding listings."
              selected={preferences.nice_to_have_amenities}
              onToggle={(amenity) =>
                updatePreferences((current) => ({
                  ...current,
                  nice_to_have_amenities: toggleArrayValue(
                    current.nice_to_have_amenities,
                    amenity,
                  ),
                }))
              }
            />
          </div>
          <ErrorText message={errors.amenities} />
        </PreferenceSection>

        <PreferenceSection
          number={6}
          title="Ranking priorities"
          description="Rate each factor from 1 to 5. Scores will be normalized later."
        >
          <div className="grid gap-4 md:grid-cols-2">
            {(
              [
                ["location", "Preferred location", "How closely the area should match."],
                ["budget", "Monthly budget", "How strongly rent should affect ranking."],
                ["space", "Property size", "Bedrooms, bathrooms, and floor area."],
                ["amenities", "Amenities", "Importance of selected property features."],
                ["rent_fairness", "Rent fairness", "Importance of model-assessed value."],
              ] as Array<[keyof RecommendationPriorities, string, string]>
            ).map(([key, label, description]) => (
              <PrioritySelector
                key={key}
                label={label}
                description={description}
                value={preferences.priorities[key]}
                onChange={(value) =>
                  updatePreferences((current) => ({
                    ...current,
                    priorities: { ...current.priorities, [key]: value },
                  }))
                }
              />
            ))}
          </div>
        </PreferenceSection>
      </div>

      <PreferenceSummary
        preferences={preferences}
        isProcessing={isProcessing}
        successMessage={successMessage}
        onFind={handleFindRecommendedHomes}
        onReset={handleReset}
      />
    </div>
  );
}

const LARGE_MICRO_AREA_THRESHOLD = 12;

function MicroAreaGroup({
  location,
  selectedMicroAreas,
  onToggle,
}: {
  location: AreaOption;
  selectedMicroAreas: PreferredMicroArea[];
  onToggle: (broadArea: string, microArea: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [searchText, setSearchText] = useState("");
  const normalizedSearch = searchText.trim().toLowerCase();
  const selectedForArea = useMemo(
    () =>
      selectedMicroAreas.filter(
        (selected) => selected.broad_area === location.broadArea,
      ),
    [location.broadArea, selectedMicroAreas],
  );
  const visibleMicroAreas = useMemo(
    () =>
      location.microAreas.filter(
        (microArea) =>
          selectedForArea.some((selected) => selected.micro_area === microArea) ||
          microArea.toLowerCase().includes(normalizedSearch),
      ),
    [location.microAreas, normalizedSearch, selectedForArea],
  );

  function isSelected(microArea: string): boolean {
    return selectedForArea.some((selected) => selected.micro_area === microArea);
  }

  return (
    <section className="rounded-lg border border-slate-200 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-900">
            {location.broadArea}
          </h4>
          <p className="mt-1 text-xs font-medium text-emerald-700">
            {selectedForArea.length} selected
          </p>
        </div>
        <button
          type="button"
          aria-expanded={isExpanded}
          aria-controls={`micro-areas-${location.broadArea.replace(/\s+/g, "-").toLowerCase()}`}
          onClick={() => setIsExpanded((current) => !current)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          {isExpanded ? "Hide micro-areas" : "Show micro-areas"}
        </button>
      </div>

      {isExpanded && (
        <div
          id={`micro-areas-${location.broadArea.replace(/\s+/g, "-").toLowerCase()}`}
          className="mt-4"
        >
          {location.microAreas.length >= LARGE_MICRO_AREA_THRESHOLD && (
            <label className="block">
              <span className="text-xs font-medium text-slate-700">
                Search {location.broadArea} micro-areas
              </span>
              <input
                type="search"
                value={searchText}
                placeholder={`Search ${location.broadArea} micro-areas`}
                onChange={(event) => setSearchText(event.target.value)}
                className={fieldClass}
              />
            </label>
          )}

          {location.microAreas.length === 0 ? (
            <p className="text-sm text-slate-500">
              No specific micro-areas are currently configured for this area.
            </p>
          ) : visibleMicroAreas.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              No micro-areas match your search.
            </p>
          ) : (
            <div className="mt-3 grid max-h-72 gap-2 overflow-y-auto sm:grid-cols-2 lg:grid-cols-3">
              {visibleMicroAreas.map((microArea) => (
                <CheckboxChoice
                  key={`${location.broadArea}-${microArea}`}
                  label={microArea}
                  checked={isSelected(microArea)}
                  onChange={() => onToggle(location.broadArea, microArea)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function FieldHeading({
  label,
  requirement,
  detail,
}: {
  label: string;
  requirement: "Required" | "Optional";
  detail?: string;
}) {
  return (
    <span className="flex flex-wrap items-center justify-between gap-2 text-sm font-semibold text-slate-900">
      <span>
        {label} <span className="font-normal text-slate-500">({requirement})</span>
      </span>
      {detail && <span className="text-xs font-medium text-emerald-700">{detail}</span>}
    </span>
  );
}

function CheckboxChoice({
  label,
  checked,
  disabled = false,
  onChange,
}: {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onChange: () => void;
}) {
  return (
    <label
      className={[
        "flex min-h-11 items-center gap-3 rounded-lg border px-3 py-2.5 text-sm font-medium",
        checked
          ? "border-emerald-600 bg-emerald-50 text-emerald-950"
          : "border-slate-200 bg-white text-slate-700",
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer hover:border-slate-400",
      ].join(" ")}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={onChange}
        className="h-4 w-4 accent-emerald-700"
      />
      {label}
    </label>
  );
}

function NumberField({
  label,
  requirement,
  value,
  onChange,
  min,
  step = 1,
  prefix,
  suffix,
}: {
  label: string;
  requirement: "Required" | "Optional";
  value: number | null;
  onChange: (value: number | null) => void;
  min: number;
  step?: number;
  prefix?: string;
  suffix?: string;
}) {
  return (
    <label>
      <FieldHeading label={label} requirement={requirement} />
      <div className="relative">
        {prefix && (
          <span className="pointer-events-none absolute left-3 top-1/2 mt-1 -translate-y-1/2 text-xs font-semibold text-slate-500">
            {prefix}
          </span>
        )}
        <input
          type="number"
          min={min}
          step={step}
          value={value ?? ""}
          onChange={(event) => onChange(nullableNumber(event.target.value))}
          className={`${fieldClass} ${prefix ? "pl-12" : ""} ${suffix ? "pr-16" : ""}`}
        />
        {suffix && (
          <span className="pointer-events-none absolute right-3 top-1/2 mt-1 -translate-y-1/2 text-xs text-slate-500">
            {suffix}
          </span>
        )}
      </div>
    </label>
  );
}

function SelectNumberField({
  label,
  value,
  maximum,
  onChange,
}: {
  label: string;
  value: number;
  maximum: number;
  onChange: (value: number) => void;
}) {
  return (
    <label>
      <FieldHeading label={label} requirement="Required" />
      <select
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className={fieldClass}
      >
        {Array.from({ length: maximum }, (_, index) => index + 1).map((number) => (
          <option key={number} value={number}>
            {number}+
          </option>
        ))}
      </select>
    </label>
  );
}

function AmenityGroup({
  title,
  description,
  selected,
  onToggle,
}: {
  title: string;
  description: string;
  selected: string[];
  onToggle: (amenity: string) => void;
}) {
  return (
    <fieldset>
      <legend className="text-sm font-semibold text-slate-900">{title}</legend>
      <p className="mt-1 text-xs text-slate-500">{description}</p>
      <p className="mt-2 text-xs font-medium text-emerald-700">
        {selected.length} selected
      </p>
      <div className="mt-3 space-y-2">
        {AMENITY_OPTIONS.map((amenity) => (
          <CheckboxChoice
            key={amenity}
            label={amenity}
            checked={selected.includes(amenity)}
            onChange={() => onToggle(amenity)}
          />
        ))}
      </div>
    </fieldset>
  );
}

function ErrorText({ message }: { message?: string }) {
  return message ? (
    <p className="mt-3 text-sm font-medium text-red-700" role="alert">
      {message}
    </p>
  ) : null;
}
