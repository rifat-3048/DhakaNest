import type { ListingStatus } from "@/types/listing";

interface ListingStatusBadgeProps {
  status: ListingStatus;
}

const labelByStatus: Record<ListingStatus, string> = {
  draft: "Draft",
  pending_review: "Pending Review",
  revision_requested: "Revision Requested",
  approved: "Approved",
  rejected: "Rejected",
  rented: "Rented",
};

const classByStatus: Record<ListingStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  pending_review: "bg-amber-100 text-amber-800",
  revision_requested: "bg-orange-100 text-orange-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
  rented: "bg-blue-100 text-blue-800",
};

export default function ListingStatusBadge({ status }: ListingStatusBadgeProps) {
  return (
    <span
      className={[
        "inline-flex rounded-full px-3 py-1 text-xs font-semibold",
        classByStatus[status],
      ].join(" ")}
    >
      {labelByStatus[status]}
    </span>
  );
}
