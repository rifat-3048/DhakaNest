# Phase 3D v7: two independent C++ compatibility problems

## Actual evidence, not a successful native build

User-provided excerpts identify original run `phase3d-colab-additive-apt-001`,
`setup-1792925153006014625.log`, and reported log SHA-256
`4871e777c71a3df501917dbaa23f0f333dd8775007d0a738226a51744424a3cd`.
The full original log is not available locally, so that log hash cannot be
independently verified. The excerpts, rather than invented full logs, support:

1. First probe error (log line 6203): `coordinate.hpp:66:34`, `std::int32_t`
   missing from namespace std. The probe failed, but was NOT the terminal failure:
   v6 supports a fallback compiler and the supplied log later reached compilation.
2. Terminal build error (log line 11834): GCC 11's `ext/new_allocator.h:145:26`
   diagnoses `operator delete` on unallocated object `result`, with
   `[-Werror=free-nonheap-object]`. The inline chain passes through vendored
   Mapbox variant destruction into `OSRM::Route`, `src/osrm/osrm.cpp:70:1`;
   `result` is declared at line 66. The failing target is `osrm-routed` via
   `CMakeFiles/osrm.dir/src/osrm/osrm.cpp.o`.
3. The trailing unrecognized `-Wno-*` options are notes, not evidence that those
   options caused the failure. They are not removed to disguise the real error.

The full compiler invocation and original CMake cache were not supplied. V7
records actual invocations and verifies exported compile commands, rather than
claiming these original details are known. No success for any individual v6
target is inferred from the fact the multi-target command reached osrm-routed.

## Source verification and selected correction

OSRM remains v5.27.1, commit
`4f3ee609ec1af40eb1f445c6706cfa5beb04c990`.
The exact pinned official files were read over HTTPS and hashed locally:

- `include/util/coordinate.hpp` SHA-256:
  `3effbc646484885e53150589c3287852c3133a85fe258de4035eddf08c9c4361`
- `cmake/warnings.cmake` SHA-256:
  `76719432644394a2f879beb20338192909ed0d051008a61cd633f8e3d4eab79b`

The header directly uses std::int32_t without including cstdint. The warning
configuration explicitly calls `add_warning(error)`, enabling global Werror.
Both hashes are enforced against the new runtime checkout before probing.

https://github.com/Project-OSRM/osrm-backend/blob/4f3ee609ec1af40eb1f445c6706cfa5beb04c990/include/util/coordinate.hpp
https://github.com/Project-OSRM/osrm-backend/blob/4f3ee609ec1af40eb1f445c6706cfa5beb04c990/cmake/warnings.cmake

For each available candidate compiler, v7 compares three inputs: the original
coordinate header, a disposable include-tree copy with one explicit cstdint
include added, and the unchanged source with `-include cstdint`. Both corrected
probes must pass. Failed original diagnostics remain in compiler-selection.json.
An already installed GNU >=11 is preferred; an already installed GCC 11 is the
fallback. No compiler is installed automatically by the corrected probe routine.

The real build uses the **unchanged official source** and build-only
`-include cstdint`. This is a standard-header dependency correction, not error
suppression, and preserves the existing clean-source integrity checks. The
candidate diff, original/candidate header hashes, policy hash, actual flags,
compiler choice and CMake command are recorded. Exported C++ compile commands
must contain the correction before any expensive build or binary publication.

## Independent warning exception

GCC 11 reports a standard-library deallocation diagnostic from optimized inlining
of a vendored tagged-variant destructor. GCC documents false positives in this
area, and variant-related examples exist. This makes a compatibility false
positive plausible, NOT proven for this exact OSRM binary:

https://gcc.gnu.org/pipermail/gcc-bugs/2022-December/806412.html
https://gcc.gnu.org/onlinedocs/gcc-11.1.0/gcc/Warning-Options.html

`gcc11_compat.cmake` is supplied as a recorded CMake project include. Only with
GNU major 11, it adds `-Wno-error=free-nonheap-object` to the single source
`src/osrm/osrm.cpp`. The warning remains enabled and visible. Global Werror and
every other diagnostic stay unchanged. No global `-Wno-error`, `-w`, broad
warning suppression or algorithm modification is permitted. Exported commands
are audited for the exact compiler/source/category scope. The compatibility hook
and build-override JSON receive checksums.

This is a narrowly bounded research build exception supported by the supplied
diagnostic, not a declaration that a real memory defect has been ruled out.
A Linux reproduction/sanitizer investigation is still required to prove that.
Other warnings/errors remain fatal and need separate evidence, not auto-demotion.

## Local validation limits

The existing Ubuntu WSL distribution was checked with approval, but cannot start:
`HCS_E_SERVICE_NOT_AVAILABLE` (required virtualization feature unavailable).
No Linux APT/probe/native build was run. The optional real host smoke checks
only the cstdint forced-include flag with Windows MinGW, NOT OSRM or Linux Boost.
Unit tests use explicitly synthetic compiler fixtures; they are not Linux results.

All four real tools must compile and then pass version/help/ldd validation:
osrm-extract, osrm-partition, osrm-customize and osrm-routed. Existing v6 validation
and clean-source checks remain in force. No native-build success is claimed.

## Safe new-run instructions

1. Keep all v6 records and logs. Upload the v7 ZIP and notebook. Use a CPU runtime
   with the new default run ID `phase3d-colab-cstdint-001` and local root
   `/content/dhakanest_phase3d_cstdint`. Enter the exact v7 ZIP checksum in CONFIG.
2. The existing Python 3.12/3.13 isolated setup, 33-dependency locks/hashes,
   checksum import, pip check, resource limits and additive-only APT are inherited.
   Existing Boost 1.83 is retained in the affected runtime.
3. Explicitly set `authorize_native_build=True` when ready. Keep
   `repair_only=True`, `allow_retry_failed_stage=False`, `native_retry_attempt=0`.
   Run through setup ONLY, then STOP. Do not use Run all or acquire routing.
4. Inspect full setup logs and the new `*.compatibility-diagnostics.json`, which
   distinguishes recovered probe errors from terminal build errors and captures
   exact Werror categories. Drive `native_attempts/<attempt>/` keeps source/patch/
   policy/override checksums, probe comparisons, CMake cache and compile commands.

For a controlled retry in the SAME v7 run, first inspect its failure evidence.
With one started attempt, use the exact next attempt number:

```python
CONFIG['authorize_native_build'] = True
CONFIG['allow_retry_failed_stage'] = True
CONFIG['native_retry_attempt'] = 2
config_path.write_text(json.dumps(CONFIG, indent=2))
stage('setup')
```

Every retry uses a new source/build directory; no old records are deleted.
Completed stages are immutable. A changed compatibility policy requires a new
run, never rewriting historical configuration. The inherited native-build spec
and the additional compatibility-policy hash jointly bind the new run.

All changes are research-only. No production application, database, predictions,
KNN, WSM, frozen datasets, routing acquisition or scientific methodology changes.
Phase 3D is not complete and Phase 4 is not started.
