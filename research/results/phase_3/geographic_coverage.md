# Geographic Coverage

Properties and destination definitions use twelve coordinate anchors already
present in the original repository seed: Mirpur/Pallabi, Dhanmondi,
Mohammadpur/Tajmahal Road, Uttara/Sector 7, Banasree/Block D,
Bashundhara R/A/Block C, Banani, Gulshan 2, Rampura/East Rampura,
Khilgaon/Tilpapara, Motijheel/Naya Paltan, and Lalmatia.

Each area contributes one fixture property and one destination anchor. Tenant
requests reference each destination 30-38 times. All coordinates pass finite
numeric checks and the declared Dhaka study box (latitude 23.5-24.1,
longitude 90.15-90.65). Swapped coordinates fail. Property coordinates are unique
within the 12 records; the destination coordinates intentionally reuse the same
anchors. Reusing anchors does not imply properties are actual destinations.

The source script claims OSM Nominatim verification on 2026-08-26. That is
repository provenance, **not fresh independent verification** in this phase.
There are 12 repository-claimed verified anchors and **zero independently
verified precise property or institution geocodes**. No coordinate jitter,
invented POI, geocoding request, or artificial geographic expansion was added.

Area anchors are proxies, not precise hospital/university/workplace locations.
Healthcare/student scenario names describe needs, not validated journey endpoints.
Routing from approximate origins to approximate destinations cannot establish
real address-level commute feasibility, even after acquisition.

Other Dhaka neighborhoods and within-area diversity remain unsupported. The
academic coverage summary and model routing registry cannot authenticate new
property coordinates. A future real-inventory snapshot needs explicit location
precision/provenance, concentration diagnostics, and privacy review. The current
shared-anchor partition is neither spatial holdout nor real-market validation.
