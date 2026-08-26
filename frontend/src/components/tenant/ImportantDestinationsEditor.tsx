"use client";

import { type KeyboardEvent, useEffect, useRef, useState } from "react";

import {
  GeocodingError,
  type GeocodingResult,
  searchDhakaDestinations,
} from "@/lib/geocoding";
import {
  applyDestinationSelection,
  canAddDestination,
  createImportantDestination,
  hasResolvedCoordinates,
  updateDestinationSearchText,
} from "@/lib/tenant-destination";
import type {
  ImportantDestinationPreference,
  PreferenceScore,
} from "@/types/tenant-preference";

interface ImportantDestinationsEditorProps {
  destinations: ImportantDestinationPreference[];
  errorMessage?: string;
  onChange: (destinations: ImportantDestinationPreference[]) => void;
}

export default function ImportantDestinationsEditor({
  destinations,
  errorMessage,
  onChange,
}: ImportantDestinationsEditorProps) {
  function replaceDestination(updated: ImportantDestinationPreference) {
    onChange(
      destinations.map((destination) =>
        destination.id === updated.id ? updated : destination,
      ),
    );
  }

  function updateDestination(
    id: string,
    updates: Partial<ImportantDestinationPreference>,
  ) {
    onChange(
      destinations.map((destination) =>
        destination.id === id ? { ...destination, ...updates } : destination,
      ),
    );
  }

  function addDestination() {
    if (canAddDestination(destinations.length)) {
      onChange([
        ...destinations,
        createImportantDestination(crypto.randomUUID()),
      ]);
    }
  }

  function removeDestination(id: string) {
    if (destinations.length > 1) {
      onChange(destinations.filter((destination) => destination.id !== id));
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            Important destinations <span className="text-red-600">*</span>
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            Search and select one to three real places. Commute time is optional.
          </p>
        </div>
        <span className="text-xs font-semibold text-emerald-700">
          {destinations.length}/3
        </span>
      </div>

      {errorMessage && (
        <div
          className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          {errorMessage}
        </div>
      )}

      <div className="mt-4 space-y-4">
        {destinations.map((destination, index) => (
          <article
            key={destination.id}
            className="rounded-lg border border-slate-200 bg-slate-50 p-4"
          >
            <div className="flex items-center justify-between gap-3">
              <h4 className="text-sm font-semibold text-slate-900">
                Destination {index + 1}
              </h4>
              {destinations.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeDestination(destination.id)}
                  className="text-xs font-semibold text-red-700 hover:underline"
                >
                  Remove
                </button>
              )}
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_180px_200px]">
              <DestinationSearchField
                destination={destination}
                onChange={replaceDestination}
              />

              <label>
                <span className="text-sm font-medium text-slate-700">
                  Importance <span className="text-red-600">*</span>
                </span>
                <select
                  value={destination.preference ?? ""}
                  onChange={(event) =>
                    updateDestination(destination.id, {
                      preference: event.target.value
                        ? (Number(event.target.value) as PreferenceScore)
                        : null,
                    })
                  }
                  className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                >
                  <option value="">Select</option>
                  <option value="5">5 - Very important</option>
                  <option value="4">4 - High importance</option>
                  <option value="3">3 - Medium</option>
                  <option value="2">2 - Somewhat important</option>
                  <option value="1">1 - Low importance</option>
                </select>
              </label>

              <label>
                <span className="text-sm font-medium text-slate-700">
                  Maximum commute{" "}
                  <span className="font-normal text-slate-500">(Optional)</span>
                </span>
                <div className="relative mt-1">
                  <input
                    type="number"
                    min={1}
                    max={240}
                    step={1}
                    value={destination.max_commute_minutes ?? ""}
                    placeholder="30"
                    onChange={(event) =>
                      updateDestination(destination.id, {
                        max_commute_minutes:
                          event.target.value === ""
                            ? null
                            : Number(event.target.value),
                      })
                    }
                    className="min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 pr-16 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                  />
                  <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500">
                    minutes
                  </span>
                </div>
              </label>
            </div>
          </article>
        ))}
      </div>

      {canAddDestination(destinations.length) && (
        <button
          type="button"
          onClick={addDestination}
          className="mt-4 rounded-lg border border-emerald-300 bg-white px-4 py-2.5 text-sm font-semibold text-emerald-700 hover:bg-emerald-50"
        >
          + Add another destination
        </button>
      )}

      <p className="mt-4 text-xs text-slate-500">
        Search data ©{" "}
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer"
          className="font-medium text-emerald-700 hover:underline"
        >
          OpenStreetMap contributors
        </a>
      </p>
    </div>
  );
}

