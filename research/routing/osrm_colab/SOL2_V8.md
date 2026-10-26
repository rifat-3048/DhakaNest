# Phase 3D v8: source-scoped Sol2 compilation compatibility

## Evidence and uncertainty

User-supplied v7 evidence identifies `phase3d-colab-cstdint-001`,
`setup-1792979266840993294.log`, reported SHA-256
`382f4df1d3f0b1b540037cfc51e495de2f1d312312cb9df4feec0443fdd4f382`.
The full original log and compile_commands.json are not present locally; their
hash/complete flags cannot be independently verified from excerpts alone.

The terminal warning is `[-Werror=array-bounds=]`, not free-nonheap-object.
Sol2 `sol.hpp:16151:49` reports char[23] against char[17] and char[30] against
char[18], inlined into `scripting_environment_lua.cpp:611/615`. Make identifies
`CMakeFiles/EXTRACTOR.dir/src/extractor/scripting_environment_lua.cpp.o` while
building osrm-extract. The earlier baseline coordinate-probe diagnostic was
recoverable; it does not explain the final build failure.

The exact pinned upstream Sol2 header was downloaded read-only and inspected:

https://github.com/Project-OSRM/osrm-backend/blob/4f3ee609ec1af40eb1f445c6706cfa5beb04c990/third_party/sol2-3.3.0/include/sol/sol.hpp

SHA-256: `ece673cd7b712e372f20d6be21225c4785796b12ef94a405a0d4e432c70e0e81`.
At 16145-16151 a string-like template branch passes `&key[0]` to lua_getfield.
At 16322-16328 probe_field_getter forwards Key to get_field. Index zero is not
itself an access at offset 23/30, but the differing template-array extents and
optimized inline chain need a reproduction/lifetime/null-termination audit to
rule out an actual bounds defect. Neither harmlessness nor a real defect is
proven here. Successful runtime smoke would still not be a memory-safety proof.

Matching upstream reports exist:

- https://github.com/Project-OSRM/osrm-backend/issues/6704
- https://github.com/Project-OSRM/osrm-backend/issues/6867
- https://github.com/ThePhD/sol2/issues/1535

The inspected reports do not provide a validated pinned backport proving this
exact case harmless. Therefore no guessed Sol2 patch/version change is made.

## Exact correction and command auditing

OSRM v5.27.1 commit `4f3ee609ec1af40eb1f445c6706cfa5beb04c990` remains pristine.
The v6 additive-only APT policy, installed Boost, isolated Python 3.12/3.13,
33 dependency pins/hashes, resource monitoring, checksums and retry controls stay.

`sol2_compat.cmake` sets a SOURCE property, never EXTRACTOR target flags or global
CXX flags. For GNU compilation only, `-Wno-error=array-bounds` applies solely to
`src/extractor/scripting_environment_lua.cpp`. The warning is still visible.
It includes the original unchanged gcc11_compat.cmake, retaining GCC-11-only
`-Wno-error=free-nonheap-object` solely for `src/osrm/osrm.cpp`. The build-only
`-include cstdint` remains on C++ commands. Global Werror is retained.

Before compilation AND before publishing binaries, the actual generated
compile_commands.json must pass compatibility_v2.verify_compile_commands:

- Both exact canonical source paths must appear; suffix-only matching is unsafe.
- Lua's output must belong to EXTRACTOR. Other EXTRACTOR sources must NOT receive
  its exception. Neither exception may leak into the other translation unit.
- Every C++ command needs the cstdint correction; all OSRM source commands need
  Werror. Missing flags, global demotions, disabled array-bounds diagnostics and
  unrelated warning demotions fail closed.
- Exact source/argument/target scopes, command-file SHA, hook and policy hashes
  persist in compile-compatibility.json on Drive, including during failed builds.

The pinned Sol2/header/warning-config hashes are checked before each clean build.
All four executables must compile and pass existing version/help/shared-library
validation before setup is accepted. No expensive automatic retry is introduced.

