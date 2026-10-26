# Phase 3D v9: systematic header compatibility preflight

## Confirmed failure and exact source

The provided v8 command compiles `src/extractor/suffix_table.cpp` with global
Werror and the inherited cstdint include, but no Lua-specific warning exception.
The compiler correctly reports `suffix_table.hpp:38:10` uses std::vector without
a vector declaration and explicitly suggests `<vector>`. This is not another
Sol2 diagnostic. The original coordinate error is an intentional baseline probe,
not the terminal full-build error. The full original log is not available locally;
its reported SHA `58eb2db15ade38d2ed3531bd604906f7634ae6e02626fe6dc0667fedb59e7cc9`
is recorded as user-supplied, not independently verified.

An authorized read-only source clone verified OSRM v5.27.1 commit
`4f3ee609ec1af40eb1f445c6706cfa5beb04c990`. A Git archive with LF configuration
preserves canonical blob bytes independently of Windows checkout CRLF conversion.
Only nonregular files irrelevant to the header audit are omitted locally and
listed in the audit report; this is not a reconstructed full Linux build.

Verified correction:

- `include/extractor/suffix_table.hpp` original SHA-256:
  `4035f945b7507677586cab639971293d34ea8f526df66dedf01ff23887af7945`
- Corrected SHA-256, adding ONLY `#include <vector>`:
  `7c1dc301eaf255452ec05b994bf6026dfc61a567554d6cdb4f549a1cfe3d9203`
- Unified patch SHA-256:
  `01516e0aeeaf0aae873ecdecfc98dbdfd7dabbaf8c2dc567010c44f9374f741c`

The runtime keeps `attempt/source` as the pristine Git checkout. It builds a
separate `attempt/build_source` copy with this one header correction. Every file
is checksummed before/after; no other source changes or speculative includes
are permitted. All suffix-header consumers receive the proper direct include,
not just the currently failing .cpp. The existing binary validation checks the
pristine checkout; v9 additionally verifies the disposable build-source manifest.

Existing `<cstdint>` forced include remains the ONLY forced header. Existing
Sol2/Lua and GCC-11/osrm.cpp warning exceptions are inherited byte-for-byte;
global Werror and their exact scopes remain mandatory. There is no forced-vector
flag, warning-policy expansion, algorithm replacement or scientific change.

## Compiler-backed preflight before full target compilation

1. Preserve v8's isolated Python, hashed dependencies, additive-only APT planning,
   compiler selection, memory/disk/time gates, all logs and retry authorization.
2. Verify pinned coordinate, warning-configuration and Sol2 source hashes. Create
   and checksum the disposable one-header correction.
3. Configure CMake with a File API `codemodel-v2` query. Traverse its actual
   target/dependency graph from osrm-extract, osrm-partition, osrm-customize and
   osrm-routed, including their object/static dependencies.
4. Audit actual exported compile commands using the existing v8 warning checks.
   Reject any forced header other than the single inherited cstdint include.
5. Record compiler/standard-library macros, selected compiler version and actual
   dependency versions. Verify vector/cstdint availability and Boost linking.
6. Compile the pristine suffix header as a labelled baseline negative probe,
   then require the corrected header to compile with real CMake include/define
   flags. Baseline failure is NOT automatically classified as a terminal build
   error; failures of required/corrected probes do stop setup.
7. Discover missing-direct-include candidates throughout owned headers. These
   lexical hints are NOT verified defects. Prioritize headers reachable through
   quoted includes from the four-target source closure and run standalone syntax
   probes with actual project flags (without leaked per-source warning exceptions).
   The inventory/reachability pass is not a formal C++ parser or proof of every
   preprocessor configuration. Compiler results, not text patterns, decide pass.
8. A blocked, failed, timed-out or incomplete header audit prevents the full
   build. Budget: 256 candidates, 300 seconds, 45 seconds per compiler probe.
   New problems require reviewed evidence, not automatic source changes or a
   growing forced-header list. JSON retains all candidate and probe diagnostics.
9. Only after preflight passes run the four existing native targets serially.
   Require all binary/version/help/library checks and pristine/disposable-source
   integrity checks before accepting setup. The parent resource monitor remains.

