"""Document area anchors and generated offsets without claiming exact geocodes."""

from collections import Counter
from ..common import backend
from ..validate_coordinates import coordinate_report, validate_coordinate


def validate_geography(properties, destinations):
    backend()
    from app.services.academic_inventory_service import LOCATION_ANCHORS
    anchors = {(a["broad_area"], a["micro_area"]): a for a in LOCATION_ANCHORS}
    for row in properties:
        validate_coordinate(row)
        anchor = anchors.get((row["broad_area"], row["model_micro_area"]))
        if anchor is None or abs(row["latitude"] - anchor["latitude"]) > .0015001 or abs(row["longitude"] - anchor["longitude"]) > .0015001:
            raise ValueError("Generated coordinate differs from original anchor-offset bounds.")
        proof = row["provenance"]
        if proof.get("independently_verified") is not False or proof.get("location_kind") != "synthetic_area_anchor_offset":
            raise ValueError("Unsupported precise/verified property geocode claim.")
    for destination in destinations:
        proof = destination["provenance"]
        if proof.get("independently_verified") is not False or proof.get("location_kind") != "area_anchor":
            raise ValueError("Unsupported institution verification claim.")
    report = coordinate_report(properties, destinations)
    report["limitation"] = "Synthetic coordinates retain original seeded offsets; destinations remain area proxies, not institutions. No external verification performed."
    report["property_coordinate_precision"] = "synthetic offsets around 12 repository area anchors"
    report["independently_verified_properties"] = 0
    report["independently_verified_destinations"] = 0
    report["destination_coordinate_duplicates"] = len(destinations) - len({(d["latitude"], d["longitude"]) for d in destinations})
    report["property_type_counts"] = dict(Counter(p["property_type"] for p in properties))
    return report
