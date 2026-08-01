"use client";

import type { RentAssessment } from "@/types/listing";

interface RentFairnessPanelProps {
  assessment: RentAssessment | null;
  askingRentBdt: number;
  isChecking: boolean;
  disabled: boolean;
  onCheck: () => Promise<void>;
}

const currencyFormatter = new Intl.NumberFormat("en-BD", {
  maximumFractionDigits: 2,
});
type AssessmentRecord = Record<string, unknown>;

function readNumber(assessment: RentAssessment, keys: string[]): number | null {
  const record = assessment as unknown as AssessmentRecord;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return null;
}

function formatCurrency(value: number | null): string {
  return value === null ? "Not available" : `BDT ${currencyFormatter.format(value)}`;
}

function formatDateTime(value: string | undefined): string {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-BD", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

const fairnessLabels: Record<string, string> = {
  significantly_below_estimated_range: "Significantly Below Estimated Range",
  below_estimated_range: "Below Estimated Range",
  fairly_priced: "Fairly Priced",
  above_estimated_range: "Above Estimated Range",
  significantly_above_estimated_range: "Significantly Above Estimated Range",
};

const fairnessClasses: Record<string, string> = {
  significantly_below_estimated_range: "border-blue-200 bg-blue-50 text-blue-800",
  below_estimated_range: "border-cyan-200 bg-cyan-50 text-cyan-800",
  fairly_priced: "border-emerald-200 bg-emerald-50 text-emerald-800",
  above_estimated_range: "border-orange-200 bg-orange-50 text-orange-800",
  significantly_above_estimated_range: "border-red-200 bg-red-50 text-red-800",
};

function humanize(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function RentFairnessPanel({
  assessment,
  askingRentBdt,
  isChecking,
  disabled,
  onCheck,
}: RentFairnessPanelProps) {
  if (!assessment) {
    return (
      <section className="rounded-lg border border-amber-200 bg-amber-50 p-5">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-amber-700">
              Required before approval
            </p>
            <h2 className="mt-1 text-xl font-semibold text-amber-950">
              Rent fairness has not been checked
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-amber-800">
              Run the trained model against the submitted property values. The
              result is advisory and the administrator retains final authority.
            </p>
          </div>
          <button
            type="button"
            disabled={disabled || isChecking}
            onClick={() => void onCheck()}
            className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-lg bg-amber-700 px-5 py-3 text-sm font-semibold text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isChecking ? "Running model..." : "Check rent fairness"}
          </button>
        </div>
      </section>
    );
  }

  const predictedRent = readNumber(assessment, [
    "predicted_rent_bdt",
    "estimated_rent_bdt",
    "prediction_bdt",
  ]);
  const lowerRange = readNumber(assessment, [
    "estimated_lower_bdt",
    "lower_bound_bdt",
    "fair_range_lower_bdt",
  ]);
  const upperRange = readNumber(assessment, [
    "estimated_upper_bdt",
    "upper_bound_bdt",
    "fair_range_upper_bdt",
  ]);
  const differenceBdt = readNumber(assessment, [
    "difference_bdt",
    "rent_difference_bdt",
  ]);
  const differencePercent = readNumber(assessment, [
    "difference_percent",
    "percentage_difference",
  ]);
  const statusClass =
    fairnessClasses[assessment.fairness_status] ??
    "border-slate-200 bg-slate-50 text-slate-800";

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-emerald-700">
            Machine-learning assessment
          </p>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">
            Rent fairness result
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            The result informs review but does not make the final decision.
          </p>
        </div>
        <div className={`rounded-full border px-4 py-2 text-sm font-semibold ${statusClass}`}>
          {fairnessLabels[assessment.fairness_status] ?? assessment.fairness_status}
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <AssessmentMetric label="Landlord asking rent" value={formatCurrency(askingRentBdt)} />
        <AssessmentMetric label="Model prediction" value={formatCurrency(predictedRent)} />
        <AssessmentMetric label="Estimated lower range" value={formatCurrency(lowerRange)} />
        <AssessmentMetric label="Estimated upper range" value={formatCurrency(upperRange)} />
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <AssessmentMetric label="Difference in BDT" value={formatCurrency(differenceBdt)} />
        <AssessmentMetric
          label="Difference percentage"
          value={
            differencePercent === null
              ? "Not available"
              : `${differencePercent.toFixed(2)}%`
          }
        />
      </div>

      <dl className="mt-6 grid gap-4 rounded-lg bg-slate-50 p-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <DetailItem label="Model route" value={humanize(assessment.model_route)} />
        <DetailItem label="Model version" value={assessment.model_version} />
        <DetailItem label="Target strategy" value={assessment.target_strategy} />
        <DetailItem label="Checked at" value={formatDateTime(assessment.checked_at)} />
      </dl>
      <button
        type="button"
        disabled={disabled || isChecking}
        onClick={() => void onCheck()}
        className="mt-5 rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isChecking ? "Rechecking..." : "Run fairness check again"}
      </button>
    </section>
  );
}

function AssessmentMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-bold text-slate-950">{value}</p>
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 break-words font-medium text-slate-800">{value}</dd>
    </div>
  );
}
