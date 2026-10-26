# Phase 3D: Google Colab OSRM

This new research-only adapter runs native OSRM in Colab and reuses the sealed
Phase 3C acquisition, matrix validator, Phase 3B sampler and production-compatible
offline filters. It does not change earlier research evidence or the application.
No Docker, Windows/WSL repair, MongoDB, GPU, retraining or deployment is needed.

## Current status

The workflow is implemented, but **Colab execution is outstanding**. A generated
notebook is not measured road evidence. The historical benchmark still has zero
genuine measurements, zero verified unreachable pairs and 30,000 missing pairs.
The completed overlay is intentionally NOT created on Windows.

## Run It

1. Use the prepared `research/exports/dhakanest_colab_input_v2.zip` when present.
   Otherwise, from the project root in VS Code create a byte-preserving bundle:

   ```powershell
   .\backend\.venv\Scripts\python.exe -m research.routing.osrm_colab.storage --output research/exports/dhakanest_colab_input_v2.zip
   ```

   This creates a NEW file and prints its SHA-256. Keep that value. Existing ZIPs
   are not overwritten; use a new filename when packaging a changed workspace.
   The allowlisted ZIP includes research inputs and required backend source/model
   assets. It omits real `.env` files, `.venv`, `.git`, node_modules, caches and
   runtime data. Public `.env.example` templates are retained because historical
   manifests verify them; they are templates, not private environment files.
   It is an input bundle, not an automatically anonymized public-release archive;
   review files before sharing outside your research team.

