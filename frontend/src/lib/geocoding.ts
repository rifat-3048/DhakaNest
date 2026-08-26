export interface GeocodingResult {
  id: string;
  label: string;
  latitude: number;
  longitude: number;
}

interface NominatimResult {
  place_id?: number | string;
  osm_id?: number | string;
  osm_type?: string;
  display_name?: string;
  lat?: string;
  lon?: string;
}

const NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search";
const MINIMUM_QUERY_LENGTH = 3;
const REQUEST_INTERVAL_MS = 1_050;
const REQUEST_TIMEOUT_MS = 10_000;
const resultCache = new Map<string, GeocodingResult[]>();

let requestQueue: Promise<void> = Promise.resolve();
let lastRequestStartedAt = 0;

export class GeocodingError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "GeocodingError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isCoordinateInRange(
  value: number,
  minimum: number,
  maximum: number,
): boolean {
  return Number.isFinite(value) && value >= minimum && value <= maximum;
}

export function normalizeGeocodingResponse(value: unknown): GeocodingResult[] {
  if (!Array.isArray(value)) return [];

  return value.flatMap((item): GeocodingResult[] => {
    if (!isRecord(item)) return [];

    const providerItem = item as NominatimResult;
    if (
      typeof providerItem.lat !== "string" ||
      typeof providerItem.lon !== "string"
    ) {
      return [];
    }
    const latitude = Number(providerItem.lat);
    const longitude = Number(providerItem.lon);
    const label = providerItem.display_name?.trim();
    const providerId =
      providerItem.osm_id ?? providerItem.place_id ?? `${latitude}-${longitude}`;

    if (
      !label ||
      !isCoordinateInRange(latitude, -90, 90) ||
      !isCoordinateInRange(longitude, -180, 180)
    ) {
      return [];
    }

    return [
      {
        id: `${providerItem.osm_type ?? "place"}-${providerId}`,
        label,
        latitude,
        longitude,
      },
    ];
  });
}

function wait(delayMs: number, signal?: AbortSignal): Promise<void> {
  if (delayMs <= 0) return Promise.resolve();

  return new Promise((resolve, reject) => {
    const timeoutId = window.setTimeout(resolve, delayMs);

    signal?.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timeoutId);
        reject(new DOMException("Search cancelled.", "AbortError"));
      },
      { once: true },
    );
  });
}

function enqueueRequest<T>(request: () => Promise<T>): Promise<T> {
  const result = requestQueue.then(request, request);
  requestQueue = result.then(
    () => undefined,
    () => undefined,
  );
  return result;
}

export async function searchDhakaDestinations(
  query: string,
  signal?: AbortSignal,
): Promise<GeocodingResult[]> {
  const trimmedQuery = query.trim();
  if (trimmedQuery.length < MINIMUM_QUERY_LENGTH) {
    throw new GeocodingError(
      `Enter at least ${MINIMUM_QUERY_LENGTH} characters before searching.`,
    );
  }

  const cacheKey = trimmedQuery.toLowerCase();
  const cached = resultCache.get(cacheKey);
  if (cached) return cached.map((result) => ({ ...result }));

  return enqueueRequest(async () => {
    if (signal?.aborted) {
      throw new DOMException("Search cancelled.", "AbortError");
    }

    const elapsed = Date.now() - lastRequestStartedAt;
    await wait(Math.max(0, REQUEST_INTERVAL_MS - elapsed), signal);
    lastRequestStartedAt = Date.now();

    const parameters = new URLSearchParams({
      q: trimmedQuery,
      format: "jsonv2",
      limit: "5",
      countrycodes: "bd",
      // Bias toward Dhaka while allowing legitimate nearby Bangladesh results.
      viewbox: "90.28,23.95,90.55,23.63",
      bounded: "0",
      "accept-language": "en",
    });
    const timeoutController = new AbortController();
    const timeoutId = window.setTimeout(
      () => timeoutController.abort(),
      REQUEST_TIMEOUT_MS,
    );
    const combinedSignal = signal
      ? AbortSignal.any([signal, timeoutController.signal])
      : timeoutController.signal;

    try {
      const response = await fetch(`${NOMINATIM_SEARCH_URL}?${parameters}`, {
        headers: { Accept: "application/json" },
        referrerPolicy: "strict-origin-when-cross-origin",
        signal: combinedSignal,
      });

      if (!response.ok) {
        throw new GeocodingError(
          "Destination search is temporarily unavailable. Please try again.",
        );
      }

      const results = normalizeGeocodingResponse(await response.json());
      resultCache.set(cacheKey, results);
      return results.map((result) => ({ ...result }));
    } catch (error) {
      if (signal?.aborted) throw error;
      if (timeoutController.signal.aborted) {
        throw new GeocodingError(
          "Destination search timed out. Please try again.",
        );
      }
      if (error instanceof GeocodingError) throw error;
      throw new GeocodingError(
        "Could not search for destinations. Check your connection and try again.",
      );
    } finally {
      window.clearTimeout(timeoutId);
    }
  });
}