The original/required probe labels, input, commands, stdout/stderr and exit codes
are retained. Read `header-preflight.json`, `suffix-*-probe.json`,
`compiler-stdlib.json`, `header-source-manifest.json`, `compile-compatibility.json`
and full logs together; do not treat the first baseline error as the final cause.
CMake File API replies and the patch are copied to Drive on failure as well.

## Local audit findings and limits

The frozen source inventory found **188 candidate headers**, not 188 compiler
defects. No additional changes were made from those hints. The evidence-backed
missing includes corrected by the workflow are cstdint (earlier confirmed
coordinate failure) and vector (the new suffix failure).

Real Windows MinGW 8.1.0 syntax checks reproduced the missing-vector error using
the exact frozen member declaration and its standard includes. Adding vector
passed. This isolated reproduction deliberately omits Boost. Attempts to compile
the complete frozen suffix header were blocked by missing host Boost headers;
they are NOT reported as passes or used to infer additional required includes.
The Linux/Boost-backed full-header and target audit must pass in Colab.

The approved private CMake 3.31.10 tool is reused for a minimal host fixture. Its
real File API reply verifies four executable roots and object dependencies; its
generated compile databases exercise the inherited source-scope guards for the
actual host compiler and a SIMULATED GCC-11 CMake version branch. This does not
execute GCC 11 or compile Linux OSRM. No new tool was installed into backend or
system Python. Full native Linux compilation/OSM/server/Table activity was NOT
executed as part of this repair.

## Lower-maintenance prebuilt evaluation

Official release metadata lists 15 uploaded Node binding packages, with null
digest fields. Their contents were NOT downloaded and they are not validated as
a standalone four-CLI installation. The official package page does publish a
v5.27.1 Linux/amd64 OCI manifest:

`sha256:b1ca5d72da456e82f81b8732a095c2357b00710099efa844040d1eb40b4b5386`

https://github.com/project-osrm/osrm-backend/pkgs/container/osrm-backend/45826644?tag=v5.27.1
https://github.com/Project-OSRM/osrm-backend/releases/tag/v5.27.1

This is a trustworthy publisher/version/architecture candidate, NOT a locally
verified Colab installation. Manifest/layer bytes were not fetched/rehashed,
source labels/ELF loader/dependencies/profiles were not inspected, and Table API
compatibility was not run. Authorized OCI-layer extraction could avoid a Docker
daemon, but would require explicit approval, SHA verification of all layers and
executables, and genuine extraction/MLD/server/Table validation. No alternative
was downloaded, executed, selected, or silently substituted. Native stays selected.
See prebuilt-v9.json for published digests and outstanding checks.

## Controlled Colab execution

1. Preserve v1-v8 notebooks, ZIPs, failure records and logs. Upload v9 ZIP and
   notebook, use a CPU runtime, and enter the exact ZIP checksum in CONFIG.
2. Use fresh defaults `phase3d-colab-headers-001` and
   `/content/dhakanest_phase3d_headers`; never overwrite an old run's identity.
3. Explicitly set authorize_native_build=True to authorize APT/setup/preflight
   and build. Keep repair_only=True, authorize_runtime_smoke=False,
   allow_retry_failed_stage=False and native_retry_attempt=0.
4. Run through setup ONLY, then STOP. Do not use Run all. If preflight blocks,
   inspect its precise header diagnostics; do not force a full build past it.

For a retry in the SAME v9 run, inspect previous failure evidence first. With one
started setup attempt, explicitly authorize exact attempt 2:

```python
CONFIG['authorize_native_build'] = True
CONFIG['allow_retry_failed_stage'] = True
CONFIG['native_retry_attempt'] = 2
config_path.write_text(json.dumps(CONFIG, indent=2))
stage('setup')
```

Each retry uses fresh directories and retains failures. Changed source/header
policy requires a new run. All v8 runtime-smoke authorization and bulk-acquisition
blocks are inherited: v9 cannot acquire 30,000 routes, even with repair_only=False.
No OSM download, production, MongoDB, XGBoost, KNN, WSM, frozen benchmark-data or
methodology changes occur in this repair. Phase 3D is not complete.
