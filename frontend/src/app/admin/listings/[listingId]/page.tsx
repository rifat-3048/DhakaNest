"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import AdminDecisionPanel from "@/components/admin/AdminDecisionPanel";
import AdminImageGallery from "@/components/admin/AdminImageGallery";
import RentFairnessPanel from "@/components/admin/RentFairnessPanel";
import ListingStatusBadge from "@/components/listings/ListingStatusBadge";
import {
  AdminApiError,
  checkListingRentFairness,
  getAdminListing,
  submitAdminListingDecision,
} from "@/lib/admin-api";
import type { AdminDecision, RentalListing } from "@/types/listing";

const currencyFormatter = new Intl.NumberFormat("en-BD", {
  maximumFractionDigits: 0,
});

function formatDate(value: string | null): string {
  if (!value) return "Not specified";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-BD", { dateStyle: "medium" }).format(date);
}

function formatDateTime(value: string | null): string {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-BD", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function humanizeValue(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function AdminListingReviewPage() {
  const params = useParams<{ listingId: string }>();
  const router = useRouter();
  const listingId = params.listingId;
  const [listing, setListing] = useState<RentalListing | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCheckingFairness, setIsCheckingFairness] = useState(false);
  const [isSavingDecision, setIsSavingDecision] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadListing = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      setListing(await getAdminListing(listingId));
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 404) {
        setErrorMessage("The requested listing was not found.");
      } else if (error instanceof AdminApiError && error.status === 403) {
        setErrorMessage("Your account does not have administrator permission.");
      } else {
        setErrorMessage(
          error instanceof Error ? error.message : "The listing could not be loaded.",
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, [listingId]);

  useEffect(() => {
    void loadListing();
  }, [loadListing]);

  async function handleFairnessCheck() {
    if (!listing) return;
    setIsCheckingFairness(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await checkListingRentFairness(listing.id);
      setListing(await getAdminListing(listing.id));
      setSuccessMessage("The rent-fairness assessment was generated and saved.");
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 409) {
        setErrorMessage(
          error.message || "The fairness check is not allowed for this status.",
        );
      } else {
        setErrorMessage(
          error instanceof Error ? error.message : "The rent-fairness check failed.",
        );
      }
    } finally {
      setIsCheckingFairness(false);
    }
  }

  async function handleDecision(decision: AdminDecision, notes: string | null) {
    if (!listing) return;
    setIsSavingDecision(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const response = await submitAdminListingDecision(listing.id, {
        decision,
        notes,
      });
      const fallbackMessages: Record<AdminDecision, string> = {
        approve: "Listing approved successfully.",
        request_revision: "Revision request sent to the landlord.",
        reject: "Listing rejected successfully.",
      };
      setSuccessMessage(response.message ?? fallbackMessages[decision]);
      window.setTimeout(() => {
        router.replace("/admin/dashboard");
        router.refresh();
      }, 1000);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 409) {
        setErrorMessage(
          error.message || "The decision conflicts with the listing's current state.",
        );
      } else if (error instanceof AdminApiError && error.status === 422) {
        setErrorMessage(error.message || "The decision information is incomplete.");
      } else {
        setErrorMessage(
          error instanceof Error ? error.message : "The decision could not be saved.",
        );
      }
    } finally {
      setIsSavingDecision(false);
    }
  }

  if (isLoading) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-16 text-center text-sm text-slate-600">
        Loading listing review...
      </main>
    );
  }

  if (!listing) {
    return (
      <main className="mx-auto max-w-4xl px-4 py-16">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6">
          <h1 className="text-lg font-semibold text-red-900">Listing unavailable</h1>
          <p className="mt-2 text-sm text-red-700">
            {errorMessage ?? "The listing could not be loaded."}
          </p>
          <Link
            href="/admin/dashboard"
            className="mt-5 inline-flex rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white"
          >
            Return to review queue
          </Link>
        </div>
      </main>
    );
  }

  const isPending = listing.status === "pending_review";
  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        href="/admin/dashboard"
        className="text-sm font-medium text-emerald-700 hover:underline"
      >
        Back to review queue
      </Link>

      <div className="mt-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold text-slate-950">Review listing</h1>
            <ListingStatusBadge status={listing.status} />
          </div>
          <p className="mt-2 break-all text-sm text-slate-600">
            Listing ID: {listing.id}
          </p>
          <p className="mt-1 break-all text-sm text-slate-600">
            Landlord ID: {listing.landlord_id}
          </p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <p className="text-xs font-medium uppercase text-slate-500">Submitted</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">
            {formatDateTime(listing.submitted_at)}
          </p>
        </div>
      </div>

      {!isPending && (
        <section className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-5">
          <h2 className="font-semibold text-amber-900">
            This listing is no longer pending
          </h2>
          <p className="mt-2 text-sm text-amber-800">
            The status is <strong>{humanizeValue(listing.status)}</strong>. Review
            actions have been disabled.
          </p>
        </section>
      )}
      {successMessage && (
        <section className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          {successMessage}
        </section>
      )}
      {errorMessage && (
        <section className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {errorMessage}
        </section>
      )}

      <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-8">
          <AdminImageGallery images={listing.images} listingTitle={listing.title} />

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-emerald-700">Submitted property</p>
            <h2 className="mt-1 text-2xl font-semibold text-slate-950">
              {listing.title}
            </h2>
            <p className="mt-4 whitespace-pre-line text-sm leading-7 text-slate-700">
              {listing.description}
            </p>
          </section>

          <RentFairnessPanel
            assessment={listing.rent_assessment}
            askingRentBdt={listing.asking_rent_bdt}
            isChecking={isCheckingFairness}
            disabled={!isPending}
            onCheck={handleFairnessCheck}
          />
          <AdminDecisionPanel
            hasAssessment={Boolean(listing.rent_assessment)}
            isSubmitting={isSavingDecision}
            disabled={!isPending}
            onDecision={handleDecision}
          />
        </div>

        <aside className="space-y-6">
          <DetailSection title="Rental information">
            <SidebarDetail
              label="Asking rent"
              value={`BDT ${currencyFormatter.format(listing.asking_rent_bdt)} per month`}
            />
            <SidebarDetail
              label="Property type"
              value={humanizeValue(listing.property_type)}
            />
            <SidebarDetail
              label="Furnishing"
              value={humanizeValue(listing.furnishing_status)}
            />
            <SidebarDetail
              label="Available from"
              value={formatDate(listing.available_from)}
            />
          </DetailSection>

          <DetailSection title="Property specifications">
            <SidebarDetail
              label="Area"
              value={`${listing.area_sqft.toLocaleString("en-BD")} sq ft`}
            />
            <SidebarDetail label="Bedrooms" value={String(listing.bedrooms)} />
            <SidebarDetail label="Bathrooms" value={String(listing.bathrooms)} />
            <SidebarDetail
              label="Uploaded images"
              value={String(listing.images.length)}
            />
          </DetailSection>

          <DetailSection title="Location">
            <SidebarDetail label="Broad area" value={listing.broad_area} />
            <SidebarDetail label="Model micro-area" value={listing.model_micro_area} />
            <SidebarDetail label="Full address" value={listing.address} />
          </DetailSection>

          <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-950">Amenities</h2>
            {listing.amenities.length === 0 ? (
              <p className="mt-4 text-sm text-slate-500">No amenities listed.</p>
            ) : (
              <div className="mt-4 flex flex-wrap gap-2">
                {listing.amenities.map((amenity) => (
                  <span
                    key={amenity}
                    className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700"
                  >
                    {amenity}
                  </span>
                ))}
              </div>
            )}
          </section>

          <DetailSection title="Record information">
            <SidebarDetail label="Created" value={formatDateTime(listing.created_at)} />
            <SidebarDetail
              label="Last updated"
              value={formatDateTime(listing.updated_at)}
            />
            <SidebarDetail
              label="Available publicly"
              value={listing.is_available ? "Yes" : "No"}
            />
          </DetailSection>
        </aside>
      </div>
    </main>
  );
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
      <dl className="mt-5 space-y-4">{children}</dl>
    </section>
  );
}

function SidebarDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 break-words text-sm font-semibold text-slate-900">
        {value}
      </dd>
    </div>
  );
}
