# Routing Validation

Status: partially complete. Endpoint acquisition is blocked by missing explicit workload permission and verified endpoint-specific matrix limits. No live route request was sent.

The new overlay freezes inputs/mappings/missingness, NOT a completed road matrix.
Logical=30000, physical=30000, valid=0,
unreachable=0, missing logical=30000; complete=false.
There are no acquired payload timestamps or actual road-data versions to report.
All missing cells have null measurements. Route key, coordinate/profile, batch
coverage and source-reference checks pass. Known valid/unreachable records would
require raw response hashes, exact batch URLs, timestamps and production-parser
equivalence; unverified metadata cannot establish route truth.

All overlay hashes and parent property/profile/split/destination references are
verified. Large unchanged datasets were not copied. No old dataset or manifest
was overwritten. Actual acquisition must publish another new version, preserving
this partial overlay and its declared blocker. Inputs: research/datasets/benchmark_v1_1 (checksum-referenced unchanged) and benchmark_v1_2/routing. Code: research/benchmark/phase3c.
