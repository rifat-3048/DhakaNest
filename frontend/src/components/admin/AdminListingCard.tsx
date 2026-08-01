import Image from "next/image";
import Link from "next/link";

import ListingStatusBadge from "@/components/listings/ListingStatusBadge";
import type { RentalListing } from "@/types/listing";

const currencyFormatter = new Intl.NumberFormat("en-BD", {
  maximumFractionDigits: 0,
});

function formatDate(value: string | null): string {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-BD", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function AdminListingCard({ listing }: { listing: RentalListing }) {
  const sortedImages = [...listing.images].sort(
    (first, second) => first.sort_order - second.sort_order,
  );
  const primaryImage =
    sortedImages.find((image) => image.is_primary) ?? sortedImages[0];

  return (
    <article className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="relative h-52 bg-slate-100">
        {primaryImage ? (
          <Image
            src={primaryImage.url}
            alt={listing.title}
            fill
            sizes="(max-width: 768px) 100vw, 33vw"
            className="object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            No property image
          </div>
        )}
        <div className="absolute left-3 top-3">
          <ListingStatusBadge status={listing.status} />
        </div>
        <span
          className={[
            "absolute bottom-3 right-3 rounded-full px-3 py-1 text-xs font-semibold text-white",
            listing.rent_assessment ? "bg-emerald-700" : "bg-slate-900/80",
          ].join(" ")}
        >
          {listing.rent_assessment ? "Fairness checked" : "Check required"}
        </span>
      </div>

      <div className="p-5">
        <h2 className="line-clamp-2 text-lg font-semibold text-slate-900">
          {listing.title}
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          {listing.model_micro_area}, {listing.broad_area}
        </p>
        <p className="mt-3 text-xl font-bold text-emerald-700">
          BDT {currencyFormatter.format(listing.asking_rent_bdt)}
          <span className="text-sm font-normal text-slate-500">/month</span>
        </p>

        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          <Fact label="Bedrooms" value={listing.bedrooms} />
          <Fact label="Bathrooms" value={listing.bathrooms} />
          <Fact label="Images" value={listing.images.length} />
        </div>
        <div className="mt-4 border-t pt-4 text-xs text-slate-500">
          {listing.submitted_at ? "Submitted" : "Created"}: {" "}
          {formatDate(listing.submitted_at ?? listing.created_at)}
        </div>
        <Link
          href={`/admin/listings/${listing.id}`}
          className="mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800"
        >
          {listing.status === "pending_review" ? "Review listing" : "View listing"}
        </Link>
      </div>
    </article>
  );
}

function Fact({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-slate-50 p-2">
      <strong className="block text-sm text-slate-900">{value}</strong>
      <span className="text-xs text-slate-500">{label}</span>
    </div>
  );
}
