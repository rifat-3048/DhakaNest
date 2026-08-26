"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { clearStoredAuth } from "@/lib/auth";
import {
  getRecommendationHistory,
  RecommendationApiError,
} from "@/lib/recommendation-api";
import {
  historyBudgetSummary,
  historyRunsInBackendOrder,
} from "@/lib/recommendation-history-display";
import { suitabilityPercent } from "@/lib/recommendation-display";
import type { RecommendationHistoryListResponse } from "@/types/recommendation";


const generatedDate = new Intl.DateTimeFormat("en-BD", {
  dateStyle: "long",
  timeStyle: "short",
});

export default function RecommendationHistory() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [response, setResponse] =
    useState<RecommendationHistoryListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    async function loadHistory() {
      await Promise.resolve();
      setIsLoading(true);
      setHasError(false);
      try {
        const result = await getRecommendationHistory(page, 10, {
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setResponse(result);
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
        if (!controller.signal.aborted) setHasError(true);
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }
    void loadHistory();
    return () => controller.abort();
  }, [page, retry, router]);

  if (isLoading) {
    return <HistoryState title="Loading recommendation history..." />;
  }
  if (hasError) {
    return (
      <HistoryState title="We couldn't load your recommendation history.">
        <p>Please try again.</p>
        <button
          type="button"
          onClick={() => setRetry((value) => value + 1)}
          className="mt-5 min-h-11 bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white"
        >
          Try again
        </button>
      </HistoryState>
    );
  }
  if (!response || response.runs.length === 0) {
    return (
      <HistoryState title="You haven't generated any recommendation searches yet.">
        <Link
          href="/tenant/dashboard"
          className="mt-5 inline-flex min-h-11 items-center bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white"
        >
          Find recommended homes
        </Link>
      </HistoryState>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 pb-16">
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-9 sm:px-6 lg:px-8">
          <p className="text-sm font-semibold text-emerald-700">Tenant History</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-950">
            Recommendation History
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            Reopen the exact homes, scores, and commute estimates saved when
            each search was generated.
          </p>
        </div>
      </section>

      <div className="mx-auto max-w-5xl space-y-5 px-4 py-8 sm:px-6 lg:px-8">
        {historyRunsInBackendOrder(response).map((run) => (
          <article
            key={run.run_id}
            className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
          >
            <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_220px]">
              <div>
                <time className="text-sm font-semibold text-emerald-700">
                  {generatedDate.format(new Date(run.created_at))}
                </time>
                <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
                  <HistoryFact
                    label="Destinations"
                    value={run.destination_labels.join(", ")}
                  />
                  <HistoryFact label="Budget" value={historyBudgetSummary(run)} />
                  <HistoryFact
                    label="Recommendations"
                    value={`${run.recommendation_count} homes`}
                  />
                  <HistoryFact
                    label="Top match"
                    value={run.top_recommendation?.title ?? "No matching homes"}
                  />
                </dl>
              </div>
              <div className="flex flex-col justify-between border-t border-slate-100 pt-4 md:border-l md:border-t-0 md:pl-5 md:pt-0">
                <div>
                  {run.top_recommendation && (
                    <>
                      <strong className="text-3xl text-slate-950">
                        {suitabilityPercent(
                          run.top_recommendation.final_suitability_score,
                        )}%
                      </strong>
                      <p className="text-xs font-semibold uppercase text-slate-500">
                        Top suitability
                      </p>
                    </>
                  )}
                </div>
                <Link
                  href={`/tenant/recommendations/history/${encodeURIComponent(run.run_id)}`}
                  className="mt-5 inline-flex min-h-11 items-center justify-center bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white"
                >
                  View results
                </Link>
              </div>
            </div>
          </article>
        ))}

        {response.total_pages > 1 && (
          <nav className="flex items-center justify-between pt-3" aria-label="History pages">
            <button
              type="button"
              disabled={page === 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              className="min-h-11 border border-slate-300 bg-white px-4 text-sm font-semibold disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-sm text-slate-600">
              Page {response.page} of {response.total_pages}
            </span>
            <button
              type="button"
              disabled={page >= response.total_pages}
              onClick={() => setPage((value) => value + 1)}
              className="min-h-11 border border-slate-300 bg-white px-4 text-sm font-semibold disabled:opacity-40"
            >
              Next
            </button>
          </nav>
        )}
      </div>
    </main>
  );
}

function HistoryFact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 leading-6 text-slate-800">{value}</dd>
    </div>
  );
}

function HistoryState({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <main className="flex min-h-[70vh] items-center justify-center bg-slate-50 px-4 py-16">
      <section className="w-full max-w-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-slate-950">{title}</h1>
        <div className="mt-3 text-sm text-slate-600">{children}</div>
      </section>
    </main>
  );
}
