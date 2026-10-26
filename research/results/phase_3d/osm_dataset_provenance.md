# OSM Dataset Provenance

Status: BLOCKED. Research-only implementation exists, but host virtualization/engine prerequisites prevent genuine local OSRM execution. No route measurements were manufactured.

Candidate: [Geofabrik Bangladesh PBF](https://download.geofabrik.de/asia/bangladesh.html).
On 2026-10-25 the provider advertises 339 MB and data through
2026-10-24T20:20:51Z. Actual downloaded size, hash/date: UNKNOWN, not downloaded.
The changing latest URL is not frozen evidence. No fake PBF or graph was made.
The full country is preferred over an arbitrary city crop for connectivity;
all 2512 origin/destination coordinate bounds are {'latitude': [23.7257602, 23.8762989], 'longitude': [90.362855, 90.4302289]}.

The public provider polygon was inspected as documentation. No downloaded
polygon was frozen and full point containment has not been executed. Registration
requires the actual PBF and .poly under ignored runtime/, hashes both, and
checks every input point. Polygon containment still does not prove every route.
Preparation binds the exact image/profile and all output graph hashes.

Attribution: OpenStreetMap contributors; Geofabrik extract. Review [ODbL and
attribution requirements](https://www.openstreetmap.org/copyright) before
redistributing data/derived databases. Keep exact downloaded bytes and hashes;
do not commit extracts/graphs to Git. No 339-MB download or container-image pull
was started because usable infrastructure/resource readiness is not established.
Source tools: research/routing/osrm_local/. Data: benchmark_v1_3 reference overlay and its immutable benchmark_v1_2/v1_1 parents.
