# Phase 3 Manifest Revision

The first seal followed passing runs of 75 research tests and 96 backend tests.
A subsequent repetition exposed an intermittent Windows clock-resolution issue:
mocked immediate retries could generate identical `time.time_ns()` failure-log
filenames. Exclusive writing correctly refused the collision, failing that test.

The acquisition logger now uses retry number plus a UUID for unique immutable
failure records. Its existing test fixes the clock to a constant and requires
three distinct failure logs. This changes neither frozen dataset content nor
production code, routing calculations, candidate filtering or rankings.

The original configuration and manifest are retained without overwrite as
superseded first-pass metadata. `phase_3_manifest_v2.json` is the authoritative
final seal, binding the corrected source, tests, this revision note, current
reports, original seal files, and unchanged benchmark evidence. Verification
defaults to the latest manifest revision. Phase 0-2 seals remain unchanged.
