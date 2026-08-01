"use client";

import Image from "next/image";
import {
  type ChangeEvent,
  type DragEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  deleteListingImage,
  reorderListingImages,
  setPrimaryListingImage,
  uploadListingImages,
} from "@/lib/listing-api";
import type { ListingImage, RentalListing } from "@/types/listing";

interface ListingImageManagerProps {
  listing: RentalListing;
  editable: boolean;
  onListingChanged: (listing: RentalListing) => void;
}

const MAX_IMAGE_COUNT = 8;
const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
]);

function validateSelectedFiles(files: File[], existingCount: number): string | null {
  if (files.length === 0) return "Select at least one image.";
  if (existingCount + files.length > MAX_IMAGE_COUNT) {
    return `A listing can contain no more than ${MAX_IMAGE_COUNT} images.`;
  }

  for (const file of files) {
    if (!ACCEPTED_IMAGE_TYPES.has(file.type)) {
      return `${file.name} is not a supported JPEG, PNG, or WebP image.`;
    }
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      return `${file.name} is larger than 5 MB.`;
    }
  }
  return null;
}

export default function ListingImageManager({
  listing,
  editable,
  onListingChanged,
}: ListingImageManagerProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [draggedImageId, setDraggedImageId] = useState<string | null>(null);

  const sortedImages = useMemo(
    () =>
      [...listing.images].sort(
        (first, second) => first.sort_order - second.sort_order,
      ),
    [listing.images],
  );

  const previewUrls = useMemo(
    () =>
      selectedFiles.map((file) => ({
        file,
        url: URL.createObjectURL(file),
      })),
    [selectedFiles],
  );

  useEffect(() => {
    return () => {
      for (const preview of previewUrls) {
        URL.revokeObjectURL(preview.url);
      }
    };
  }, [previewUrls]);

  function addFiles(files: File[]) {
    setErrorMessage(null);
    setMessage(null);
    const validationError = validateSelectedFiles(files, listing.images.length);

    if (validationError) {
      setErrorMessage(validationError);
      return;
    }
    setSelectedFiles(files);
  }

  function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    addFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (!editable) return;
    addFiles(Array.from(event.dataTransfer.files));
  }

  async function handleUpload() {
    if (!editable || selectedFiles.length === 0) return;

    setIsUploading(true);
    setErrorMessage(null);
    setMessage(null);
    try {
      const response = await uploadListingImages(listing.id, selectedFiles);
      onListingChanged(response.listing);
      setSelectedFiles([]);
      setMessage(response.message);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "The images could not be uploaded.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  async function handleSetPrimary(imageId: string) {
    setActiveAction(`primary-${imageId}`);
    setErrorMessage(null);
    setMessage(null);
    try {
      const response = await setPrimaryListingImage(listing.id, imageId);
      onListingChanged(response.listing);
      setMessage("Cover image updated.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "The cover image could not be changed.",
      );
    } finally {
      setActiveAction(null);
    }
  }

  async function handleDelete(imageId: string) {
    if (!window.confirm("Delete this property image?")) return;

    setActiveAction(`delete-${imageId}`);
    setErrorMessage(null);
    setMessage(null);
    try {
      const response = await deleteListingImage(listing.id, imageId);
      onListingChanged(response.listing);
      setMessage("Image deleted.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "The image could not be deleted.",
      );
    } finally {
      setActiveAction(null);
    }
  }

  async function handleImageDrop(targetImageId: string) {
    if (!editable || !draggedImageId || draggedImageId === targetImageId) {
      setDraggedImageId(null);
      return;
    }

    const reorderedIds = sortedImages.map((image) => image.image_id);
    const currentIndex = reorderedIds.indexOf(draggedImageId);
    const targetIndex = reorderedIds.indexOf(targetImageId);
    reorderedIds.splice(currentIndex, 1);
    reorderedIds.splice(targetIndex, 0, draggedImageId);

    setActiveAction("reorder");
    setErrorMessage(null);
    setMessage(null);
    try {
      const response = await reorderListingImages(listing.id, reorderedIds);
      onListingChanged(response.listing);
      setMessage("Image order updated.");
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "The image order could not be updated.",
      );
    } finally {
      setDraggedImageId(null);
      setActiveAction(null);
    }
  }

  return (
    <section className="rounded-lg border bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Property images</h2>
          <p className="mt-1 text-sm text-slate-600">
            Upload 1-8 JPEG, PNG, or WebP images, up to 5 MB each.
          </p>
        </div>
        <span className="text-sm font-medium text-slate-600">
          {listing.images.length}/{MAX_IMAGE_COUNT}
        </span>
      </div>

      {errorMessage && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}
      {message && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {message}
        </div>
      )}

      {editable && (
        <div className="mt-5">
          <div
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
            className="rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center transition hover:border-emerald-600 hover:bg-emerald-50"
          >
            <p className="font-medium text-slate-800">Drag property images here</p>
            <p className="mt-1 text-sm text-slate-500">
              or choose files from your computer
            </p>
            <label className="mt-4 inline-flex cursor-pointer rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700">
              Select images
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                className="hidden"
                onChange={handleFileInputChange}
              />
            </label>
          </div>

          {previewUrls.length > 0 && (
            <div className="mt-5">
              <h3 className="text-sm font-semibold text-slate-800">Ready to upload</h3>
              <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {previewUrls.map(({ file, url }) => (
                  <div
                    key={`${file.name}-${file.lastModified}`}
                    className="overflow-hidden rounded-lg border bg-white"
                  >
                    {/* Blob URLs are local browser previews, not remote images. */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={url} alt={file.name} className="h-36 w-full object-cover" />
                    <div className="p-3">
                      <p className="truncate text-xs font-medium text-slate-700">
                        {file.name}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleUpload}
                  disabled={isUploading}
                  className="rounded-lg bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-60"
                >
                  {isUploading
                    ? "Uploading..."
                    : `Upload ${selectedFiles.length} image(s)`}
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedFiles([])}
                  disabled={isUploading}
                  className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Clear selection
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-6">
        <div className="flex items-center justify-between gap-4">
          <h3 className="text-sm font-semibold text-slate-800">Uploaded images</h3>
          {editable && sortedImages.length > 1 && (
            <p className="text-xs text-slate-500">
              Drag an image onto another image to reorder.
            </p>
          )}
        </div>

        {sortedImages.length === 0 ? (
          <div className="mt-3 rounded-lg border border-dashed p-8 text-center text-sm text-slate-500">
            No property images uploaded.
          </div>
        ) : (
          <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sortedImages.map((image) => (
              <ImageCard
                key={image.image_id}
                image={image}
                editable={editable}
                activeAction={activeAction}
                onDragStart={() => setDraggedImageId(image.image_id)}
                onDragEnd={() => setDraggedImageId(null)}
                onDrop={() => void handleImageDrop(image.image_id)}
                onSetPrimary={() => void handleSetPrimary(image.image_id)}
                onDelete={() => void handleDelete(image.image_id)}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

interface ImageCardProps {
  image: ListingImage;
  editable: boolean;
  activeAction: string | null;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDrop: () => void;
  onSetPrimary: () => void;
  onDelete: () => void;
}

function ImageCard({
  image,
  editable,
  activeAction,
  onDragStart,
  onDragEnd,
  onDrop,
  onSetPrimary,
  onDelete,
}: ImageCardProps) {
  return (
    <article
      draggable={editable}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={(event) => event.preventDefault()}
      onDrop={onDrop}
      className={[
        "overflow-hidden rounded-lg border bg-white shadow-sm",
        editable ? "cursor-move" : "",
      ].join(" ")}
    >
      <div className="relative h-52">
        <Image
          src={image.url}
          alt={image.original_filename || "Property image"}
          fill
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          className="object-cover"
        />
        {image.is_primary && (
          <span className="absolute left-3 top-3 rounded-full bg-emerald-700 px-3 py-1 text-xs font-semibold text-white">
            Cover image
          </span>
        )}
        <span className="absolute bottom-3 right-3 rounded bg-black/70 px-2 py-1 text-xs text-white">
          Position {image.sort_order + 1}
        </span>
      </div>

      <div className="p-4">
        <p className="truncate text-sm font-medium text-slate-800">
          {image.original_filename}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          {image.width} x {image.height}
        </p>

        {editable && (
          <div className="mt-4 flex flex-wrap gap-2">
            {!image.is_primary && (
              <button
                type="button"
                onClick={onSetPrimary}
                disabled={activeAction !== null}
                className="rounded-lg border border-emerald-300 px-3 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-50"
              >
                {activeAction === `primary-${image.image_id}`
                  ? "Updating..."
                  : "Set as cover"}
              </button>
            )}
            <button
              type="button"
              onClick={onDelete}
              disabled={activeAction !== null}
              className="rounded-lg border border-red-300 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
            >
              {activeAction === `delete-${image.image_id}`
                ? "Deleting..."
                : "Delete"}
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
