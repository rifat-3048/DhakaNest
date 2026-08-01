"use client";

import type {
  ImportantDestinationPreference,
  PreferenceScore,
} from "@/types/tenant-preference";

interface ImportantDestinationsEditorProps {
  destinations: ImportantDestinationPreference[];
  errorMessage?: string;
  onChange: (destinations: ImportantDestinationPreference[]) => void;
}

function createDestination(): ImportantDestinationPreference {
  return {
    id: crypto.randomUUID(),
    destination: "",
    preference: null,
    max_commute_minutes: null,
  };
}

export default function ImportantDestinationsEditor({
  destinations,
  errorMessage,
  onChange,
}: ImportantDestinationsEditorProps) {
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
    if (destinations.length < 3) {
      onChange([...destinations, createDestination()]);
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
            Add between one and three destinations. Commute time is optional.
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
              <label>
                <span className="text-sm font-medium text-slate-700">
                  Destination <span className="text-red-600">*</span>
                </span>
                <input
                  type="text"
                  value={destination.destination}
                  maxLength={150}
                  placeholder="University of Dhaka"
                  onChange={(event) =>
                    updateDestination(destination.id, {
                      destination: event.target.value,
                    })
                  }
                  className="mt-1 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
                />
              </label>

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
                  <option value="5">5 - Essential</option>
                  <option value="4">4 - Very important</option>
                  <option value="3">3 - Important</option>
                  <option value="2">2 - Somewhat important</option>
                  <option value="1">1 - Low importance</option>
                </select>
              </label>

              <label>
                <span className="text-sm font-medium text-slate-700">
                  Maximum commute <span className="font-normal text-slate-500">(Optional)</span>
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

      {destinations.length < 3 && (
        <button
          type="button"
          onClick={addDestination}
          className="mt-4 rounded-lg border border-emerald-300 bg-white px-4 py-2.5 text-sm font-semibold text-emerald-700 hover:bg-emerald-50"
        >
          + Add another destination
        </button>
      )}
    </div>
  );
}
