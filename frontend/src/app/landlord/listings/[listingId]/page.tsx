"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import ListingForm from "@/components/listings/ListingForm";
import ListingImageManager from "@/components/listings/ListingImageManager";
import ListingStatusBadge from "@/components/listings/ListingStatusBadge";
import {
  getMyListing,
  submitListingForReview,
  updateListing,
} from "@/lib/listing-api";
import type { ListingFormValues, RentalListing } from "@/types/listing";

export default function LandlordListingPage() {
  const params = useParams<{ listingId: string }>();
  const router = useRouter();
  const listingId = params.listingId;
  const [listing, setListing] = useState<RentalListing | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadListing = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      setListing(await getMyListing(listingId));
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "The listing could not be loaded.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [listingId]);

  useEffect(() => {
    void loadListing();
  }, [loadListing]);

  async function handleUpdate(values: ListingFormValues) {
    if (!listing) return;
    setMessage(null);
    setErrorMessage(null);
    const response = await updateListing(listing.id, values);
    setListing(response.listing);
    setMessage("Listing details saved.");
  }

  async function handleSubmitForReview() {
    if (!listing) return;
    if (
      !window.confirm(
        "Submit this listing for admin review? You cannot edit it while it is pending.",
      )
    ) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setMessage(null);
    try {
      const response = await submitListingForReview(listing.id);
      setListing(response.listing);
      setMessage("Listing submitted for admin review.");
      window.setTimeout(() => router.push("/landlord/dashboard"), 1200);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "The listing could not be submitted.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-16 text-center text-sm text-slate-600">
        Loading listing...
      </main>
    );
  }

  if (!listing) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-16">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
          {errorMessage ?? "Listing not found."}
        </div>
      </main>
    );
  }

  const editable =
    listing.status === "draft" || listing.status === "revision_requested";
  const canSubmit =
    editable &&
    listing.images.length > 0 &&
    listing.images.filter((image) => image.is_primary).length === 1;

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        href="/landlord/dashboard"
        className="text-sm font-medium text-emerald-700 hover:underline"
      >
        Back to dashboard
      </Link>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-bold text-slate-900">
          {editable ? "Edit listing" : "Listing details"}
        </h1>
        <ListingStatusBadge status={listing.status} />
      </div>
      <p className="mt-2 break-all text-sm text-slate-600">
        Listing ID: {listing.id}
      </p>

      <ListingStateNotice listing={listing} />

      {message && (
        <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          {message}
        </div>
      )}
      {errorMessage && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      <div className="mt-8">
        <ListingForm
          key={listing.updated_at}
          initialValues={listing}
          submitLabel="Save listing details"
          readOnly={!editable}
          onSubmit={handleUpdate}
        />
      </div>

      <div className="mt-8">
        <ListingImageManager
          listing={listing}
          editable={editable}
          onListingChanged={setListing}
        />
      </div>

      {editable && (
        <section className="mt-8 rounded-lg border bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            Submit for admin review
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            The listing must contain at least one image and exactly one cover image.
          </p>
          {!canSubmit && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              Upload at least one image before submitting.
            </div>
          )}
          <button
            type="button"
            disabled={!canSubmit || isSubmitting}
            onClick={() => void handleSubmitForReview()}
            className="mt-5 rounded-lg bg-emerald-700 px-6 py-3 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? "Submitting..." : "Submit for admin review"}
          </button>
        </section>
      )}
    </main>
  );
}

function ListingStateNotice({ listing }: { listing: RentalListing }) {
  if (listing.status === "revision_requested") {
    return (
      <section className="mt-6 rounded-lg border border-orange-200 bg-orange-50 p-5">
        <h2 className="font-semibold text-orange-900">Admin requested revisions</h2>
        <p className="mt-2 text-sm text-orange-800">
          {listing.admin_review?.notes ??
            "Review the property information and submit it again."}
        </p>
      </section>
    );
  }
  if (listing.status === "pending_review") {
    return (
      <section className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-5">
        <h2 className="font-semibold text-amber-900">Pending admin review</h2>
        <p className="mt-2 text-sm text-amber-800">
          The property is locked while the admin reviews its details, images, and
          rent fairness.
        </p>
      </section>
    );
  }
  if (listing.status === "approved") {
    return (
      <section className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-5">
        <h2 className="font-semibold text-emerald-900">Listing approved</h2>
        <p className="mt-2 text-sm text-emerald-800">
          This listing completed admin review and is available for recommendations.
        </p>
      </section>
    );
  }
  if (listing.status === "rejected") {
    return (
      <section className="mt-6 rounded-lg border border-red-200 bg-red-50 p-5">
        <h2 className="font-semibold text-red-900">Listing rejected</h2>
        <p className="mt-2 text-sm text-red-800">
          {listing.admin_review?.notes ?? "The listing was not approved."}
        </p>
      </section>
    );
  }
  return null;
}
