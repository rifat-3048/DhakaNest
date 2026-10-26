# Frozen Routing Evidence

**No genuine OSRM duration/distance evidence was acquired or recovered from the
inspected repository inputs. Routing is incomplete.**

The dataset stores the full 12-properties x 12-destinations input domain:
144 rows in `routes.jsonl`, all explicitly `missing`, with null duration,
distance, acquisition time, provider, and raw-response reference. This freezes
the required inputs and missingness, not a completed road-routing matrix.
Valid=0, unreachable=0, error=0, missing=144. Every pair is accounted for as
a status record, but none is accounted for as valid or explicitly unreachable.
Engine version, map extract version, and acquisition time remain unknown.

Across repeated profile requests, hard survivors require 532 route-pair uses;
shared destination IDs allow deduplication into the 144-pair full input grid.
Unknown routes are never straight-line approximations, zero costs, or assumed
unreachable results. Forty profiles already have no hard survivors; route-based
feasibility remains unknown for the other 160.

## Functional acquisition infrastructure, not executed live

`prepare_routing` defaults to an offline plan. An explicit `--allow-network`
flag, approved endpoint and new research output path are required for capture.
The utility reuses production URL construction and OSRM response parsing, with
two-axis batching (40 homes, 20 destinations), serial bounded concurrency 1,
minimum one-second pacing, bounded exponential-backoff retries, immutable raw
JSON checkpoints and failure logs. Failed calls remain errors; only genuine
OSRM double-null cells are unreachable. Partial outputs are labeled incomplete.

Success checkpoints bind the exact request URL, coordinate digest, stable IDs,
UTC time, and canonical raw-response SHA-256. Final route data has a byte hash.
Restarting an interrupted unsealed capture reuses compatible successes; sealed
capture outputs cannot be overwritten. Versions not supplied/known stay unknown.
The offline loader checks captured URLs, coordinates, raw payload hashes and
normalized measurements, with no network fallback.

Unit tests mock HTTP payloads to verify capture behavior and failures. Those
artificial values are temporary test fixtures, not benchmark evidence. No live
capture was executed. Complete future experiments require an approved capture
and a new integrated dataset version/manifest. Local OSRM is supported without
Docker; no deployment or server start is performed in Phase 3.
