"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  recommendationImage,
  suitabilityPercent,
} from "@/lib/recommendation-display";
import { getLatestRecommendationResult } from "@/lib/recommendation-result-storage";
import type {
  RankedRecommendationCandidate,
  TravelCostMetadata,
} from "@/types/recommendation";


const currency = new Intl.NumberFormat("en-BD", { maximumFractionDigits: 0 });

export default function RecommendationDetails() {
  const params = useParams<{ listingId: string }>();
  const [candidate, setCandidate] = useState<RankedRecommendationCandidate | null>(null);
  const [travelCost, setTravelCost] = useState<TravelCostMetadata | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadDetails() {
      await Promise.resolve();
      if (cancelled) return;
      const response = getLatestRecommendationResult();
      setCandidate(
        response?.candidates.find((item) => item.id === params.listingId) ?? null,
      );
      setTravelCost(response?.travel_cost_summary ?? null);
      setLoaded(true);
    }
    void loadDetails();
    return () => {
      cancelled = true;
    };
  }, [params.listingId]);

  if (!loaded) {
    return <main className="p-10 text-center text-sm text-slate-600">Loading property details...</main>;
  }
  if (!candidate) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-slate-950">
          Recommendation details are no longer available
        </h1>
        <p className="mt-3 text-sm text-slate-600">
          Generate recommendations again to view this approved home.
        </p>
        <Link
          href="/tenant/recommendations"
          className="mt-6 inline-flex min-h-11 items-center bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white"
        >
          Back to recommendations
        </Link>
      </main>
    );
  }

  const image = recommendationImage(candidate);
  return (
    <main className="min-h-screen bg-slate-50 pb-16">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <Link href="/tenant/recommendations" className="text-sm font-semibold text-emerald-700">
          Back to recommendations
        </Link>
        <article className="mt-5 overflow-hidden border border-slate-200 bg-white shadow-sm">
          <div className="relative aspect-[16/7] min-h-64 bg-slate-100">
            {image ? (
              <Image
                src={image.url}
                alt={`${candidate.title ?? "Rental property"} image`}
                fill
                priority
                sizes="(max-width: 1024px) 100vw, 1024px"
                className="object-cover"
              />
            ) : (
              <div
                className="flex h-full items-center justify-center text-sm font-medium text-slate-600"
                role="img"
                aria-label="Property image unavailable"
              >
                Property image unavailable
              </div>
            )}
          </div>
          <div className="p-6 sm:p-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-emerald-700">Rank #{candidate.rank}</p>
                <h1 className="mt-1 text-3xl font-bold text-slate-950">
                  {candidate.title ?? "Approved rental home"}
                </h1>
                <p className="mt-2 text-sm text-slate-600">
                  {candidate.address ?? candidate.model_micro_area ?? "Dhaka City"}
                </p>
              </div>
              <div>
                <strong className="text-3xl text-slate-950">
                  {suitabilityPercent(candidate.final_suitability_score)}%
                </strong>
                <span className="ml-2 text-sm text-slate-500">Suitability</span>
              </div>
            </div>
            <p className="mt-5 text-2xl font-bold text-emerald-700">
              BDT {currency.format(candidate.asking_rent_bdt ?? 0)} / month
            </p>
            {candidate.estimated_monthly_travel_cost_bdt != null &&
            candidate.estimated_monthly_spend_bdt != null ? (
              <dl className="mt-5 grid gap-4 border border-slate-200 bg-slate-50 p-5 sm:grid-cols-3">
                <Fact
                  label="Monthly rent"
                  value={`BDT ${currency.format(candidate.asking_rent_bdt ?? 0)}`}
                />
                <Fact
                  label="Estimated monthly travel cost"
                  value={`BDT ${currency.format(candidate.estimated_monthly_travel_cost_bdt)}`}
                />
                <Fact
                  label="Estimated monthly spend"
                  value={`BDT ${currency.format(candidate.estimated_monthly_spend_bdt)}`}
                />
              </dl>
            ) : (
              <p className="mt-4 text-sm text-slate-500">
                Travel-cost estimate was not recorded for this recommendation.
              </p>
            )}
            <p className="mt-5 whitespace-pre-line text-sm leading-7 text-slate-700">
              {candidate.description ?? "No additional property description is available."}
            </p>
            <dl className="mt-7 grid gap-4 border-y border-slate-100 py-5 sm:grid-cols-4">
              <Fact label="Bedrooms" value={String(candidate.bedrooms ?? "-")} />
              <Fact label="Bathrooms" value={String(candidate.bathrooms ?? "-")} />
              <Fact label="Area" value={`${currency.format(candidate.area_sqft ?? 0)} sq ft`} />
              <Fact label="Available" value={candidate.available_from ?? "Flexible"} />
            </dl>
            <section className="mt-7">
              <h2 className="text-lg font-bold text-slate-950">Why this home matches</h2>
              <ul className="mt-3 space-y-2 text-sm text-slate-700">
                {candidate.recommendation_reasons.map((reason) => (
                  <li key={reason.code}>{reason.text}</li>
                ))}
              </ul>
            </section>
            <section className="mt-7">
              <h2 className="text-lg font-bold text-slate-950">
                Estimated monthly travel
              </h2>
              <div className="mt-3 divide-y divide-slate-100">
                {candidate.commutes.map((commute) => (
                  <div key={commute.destination_id} className="py-3 text-sm text-slate-700">
                    <strong className="text-slate-950">{commute.destination}</strong>
                    <p className="mt-1">
                      {commute.distance_km.toFixed(1)} km one way; {" "}
                      {commute.estimated_duration_minutes.toFixed(1)} minutes estimated drive
                    </p>
                    {commute.travel_days_per_month != null &&
                      commute.estimated_monthly_travel_cost_bdt != null && (
                        <p className="mt-1 font-medium text-slate-900">
                          {commute.travel_days_per_month} days/month; BDT{" "}
                          {currency.format(commute.estimated_monthly_travel_cost_bdt)}/month
                        </p>
                      )}
                  </div>
                ))}
              </div>
              {candidate.estimated_monthly_travel_cost_bdt != null && (
                <p className="mt-4 text-sm font-semibold text-slate-950">
                  Total estimated travel: BDT{" "}
                  {currency.format(candidate.estimated_monthly_travel_cost_bdt)}/month
                </p>
              )}
              {travelCost && (
                <p className="mt-2 text-xs leading-5 text-slate-500">
                  Estimated using a fixed BDT {currency.format(travelCost.cost_per_km_bdt)}/km
                  academic cost assumption and one round trip per travel day.
                </p>
              )}
            </section>
          </div>
        </article>
      </div>
    </main>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-slate-900">{value}</dd>
    </div>
  );
}
