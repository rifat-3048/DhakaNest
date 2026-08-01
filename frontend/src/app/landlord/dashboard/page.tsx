"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import LandlordListingCard from "@/components/listings/LandlordListingCard";
import { ApiRequestError, getMyListings } from "@/lib/listing-api";
import type { ListingStatus, RentalListing } from "@/types/listing";

type ListingFilter = "all" | ListingStatus;

const filters: Array<{ value: ListingFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "draft", label: "Drafts" },
  { value: "pending_review", label: "Pending" },
  { value: "revision_requested", label: "Needs Revision" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export default function LandlordDashboardPage() {
  const [listings, setListings] = useState<RentalListing[]>([]);
  const [activeFilter, setActiveFilter] = useState<ListingFilter>("all");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadListings = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await getMyListings();
      setListings(response.listings);
    } catch (error) {
      if (error instanceof ApiRequestError && error.status === 401) {
        setErrorMessage("Your session has expired. Please log in again.");
      } else {
        setErrorMessage(
          error instanceof Error ? error.message : "Listings could not be loaded.",
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadListings();
  }, [loadListings]);

  const filteredListings = useMemo(
    () =>
      activeFilter === "all"
        ? listings
        : listings.filter((listing) => listing.status === activeFilter),
    [activeFilter, listings],
  );

  const counts = useMemo(
    () => ({
      total: listings.length,
      draft: listings.filter((listing) => listing.status === "draft").length,
      pending: listings.filter((listing) => listing.status === "pending_review")
        .length,
      approved: listings.filter((listing) => listing.status === "approved").length,
      revisions: listings.filter(
        (listing) => listing.status === "revision_requested",
      ).length,
    }),
    [listings],
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-emerald-700">Landlord Dashboard</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-900">
            Your rental listings
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Create properties, upload images, and track admin review progress.
          </p>
        </div>
        <Link
          href="/landlord/listings/new"
          className="inline-flex min-h-11 items-center justify-center rounded-lg bg-emerald-700 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-800"
        >
          Add new listing
        </Link>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <SummaryCard label="Total listings" value={counts.total} />
        <SummaryCard label="Drafts" value={counts.draft} />
        <SummaryCard label="Pending review" value={counts.pending} />
        <SummaryCard label="Needs revision" value={counts.revisions} />
        <SummaryCard label="Approved" value={counts.approved} />
      </section>

      <div className="mt-8 flex flex-wrap gap-2" role="group" aria-label="Filter listings">
        {filters.map((filter) => (
          <button
            key={filter.value}
            type="button"
            onClick={() => setActiveFilter(filter.value)}
            className={[
              "rounded-full px-4 py-2 text-sm font-medium transition",
              activeFilter === filter.value
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-700 shadow-sm hover:bg-slate-100",
            ].join(" ")}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {errorMessage && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {errorMessage}
          <button
            type="button"
            onClick={() => void loadListings()}
            className="ml-3 font-semibold underline"
          >
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="mt-8 rounded-lg border bg-white p-10 text-center text-sm text-slate-600">
          Loading your listings...
        </div>
      ) : filteredListings.length === 0 ? (
        <div className="mt-8 rounded-lg border border-dashed bg-white p-12 text-center">
          <h2 className="text-lg font-semibold text-slate-900">No listings found</h2>
          <p className="mt-2 text-sm text-slate-600">
            Create your first draft property listing.
          </p>
          <Link
            href="/landlord/listings/new"
            className="mt-5 inline-flex rounded-lg bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"
          >
            Create listing
          </Link>
        </div>
      ) : (
        <section className="mt-8 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {filteredListings.map((listing) => (
            <LandlordListingCard key={listing.id} listing={listing} />
          ))}
        </section>
      )}
    </main>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <article className="rounded-lg border bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-600">{label}</p>
      <p className="mt-2 text-3xl font-bold text-slate-900">{value}</p>
    </article>
  );
}
