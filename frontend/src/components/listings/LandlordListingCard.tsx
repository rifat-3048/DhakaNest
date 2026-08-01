import Image from "next/image";
import Link from "next/link";

import ListingStatusBadge from "@/components/listings/ListingStatusBadge";
import type { RentalListing } from "@/types/listing";

interface LandlordListingCardProps {
  listing: RentalListing;
}

const currencyFormatter = new Intl.NumberFormat("en-BD", {
  maximumFractionDigits: 0,
});

export default function LandlordListingCard({ listing }: LandlordListingCardProps) {
  const sortedImages = [...listing.images].sort(
    (first, second) => first.sort_order - second.sort_order,
  );
  const primaryImage =
    sortedImages.find((image) => image.is_primary) ?? sortedImages[0];
  const editable =
    listing.status === "draft" || listing.status === "revision_requested";

  return (
    <article className="overflow-hidden rounded-lg border bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="relative h-48 bg-slate-100">
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
            No image uploaded
          </div>
        )}
        <div className="absolute left-3 top-3">
          <ListingStatusBadge status={listing.status} />
        </div>
      </div>

      <div className="p-5">
        <h2 className="text-lg font-semibold text-slate-900">{listing.title}</h2>
        <p className="mt-1 text-sm text-slate-600">
          {listing.model_micro_area}, {listing.broad_area}
        </p>
        <p className="mt-3 text-xl font-bold text-emerald-700">
          BDT {currencyFormatter.format(listing.asking_rent_bdt)}
          <span className="text-sm font-normal text-slate-500">/month</span>
        </p>

        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs text-slate-600">
          <ListingFact label="Bedrooms" value={listing.bedrooms} />
          <ListingFact label="Bathrooms" value={listing.bathrooms} />
          <ListingFact label="Images" value={listing.images.length} />
        </div>

        {listing.status === "revision_requested" && listing.admin_review?.notes && (
          <div className="mt-4 rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800">
            <strong>Revision note:</strong> {listing.admin_review.notes}
          </div>
        )}

        <Link
          href={`/landlord/listings/${listing.id}`}
          className="mt-5 inline-flex w-full items-center justify-center rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-700"
        >
          {editable ? "Continue editing" : "View listing"}
        </Link>
      </div>
    </article>
  );
}

function ListingFact({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-slate-50 p-2">
      <strong className="block text-sm text-slate-900">{value}</strong>
      {label}
    </div>
  );
}
