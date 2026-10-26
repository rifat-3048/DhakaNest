# Endpoint Authorization Audit

Status: partially complete. Endpoint acquisition is blocked by missing explicit workload permission and verified endpoint-specific matrix limits. No live route request was sent.

Selected application endpoint is https://router.project-osrm.org, from the
application default (no current environment/.env ROUTING_BASE_URL override).
Only the endpoint selection was inspected; no secrets were printed or used.
This is a public demonstration service. The OSRM wiki connects this hostname to
FOSSGIS; the operator's about page identifies FOSSGIS as owner/operator.

The [operator policy](https://routing.openstreetmap.de/about.html) gives a
one-request/second ceiling and disallows scraping/heavy usage. This does not
establish permission for 30,000 matrix cells. The full German policy page was
access-denied, not treated as reviewed. No current request was sent to test
deployment support or limits. Table duration/distance support is documented at
the OSRM API level, not experimentally verified on the configured deployment.
Maximum deployed coordinates/cells are unknown. The 52/480 planned limits are
assumptions to revise after operator confirmation, not a grant of permission.

The operator page advertises engine v5.27.1, worldwide car/bike/foot coverage and
OSM-derived graphs; no current per-response engine/extract version was captured.
Captured versions remain unknown. No authorized private/local endpoint or map
extract/runtime was established, and none was installed/probed/deployed.

Required: user approval and operator evidence for endpoint, complete workload,
rate, matrix bounds and no unapproved billing/infrastructure. Prefer an existing
controlled instance. New self-hosting/downloads require separate authorization.
Evidence references and exact scope hash are required before the opt-in tool
will execute. This task does not authorize bulk requests to the demo.

References: [OSRM demo wiki](https://github.com/Project-OSRM/osrm-backend/wiki/Demo-server),
[API semantics](https://project-osrm.org/docs/v26.4.0/http).
Evidence: benchmark/phase3c/endpoint_audit.json; routing/request_plan.json.
Inputs: research/datasets/benchmark_v1_1 (checksum-referenced unchanged) and benchmark_v1_2/routing. Code: research/benchmark/phase3c.
