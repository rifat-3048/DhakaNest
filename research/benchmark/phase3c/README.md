# Phase 3C Routing Evidence

The configured public demo is **not approved for this research workload**.
The operator forbids scraping/heavy usage and publishes one request/second as
a rate ceiling, not blanket permission for bulk matrices. Read endpoint_audit.json
and the Phase 3C authorization report. No routing request or deployment was run.

From the repository root:

```powershell
backend\.venv\Scripts\python.exe -m research.benchmark.phase3c.workflow --output research\datasets\benchmark_v1_2_reproduction
backend\.venv\Scripts\python.exe -m unittest discover -s research\tests
backend\.venv\Scripts\python.exe -m research.benchmark.phase3c.verify --verify-seal
```

The first command writes a new **offline overlay** only. It references immutable
Phase 3B inputs and hashes rather than copying the large property/candidate data.
All new output paths must be inside research and nonexistent. benchmark_v1_2
contains routing inputs, exact logical/physical mappings and explicit missing
statuses, not genuine frozen road measurements. Missing evidence is not zero
travel, unreachable status or a measured commute failure.

Keys use exact numeric coordinates, directed origin-to-destination order, and
profile. No rounding, geographic merging or inferred reverse route is used.
Inputs beyond the production URL's seven-decimal precision fail rather than
silently changing coordinates. Production Table URL generation and response
normalization are reused. Straight-line fallback cells and partial matrices are
rejected. Only verified double-null cells from an Ok response are unreachable.

## Approval Required Before Capture

Provide an authorized controlled/local or third-party endpoint and evidence of:
user workload approval, operator permission for the complete scope, verified
coordinate/cell/rate limits, no unapproved paid/infrastructure commitment, and
engine/map versions where known. Unknown versions remain unknown. The current
52-coordinate/480-cell limits are planning assumptions, NOT verified demo limits.
No local OSRM service, binaries, map extract or operator approval has been
established; no ports/services were probed and no software/data were installed.

Create a new approved configuration based on planning_configuration(). Bind
authorization.approved_scope_sha256 to make_plan(...)["scope_sha256"] and cite
reviewed evidence files under research by path/SHA-256. The code validates this
record but cannot authenticate an operator's identity or grant permission itself.
Evidence must be independently reviewed before setting approval flags. Never
put credentials or private keys into a URL or public configuration.

Only after those approvals, use the existing workflow entrypoint with explicit
--allow-network, --config APPROVED_CONFIG.json, --capture-directory NEW_OR_RESUMABLE
and a new --output. Do not execute this against the demo by assuming success or
low request rates establish permission. No example approval file grants access.

Transport is serial, bounded by configured matrices, timeout, rate, retries and
a persistent request ceiling. Each attempt is reserved on disk before sending;
interrupted attempts consume budget. Successes have immutable raw checkpoints;
resumes verify hashes and skip successes. Invalid requests are not retried,
temporary/unverified failures retain their classification, and redirects are
refused to avoid contacting an unapproved endpoint. Incomplete response payloads
are retained as failed evidence, never labeled valid. Completed idempotent
reruns use captures without sending requests. Never run concurrent writers to
the same capture directory.

RoutingFixture resolves exact physical results back to all logical pairs and
provides the existing frozen RoutingProvider interface. require_ready() blocks
incomplete evidence. A successfully approved capture lets workflow prepare
commute candidates and a new blinded pool without invoking KNN/WSM ranking or
metrics. Random-core sampling probabilities and mandatory-ineligible categories
are internal only; union probabilities are not invented. Annotation still needs
expert/pilot/ethics review and explicit Phase 4 authorization.

The intended completed study is a controlled synthetic, road-network-based
rental recommendation benchmark. Actual measurements, when authorized, would
be estimates for synthetic coordinate offsets and area anchors, not observed,
door-to-door, traffic-aware commutes or the entire Dhaka market.
