import { getAccessToken } from "@/lib/auth";
import type {
  AdminActionResponse,
  AdminDecisionPayload,
  AdminListingsQuery,
  AdminListingsResponse,
  AdminPendingListingsResponse,
  RentalListing,
} from "@/types/listing";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export class AdminApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown = null) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
    this.detail = detail;
  }
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return String(item);
        })
        .join(" ");
    }
  }

  if (
    typeof payload === "object" &&
    payload !== null &&
    "message" in payload &&
    typeof (payload as { message?: unknown }).message === "string"
  ) {
    return String((payload as { message: string }).message);
  }
  return fallback;
}

async function adminRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new AdminApiError("You are not authenticated.", 401);
  }

  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${accessToken}`);
  if (
    init.body &&
    !(init.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new AdminApiError(
      `Cannot connect to the backend API at ${API_BASE_URL}.`,
      0,
    );
  }

  const responseText = await response.text();
  let responsePayload: unknown = null;
  if (responseText) {
    try {
      responsePayload = JSON.parse(responseText);
    } catch {
      responsePayload = responseText;
    }
  }

  if (!response.ok) {
    throw new AdminApiError(
      extractErrorMessage(
        responsePayload,
        `Request failed with status ${response.status}.`,
      ),
      response.status,
      responsePayload,
    );
  }
  return responsePayload as T;
}

function normalizePendingResponse(payload: unknown): AdminPendingListingsResponse {
  if (Array.isArray(payload)) {
    return { count: payload.length, listings: payload as RentalListing[] };
  }

  if (typeof payload === "object" && payload !== null) {
    const record = payload as Record<string, unknown>;
    const possibleListings = record.listings ?? record.items ?? record.results;
    if (Array.isArray(possibleListings)) {
      return {
        count: typeof record.count === "number" ? record.count : possibleListings.length,
        listings: possibleListings as RentalListing[],
      };
    }
  }
  throw new AdminApiError(
    "The pending-listings response has an unexpected format.",
    500,
    payload,
  );
}

function normalizeListingResponse(payload: unknown): RentalListing {
  if (typeof payload !== "object" || payload === null) {
    throw new AdminApiError(
      "The listing response has an unexpected format.",
      500,
      payload,
    );
  }

  const record = payload as Record<string, unknown>;
  if (typeof record.listing === "object" && record.listing !== null) {
    return record.listing as RentalListing;
  }
  if (typeof record.id === "string") {
    return record as unknown as RentalListing;
  }
  throw new AdminApiError(
    "The listing response does not contain a listing.",
    500,
    payload,
  );
}

export async function getPendingAdminListings(): Promise<AdminPendingListingsResponse> {
  return normalizePendingResponse(
    await adminRequest<unknown>("/api/admin/listings/pending"),
  );
}

export async function getAdminListings(
  options: AdminListingsQuery = {},
): Promise<AdminListingsResponse> {
  const query = new URLSearchParams();
  query.set("status", options.status ?? "all");
  query.set("skip", String(options.skip ?? 0));
  query.set("limit", String(options.limit ?? 100));

  const cleanedSearch = options.search?.trim();
  if (cleanedSearch) query.set("search", cleanedSearch);

  return adminRequest<AdminListingsResponse>(
    `/api/admin/listings?${query.toString()}`,
  );
}

export async function getAdminListing(listingId: string): Promise<RentalListing> {
  return normalizeListingResponse(
    await adminRequest<unknown>(`/api/admin/listings/${listingId}`),
  );
}

export function checkListingRentFairness(
  listingId: string,
): Promise<AdminActionResponse> {
  return adminRequest<AdminActionResponse>(
    `/api/admin/listings/${listingId}/check-rent-fairness`,
    { method: "POST" },
  );
}

export function submitAdminListingDecision(
  listingId: string,
  payload: AdminDecisionPayload,
): Promise<AdminActionResponse> {
  return adminRequest<AdminActionResponse>(
    `/api/admin/listings/${listingId}/decision`,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
}
