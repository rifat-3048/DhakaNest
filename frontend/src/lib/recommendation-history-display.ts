import type {
  RecommendationHistoryListResponse,
  RecommendationRunDetail,
  RecommendationRunSummary,
} from "../types/recommendation.ts";


const currency = new Intl.NumberFormat("en-BD", { maximumFractionDigits: 0 });

export function historyRunsInBackendOrder(
  response: RecommendationHistoryListResponse,
): RecommendationRunSummary[] {
  return [...response.runs];
}

export function historyBudgetSummary(run: RecommendationRunSummary): string {
  const maximum = `BDT ${currency.format(run.maximum_rent_bdt)}`;
  return run.minimum_rent_bdt === null
    ? `Up to ${maximum}`
    : `BDT ${currency.format(run.minimum_rent_bdt)} - ${maximum}`;
}

export function historyState(
  response: RecommendationHistoryListResponse | null,
  hasError: boolean,
): "loading" | "error" | "empty" | "results" {
  if (hasError) return "error";
  if (!response) return "loading";
  return response.runs.length === 0 ? "empty" : "results";
}

export function historicalCandidates(detail: RecommendationRunDetail) {
  return [...detail.results];
}