function DestinationSearchField({
  destination,
  onChange,
}: {
  destination: ImportantDestinationPreference;
  onChange: (destination: ImportantDestinationPreference) => void;
}) {
  const [results, setResults] = useState<GeocodingResult[]>([]);
  const [searchMessage, setSearchMessage] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const requestController = useRef<AbortController | null>(null);
  const requestNumber = useRef(0);
  const resultsId = `destination-results-${destination.id}`;
  const isResolved = hasResolvedCoordinates(destination);

  useEffect(
    () => () => {
      requestController.current?.abort();
    },
    [],
  );

  function handleTextChange(value: string) {
    requestController.current?.abort();
    requestNumber.current += 1;
    setResults([]);
    setHasSearched(false);
    setSearchMessage(null);
    setIsSearching(false);
    onChange(updateDestinationSearchText(destination, value));
  }

  async function handleSearch() {
    const query = destination.destination.trim();
    if (query.length < 3) {
      setResults([]);
      setHasSearched(true);
      setSearchMessage("Enter at least 3 characters before searching.");
      return;
    }

    requestController.current?.abort();
    const controller = new AbortController();
    const currentRequest = requestNumber.current + 1;
    requestNumber.current = currentRequest;
    requestController.current = controller;
    setIsSearching(true);
    setHasSearched(false);
    setSearchMessage(null);
    setResults([]);

    try {
      const searchResults = await searchDhakaDestinations(
        query,
        controller.signal,
      );
      if (currentRequest !== requestNumber.current) return;
      setResults(searchResults);
      setHasSearched(true);
    } catch (error) {
      if (controller.signal.aborted || currentRequest !== requestNumber.current) {
        return;
      }
      setHasSearched(true);
      setSearchMessage(
        error instanceof GeocodingError
          ? error.message
          : "Could not search for destinations. Please try again.",
      );
    } finally {
      if (currentRequest === requestNumber.current) setIsSearching(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      void handleSearch();
    }
  }

  function handleSelection(result: GeocodingResult) {
    requestController.current?.abort();
    requestNumber.current += 1;
    setResults([]);
    setHasSearched(false);
    setSearchMessage(null);
    setIsSearching(false);
    onChange(applyDestinationSelection(destination, result));
  }

  return (
    <div>
      <label htmlFor={`destination-${destination.id}`}>
        <span className="text-sm font-medium text-slate-700">
          Search destination <span className="text-red-600">*</span>
        </span>
      </label>
      <div className="mt-1 flex gap-2">
        <input
          id={`destination-${destination.id}`}
          type="text"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={results.length > 0}
          aria-controls={resultsId}
          value={destination.destination}
          maxLength={150}
          placeholder="University of Dhaka"
          onChange={(event) => handleTextChange(event.target.value)}
          onKeyDown={handleKeyDown}
          className="min-h-11 min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
        />
        <button
          type="button"
          onClick={() => void handleSearch()}
          disabled={isSearching || destination.destination.trim().length < 3}
          className="min-h-11 shrink-0 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSearching ? "Searching..." : "Search"}
        </button>
      </div>

      {isResolved ? (
        <p className="mt-2 text-xs font-medium text-emerald-700">
          Selected place ready for future commute calculations.
        </p>
      ) : destination.destination.trim() ? (
        <p className="mt-2 text-xs font-medium text-amber-700">
          Select a search result to confirm this destination.
        </p>
      ) : null}

      {searchMessage && (
        <p className="mt-2 text-xs font-medium text-red-700" role="alert">
          {searchMessage}
        </p>
      )}
      {hasSearched && !searchMessage && results.length === 0 && (
        <p className="mt-2 text-xs text-slate-600" role="status">
          No matching places found in Bangladesh. Try a more specific name.
        </p>
      )}

      {results.length > 0 && (
        <ul
          id={resultsId}
          role="listbox"
          aria-label="Destination search results"
          className="mt-2 max-h-64 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-sm"
        >
          {results.map((result) => (
            <li key={result.id} role="none">
              <button
                type="button"
                role="option"
                aria-selected="false"
                onClick={() => handleSelection(result)}
                className="w-full border-b border-slate-100 px-3 py-3 text-left text-sm text-slate-800 last:border-b-0 hover:bg-emerald-50 focus:bg-emerald-50 focus:outline-none"
              >
                {result.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
