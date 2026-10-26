# DhakaNest Local Research OSRM

Current status: **blocked by host prerequisites**, not a working routing service.
Docker CLI/Compose exist, but the Docker Linux engine is unavailable. WSL reports
Virtual Machine Platform/BIOS virtualization prerequisites unmet. Do not enable
Windows features, change BIOS settings, install services or pull images silently.
The host has about 7.8 GiB total RAM and only 1.7 GiB free at inspection; the
provisional preparation gate requires at least 4 GiB free, not a proven minimum
for the full country extract. About 78.4 GiB disk is free on D:.

## Implemented Setup

The proposed official image is version-pinned to
`ghcr.io/project-osrm/osrm-backend:v26.10.0`; it has NOT been pulled or runtime
verified. Existing local image inspection records its immutable ID and available
registry digests. All preparation and serving use the same image ID. Automatic
pulling is disabled. A missing version tag/image must be reported, never replaced
with latest. No Docker volume or existing container is removed by these tools.

Compose isolates a single MLD/car server on **127.0.0.1:5001**, with a read-only
graph mount, 2 CPU limit, 4 GiB memory cap and no added capabilities. It does not
mount backend secrets, modify production routing, expose an external port or
start a database/frontend. Preparation is extract -> partition -> customize;
serving uses `--algorithm mld`, not a mixed CH pipeline.

The operator CLI has an offline `probe`. Every mutating/HTTP action requires
`--execute`; acquisition is restricted to the dedicated loopback endpoint.
All downloaded/derived data and execution logs stay in gitignored `runtime/`.
Do not force-add extracts/graphs to Git. Source-side manifests are reference-only;
runtime manifests contain actual downloaded hashes after registration.

## Recovery Sequence, Not Executed

1. With administrator approval, resolve the WSL virtualization prerequisite,
   restart if required, then start existing Docker Desktop with its Linux engine.
   The tools do not do this. Review free memory before attempting country-scale
   preprocessing; closing applications does not guarantee sufficient resources.
2. After approving downloads/storage, obtain the official pinned image and
   Geofabrik Bangladesh PBF plus its `.poly` file. The provider advertised 339 MB
   on 2026-10-25, data through 2026-10-24T20:20:51Z. These are provider metadata,
   not a downloaded file size/hash. Re-check on download and retain the exact
   bytes. No download occurred in this phase.
3. Store the PBF as `runtime/data/bangladesh-latest.osm.pbf` and the provider
   polygon under `runtime/`. Preserve attribution to OpenStreetMap contributors
   and Geofabrik, with ODbL requirements reviewed before publishing derived data.
4. From the repository root, use the existing backend Python for the commands
   below. Registration computes the actual SHA-256 and validates all 2512 input
   points against the downloaded provider polygon; it cannot create map data.
5. Prepare once. Each stage is network-isolated and resource-capped, with logs.
   A failed attempt blocks automatic retries. Inspect the failure and resource
   situation before deliberately choosing a new reviewed preparation attempt.
6. Start, smoke-test and inspect snapping. Only then acquire through Phase 3C's
   bounded engine into a NEW overlay. No ranking/labels are calculated.

```powershell
backend\.venv\Scripts\python.exe -m research.routing.osrm_local.operator probe
backend\.venv\Scripts\python.exe -m research.routing.osrm_local.operator register --execute --source-date ACTUAL_PROVIDER_TIMESTAMP --polygon research/routing/osrm_local/runtime/bangladesh.poly
backend\.venv\Scripts\python.exe -m research.routing.osrm_local.operator prepare --execute
backend\.venv\Scripts\python.exe -m research.routing.osrm_local.operator start --execute
backend\.venv\Scripts\python.exe -m research.routing.osrm_local.operator smoke --execute
backend\.venv\Scripts\python.exe -m research.routing.osrm_local.operator acquire --execute --output research/datasets/benchmark_v1_3_acquired
```

The source-date placeholder must be replaced with verified metadata for the
actual PBF. Changing-latest URLs do not freeze a dataset. The default example
resource budgets are conservative gates, not measured preparation requirements;
country-wide road connectivity is preferred over an unverified tiny Dhaka crop.
Geographic polygon containment alone does not prove route connectivity.

Shutdown only this project service after acquiring/validating evidence:

```powershell
docker compose --env-file research/routing/osrm_local/.env.example -f research/routing/osrm_local/docker-compose.yml stop osrm
```

This stops the dedicated server without removing containers, images or volumes.
Do not use global pruning or `down -v`. Final frozen capture evidence references
runtime raw response files: archive those files with their hashes before sharing
or removing a runtime directory. Runtime data is excluded from Git, not disposable
while referenced by research evidence.

## Evidence and Limits

Smoke uses four genuine local Table cells, preserves raw/snapping metadata and
requires at least one routable pair. It verifies the running project container's
image, command, loopback binding and read-only graph mount. Full acquisition
retains the Phase 3C exact-key plan: 30,000 physical/logical pairs, 63 requests,
189 worst-case with retries, plus the separate one-request smoke test. Raw
payloads, versions/data provenance and graph hashes remain required.

No server, smoke route, road matrix, post-commute counts or final annotation pool
has been produced on the currently blocked host. Missing road evidence is never
called unreachable. The old 4800-pair pool stays provisional. The final fixture
fails readiness until genuine routes exist. No Phase 4 annotation is authorized.

Sources: [OSRM setup](https://github.com/Project-OSRM/osrm-backend),
[26.10.0 release](https://github.com/Project-OSRM/osrm-backend/releases/tag/v26.10.0),
[Geofabrik](https://download.geofabrik.de/asia/bangladesh.html),
[OpenStreetMap license](https://www.openstreetmap.org/copyright).
