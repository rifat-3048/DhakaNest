# Phase 3 Offline Benchmark Tools

Run from `D:\DhakaNest` using the existing backend environment. No package
installation, server, MongoDB, OSRM request, or model inference is needed.

```powershell
backend\.venv\Scripts\python.exe -m research.benchmark.validate_benchmark
backend\.venv\Scripts\python.exe -m unittest discover -s research\tests -v
backend\.venv\Scripts\python.exe -m research.benchmark.prepare_routing
backend\.venv\Scripts\python.exe -m research.benchmark.seal_phase3 --verify
```

The last command prints an **offline acquisition plan**, not a network call.
Frozen `benchmark_v1` is deliberately incomplete: 200 synthetic scenarios,
12 reconstructed development fixtures, no stored assessments and no acquired
road routes. Missing routes are null/status `missing`, never zero/unreachable.

To reproduce generation into a new, nonexistent research directory:

```powershell
backend\.venv\Scripts\python.exe -m research.benchmark.build_benchmark --output research\datasets\benchmark_v1_reproduction
backend\.venv\Scripts\python.exe -m research.benchmark.validate_benchmark --dataset research\datasets\benchmark_v1_reproduction
```

Generation refuses any existing output directory. Configuration/data contents
are deterministic. The separate experiment manifest includes actual execution
time and is not expected to have a deterministic timestamp.

`OfflineFixture()` checks hashes, schemas, source drift, coordinates, and route
accounting, then supports `prepare(profile_id)`. Its injected frozen routing
provider cannot call the network. `require_experiment_ready()` fails until all
required routes and stored assessments are genuine and present. It does not run
KNN, WSM, annotation, baselines, metrics, or experiments. The dedicated process
adapter supplies inert settings, never loads the application's real `.env`, and
refuses an already production-configured Python process. Model modules are
transitively imported, but prediction/model loading is never invoked.

## Authorized evidence acquisition, later

Read `export_specification.md` before exporting any MongoDB data. No DB connector
is included in the research importer. Import an already authorized, de-identified
JSON array into a new file:

```powershell
backend\.venv\Scripts\python.exe -m research.benchmark.import_properties authorized_export.json research\datasets\authorized_properties_v2.json
```

The provenance/source reference supplied with the export must already be free
of private data. The importer hashes listing IDs, allowlists structural fields,
and excludes owner/authentication fields. Real observations need independently
verifiable source/time/license; an import validation pass is not that verification.
Do not publish arbitrary free-text private descriptions or source notes.

Routing acquisition is **not authorized/executed in Phase 3**. After separate
approval, this example captures into a new research directory:

```powershell
backend\.venv\Scripts\python.exe -m research.benchmark.prepare_routing --allow-network --base-url http://127.0.0.1:5000 --backend-version YOUR_VERIFIED_VERSION --output research\datasets\routing_capture_v2
```

This URL is an example of a separately running, approved local OSRM service,
not a requirement to start one now and not a claim it exists. No Docker is used.
The utility supports approved remote OSRM URLs as well. It uses production URL
construction/response normalization, serial bounded concurrency (1), at least
one second between calls, bounded retries, two-axis batching, immutable success
checkpoints, and per-attempt failure records. Restart an interrupted, unsealed
capture to reuse compatible checkpoints. Frozen captures cannot be overwritten.
Null OSRM cells are explicit unreachable routes; HTTP/provider errors remain
errors. Unknown engine/map versions stay unknown. Publish a new integrated
benchmark version and manifest after authorized captures/imports; do not patch v1.

Initial blinded exports have no labels. Keep `annotation_pool.json` internal:
it contains sampling provenance. Only the blinded export is intended for later
annotation, after sufficient inventory/routes, expert review, and any ethics
approval. No annotation should begin on incomplete commute evidence.
