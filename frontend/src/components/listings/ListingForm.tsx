"use client";

import { type FormEvent, useState } from "react";

import type {
  FurnishingStatus,
  ListingFormValues,
  PropertyType,
  RentalListing,
} from "@/types/listing";

interface ListingFormProps {
  initialValues?: Partial<RentalListing>;
  submitLabel: string;
  readOnly?: boolean;
  onSubmit: (values: ListingFormValues) => Promise<void>;
}

function buildAmenitiesText(amenities?: string[]): string {
  return amenities?.join(", ") ?? "";
}

export default function ListingForm({
  initialValues,
  submitLabel,
  readOnly = false,
  onSubmit,
}: ListingFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (readOnly) return;

    setErrorMessage(null);
    setIsSubmitting(true);
    const formData = new FormData(event.currentTarget);
    const amenities = String(formData.get("amenities") ?? "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
    const availableFrom = String(formData.get("available_from") ?? "");

    const values: ListingFormValues = {
      title: String(formData.get("title") ?? "").trim(),
      description: String(formData.get("description") ?? "").trim(),
      property_type: String(formData.get("property_type")) as PropertyType,
      furnishing_status: String(
        formData.get("furnishing_status"),
      ) as FurnishingStatus,
      broad_area: String(formData.get("broad_area") ?? "").trim(),
      model_micro_area: String(formData.get("model_micro_area") ?? "").trim(),
      address: String(formData.get("address") ?? "").trim(),
      area_sqft: Number(formData.get("area_sqft")),
      bedrooms: Number(formData.get("bedrooms")),
      bathrooms: Number(formData.get("bathrooms")),
      asking_rent_bdt: Number(formData.get("asking_rent_bdt")),
      amenities,
      available_from: availableFrom || null,
    };

    try {
      await onSubmit(values);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "The listing could not be saved.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const inputClassName =
    "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100 disabled:cursor-not-allowed disabled:bg-slate-100";

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {errorMessage && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      <section className="rounded-lg border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">
          Basic property information
        </h2>
        <div className="mt-5 grid gap-5 md:grid-cols-2">
          <label className="md:col-span-2">
            <span className="text-sm font-medium text-slate-700">Listing title</span>
            <input
              name="title"
              required
              minLength={5}
              maxLength={150}
              disabled={readOnly}
              defaultValue={initialValues?.title ?? ""}
              placeholder="3 Bedroom Apartment in Mirpur"
              className={inputClassName}
            />
          </label>

          <label className="md:col-span-2">
            <span className="text-sm font-medium text-slate-700">Description</span>
            <textarea
              name="description"
              required
              minLength={10}
              maxLength={3000}
              rows={5}
              disabled={readOnly}
              defaultValue={initialValues?.description ?? ""}
              placeholder="Describe the property, nearby facilities, and important details."
              className={inputClassName}
            />
          </label>

          <label>
            <span className="text-sm font-medium text-slate-700">Property type</span>
            <select
              name="property_type"
              disabled={readOnly}
              defaultValue={initialValues?.property_type ?? "apartment"}
              className={inputClassName}
            >
              <option value="apartment">Apartment</option>
              <option value="house">House</option>
              <option value="sublet">Sublet</option>
              <option value="room">Room</option>
            </select>
          </label>

          <label>
            <span className="text-sm font-medium text-slate-700">
              Furnishing status
            </span>
            <select
              name="furnishing_status"
              disabled={readOnly}
              defaultValue={initialValues?.furnishing_status ?? "unfurnished"}
              className={inputClassName}
            >
              <option value="unfurnished">Unfurnished</option>
              <option value="semi_furnished">Semi-furnished</option>
              <option value="furnished">Furnished</option>
            </select>
          </label>
        </div>
      </section>

      <section className="rounded-lg border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Location</h2>
        <div className="mt-5 grid gap-5 md:grid-cols-2">
          <label>
            <span className="text-sm font-medium text-slate-700">Broad area</span>
            <input
              name="broad_area"
              required
              disabled={readOnly}
              defaultValue={initialValues?.broad_area ?? ""}
              placeholder="Mirpur"
              className={inputClassName}
            />
          </label>
          <label>
            <span className="text-sm font-medium text-slate-700">Micro-area</span>
            <input
              name="model_micro_area"
              required
              disabled={readOnly}
              defaultValue={initialValues?.model_micro_area ?? ""}
              placeholder="Section 12"
              className={inputClassName}
            />
          </label>
          <label className="md:col-span-2">
            <span className="text-sm font-medium text-slate-700">Full address</span>
            <input
              name="address"
              required
              minLength={5}
              maxLength={500}
              disabled={readOnly}
              defaultValue={initialValues?.address ?? ""}
              placeholder="Mirpur Section 12, Dhaka"
              className={inputClassName}
            />
          </label>
        </div>
      </section>

      <section className="rounded-lg border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">
          Property specifications
        </h2>
        <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <NumberField
            name="area_sqft"
            label="Area in square feet"
            max={20000}
            defaultValue={initialValues?.area_sqft ?? 1000}
            disabled={readOnly}
            className={inputClassName}
          />
          <NumberField
            name="bedrooms"
            label="Bedrooms"
            max={20}
            defaultValue={initialValues?.bedrooms ?? 3}
            disabled={readOnly}
            className={inputClassName}
          />
          <NumberField
            name="bathrooms"
            label="Bathrooms"
            max={20}
            defaultValue={initialValues?.bathrooms ?? 2}
            disabled={readOnly}
            className={inputClassName}
          />
          <NumberField
            name="asking_rent_bdt"
            label="Monthly rent in BDT"
            max={10000000}
            defaultValue={initialValues?.asking_rent_bdt ?? 20000}
            disabled={readOnly}
            className={inputClassName}
          />
        </div>
      </section>

      <section className="rounded-lg border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Additional details</h2>
        <div className="mt-5 grid gap-5 md:grid-cols-2">
          <label>
            <span className="text-sm font-medium text-slate-700">Amenities</span>
            <input
              name="amenities"
              disabled={readOnly}
              defaultValue={buildAmenitiesText(initialValues?.amenities)}
              placeholder="Lift, Generator, Parking"
              className={inputClassName}
            />
            <span className="mt-1 block text-xs text-slate-500">
              Separate amenities with commas.
            </span>
          </label>
          <label>
            <span className="text-sm font-medium text-slate-700">
              Available from
            </span>
            <input
              name="available_from"
              type="date"
              disabled={readOnly}
              defaultValue={
                initialValues?.available_from
                  ? String(initialValues.available_from).slice(0, 10)
                  : ""
              }
              className={inputClassName}
            />
          </label>
        </div>
      </section>

      {!readOnly && (
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex min-h-11 items-center justify-center rounded-lg bg-emerald-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Saving..." : submitLabel}
        </button>
      )}
    </form>
  );
}

interface NumberFieldProps {
  name: string;
  label: string;
  max: number;
  defaultValue: number;
  disabled: boolean;
  className: string;
}

function NumberField({
  name,
  label,
  max,
  defaultValue,
  disabled,
  className,
}: NumberFieldProps) {
  return (
    <label>
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input
        name={name}
        type="number"
        required
        min={1}
        max={max}
        step="1"
        disabled={disabled}
        defaultValue={defaultValue}
        className={className}
      />
    </label>
  );
}
