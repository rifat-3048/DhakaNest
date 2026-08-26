"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import RecommendationCard from "@/components/tenant/RecommendationCard";
import { clearStoredAuth } from "@/lib/auth";
import {
  getRankedRecommendations,
  RecommendationApiError,
  type RecommendationErrorKind,
} from "@/lib/recommendation-api";
import { candidatesInBackendOrder } from "@/lib/recommendation-display";
import { saveLatestRecommendationResult } from "@/lib/recommendation-result-storage";
import { getRecommendationSubmissionKey } from "@/lib/recommendation-submission";
import { getSavedTenantPreferences } from "@/lib/tenant-preference-storage";
import type { RankedRecommendationResponse } from "@/types/recommendation";


const WEIGHT_LABELS = {
  location: "Location",
  budget: "Budget",
  space: "Space",
  amenities: "Amenities",
  rent_fairness: "Rent fairness",
} as const;

export default function RecommendationResults() {
  const router = useRouter();
  const [response, setResponse] = useState<RankedRecommendationResponse | null>(null);
  const [errorKind, setErrorKind] = useState<RecommendationErrorKind | null>(null);
  const [hasPreferences, setHasPreferences] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    async function loadRecommendations() {
      await Promise.resolve();
      if (controller.signal.aborted) return;
      const saved = getSavedTenantPreferences();
      if (!saved) {
        setHasPreferences(false);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setErrorKind(null);
      try {
        const result = await getRankedRecommendations(saved.preferences, {
          signal: controller.signal,
          idempotencyKey: getRecommendationSubmissionKey(),
        });
        setResponse(result);
        saveLatestRecommendationResult(result);
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (error instanceof RecommendationApiError) {
          if (error.kind === "authentication") {
            clearStoredAuth();
            router.replace("/login");
            return;
          }
          setErrorKind(error.kind);
          return;
        }
        setErrorKind("request");
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }

    void loadRecommendations();

    return () => controller.abort();
  }, [retryCount, router]);

  if (isLoading) {
    return (
      <StateLayout title="Finding your best-matching homes...">
        Evaluating approved homes and estimated commute options.
      </StateLayout>
    );
  }

  if (!hasPreferences) {
    return (
      <StateLayout title="Set your housing preferences first">
        <p>DhakaNest needs your requirements and important destinations.</p>
        <EditPreferencesLink />
      </StateLayout>
    );
  }

  if (errorKind) {
    const serviceFailure =
      errorKind === "service_unavailable" || errorKind === "network";
    return (
      <StateLayout
        title={
          serviceFailure
            ? "We couldn't calculate recommendations right now."
            : "Your recommendations could not be loaded."
        }
      >
        <p>Please try again shortly or review your saved preferences.</p>
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={() => setRetryCount((value) => value + 1)}
            className="min-h-11 bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"
          >
            Try again
          </button>
          <EditPreferencesLink />
        </div>
      </StateLayout>
    );
  }

  if (!response || response.candidates.length === 0) {
    return (
      <StateLayout title="No homes currently match all of your requirements.">
        <p>
          Try adjusting your budget, property requirements, amenities, or
          commute limits.
        </p>
        <EditPreferencesLink />
      </StateLayout>
    );
  }

  const candidates = candidatesInBackendOrder(response);
  return (
    <main className="min-h-screen bg-slate-50 pb-16">
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-9 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-semibold text-emerald-700">
                Tenant Recommendations
              </p>
              <h1 className="mt-2 text-3xl font-bold text-slate-950">
                Recommended Homes for You
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
                Showing your top {response.total_ranked} recommendations, ranked
                using your housing requirements, destinations, commute preferences,
                and priorities.
              </p>
            </div>
            <EditPreferencesLink />
            <HistoryLink />
          </div>

          <section className="mt-7 border-t border-slate-100 pt-5" aria-labelledby="weights-heading">
            <h2 id="weights-heading" className="text-sm font-bold text-slate-900">
              Importance in your ranking
            </h2>
            <div className="mt-3 grid grid-cols-2 gap-x-5 gap-y-3 sm:grid-cols-5">
              {Object.entries(response.normalized_weights).map(([key, value]) => (
                <div key={key}>
                  <div className="flex justify-between text-xs text-slate-600">
                    <span>{WEIGHT_LABELS[key as keyof typeof WEIGHT_LABELS]}</span>
                    <span>{Math.round(value * 100)}%</span>
                  </div>
                  <div className="mt-1 h-1.5 bg-slate-100">
                    <div
                      className="h-full bg-cyan-600"
                      style={{ width: `${Math.round(value * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>

      <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {candidates.map((candidate) => (
          <RecommendationCard key={candidate.id} candidate={candidate} />
        ))}
      </div>
    </main>
  );
}

function StateLayout({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <main className="flex min-h-[70vh] items-center justify-center bg-slate-50 px-4 py-16">
      <section className="w-full max-w-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-slate-950">{title}</h1>
        <div className="mt-3 text-sm leading-6 text-slate-600">{children}</div>
      </section>
    </main>
  );
}

function EditPreferencesLink() {
  return (
    <Link
      href="/tenant/dashboard"
      className="mt-5 inline-flex min-h-11 items-center justify-center border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
    >
      Edit preferences
    </Link>
  );
}

function HistoryLink() {
  return (
    <Link
      href="/tenant/recommendations/history"
      className="mt-5 inline-flex min-h-11 items-center justify-center border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
    >
      Recommendation history
    </Link>
  );
}
