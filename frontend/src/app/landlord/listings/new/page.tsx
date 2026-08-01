"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import ListingForm from "@/components/listings/ListingForm";
import { createListing } from "@/lib/listing-api";
import type { ListingFormValues } from "@/types/listing";

export default function NewListingPage() {
  const router = useRouter();
  const [pageMessage, setPageMessage] = useState<string | null>(null);

  async function handleCreate(values: ListingFormValues) {
    setPageMessage(null);
    const response = await createListing(values);
    setPageMessage("Draft created. Opening image upload...");
    router.push(`/landlord/listings/${response.listing.id}`);
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Link
        href="/landlord/dashboard"
        className="text-sm font-medium text-emerald-700 hover:underline"
      >
        Back to dashboard
      </Link>

      <div className="mt-5">
        <p className="text-sm font-medium text-emerald-700">New Listing</p>
        <h1 className="mt-1 text-3xl font-bold text-slate-900">
          Create a property listing
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Save the property information first, then upload images.
        </p>
      </div>

      {pageMessage && (
        <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          {pageMessage}
        </div>
      )}

      <div className="mt-8">
        <ListingForm
          submitLabel="Create draft and continue"
          onSubmit={handleCreate}
        />
      </div>
    </main>
  );
}
