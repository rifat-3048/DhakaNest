# Read-Only Export Specification (Not Executed)

Missing evidence: full 2,500 academic active listing documents, their actual
IDs, eligibility/availability state, coordinates, advertised rents and complete
stored review assessments. The repository coverage summary contains aggregate
counts, not per-record snapshots. Rerunning the academic generator would create
jittered positions and new predictions rather than recover the stored records.
No database access, model inference, or invented assessments is used here.

Request separate authorization for a read-only export from collection `listings`.
Do not create indexes, update status, backfill ownership, or alter assessments.
Capture the export UTC time and hash locally, database identity as a nonsecret
alias, selection query, counts, source license/consent, and exporter version.

Use the intended academic dataset tag (verify its actual field first) and/or
an explicitly approved real-listing scope. Export lifecycle entries separately
if needed to test base eligibility. Preserve `status` and `is_available`; never
mark all exported records approved. Original database IDs must be strings in
the private export; the offline importer replaces them with deterministic hashes.

Allowed structural fields: title, de-identified description, property_type,
furnishing_status, broad_area, model_micro_area, latitude, longitude, area_sqft,
bedrooms, bathrooms, asking_rent_bdt, canonical amenities, available_from,
status, is_available. Include complete stored `rent_assessment` numeric/model
fields and input_snapshot, excluding checked_by or any administrator identity.
Missing or stale assessments stay missing/invalid and prevent experiment readiness.

Every record needs provenance.source_type from real_market_observation,
academic_synthetic, derived_transformed, evaluation_fixture. Also require
source_reference, coordinate_source, coordinate_precision, license_or_basis,
observed_at (required for real observations), source_sha256 when available,
and transformations. Academic jittered coordinates must be labeled synthetic
offsets around repository anchors, not surveyed property locations. Assessments
from model-linked synthetic rents can create circular fairness evidence; this
requires a separately declared subgroup/limitation in future comparisons.

Exclude owner names, email, phone, owner/landlord IDs, authentication data,
private notes, photos, precise private addresses, and all unnecessary personal
data. Review free text and provenance before import/publication. Do not make a
private raw export part of the public benchmark. Validate imported JSON with
`import_properties`, then freeze a new version with route evidence matching the
new anonymized IDs and exact coordinates. Never merge into the existing v1.
