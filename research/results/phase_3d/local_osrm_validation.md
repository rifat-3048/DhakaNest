# Local OSRM Validation

Status: BLOCKED. Research-only implementation exists, but host virtualization/engine prerequisites prevent genuine local OSRM execution. No route measurements were manufactured.

Implemented pinned official-image candidate ghcr.io/project-osrm/osrm-backend:v26.10.0
(release verified; image availability/runtime not tested), extract/partition/customize
MLD commands, isolated Compose startup, genuine local smoke and shutdown guidance.
Compose config validation passed without starting the engine. No service was
started and no image was pulled. Installed OSRM version/profile checksum remains
unknown until existing-image inspection and binary checks can run.

Preparation uses the exact locally inspected immutable image ID and records
car.lua hash/binary version; network is disabled and resource limits enforced.
Serving uses the same ID, read-only graph mount, localhost:5001 only, MLD and
max-table-size 100. Graph/source checksums and inspected project container
identity/binding/mount/command are required before smoke. A four-cell Table
smoke preserves raw data/snapping metadata and at least one valid road route.
No such genuine smoke succeeded or failed here: it was not attempted.
Actual graph/preprocessing CPU/RAM/disk usage and snapping behavior are unknown.
Mocked tests are not real infrastructure validation. Source tools: research/routing/osrm_local/. Data: benchmark_v1_3 reference overlay and its immutable benchmark_v1_2/v1_1 parents.
