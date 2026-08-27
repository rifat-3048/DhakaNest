"use client";

import { divIcon, latLngBounds } from "leaflet";
import { useEffect, useMemo } from "react";
import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";

import { suitabilityPercent } from "@/lib/recommendation-display";
import type {
  RecommendationMapDestination,
  RecommendationMapHome,
} from "@/lib/recommendation-map";
import type { RecommendationRouteGeometryResponse } from "@/types/recommendation";


const currency = new Intl.NumberFormat("en-BD", { maximumFractionDigits: 0 });
const FALLBACK_CENTER: [number, number] = [23.8103, 90.4125];

interface RecommendationMapProps {
  homes: RecommendationMapHome[];
  destinations: RecommendationMapDestination[];
  selectedHomeId: string | null;
  routes: RecommendationRouteGeometryResponse | null;
  focusSelected: boolean;
  onSelectHome: (listingId: string) => void;
  onTileError: () => void;
}

function homeIcon(rank: number, selected: boolean) {
  return divIcon({
    className: "dhakanest-map-icon",
    html: `<span class="dhakanest-home-marker${selected ? " is-selected" : ""}" aria-hidden="true">${rank}</span>`,
    iconSize: selected ? [38, 38] : [32, 32],
    iconAnchor: selected ? [19, 19] : [16, 16],
  });
}

function destinationIcon() {
  return divIcon({
    className: "dhakanest-map-icon",
    html: '<span class="dhakanest-destination-marker" aria-hidden="true">D</span>',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

function MapViewport({
  homes,
  destinations,
  selectedHomeId,
  routes,
  focusSelected,
}: Omit<RecommendationMapProps, "onSelectHome" | "onTileError">) {
  const map = useMap();

  useEffect(() => {
    function fitVisibleLocations() {
      const selected = homes.find((home) => home.id === selectedHomeId);
      const points: [number, number][] = [];
      if (focusSelected && selected) {
        points.push([selected.latitude, selected.longitude]);
        points.push(
          ...destinations.map(
            (destination) =>
              [destination.latitude, destination.longitude] as [number, number],
          ),
        );
        for (const route of routes?.routes ?? []) {
          points.push(
            ...route.geometry.coordinates.map(
              ([longitude, latitude]) => [latitude, longitude] as [number, number],
            ),
          );
        }
      } else {
        points.push(
          ...homes.map((home) => [home.latitude, home.longitude] as [number, number]),
          ...destinations.map(
            (destination) =>
              [destination.latitude, destination.longitude] as [number, number],
          ),
        );
      }

      if (points.length > 1) {
        map.fitBounds(latLngBounds(points), { padding: [46, 46], maxZoom: 15 });
      } else if (points.length === 1) {
        map.setView(points[0], 14);
      }
    }

    fitVisibleLocations();
    map.on("resize", fitVisibleLocations);
    return () => {
      map.off("resize", fitVisibleLocations);
    };
  }, [destinations, focusSelected, homes, map, routes, selectedHomeId]);

  return null;
}

export default function RecommendationMap({
  homes,
  destinations,
  selectedHomeId,
  routes,
  focusSelected,
  onSelectHome,
  onTileError,
}: RecommendationMapProps) {
  const destinationMarkerIcon = useMemo(() => destinationIcon(), []);

  return (
    <MapContainer
      center={FALLBACK_CENTER}
      zoom={11}
      scrollWheelZoom={false}
      className="h-full min-h-80 w-full"
      aria-label="Map of ranked rental homes and important destinations"
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        eventHandlers={{ tileerror: onTileError }}
      />
      <MapViewport
        homes={homes}
        destinations={destinations}
        selectedHomeId={selectedHomeId}
        routes={routes}
        focusSelected={focusSelected}
      />

      {routes?.routes.map((route, index) => (
        <Polyline
          key={route.destination_id}
          positions={route.geometry.coordinates.map(
            ([longitude, latitude]) => [latitude, longitude] as [number, number],
          )}
          pathOptions={{ color: index % 2 === 0 ? "#0891b2" : "#0f766e", weight: 5 }}
        />
      ))}

      {homes.map((home) => {
        const selected = home.id === selectedHomeId;
        const candidate = home.candidate;
        const location =
          candidate.model_micro_area ?? candidate.broad_area ?? candidate.address;
        return (
          <Marker
            key={home.id}
            position={[home.latitude, home.longitude]}
            icon={homeIcon(home.rank, selected)}
            zIndexOffset={selected ? 1000 : 0}
            eventHandlers={{ click: () => onSelectHome(home.id) }}
            title={`Rank ${home.rank}: ${candidate.title ?? "Recommended home"}${selected ? ", selected" : ""}`}
          >
            <Popup>
              <div className="min-w-52 text-sm text-slate-700">
                <strong className="text-base text-slate-950">
                  #{home.rank} {candidate.title ?? "Recommended home"}
                </strong>
                <p className="mt-1">BDT {currency.format(candidate.asking_rent_bdt ?? 0)}/month</p>
                <p>{suitabilityPercent(candidate.final_suitability_score)}% suitability</p>
                <p>{candidate.bedrooms ?? "-"} beds, {candidate.bathrooms ?? "-"} baths, {currency.format(candidate.area_sqft ?? 0)} sq ft</p>
                {location && <p>{location}</p>}
              </div>
            </Popup>
          </Marker>
        );
      })}

      {destinations.map((destination) => (
        <Marker
          key={destination.id}
          position={[destination.latitude, destination.longitude]}
          icon={destinationMarkerIcon}
          title={`Destination: ${destination.label}`}
        >
          <Popup>
            <div className="min-w-44 text-sm text-slate-700">
              <strong className="text-base text-slate-950">{destination.label}</strong>
              <p className="mt-1">Importance: {destination.importance}/5</p>
              <p>{destination.maxCommuteMinutes ? `Maximum commute: ${destination.maxCommuteMinutes} min` : "Flexible commute"}</p>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
