# Geographic Verification

Supporting frozen evidence: research/datasets/benchmark_v1_1/. Status: partially complete; genuine routing remains missing. No final ranking benchmark, human labels or Phase 4 work was performed.

Represented broad areas: {'Banani': 210, 'Banasree': 210, 'Bashundhara R/A': 205, 'Dhanmondi': 210, 'Gulshan': 210, 'Khilgaon': 210, 'Lalmatia': 210, 'Mirpur': 210, 'Mohammadpur': 210, 'Motijheel': 205, 'Rampura': 205, 'Uttara': 205}.
The original generator's seeded +/-0.0015-degree offsets around 12 existing
repository anchors are preserved. All coordinates pass finite/Dhaka-bounds and
original offset checks; OSRM URLs use longitude,latitude. Unique property
coordinates: 2500; duplicate groups:
0. Destination definitions: 12 area anchors,
unchanged coordinates from Phase 3A.

Independently verified precise property geocodes=0; independently verified
institution endpoints=0. Each property explicitly identifies synthetic offset
precision, area label, source, verification method and absent independent date.
Destination provenance similarly identifies area proxies. The old seed claims
OSM verification on 2026-08-26; it is repository evidence, not fresh verification.
No external geocoding or invented exact institution/property location was used.

This can support an area-anchor synthetic scenario study once genuine routes
exist, not claims about actual address-level commutes or Dhaka-wide geographic
generalization. Any future precise-location study needs separately enabled
research lookup and verifiable coordinate evidence.

Evidence: geographic_coverage.json, destinations.json, property provenance,
route_pair_manifest.jsonl. No source precision was promoted to verified geocodes.
