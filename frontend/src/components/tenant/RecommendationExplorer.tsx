"use client";

import { useState } from "react";

import RecommendationCard from "@/components/tenant/RecommendationCard";
import RecommendationMapPanel from "@/components/tenant/RecommendationMapPanel";
import {
  initialRecommendationId,
  recommendationMapDestinations,
  recommendationMapHomes,
} from "@/lib/recommendation-map";
import type { RankedRecommendationCandidate } from "@/types/recommendation";
import type { ImportantDestinationPreference } from "@/types/tenant-preference";


interface RecommendationExplorerProps {
  candidates: RankedRecommendationCandidate[];
  destinations: ImportantDestinationPreference[];
  runId: string | null;
  historical?: boolean;
}

export default function RecommendationExplorer({
  candidates,
  destinations,
  runId,
  historical = false,
}: RecommendationExplorerProps) {
  const [selectedId, setSelectedId] = useState(() => initialRecommendationId(candidates));
  const [hasInteracted, setHasInteracted] = useState(false);
  const homes = recommendationMapHomes(candidates);
  const mapDestinations = recommendationMapDestinations(destinations);

  function selectFromCard(listingId: string) {
    setHasInteracted(true);
    setSelectedId(listingId);
  }

  function selectFromMap(listingId: string) {
    setHasInteracted(true);
    setSelectedId(listingId);
    window.requestAnimationFrame(() => {
      document.getElementById(`recommendation-card-${listingId}`)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
  }

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(380px,0.72fr)]">
      <div className="order-2 space-y-6 lg:order-1">
        {candidates.map((candidate) => (
          <RecommendationCard
            key={candidate.id}
            candidate={candidate}
            detailsHref={historical ? null : undefined}
            selected={candidate.id === selectedId}
            onSelect={() => selectFromCard(candidate.id)}
          />
        ))}
      </div>
      <div className="order-1 lg:sticky lg:top-5 lg:order-2">
        <RecommendationMapPanel
          homes={homes}
          destinations={mapDestinations}
          selectedHomeId={selectedId}
          runId={runId}
          historical={historical}
          focusSelected={hasInteracted}
          onSelectHome={selectFromMap}
        />
      </div>
    </div>
  );
}