2. In Google Drive create `MyDrive/DhakaNestResearch` and upload the ZIP there.
3. Open [Google Colab](https://colab.research.google.com/), select **File > Upload
   notebook**, and choose `research/notebooks/DhakaNest_Phase3D_Colab_OSRM.ipynb`.
4. Choose **Runtime > Change runtime type > CPU**. Edit only the configuration
   cell: ZIP path, printed SHA-256, workspace, and a unique run ID if necessary.
5. Run cells in order. Authenticate the supported Drive mount when prompted.
   Resource checks happen before the OSM download/build. The first run installs
   Python/system dependencies inside Colab and builds native OSRM, which can take
   considerable time. No installation is performed on your Windows computer.
6. Check the genuine smoke, matrix counts, candidate coverage, pool and offline
   verification. Retain actual regression logs. Full acceptance requires all
   30,000 pairs resolved plus passing tests, not simply a successful notebook import.
7. Download `<run_id>-offline.zip` and retain its printed SHA-256. Drive also keeps
   the original map, binary/graph files, logs, raw captures and reports. Keep large
   OSM/graph artifacts out of Git. The ZIP has the source/parent assets and raw
   evidence necessary to load the fixture offline; regression logs live separately
   under `<workspace>/<run_id>/regressions/`. The later `results/colab_acceptance.json`
   binds actual passing test logs to the frozen dataset; retain that supplemental
   evidence with the ZIP. It is created only after real Colab tests pass.

Alternative import: provide an explicitly authorized, credential-free HTTPS Git
URL and exact 40-character commit in the same cell. The commit must actually
include untracked research and model assets. Historical checks bind exact bytes:
Git line-ending conversion or missing large model files causes a deliberate stop.
Use the ZIP instead; never rewrite historical hashes to make an import pass.

## Resume and Failures

Reopen the same notebook and run all cells with the SAME ZIP/hash, run ID and
settings. Local `/content` is disposable; Drive is the persistent source. Completed
stages are copied back and checked. Every request reservation is copied to Drive
before HTTP begins, and completed captures are reparsed and skipped. An interrupted
reserved request consumes the original retry/attempt budget. The engine enforces
the global ceiling across sessions; it never silently resets exhausted budgets.

The initial configuration computes 63 batches (40 origins x 12 destinations) and
permits 189 attempts, plus one separate smoke per server start. Different valid
batch sizes recalculate the plan; a too-small ceiling fails before requests.
Concurrency remains one. Routes remain exact, directional keys; no rounding,
straight-line substitute or public demo fallback is introduced.

Fully completed exports and passing test logs are reused without rewriting their
seals. New local verification runs are saved in numbered directories rather than
overwriting the original implementation-verification evidence. If you intentionally
change the routing snapshot, select both a new run ID and a new local_root to avoid
conflicting files from the previous local runtime.

If a build/download/preprocessing stage fails, inspect Drive logs first. An
explicit `allow_retry_failed_stage=True` is required for another expensive attempt.
A partially downloaded unregistered file or conflicting artifact requires a fresh
run ID/local_root; do not guess provenance or overwrite conflicting evidence.
If memory is inadequate, choose a larger CPU runtime or separately review a
connectivity-preserving smaller extract. This workflow never silently substitutes
a city crop. The conservative 6 GiB-free RAM/20 GiB-disk gates are safety estimates,
not measured promises about Bangladesh preprocessing on every assigned runtime.
The child process group is monitored and terminated at a 1 GiB free-memory floor.

Map, native binary, dynamic libraries, profile tree, graph hashes and request
configuration are scope-bound. Changed Colab base libraries intentionally stop
resume; use a new run ID for a new snapshot, never mix old measurements. A saved
binary may need the system dependency cell rerun on a fresh Colab image. A occupied
port is refused instead of killing unrelated processes. The owned server is bound
to 127.0.0.1 only and stopped in `finally`; no public proxy is created.

## Evidence and Reuse

- `workflow.py`: resources, real download/header/polygon provenance, bounded native
  stages, server lifetime, scope binding and existing Phase 3C finalization.
- `storage.py`: immutable verified atomic copies, safe ZIP import/export and the
  scoped durability adapter. No historical source file is patched on disk.
- `verify_osrm.py`: smoke/snap validation, blinded-field checks and stage counts.
- `report.py`: append-only local implementation/runtime reports and checksums.
- `notebook.py`: deterministic notebook generator; outputs are empty until executed.
- `install_dependencies.sh`, `setup_osrm.sh`, `preprocess_osm.sh`, `start_osrm.sh`:
  reviewable native Linux commands, no downloaded installation scripts.

Native OSRM is pinned to **v5.27.1 / 4f3ee609ec1af40eb1f445c6706cfa5beb04c990**.
This deliberately differs from the unexecuted Windows Docker candidate: it uses
the official native build path and matching car.lua, extract/partition/customize
MLD stages. Actual compatibility with the assigned Colab image must be established
by execution. Unsupported compiler/library combinations stop with preserved logs.
System packages and Python `pip freeze` are recorded by the runtime workflow;
binary/library hashes, not mutable apt package availability alone, bind routes.

Completed data: `research/datasets/benchmark_v1_3_colab/` (new overlay only).
Local implementation reports: `research/results/phase_3d_colab/`.
Real Colab reports: `research/results/phase_3d_colab/<run_id>/`, mirrored in Drive.
Raw evidence remains under `research/routing/osrm_colab/runtime/<run_id>/` and MUST
accompany the dataset, because the existing strict loader validates raw payloads.
The source/graph/input provenance sidecar binds the completed manifest and readiness
without changing its immutable inventory. No parent data are regenerated.

After verified extraction of the offline export at a repository root:

```python
from research.benchmark.phase3c.fixture import RoutingFixture
fixture = RoutingFixture("research/datasets/benchmark_v1_3_colab")
fixture.require_ready()
print(fixture.validation)
```

Export import: `storage.extract_bundle(zip_path, new_repo_path, expected_sha256)`
accepts both input and evidence bundles. Use an empty destination or identical
files; it refuses traversal, symlinks, duplicate members and byte conflicts.

## Methodology and Phase Boundary

The current frozen 200 profiles (60 development/140 held-out), 2,500 active synthetic
listings, 100 lifecycle records and 2,600 assessments remain unchanged. Existing
filters, OSRM URL/parser semantics, WSM v4 and KNN are reused, not rewritten.
WSM v4 budget stays `clamp(1 - advertised_rent / maximum_rent_budget, 0, 1)`.
Transportation costs and total monthly spend remain informational.

Complete routes trigger the existing independent seeded 24-per-profile sampler;
the actual final pool size is measured, not assumed. It preserves random eligible,
boundary, type/area/budget and commute diversity. Future method nominations can be
unioned using the existing `merge_nominations`; no baseline runs here. The blinded
export contains opaque pair IDs and facts, never score/rank/sampling source/label.
Human pilot/ethics review and explicit Phase 4 approval remain outstanding.

Listings and coordinates are synthetic, destinations are area anchors, and OSRM
driving durations are not observed Dhaka traffic. XGBoost outputs do not independently
prove market fairness. Colab does not establish real-market generalization.

## Offline Checks

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s research/tests
.\backend\.venv\Scripts\python.exe -m research.routing.osrm_local.verify_phase3d --verify-seal
```

Ordinary tests use mock transport only. Native download/build/preprocessing and
real 30,000-pair coverage cannot pass on Windows by substituting mocked evidence.
No historical snapshot is overwritten, and no Phase 4 labels or metrics are made.

## Primary References

- [Official OSRM v5.27.1 native installation](https://github.com/Project-OSRM/osrm-backend/tree/v5.27.1#readme)
- [Pinned OSRM source](https://github.com/Project-OSRM/osrm-backend/commit/4f3ee609ec1af40eb1f445c6706cfa5beb04c990)
- [Geofabrik Bangladesh extract](https://download.geofabrik.de/asia/bangladesh.html)
- [Colab FAQ and Drive limitations](https://research.google.com/colaboratory/faq.html)
- [OSM licensing and attribution](https://www.openstreetmap.org/copyright)
