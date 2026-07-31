# DhakaNest Data Cleaning Report

## Dataset

- Original rows: 28,800
- Original columns: 6
- Exact source duplicates removed: 13,541
- Invalid records quarantined: 11
- Final processed records: 15,248

## Parsing

The following transformations were applied:

- `Area` to `area_sqft`
- `Bed` to `bedrooms`
- `Bath` to `bathrooms`
- `Price` to `base_rent_bdt`
- `Location` to `location_raw`

Malformed values were converted to missing values and quarantined.
They were not silently converted to zero.

## Location Normalization

- Broad areas: 68
- Raw micro-areas: 353
- Model micro-area categories: 198
- Minimum support threshold: 30

Micro-areas below the threshold were mapped to an
`OTHER_<BROAD_AREA>` model category.

## Duplicate Policy

Exact source duplicates were removed.

Repeated normalized combinations were retained because separate rental
properties may share identical location, area, bedroom, bathroom, and rent
values. These records were assigned a shared `duplicate_group_id` and kept
within the same dataset split.

## Outlier Policy

Records with missing or non-positive required values were quarantined.

Plausible high-value, unusually large, unusually small, and whole-building
records were retained with documented outlier labels.

Rent per square foot was used only for data analysis and was not included as
a model input.

## Frozen Splits

- Training rows: 10,668
- Validation rows: 2,289
- Test rows: 2,291
- Random state: 42

The test dataset must remain untouched until the winning algorithm has been
selected using validation performance.


## Duplicate-Handling Limitation

Rows identical across Location, Area, Bed, Bath, and Price were treated as
exact dataset duplicates, and one representative from each group was
retained. This reduced repetition bias and prevented identical information
from entering multiple data splits.

The source dataset did not contain listing IDs, URLs, timestamps, or landlord
identifiers. Therefore, it was not possible to determine whether every
repeated row represented the same advertisement or a separate property with
identical attributes. This is recorded as a limitation of the source data.
