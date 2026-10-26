# Phase 3D native compilation repair (v5)

## Evidence and limits

The supplied retry traceback establishes only that `setup` refused to repeat an
earlier failed/interrupted stage. It contains no compiler diagnostics. Therefore
the original compiler root cause is **not confirmed**. Coordinate-symbol errors
can be secondary diagnostics; do not identify them as the earliest error.

Official v5.27.1 `include/util/coordinate.hpp` defines FixedLongitude and
FixedLatitude using `std::int32_t`, without directly including `<cstdint>`.
GCC 13's documented transitive-header changes make a toolchain/header mismatch
a plausible explanation, NOT an established cause in this runtime:

- https://raw.githubusercontent.com/Project-OSRM/osrm-backend/v5.27.1/include/util/coordinate.hpp
- https://gcc.gnu.org/gcc-13/porting_to.html
- https://github.com/Project-OSRM/osrm-backend/tree/v5.27.1#building-from-source

No Linux/Colab native build has been executed as part of this local Windows
repair. Offline tests validate orchestration, not actual binary compatibility.

## Repair configuration

Retain official v5.27.1, commit
`4f3ee609ec1af40eb1f445c6706cfa5beb04c990`. Every attempt uses an empty private
directory, verifies the release ref against that commit, initializes submodules,
checks Git integrity/cleanliness, and runs a coordinate-header syntax probe.
No OSRM C++ source is edited; the probe is an independent research source file.

Use Ubuntu 22.04/24.04 amd64, GCC/G++ 11, Boost 1.74, system CMake 3.x and
C++17. Apt refuses package removals. Use a **fresh Colab CPU runtime** rather
than trying to replace conflicting Boost development packages in an old VM.
All actual installed package versions are logged. These apt repositories are
not an immutable binary archive: the package inventory and library/binary hashes
record the actual environment; do not claim bit-identical builds across dates.

Serial verbose Release builds disable LTO and ccache. Existing RAM/disk/time
guards remain in force. Complete combined stdout/stderr logs survive failures,
with a first-diagnostic summary and context. Pre/post package inventories,
CMakeCache and compile commands are copied to Drive when available. All four
tools must pass version/help/shared-library checks before canonical publication.
Completed setup records and binaries are checksum-verified before reuse; changed
libraries/specification require a new run, not a rewrite of completed evidence.

## Operator procedure

1. Keep the old Drive run, `setup-1.failed.json`, logs, notebooks and ZIPs.
2. Upload the new v5 ZIP and notebook. Start a fresh CPU runtime. Use the new
   default `run_id` and `local_root`; do not mutate an old run's configuration.
3. Enter the **v5 ZIP's** SHA-256 in CONFIG. Keep `repair_only=True`.
4. To explicitly authorize package installation and compilation, set
   `authorize_native_build=True`. Run notebook cells through **setup only**.
   The default False intentionally refuses installation/compilation.
5. STOP after successful setup during this repair. Do not run OSM downloads or
   routing requests. Those stages refuse execution while repair_only is True.
6. If setup fails, inspect Drive `<run_id>/logs/setup-*.log` and
   `<run_id>/evidence/setup-*.diagnostics.json`. Supply the first meaningful
   diagnostic and surrounding lines. Compiler versions are in the full log.

### Explicit retry in the same v5 run

Inspect logs FIRST. Count `setup-*.started.json` in Drive evidence. If there is
one attempt, set `native_retry_attempt=2`, `allow_retry_failed_stage=True`, and
`authorize_native_build=True`. Each later attempt requires its exact next
number. No automatic retry loop exists, and completed setup is never rebuilt.

After editing CONFIG, update the local operational configuration before calling
the setup stage (the immutable Drive data-identity binding is unchanged):

```python
config_path.write_text(json.dumps(CONFIG, indent=2))
stage('setup')
```

Failed attempt directories and records are retained; the retry builds in a new
directory. If a previous attempt partially published canonical artifacts, do
not overwrite them: use a fresh runtime and new run ID. Never delete failure
records to bypass authorization. An old v4 failure is evidence, not permission
to alter its historical configuration or rerun its old build script.

To read the original failure without running setup, use a separate Colab cell:

```python
logs = pathlib.Path('/content/drive/MyDrive/DhakaNestResearch/phase3d-colab-venv-001/logs')
for path in sorted(logs.glob('setup-*.log')):
    print(path)
# Select the original compilation log, not the later safeguard traceback.
# Download that full file from the Colab Files panel; do not delete or edit it.
```

## Scope and resumption

Only research files are added. Previous notebooks, scripts, locks, artifacts,
benchmarks and seals remain unchanged. The v4 isolated Python 3.12/3.13 setup,
33-dependency locks, hashes, pip check and import validation are inherited.
No production, database, model, KNN, WSM, frozen data or routing measurements
are changed. Phase 3D can resume only after genuine Colab native-build validation
and a separate explicit decision to leave repair-only mode. It is not complete.
