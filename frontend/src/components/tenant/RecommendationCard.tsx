import Image from "next/image";
import Link from "next/link";

import {
  recommendationDetailsPath,
  recommendationImage,
  suitabilityPercent,
} from "@/lib/recommendation-display";
import type { RankedRecommendationCandidate } from "@/types/recommendation";


const currency = new Intl.NumberFormat("en-BD", {
  maximumFractionDigits: 0,
});

const CRITERIA = [
  ["Location", "destination_access_score"],
  ["Budget", "budget_score"],
  ["Space", "space_score"],
  ["Amenities", "amenities_score"],
  ["Rent fairness", "rent_fairness_score"],
] as const;

function words(value: string | null): string {
  if (!value) return "Not specified";
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function RecommendationCard({
  candidate,
  detailsHref,
}: {
  candidate: RankedRecommendationCandidate;
  detailsHref?: string | null;
}) {
  const image = recommendationImage(candidate);
  const suitability = suitabilityPercent(candidate.final_suitability_score);
  const location =
    candidate.model_micro_area ?? candidate.broad_area ?? candidate.address;

  return (
    <article className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="grid lg:grid-cols-[300px_minmax(0,1fr)]">
        <div className="relative min-h-56 bg-slate-100 lg:min-h-full">
          {image ? (
            <Image
              src={image.url}
              alt={`${candidate.title ?? "Rental property"} exterior or interior`}
              fill
              sizes="(max-width: 1024px) 100vw, 300px"
              className="object-cover"
            />
          ) : (
            <div
              className="flex h-full min-h-56 flex-col items-center justify-center border-b border-dashed border-slate-300 bg-slate-50 px-6 text-center lg:border-b-0 lg:border-r"
              role="img"
              aria-label="Property image unavailable"
            >
              <span className="text-2xl font-bold text-emerald-700">DN</span>
              <span className="mt-2 text-sm font-medium text-slate-600">
                Property image unavailable
              </span>
            </div>
          )}
          <span className="absolute left-4 top-4 bg-slate-950 px-3 py-1.5 text-sm font-bold text-white shadow-sm">
            Rank #{candidate.rank}
          </span>
        </div>

        <div className="min-w-0 p-5 sm:p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h2 className="text-xl font-bold text-slate-950">
                {candidate.title ?? "Approved rental home"}
              </h2>
              <p className="mt-1 text-sm text-slate-600">
                {location ?? "Dhaka City"}
              </p>
              <p className="mt-3 text-xl font-bold text-emerald-700">
                BDT {currency.format(candidate.asking_rent_bdt ?? 0)}
                <span className="text-sm font-normal text-slate-500"> / month</span>
              </p>
            </div>
            <div className="shrink-0 border-l-4 border-emerald-600 pl-3 sm:text-right">
              <strong className="block text-2xl text-slate-950">
                {suitability}%
              </strong>
              <span className="text-xs font-semibold uppercase text-slate-500">
                Suitability
              </span>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-x-4 gap-y-2 border-y border-slate-100 py-3 text-sm text-slate-700">
            <span>{candidate.bedrooms ?? "-"} bedrooms</span>
            <span>{candidate.bathrooms ?? "-"} bathrooms</span>
            <span>{currency.format(candidate.area_sqft ?? 0)} sq ft</span>
            <span>{words(candidate.property_type)}</span>
            <span>{words(candidate.furnishing_status)}</span>
          </div>

          {candidate.amenities.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2" aria-label="Property amenities">
              {candidate.amenities.slice(0, 6).map((amenity) => (
                <span
                  key={amenity}
                  className="border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700"
                >
                  {amenity}
                </span>
              ))}
            </div>
          )}

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <section aria-labelledby={`reasons-${candidate.id}`}>
              <h3
                id={`reasons-${candidate.id}`}
                className="text-sm font-bold text-slate-950"
              >
                Why this matches
              </h3>
              <ul className="mt-3 space-y-2">
                {candidate.recommendation_reasons.map((reason) => (
                  <li key={reason.code} className="flex gap-2 text-sm text-slate-700">
                    <span
                      className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-600"
                      aria-hidden="true"
                    />
                    <span>{reason.text}</span>
                  </li>
                ))}
              </ul>
            </section>

            <section aria-labelledby={`criteria-${candidate.id}`}>
              <h3
                id={`criteria-${candidate.id}`}
                className="text-sm font-bold text-slate-950"
              >
                Suitability breakdown
              </h3>
              <div className="mt-3 space-y-2.5">
                {CRITERIA.map(([label, key]) => {
                  const percent = suitabilityPercent(candidate[key]);
                  return (
                    <div key={key}>
                      <div className="flex justify-between text-xs text-slate-600">
                        <span>{label}</span>
                        <span className="font-semibold text-slate-900">{percent}%</span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden bg-slate-100">
                        <div
                          className="h-full bg-emerald-600"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          <section className="mt-6 border-t border-slate-100 pt-5">
            <h3 className="text-sm font-bold text-slate-950">Commute estimates</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {candidate.commutes.map((commute) => (
                <div key={commute.destination_id} className="border-l-2 border-cyan-600 pl-3">
                  <p className="text-sm font-semibold text-slate-900">
                    {commute.destination}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {commute.estimated_duration_minutes.toFixed(1)} min estimated
                    drive, {commute.distance_km.toFixed(1)} km
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Importance {commute.destination_preference}/5; maximum {" "}
                    {commute.max_commute_minutes
                      ? `${commute.max_commute_minutes} min`
                      : "flexible"}
                  </p>
                </div>
              ))}
            </div>
          </section>

          {detailsHref !== null && (
            <div className="mt-6 flex justify-end">
              <Link
                href={detailsHref ?? recommendationDetailsPath(candidate.id)}
                className="inline-flex min-h-11 items-center justify-center bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
              >
                View Details
              </Link>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
