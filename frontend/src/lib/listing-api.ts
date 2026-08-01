import { getAccessToken } from "@/lib/auth";
import type {
  LandlordListingsResponse,
  ListingCreatePayload,
  ListingImageUploadResponse,
  ListingMutationResponse,
  ListingUpdatePayload,
  RentalListing,
} from "@/types/listing";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export class ApiRequestError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail?: unknown }).detail;

    if (typeof detail === "string") {
      return detail;
    }

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

  return fallback;
}

async function authenticatedRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new ApiRequestError("You are not authenticated.", 401);
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
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiRequestError(
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
    throw new ApiRequestError(
      extractErrorMessage(
        responsePayload,
        `Request failed with status ${response.status}.`,
      ),
      response.status,
    );
  }

  return responsePayload as T;
}

export function createListing(
  payload: ListingCreatePayload,
): Promise<ListingMutationResponse> {
  return authenticatedRequest<ListingMutationResponse>("/api/listings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getMyListings(): Promise<LandlordListingsResponse> {
  return authenticatedRequest<LandlordListingsResponse>("/api/listings/mine");
}

export function getMyListing(listingId: string): Promise<RentalListing> {
  return authenticatedRequest<RentalListing>(`/api/listings/${listingId}`);
}

export function updateListing(
  listingId: string,
  payload: ListingUpdatePayload,
): Promise<ListingMutationResponse> {
  return authenticatedRequest<ListingMutationResponse>(
    `/api/listings/${listingId}`,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
}

export function uploadListingImages(
  listingId: string,
  files: File[],
): Promise<ListingImageUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file, file.name);
  }

  // The browser sets the multipart boundary; do not set Content-Type manually.
  return authenticatedRequest<ListingImageUploadResponse>(
    `/api/listings/${listingId}/images`,
    { method: "POST", body: formData },
  );
}

export function deleteListingImage(
  listingId: string,
  imageId: string,
): Promise<ListingMutationResponse> {
  return authenticatedRequest<ListingMutationResponse>(
    `/api/listings/${listingId}/images/${imageId}`,
    { method: "DELETE" },
  );
}

export function setPrimaryListingImage(
  listingId: string,
  imageId: string,
): Promise<ListingMutationResponse> {
  return authenticatedRequest<ListingMutationResponse>(
    `/api/listings/${listingId}/images/${imageId}/primary`,
    { method: "PATCH" },
  );
}

export function reorderListingImages(
  listingId: string,
  imageIds: string[],
): Promise<ListingMutationResponse> {
  return authenticatedRequest<ListingMutationResponse>(
    `/api/listings/${listingId}/images/reorder`,
    { method: "PATCH", body: JSON.stringify({ image_ids: imageIds }) },
  );
}

export function submitListingForReview(
  listingId: string,
): Promise<ListingMutationResponse> {
  return authenticatedRequest<ListingMutationResponse>(
    `/api/listings/${listingId}/submit`,
    { method: "POST" },
  );
}
