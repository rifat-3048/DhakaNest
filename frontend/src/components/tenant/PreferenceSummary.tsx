import type { TenantSearchPreferences } from "@/types/tenant-preference";

const currencyFormatter = new Intl.NumberFormat("en-BD", {
  maximumFractionDigits: 0,
});

const PRIORITY_LABELS: Record<keyof TenantSearchPreferences["priorities"], string> = {
  location: "Location",
  budget: "Budget",
  space: "Property size",
  amenities: "Amenities",
  rent_fairness: "Rent fairness",
};

function words(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

interface PreferenceSummaryProps {
  preferences: TenantSearchPreferences;
  isProcessing: boolean;
  successMessage: string | null;
  onFind: () => void;
  onReset: () => void;
}

export default function PreferenceSummary({
  preferences,
  isProcessing,
  successMessage,
  onFind,
  onReset,
}: PreferenceSummaryProps) {
  const highestValue = Math.max(...Object.values(preferences.priorities));
  const highestPriorities = Object.entries(preferences.priorities)
    .filter(([, value]) => value === highestValue)
    .map(([key]) => PRIORITY_LABELS[key as keyof typeof PRIORITY_LABELS]);

  const budget = preferences.minimum_rent_bdt
    ? `BDT ${currencyFormatter.format(preferences.minimum_rent_bdt)} - ${currencyFormatter.format(preferences.maximum_rent_bdt)}`
    : `Up to BDT ${currencyFormatter.format(preferences.maximum_rent_bdt)}`;

  return (
    <aside className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm xl:sticky xl:top-6">
      <h2 className="text-lg font-semibold text-slate-950">Your Search Summary</h2>
      <p className="mt-1 text-sm text-slate-600">
        This updates as you refine your preferences.
      </p>

      <dl className="mt-6 divide-y divide-slate-100">
        <SummaryItem
          label="Preferred areas"
          value={preferences.preferred_areas.join(", ") || "Not selected"}
        />
        <SummaryItem label="Monthly budget" value={budget} />
        <SummaryItem
          label="Property"
          value={`${preferences.property_types.map(words).join(", ") || "Not selected"} | ${preferences.minimum_bedrooms}+ bedrooms | ${preferences.minimum_bathrooms}+ bathrooms`}
        />
        <SummaryItem
          label="Minimum area"
          value={
            preferences.minimum_area_sqft
              ? `${currencyFormatter.format(preferences.minimum_area_sqft)} sq ft`
              : "No minimum"
          }
        />
        <SummaryItem
          label="Move-in date"
          value={preferences.desired_move_in_date || "Flexible"}
        />
        <SummaryItem
          label="Must-have amenities"
          value={preferences.must_have_amenities.join(", ") || "None selected"}
        />
        <SummaryItem
          label="Flexibility"
          value={`${preferences.accept_nearby_areas ? "Nearby areas allowed" : "Selected areas only"}; ${preferences.over_budget_percent ? `up to ${preferences.over_budget_percent}% over budget` : "no over-budget flexibility"}`}
        />
        <SummaryItem
          label="Highest priorities"
          value={highestPriorities.join(" and ")}
        />
      </dl>

      <button
        type="button"
        onClick={onFind}
        disabled={isProcessing}
        className="mt-6 flex min-h-12 w-full items-center justify-center rounded-lg bg-emerald-700 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isProcessing ? "Saving preferences..." : "Find My Recommended Homes"}
      </button>
      <p className="mt-2 text-center text-xs text-slate-500">
        Recommendations are not generated in this frontend phase.
      </p>

      {successMessage && (
        <p className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
          {successMessage}
        </p>
      )}

      <button
        type="button"
        onClick={onReset}
        className="mt-4 min-h-11 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
      >
        Reset preferences
      </button>
    </aside>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="py-3 first:pt-0">
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 break-words text-sm font-semibold text-slate-900">
        {value}
      </dd>
    </div>
  );
}
