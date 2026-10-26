# Benchmark Readiness

Status: BLOCKED. Research-only implementation exists, but host virtualization/engine prerequisites prevent genuine local OSRM execution. No route measurements were manufactured.

| Objective | Readiness |
|---|---|
| Structural candidate coverage | Ready with limitations: synthetic inventory |
| Full-pipeline KNN comparison | Not ready: missing road evidence and independent labels |
| WSM v4 ranking evaluation | Not ready: missing routes/labels |
| Destination-importance / commute ablations | Not ready |
| Rent Fairness arithmetic | Ready with limitations: model-linked synthetic rents |
| Rent Fairness ranking validity | Not ready without independent judgments |
| Single-destination / journey-aware / area-first experiments | Not ready |
| Independent human annotation | Not ready: incomplete commute material |

Properties remain synthetic offsets around twelve area anchors; destinations
are area references, not verified institution addresses. Even genuine future
OSRM estimates would model driving on frozen OSM, not observed Dhaka congestion
or verified door-to-door travel. No traffic-aware or market-wide generalization
is established. A controlled synthetic road-network benchmark needs a separate
real-market study for stronger validity. No recommendation quality metrics ran.
Source tools: research/routing/osrm_local/. Data: benchmark_v1_3 reference overlay and its immutable benchmark_v1_2/v1_1 parents.
