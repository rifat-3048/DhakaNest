"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import AdminListingCard from "@/components/admin/AdminListingCard";
import { AdminApiError, getPendingAdminListings } from "@/lib/admin-api";
import type { RentalListing } from "@/types/listing";

export default function AdminDashboardPage() {
  const [listings, setListings] = useState<RentalListing[]>([]);
  const [searchText, setSearchText] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadListings = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await getPendingAdminListings();
      setListings(response.listings);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        setErrorMessage("Your admin session has expired. Log in again.");
      } else if (error instanceof AdminApiError && error.status === 403) {
        setErrorMessage(
          "Your account is authenticated but does not have administrator permission.",
        );
      } else {
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "The pending review queue could not be loaded.",
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadListings();
  }, [loadListings]);

  const filteredListings = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    if (!query) return listings;
    return listings.filter((listing) =>
      [
        listing.id,
        listing.title,
        listing.broad_area,
        listing.model_micro_area,
        listing.address,
        listing.landlord_id,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
  }, [listings, searchText]);

  const statistics = useMemo(
    () => ({
      total: listings.length,
      fairnessPending: listings.filter((listing) => !listing.rent_assessment)
        .length,
      fairnessChecked: listings.filter((listing) => Boolean(listing.rent_assessment))
        .length,
      aboveRange: listings.filter((listing) => {
        const fairness = listing.rent_assessment?.fairness_status;
        return (
          fairness === "above_estimated_range" ||
          fairness === "significantly_above_estimated_range"
        );
      }).length,
    }),
    [listings],
  );

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-emerald-700">
            Administrator Dashboard
          </p>
          <h1 className="mt-1 text-3xl font-bold text-slate-900">
            Listing review queue
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Review landlord submissions, inspect images, run rent fairness, and
            record the final decision.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadListings()}
          disabled={isLoading}
          className="inline-flex min-h-11 items-center justify-center rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
        >
          {isLoading ? "Refreshing..." : "Refresh queue"}
        </button>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          label="Pending listings"
          value={statistics.total}
          description="Awaiting a final decision"
        />
        <SummaryCard
          label="Fairness check required"
          value={statistics.fairnessPending}
          description="Model has not run yet"
        />
        <SummaryCard
          label="Fairness checked"
          value={statistics.fairnessChecked}
          description="Ready for admin review"
        />
        <SummaryCard
          label="Above estimated range"
          value={statistics.aboveRange}
          description="Still requires human judgment"
        />
      </section>

      <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <label>
          <span className="text-sm font-semibold text-slate-800">
            Search the review queue
          </span>
          <input
            type="search"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder="Search by title, listing ID, area, address, or landlord ID"
            className="mt-2 w-full rounded-lg border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
          />
        </label>
      </section>

      {errorMessage && (
        <section className="mt-6 rounded-lg border border-red-200 bg-red-50 p-5">
          <p className="text-sm text-red-700">{errorMessage}</p>
          <button
            type="button"
            onClick={() => void loadListings()}
            className="mt-3 text-sm font-semibold text-red-800 underline"
          >
            Try again
          </button>
        </section>
      )}

      {isLoading ? (
        <section className="mt-8 rounded-lg border bg-white p-12 text-center shadow-sm">
          <p className="text-sm text-slate-600">Loading pending listings...</p>
        </section>
      ) : filteredListings.length === 0 ? (
        <section className="mt-8 rounded-lg border border-dashed bg-white p-12 text-center">
          <h2 className="text-xl font-semibold text-slate-900">
            No pending listings
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {searchText
              ? "No listing matches your search."
              : "The admin review queue is currently empty."}
          </p>
        </section>
      ) : (
        <section className="mt-8 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {filteredListings.map((listing) => (
            <AdminListingCard key={listing.id} listing={listing} />
          ))}
        </section>
      )}
    </main>
  );
}

function SummaryCard({
  label,
  value,
  description,
}: {
  label: string;
  value: number;
  description: string;
}) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
      <p className="mt-2 text-xs text-slate-500">{description}</p>
    </article>
  );
}
