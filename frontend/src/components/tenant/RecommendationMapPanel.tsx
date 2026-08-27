"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { suitabilityPercent } from "@/lib/recommendation-display";
import {
  getRecommendationRouteGeometry,
  RecommendationApiError,
} from "@/lib/recommendation-api";
import {
  isLatestRouteRequest,
  RecommendationRouteCache,
  type RecommendationMapDestination,
  type RecommendationMapHome,
} from "@/lib/recommendation-map";
import type { RecommendationRouteGeometryResponse } from "@/types/recommendation";


const InteractiveMap = dynamic(() => import("./RecommendationMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-80 items-center justify-center bg-slate-100 text-sm text-slate-600">
      Loading interactive map...
    </div>
  ),
});
const routeCache = new RecommendationRouteCache();
const currency = new Intl.NumberFormat("en-BD", { maximumFractionDigits: 0 });

interface RecommendationMapPanelProps {
  homes: RecommendationMapHome[];
  destinations: RecommendationMapDestination[];
  selectedHomeId: string | null;
  runId: string | null;
  historical: boolean;
  focusSelected: boolean;
  onSelectHome: (listingId: string) => void;
}

export default function RecommendationMapPanel({
  homes,
  destinations,
  selectedHomeId,
  runId,
  historical,
  focusSelected,
  onSelectHome,
}: RecommendationMapPanelProps) {
  const [routes, setRoutes] = useState<RecommendationRouteGeometryResponse | null>(null);
  const [routeState, setRouteState] = useState<"idle" | "loading" | "ready" | "partial" | "rate_limited" | "unavailable">("idle");
  const [tileFailed, setTileFailed] = useState(false);
  const latestRequest = useRef(0);
  const selected = homes.find((home) => home.id === selectedHomeId) ?? null;

  useEffect(() => {
    const requestNumber = ++latestRequest.current;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      setRoutes(null);
      if (!selectedHomeId || !selected) {
        setRouteState("idle");
        return;
      }
      if (!runId) {
        setRouteState("unavailable");
        return;
      }
      const cached = routeCache.get(runId, selectedHomeId);
      if (cached) {
        setRoutes(cached);
        setRouteState(
          cached.unavailable_destination_ids.length ? "partial" : "ready",
        );
        return;
      }

      setRouteState("loading");
      void getRecommendationRouteGeometry(runId, selectedHomeId, {
        signal: controller.signal,
      }).then((result) => {
        if (!isLatestRouteRequest(requestNumber, latestRequest.current)) return;
        routeCache.set(result);
        setRoutes(result);
        setRouteState(result.unavailable_destination_ids.length ? "partial" : "ready");
      }).catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (isLatestRouteRequest(requestNumber, latestRequest.current)) {
          setRouteState(
            error instanceof RecommendationApiError &&
              error.kind === "rate_limited"
              ? "rate_limited"
              : "unavailable",
          );
        }
      });
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [runId, selected, selectedHomeId]);

  if (homes.length === 0) {
    return (
      <section className="border border-slate-200 bg-white p-6" aria-label="Recommendation map status">
        <h2 className="font-bold text-slate-950">Recommendation map</h2>
        <p className="mt-2 text-sm text-slate-600">
          Map location unavailable for this historical result.
        </p>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm" aria-labelledby="recommendation-map-heading">
      <div className="border-b border-slate-200 p-4">
        <p className="text-xs font-semibold uppercase text-emerald-700">
          {historical ? "Saved-run map" : "Recommendation map"}
        </p>
        <h2 id="recommendation-map-heading" className="mt-1 font-bold text-slate-950">
          Homes and important destinations
        </h2>
        {historical && (
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Based on locations saved with this recommendation run.
          </p>
        )}
      </div>

      <div className="relative h-[360px] sm:h-[430px] lg:h-[min(58vh,560px)]">
        <InteractiveMap
          homes={homes}
          destinations={destinations}
          selectedHomeId={selectedHomeId}
          routes={routes}
          focusSelected={focusSelected}
          onSelectHome={onSelectHome}
          onTileError={() => setTileFailed(true)}
        />
        {tileFailed && (
          <p className="absolute bottom-2 left-2 z-[500] bg-white/95 px-3 py-2 text-xs text-slate-700 shadow">
            Map tiles are temporarily unavailable. Results remain accessible below.
          </p>
        )}
      </div>

      {selectedHomeId && !selected && (
        <p className="border-t border-slate-200 p-4 text-sm text-slate-600" role="status">
          Map location unavailable for the selected recommendation. Other valid
          homes and destinations remain visible.
        </p>
      )}

      {selected && (
        <div className="border-t border-slate-200 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-bold text-slate-950">
                #{selected.rank} {selected.candidate.title ?? "Recommended home"}
              </p>
              <p className="mt-1 text-sm text-slate-600">
                {suitabilityPercent(selected.candidate.final_suitability_score)}% suitability · BDT {currency.format(selected.candidate.asking_rent_bdt ?? 0)}/month
              </p>
            </div>
            {!historical && (
              <Link href={`/tenant/recommendations/${encodeURIComponent(selected.id)}`} className="shrink-0 text-sm font-semibold text-emerald-700">
                View details
              </Link>
            )}
          </div>

          <div className="mt-4 space-y-3">
            {selected.candidate.commutes.map((commute) => (
              <div key={commute.destination_id} className="border-l-2 border-cyan-600 pl-3 text-xs text-slate-600">
                <p className="font-semibold text-slate-900">{commute.destination}</p>
                <p className="mt-1">Estimated drive: {commute.estimated_duration_minutes.toFixed(1)} min · Road distance: {commute.distance_km.toFixed(1)} km</p>
                <p className="mt-1">Maximum commute: {commute.max_commute_minutes ? `${commute.max_commute_minutes} min` : "Flexible"}</p>
              </div>
            ))}
          </div>

          <p className="mt-4 text-xs leading-5 text-slate-500" role="status">
            {routeState === "loading" && "Loading road route visualization..."}
            {routeState === "partial" && "Some road routes are unavailable; available routes are shown."}
            {routeState === "unavailable" && (runId ? "Road route visualization is temporarily unavailable." : "Route visualization is unavailable for this result.")}
            {routeState === "rate_limited" && "Route visualization is being requested too frequently. Please try again shortly."}
            {routeState === "ready" && "Road routes shown for the selected home."}
          </p>
        </div>
      )}
    </section>
  );
}
