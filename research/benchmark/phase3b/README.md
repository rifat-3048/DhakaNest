# Phase 3B Versioned Extensions

This package reuses the sealed Phase 3A modules without editing their source or
artifacts. It adds authorized offline reconstruction/inference and version 1.1
data. No production MongoDB connection, credential, server or Docker is needed.

From the repository root, using the existing environment:

```powershell
backend\.venv\Scripts\python.exe -m research.benchmark.phase3b.validate --replay-predictions
backend\.venv\Scripts\python.exe -m research.benchmark.phase3b.routing
backend\.venv\Scripts\python.exe -m unittest discover -s research\tests
```

`routing` prints an offline acquisition plan only. The example local OSRM URL
is not contacted, started, or asserted to exist. No live routing or geocoding is
authorized by the Phase 3B prompt. A separately approved endpoint-specific
capture is required; no guessed road measurements are substituted.

To reconstruct into a NEW nonexistent research directory:

```powershell
backend\.venv\Scripts\python.exe -m research.benchmark.phase3b.build --output research\datasets\benchmark_v1_1_reproduction
```

The original defaults generate 2,500 active plus 100 lifecycle listings. The
lifecycle count matters to RNG group allocation, so generate all 2,600 and then
retain the active subset. No model retraining occurs. All exported bundle
checksums are verified before loading the existing preprocessors and models.
Production generation, prediction and assessment logic are reused unchanged.
Only inference threads are set to one in the isolated process, with no model
file changes. Static property data and assessments reproduce deterministically;
the actual inference acquisition interval is run-specific and kept separately.
The records are a reconstruction, not a verification of live database contents.

Coordinate jitter is retained only because it is part of the original generator.
Every such point is labeled a synthetic offset around a repository area anchor,
never an exact observed property location. The unchanged tenant destinations
remain area proxies, not independently verified institutions. Synthetic rents
are model-linked: internal arithmetic integrity is not market-fairness validity.

`BenchmarkFixture` extends the sealed loader and checks parent profile hashes,
model/assessment provenance, geographic claims and coordinate-bound route IDs.
It prepares candidates without invoking KNN, WSM, metrics or API/history paths.
Missing road evidence prevents experiment readiness. Annotation exports remain
provisional, blinded, unlabeled, and unsuitable for commute judgments until
genuine routing exists and the annotation pilot/design is approved.

## Separately Authorized Routing, Later

After explicit endpoint-specific permission, an example capture command is:

```powershell
backend\.venv\Scripts\python.exe -m research.benchmark.phase3b.routing --allow-network --base-url http://127.0.0.1:5000 --backend-version VERIFIED_VERSION --output research\datasets\routing_capture_v1_1
```

Capture uses existing production URL/parsing functions and sealed acquisition
logic: 40 origins/20 destinations per batch, concurrency 1, >=1-second pacing,
30-second timeouts, two retries, immutable raw checkpoints and resume after
interruption. Unknown engine/map versions remain unknown. Failed requests and
supported unreachable cells are distinct. Exact coordinates, stable pair IDs,
hashes, failure reports and acquisition logs are retained. A full grid also
supports future baseline pools without using only the proposed shortlist.

Use `fixture.attach_capture(dataset, capture_directory, NEW_output_directory)`
to integrate approved capture evidence into a new version. It validates raw
responses, rebuilds candidate/pool diagnostics, and refuses historical output
replacement. No capture or integration with genuine routes has been executed
as part of this offline-only task.
