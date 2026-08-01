"use client";

import { useCallback, useEffect, useState } from "react";

import AdminListingCard from "@/components/admin/AdminListingCard";
import { AdminApiError, getAdminListings } from "@/lib/admin-api";
import type {
  AdminListingFilter,
  AdminListingSummary,
  RentalListing,
} from "@/types/listing";

const EMPTY_SUMMARY: AdminListingSummary = {
  all_listings: 0,
  pending_review: 0,
  approved: 0,
  revision_requested: 0,
  rejected: 0,
  fairness_check_required: 0,
  fairness_checked: 0,
  above_estimated_range: 0,
};

type StatusCountKey =
  | "all_listings"
  | "pending_review"
  | "approved"
  | "revision_requested"
  | "rejected";

interface StatusFilterOption {
  value: AdminListingFilter;
  label: string;
  description: string;
  countKey: StatusCountKey;
}

const STATUS_FILTERS: StatusFilterOption[] = [
  {
    value: "all",
    label: "All Listings",
    description: "Every listing status",
    countKey: "all_listings",
  },
  {
    value: "pending_review",
    label: "Pending Review",
    description: "Awaiting admin decision",
    countKey: "pending_review",
  },
  {
    value: "approved",
    label: "Approved",
    description: "Available listings",
    countKey: "approved",
  },
  {
    value: "revision_requested",
    label: "Needs Revision",
    description: "Returned to landlords",
    countKey: "revision_requested",
  },
  {
    value: "rejected",
    label: "Rejected",
    description: "Not approved",
    countKey: "rejected",
  },
];

export default function AdminDashboardPage() {
  const [activeStatus, setActiveStatus] = useState<AdminListingFilter>("all");
  const [searchText, setSearchText] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [listings, setListings] = useState<RentalListing[]>([]);
  const [summary, setSummary] =
    useState<AdminListingSummary>(EMPTY_SUMMARY);
  const [currentCount, setCurrentCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Wait briefly before searching so typing does not send a request per keypress.
  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearch(searchText.trim());
    }, 300);

    return () => window.clearTimeout(timeoutId);
  }, [searchText]);

  const loadListings = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await getAdminListings({
        status: activeStatus,
        search: debouncedSearch,
        skip: 0,
        limit: 100,
      });
      setListings(response.listings);
      setSummary(response.summary);
      setCurrentCount(response.count);
    } catch (error) {
      if (error instanceof AdminApiError && error.status === 401) {
        setErrorMessage("Your admin session has expired. Please log in again.");
      } else if (error instanceof AdminApiError && error.status === 403) {
        setErrorMessage(
          "Your account does not have administrator permission.",
        );
      } else {
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "The listings could not be loaded.",
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, [activeStatus, debouncedSearch]);

  useEffect(() => {
    void loadListings();
  }, [loadListings]);

  const activeFilter =
    STATUS_FILTERS.find((filter) => filter.value === activeStatus) ??
    STATUS_FILTERS[0];

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-emerald-700">
            Administrator Dashboard
          </p>
          <h1 className="mt-1 text-3xl font-bold text-slate-900">
            Listing management
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            Review pending submissions and inspect approved,
            revision-requested, and rejected listings.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadListings()}
          disabled={isLoading}
          className="inline-flex min-h-11 items-center justify-center rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
        >
          {isLoading ? "Refreshing..." : "Refresh listings"}
        </button>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          label="Pending listings"
          value={summary.pending_review}
          description="Awaiting a final decision"
        />
        <SummaryCard
          label="Fairness check required"
          value={summary.fairness_check_required}
          description="Model has not run yet"
        />
        <SummaryCard
          label="Fairness checked"
          value={summary.fairness_checked}
          description="Ready for admin review"
        />
        <SummaryCard
          label="Above estimated range"
          value={summary.above_estimated_range}
          description="Still requires human judgment"
        />
      </section>

      <section className="mt-8 border-y border-slate-200 bg-white py-5">
        <h2 className="text-base font-semibold text-slate-900">
          Filter by listing status
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Select a status to view the corresponding listings.
        </p>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {STATUS_FILTERS.map((filter) => {
            const isActive = activeStatus === filter.value;
            return (
              <button
                key={filter.value}
                type="button"
                aria-pressed={isActive}
                onClick={() => setActiveStatus(filter.value)}
                className={[
                  "rounded-lg border p-4 text-left transition",
                  isActive
                    ? "border-emerald-600 bg-emerald-50 ring-2 ring-emerald-100"
                    : "border-slate-200 bg-white hover:border-slate-400 hover:bg-slate-50",
                ].join(" ")}
              >
                <div className="flex items-center justify-between gap-3">
                  <span
                    className={[
                      "text-sm font-semibold",
                      isActive ? "text-emerald-900" : "text-slate-900",
                    ].join(" ")}
                  >
                    {filter.label}
                  </span>
                  <span
                    className={[
                      "rounded-full px-2.5 py-1 text-xs font-bold",
                      isActive
                        ? "bg-emerald-700 text-white"
                        : "bg-slate-100 text-slate-700",
                    ].join(" ")}
                  >
                    {summary[filter.countKey]}
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  {filter.description}
                </p>
              </button>
            );
          })}
        </div>
      </section>

      <section className="mt-6 border-y border-slate-200 bg-white py-5">
        <label>
          <span className="text-sm font-semibold text-slate-800">
            Search {activeFilter.label.toLowerCase()}
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

      <section className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            {activeFilter.label}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {currentCount} listing{currentCount === 1 ? "" : "s"} found
          </p>
        </div>
        {(searchText || activeStatus !== "all") && (
          <button
            type="button"
            onClick={() => {
              setSearchText("");
              setActiveStatus("all");
            }}
            className="text-sm font-semibold text-emerald-700 hover:underline"
          >
            Clear filters
          </button>
        )}
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
          <p className="text-sm text-slate-600">Loading listings...</p>
        </section>
      ) : listings.length === 0 ? (
        <section className="mt-8 rounded-lg border border-dashed bg-white p-12 text-center">
          <h2 className="text-xl font-semibold text-slate-900">
            No listings found
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            {debouncedSearch
              ? `No ${activeFilter.label.toLowerCase()} match your search.`
              : `There are currently no ${activeFilter.label.toLowerCase()}.`}
          </p>
        </section>
      ) : (
        <section className="mt-8 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {listings.map((listing) => (
            <AdminListingCard key={listing.id} listing={listing} />
          ))}
        </section>
      )}
    </main>
  );
}

interface SummaryCardProps {
  label: string;
  value: number;
  description: string;
}

function SummaryCard({ label, value, description }: SummaryCardProps) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
      <p className="mt-2 text-xs text-slate-500">{description}</p>
    </article>
  );
}
