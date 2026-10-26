# Phase 3D v6: preserve Colab dependencies

## Confirmed failure and compatibility limits

The supplied v5 APT output proposed removing `libboost-dev`, `libboost1.83-dev`,
`libgdal-dev` and `libkml-dev` to install Boost 1.74 development packages. The
`--no-remove` protection correctly refused the transaction. This was before
compilation; it does not confirm the earlier GCC 13 hypothesis.

OSRM stays at v5.27.1, commit
`4f3ee609ec1af40eb1f445c6706cfa5beb04c990`. Its official CMake configuration uses
C++17 and requires Boost >=1.70 for osrm-routed, with no upper version bound:

https://github.com/Project-OSRM/osrm-backend/blob/v5.27.1/CMakeLists.txt

That is source-level evidence for considering installed Boost 1.83, not evidence
that the entire OSRM release compiles against it. No Linux APT simulation,
compiler probe or native build was executed during this Windows repair. Offline
tests use explicitly labelled solver/compiler fixtures, not fabricated Colab
results. No Linux compatibility success is claimed.

## Dependency and compiler policy

1. Detect Ubuntu 22.04/24.04 amd64, all installed package versions, compiler paths
   and the actual Boost version header. Keep installed Boost 1.83 (affected Colab)
   or 1.74 (older supported runtime); unknown/missing headers require review.
2. Request only missing required packages. Boost component package names match
   the detected installed Boost series; never request 1.74 in a 1.83 runtime.
3. Audit dpkg, simulate APT and save complete stdout/stderr and exit status.
   Reject solver errors, removals, upgrades, downgrades, existing-package actions,
   missing/unrecognized summaries and inconsistent action counts.
4. Pin every proposed new package (including transitive dependencies) to the
   exact simulated version. Simulate those pins again; refuse changed plans.
5. Install with `--no-remove --no-upgrade`, without force or allow-downgrade flags.
   Check that existing package versions are unchanged before/after installation.
   APT indexes can be refreshed, but no installation precedes simulation.
6. Prefer the existing GNU >=11 compiler if the original OSRM coordinate-header
   syntax probe passes. Only after failure/absence try an installed GCC 11 or
   safely simulate/install GCC 11 additively. Preserve failed probe stderr.
   GCC 11 is a conditional compatibility fallback, not a proven requirement.
7. Verify Boost headers and actual library linking/execution in a separate probe.
   Configure the pristine pinned source using system CMake 3.x, the selected
   compiler and matching Boost. CMake must resolve all required components.
8. Build serially, retaining memory/time guards, no LTO/ccache, verbose full logs
   and first-error context. Only all four validated 5.27.1 executables, with clean
   source and resolved shared libraries, permit completed setup/publication.

New attempt evidence is copied to Drive even on failure: `apt-*.json`, package
inventories, `detected-environment.json`, `compiler-selection.json`, compatibility
probes, CMake cache/compile commands, full logs and first-error summaries.

Repository versions are recorded, not immutable across time. The exact successful
package pins and compiler/library/binary hashes establish the actual run's
provenance. Do not claim bit-identical builds from floating APT repositories.

## Notebook import correction

V6 uses the actual exports:

```python
from research.routing.osrm_colab.workflow import validate_config, guard
```

CLI stages use `research.routing.osrm_colab.native_build_v3`. All research
`from ... import ...` statements in v6 are resolved by a regression test. V5's
incorrect import and archive are retained as historical artifacts; use v6 instead.
The isolated Python 3.12/3.13 environment, 33 pinned research dependencies, wheel
hashes, checksum extraction, `pip check` and import validation remain unchanged.

## Safe new-run procedure (recommended)

1. Upload `dhakanest_colab_input_v6.zip` to the existing research Drive folder.
   Open `DhakaNest_Phase3D_Colab_OSRM_v6.ipynb` in a CPU runtime. A fresh runtime
   is fine but does not need to remove or downgrade its preinstalled Boost.
2. Use the new default run ID `phase3d-colab-additive-apt-001` and local root
   `/content/dhakanest_phase3d_apt_v3`. Enter the v6 ZIP SHA-256 in CONFIG.
   Never reuse an old v5 configuration or delete failed-stage records.
3. Keep `repair_only=True`, `native_retry_attempt=0` and
   `allow_retry_failed_stage=False`. Native setup is NOT pre-authorized by the
   notebook. Explicitly set `authorize_native_build=True` when ready to permit
   package installation and native compilation.
4. Run cells in order through `stage('setup')` only. Do NOT use Run all. Stop
   after setup; map download/preprocessing/routing refuse repair-only execution.
5. If APT rejects a plan, inspect saved `apt-*.json`. Do not disable protections,
   remove existing libraries or substitute a different Boost series. Review
   candidate availability and conflicting dependencies before another attempt.

## Controlled retry in a v6 run

Inspect the failed attempt's full log and simulation/probe records first. With
one `setup-1.started.json`, authorize exactly attempt 2:

```python
CONFIG['authorize_native_build'] = True
CONFIG['allow_retry_failed_stage'] = True
CONFIG['native_retry_attempt'] = 2
config_path.write_text(json.dumps(CONFIG, indent=2))
stage('setup')
```

For later failures use the count of `setup-*.started.json` plus one. Authorization
is checked before expensive work. Each retry creates a new source/build directory;
all prior records remain. Completed stages are immutable and never rebuilt by
retry flags. Changed build specification or conflicting partial publication
requires a new run ID/local root, not deletion or evidence rewriting.

This repair does not execute OSM downloads/routing, change scientific methodology,
or complete Phase 3D. Successful native compilation must be established in Colab
before any separately authorized routing work can resume.
