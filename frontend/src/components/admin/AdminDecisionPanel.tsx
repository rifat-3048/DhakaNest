"use client";

import { useState } from "react";

import type { AdminDecision } from "@/types/listing";

interface AdminDecisionPanelProps {
  hasAssessment: boolean;
  isSubmitting: boolean;
  disabled: boolean;
  onDecision: (decision: AdminDecision, notes: string | null) => Promise<void>;
}

const MAX_NOTES_LENGTH = 1000;

export default function AdminDecisionPanel({
  hasAssessment,
  isSubmitting,
  disabled,
  onDecision,
}: AdminDecisionPanelProps) {
  const [notes, setNotes] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  async function handleDecision(decision: AdminDecision) {
    setValidationMessage(null);
    const trimmedNotes = notes.trim();

    if (
      (decision === "request_revision" || decision === "reject") &&
      !trimmedNotes
    ) {
      setValidationMessage(
        "Admin notes are required when requesting revision or rejecting a listing.",
      );
      return;
    }
    if (decision === "approve" && !hasAssessment) {
      setValidationMessage(
        "Run the rent-fairness check before approving this listing.",
      );
      return;
    }

    const decisionLabel =
      decision === "approve"
        ? "approve"
        : decision === "request_revision"
          ? "request revision for"
          : "reject";
    if (!window.confirm(`Are you sure you want to ${decisionLabel} this listing?`)) {
      return;
    }
    await onDecision(decision, trimmedNotes || null);
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-emerald-700">Final human decision</p>
      <h2 className="mt-1 text-xl font-semibold text-slate-950">
        Complete the admin review
      </h2>
      <p className="mt-2 text-sm text-slate-600">
        Approval requires a current fairness assessment. Revision and rejection
        require a clear explanation for the landlord.
      </p>

      {!hasAssessment && (
        <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          Approval is disabled until the rent-fairness check is complete.
        </div>
      )}
      {validationMessage && (
        <div className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {validationMessage}
        </div>
      )}

      <label className="mt-5 block">
        <span className="text-sm font-semibold text-slate-800">
          Administrator notes
        </span>
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          disabled={disabled || isSubmitting}
          rows={5}
          maxLength={MAX_NOTES_LENGTH}
          placeholder="Notes are mandatory for revision requests and rejection."
          className="mt-2 w-full rounded-lg border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100 disabled:bg-slate-100"
        />
        <span className="mt-1 block text-right text-xs text-slate-500">
          {notes.length}/{MAX_NOTES_LENGTH}
        </span>
      </label>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <button
          type="button"
          disabled={disabled || isSubmitting || !hasAssessment}
          onClick={() => void handleDecision("approve")}
          className="min-h-11 rounded-lg bg-emerald-700 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "Saving..." : "Approve listing"}
        </button>
        <button
          type="button"
          disabled={disabled || isSubmitting}
          onClick={() => void handleDecision("request_revision")}
          className="min-h-11 rounded-lg bg-orange-600 px-4 py-3 text-sm font-semibold text-white hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Request revision
        </button>
        <button
          type="button"
          disabled={disabled || isSubmitting}
          onClick={() => void handleDecision("reject")}
          className="min-h-11 rounded-lg bg-red-700 px-4 py-3 text-sm font-semibold text-white hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reject listing
        </button>
      </div>
    </section>
  );
}