## Local tests: real generated commands, not a Linux build

With approval, a portable CMake 3.31.10 wheel was downloaded into research-only
runtime storage, verified and unpacked privately. Nothing was pip-installed into
the backend/system environment. Tool wheel SHA-256:
`f1ea1fe826355560e8976c3d5794d9357444209bc0e0d56676c71e6a571fd474`.

scope_smoke_v8 generated real compilation databases for a minimal C++ fixture
using Windows MinGW 8.1.0. It checked native GNU behavior and a SIMULATED GCC-11
CMake version branch. It did NOT execute a real GCC 11, compile OSRM, or validate
the Sol2 warning. Both databases demonstrate the intended SOURCE property scopes
and unchanged behavior on another EXTRACTOR source. Immutable raw commands and
reports are in `research/results/phase_3d_colab/sol2_scope_v4/`. Original generated
command databases are preserved byte-for-byte with their recorded checksums.

Earlier local scope attempts are retained. The first exposed Windows command
path parsing; the final verifier uses the Windows native command parser and
CMake's structured output field rather than losing backslashes through POSIX
escaping. Linux Colab command parsing remains POSIX. Portable tool files and
disposable fixtures are excluded from input archives, not research dependencies.

No Linux OSRM build, extraction, graph preprocessing, server or Table smoke was
executed during this repair. Prior WSL startup was unavailable; this task does
not repair WSL or start Docker. Test successes are not genuine road evidence.

## New-run procedure: setup only

1. Preserve all v7 logs, failed-stage records, notebooks and ZIPs. Upload v8 ZIP
   and open the v8 notebook in a CPU runtime.
2. Use new defaults `phase3d-colab-sol2-001` and
   `/content/dhakanest_phase3d_sol2`; enter the exact v8 ZIP SHA in CONFIG.
3. Explicitly set authorize_native_build=True when ready to permit installation
   and compilation. Keep repair_only=True, authorize_runtime_smoke=False,
   allow_retry_failed_stage=False, native_retry_attempt=0.
4. Run through setup ONLY, then STOP. Do not use Run all. Inspect the generated
   compile-compatibility.json and full diagnostics if the build fails again.

Controlled retry in the SAME v8 run requires prior failure inspection and exact
next attempt authorization. With one started attempt:

```python
CONFIG['authorize_native_build'] = True
CONFIG['allow_retry_failed_stage'] = True
CONFIG['native_retry_attempt'] = 2
config_path.write_text(json.dumps(CONFIG, indent=2))
stage('setup')
```

Never delete old records or reuse old build directories. A changed compatibility
policy requires a new run ID/local root, not mutation of completed evidence.

## Required runtime gate, not authorized by this repair

The warning's harmlessness is unproven. Before ANY future bulk acquisition, a
separately authorized `runtime-smoke` stage must successfully run the existing
actual-map extraction -> partition -> customize pipeline, start the owned local
server, and validate a real Table response (dimensions, values, snap metadata
and at least one reachable cell). Server shutdown is guaranteed on test failure.
The readiness record binds current binaries/libraries/profile/OSM/graph hashes.

Only after separate approval for map processing/server/Table activity:

```python
CONFIG['repair_only'] = False
CONFIG['authorize_runtime_smoke'] = True
config_path.write_text(json.dumps(CONFIG, indent=2))
stage('runtime-smoke')
```

This may download the configured OSM extract if not already frozen in that run;
do NOT run it as part of the present compilation repair. It uses one bounded
Table smoke batch, not acquisition of the full 30,000-pair workload.

V8's acquire command ALWAYS refuses bulk acquisition, even after smoke succeeds
or repair_only=False. A separate future request/approval is required to enable
acquisition after reviewing genuine smoke evidence. Old acquisition code is not
silently called. No Phase 4, production functionality, database, model, KNN, WSM,
frozen datasets, benchmark synthetic inventory or scientific methodology changed.
Phase 3D remains incomplete.
