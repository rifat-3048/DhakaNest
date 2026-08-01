"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";

import type { ListingImage } from "@/types/listing";

interface AdminImageGalleryProps {
  images: ListingImage[];
  listingTitle: string;
}

export default function AdminImageGallery({
  images,
  listingTitle,
}: AdminImageGalleryProps) {
  const sortedImages = useMemo(
    () => [...images].sort((first, second) => first.sort_order - second.sort_order),
    [images],
  );
  const initialIndex = Math.max(
    0,
    sortedImages.findIndex((image) => image.is_primary),
  );
  const [selectedIndex, setSelectedIndex] = useState(initialIndex);

  useEffect(() => {
    if (selectedIndex >= sortedImages.length) setSelectedIndex(0);
  }, [selectedIndex, sortedImages.length]);

  if (sortedImages.length === 0) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Property images</h2>
        <div className="mt-4 rounded-lg border border-dashed p-10 text-center text-sm text-slate-500">
          The landlord did not upload any images.
        </div>
      </section>
    );
  }

  const selectedImage = sortedImages[selectedIndex];
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Property images</h2>
          <p className="mt-1 text-sm text-slate-600">
            Inspect all submitted images before making a decision.
          </p>
        </div>
        <span className="text-sm font-medium text-slate-600">
          {selectedIndex + 1} of {sortedImages.length}
        </span>
      </div>

      <div className="relative mt-5 aspect-[16/9] overflow-hidden rounded-lg bg-slate-100">
        <Image
          src={selectedImage.url}
          alt={`${listingTitle} image ${selectedIndex + 1}`}
          fill
          priority
          sizes="(max-width: 1024px) 100vw, 900px"
          className="object-contain"
        />
        {selectedImage.is_primary && (
          <span className="absolute left-4 top-4 rounded-full bg-emerald-700 px-3 py-1 text-xs font-semibold text-white">
            Landlord cover image
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap justify-between gap-2 text-xs text-slate-500">
        <span>Original file: {selectedImage.original_filename}</span>
        <span>
          {selectedImage.width} x {selectedImage.height} |{" "}
          {selectedImage.format.toUpperCase()}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
        {sortedImages.map((image, index) => (
          <button
            key={image.image_id}
            type="button"
            onClick={() => setSelectedIndex(index)}
            className={[
              "relative aspect-square overflow-hidden rounded-lg border-2 bg-slate-100 transition",
              index === selectedIndex
                ? "border-emerald-700 ring-2 ring-emerald-100"
                : "border-transparent hover:border-slate-400",
            ].join(" ")}
            aria-label={`View image ${index + 1}`}
          >
            <Image
              src={image.url}
              alt={`${listingTitle} thumbnail ${index + 1}`}
              fill
              sizes="150px"
              className="object-cover"
            />
            <span className="absolute bottom-1 right-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] font-semibold text-white">
              {index + 1}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}
