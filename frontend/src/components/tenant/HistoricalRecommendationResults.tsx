"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import RecommendationExplorer from "@/components/tenant/RecommendationExplorer";
import { clearStoredAuth } from "@/lib/auth";
import {
  getRecommendationHistoryDetail,
  RecommendationApiError,
} from "@/lib/recommendation-api";
import { historicalCandidates } from "@/lib/recommendation-history-display";
import type { RecommendationRunDetail } from "@/types/recommendation";


const generatedDate = new Intl.DateTimeFormat("en-BD", {
  dateStyle: "long",
  timeStyle: "short",
});
const currency = new Intl.NumberFormat("en-BD", { maximumFractionDigits: 0 });
const WEIGHT_LABELS = {
  location: "Location",
  budget: "Budget",
  space: "Space",
  amenities: "Amenities",
  rent_fairness: "Rent fairness",
} as const;

export default function HistoricalRecommendationResults() {
  const params = useParams<{ runId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<RecommendationRunDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadSnapshot() {
      await Promise.resolve();
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const result = await getRecommendationHistoryDetail(params.runId, {
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setDetail(result);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (
          error instanceof RecommendationApiError &&
          error.kind === "authentication"
        ) {
          clearStoredAuth();
          router.replace("/login");
          return;
        }
        setErrorMessage(
          error instanceof RecommendationApiError && error.status === 404
            ? "This recommendation run was not found."
            : "We couldn't load these historical recommendations.",
        );
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }
    void loadSnapshot();
    return () => controller.abort();
  }, [params.runId, router]);

  if (isLoading) return <SimpleState title="Loading saved recommendations..." />;
  if (errorMessage || !detail) {
    return (
      <SimpleState title={errorMessage ?? "Recommendation run unavailable"}>
        <Link href="/tenant/recommendations/history" className="mt-5 inline-block font-semibold text-emerald-700">
          Back to recommendation history
        </Link>
      </SimpleState>
    );
  }

  const request = detail.request_snapshot;
  return (
    <main className="min-h-screen bg-slate-50 pb-16">
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-9 sm:px-6 lg:px-8">
          <Link href="/tenant/recommendations/history" className="text-sm font-semibold text-emerald-700">
            Back to recommendation history
          </Link>
          <p className="mt-6 text-sm font-semibold text-emerald-700">
            Historical Recommendation Results
          </p>
          <h1 className="mt-2 text-3xl font-bold text-slate-950">
            Recommendation Results
          </h1>
          <p className="mt-2 text-sm font-semibold text-slate-700">
            Generated {generatedDate.format(new Date(detail.created_at))}
          </p>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
            These results reflect the listings and recommendation data saved at
            the time this search was generated. They have not been rerouted or rescored.
          </p>

          <section className="mt-7 border-t border-slate-100 pt-5">
            <h2 className="text-sm font-bold text-slate-900">Original search</h2>
            <dl className="mt-3 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
              <SnapshotFact
                label="Destinations"
                value={request.important_destinations.map((item) =>
                  `${item.destination} (${item.preference}/5${item.max_commute_minutes ? `, max ${item.max_commute_minutes} min` : ", flexible"}${item.travel_days_per_month ? `, ${item.travel_days_per_month} days/month` : ""})`
                ).join("; ")}
              />
              <SnapshotFact label="Budget" value={request.minimum_rent_bdt === null ? `Up to BDT ${currency.format(request.maximum_rent_bdt)}` : `BDT ${currency.format(request.minimum_rent_bdt)} - ${currency.format(request.maximum_rent_bdt)}`} />
              <SnapshotFact label="Property types" value={propertyTypeSummary(request.property_types)} />
              <SnapshotFact label="Rooms needed" value={`${request.minimum_bedrooms} bed, ${request.minimum_bathrooms} bath`} />
              <SnapshotFact
                label={request.preferred_area_sqft != null ? "Preferred floor size" : "Area requirement"}
                value={areaSummary(request.preferred_area_sqft ?? null, request.minimum_area_sqft, request.maximum_area_sqft)}
              />
              <SnapshotFact label="Furnishing" value={request.furnishing_statuses.length ? request.furnishing_statuses.join(", ") : "Any"} />
              <SnapshotFact label="Must-have amenities" value={request.must_have_amenities.join(", ") || "None"} />
              <SnapshotFact label="Preferred amenities" value={request.nice_to_have_amenities.join(", ") || "None"} />
              <SnapshotFact label="Move-in date" value={request.desired_move_in_date ?? "Flexible"} />
              <SnapshotFact label="Household size" value={request.household_size ? `${request.household_size} people` : "Not specified"} />
            </dl>
            {detail.travel_cost_summary ? (
              <p className="mt-4 text-xs leading-5 text-slate-500">
                Stored travel estimates use BDT{" "}
                {currency.format(detail.travel_cost_summary.cost_per_km_bdt)}/km
                and one round trip per travel day. These historical values are not recalculated.
              </p>
            ) : (
              <p className="mt-4 text-xs text-slate-500">
                Travel-cost estimate was not recorded for this recommendation.
              </p>
            )}
          </section>

          <section className="mt-6 border-t border-slate-100 pt-5">
            <h2 className="text-sm font-bold text-slate-900">What mattered most</h2>
            <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-5">
              {Object.entries(detail.normalized_weights).map(([key, value]) => (
                <div key={key}>
                  <div className="flex justify-between text-xs text-slate-600">
                    <span>{WEIGHT_LABELS[key as keyof typeof WEIGHT_LABELS]}</span>
                    <span>{Math.round(value * 100)}%</span>
                  </div>
                  <div className="mt-1 h-1.5 bg-slate-100">
                    <div className="h-full bg-cyan-600" style={{ width: `${Math.round(value * 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>

      <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {detail.results.length === 0 ? (
          <section className="border border-slate-200 bg-white p-8 text-center">
            <h2 className="text-xl font-bold text-slate-950">
              This search returned no matching homes.
            </h2>
          </section>
        ) : (
          <RecommendationExplorer
            candidates={historicalCandidates(detail)}
            destinations={request.important_destinations}
            runId={detail.run_id}
            historical
          />
        )}
      </div>
    </main>
  );
}

function areaSummary(
  preferred: number | null,
  minimum: number | null,
  maximum: number | null,
): string {
  if (preferred !== null) return `${preferred} sq ft`;
  if (minimum !== null && maximum !== null) return `${minimum}-${maximum} sq ft`;
  if (minimum !== null) return `At least ${minimum} sq ft`;
  if (maximum !== null) return `Up to ${maximum} sq ft`;
  return "Any";
}

function propertyTypeSummary(propertyTypes: string[]): string {
  const labels: string[] = [];
  if (propertyTypes.includes("apartment")) labels.push("Apartment");
  if (propertyTypes.includes("house")) labels.push("House");
  if (propertyTypes.includes("room") || propertyTypes.includes("sublet")) {
    labels.push("Room / Sublet");
  }
  return labels.join(", ") || "Not selected";
}

function SnapshotFact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 capitalize leading-6 text-slate-800">{value}</dd>
    </div>
  );
}

function SimpleState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <main className="flex min-h-[70vh] items-center justify-center bg-slate-50 px-4 py-16 text-center">
      <section className="max-w-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-950">{title}</h1>
        {children}
      </section>
    </main>
  );
}
