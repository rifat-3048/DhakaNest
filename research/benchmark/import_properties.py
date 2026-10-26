"""Extract literal seed definitions without importing a database seed script.

An authorized, de-identified JSON export can also be imported offline. This
utility never connects to MongoDB. Missing assessments are kept missing.
"""

import argparse
import ast
from datetime import date, timedelta
import hashlib

from .common import ROOT, read, write_once

SOURCE = "backend/scripts/seed_recommendation_listings.py"
TYPES = {"real_market_observation", "academic_synthetic", "derived_transformed", "evaluation_fixture"}
FIELDS = {
    "title", "description", "property_type", "furnishing_status", "broad_area",
    "model_micro_area", "latitude", "longitude", "area_sqft", "bedrooms",
    "bathrooms", "asking_rent_bdt", "amenities", "available_from", "status", "is_available",
}
ASSESSMENT_FIELDS = {
    "asking_rent_bdt", "predicted_rent_bdt", "difference_percent", "difference_bdt",
    "estimated_lower_bdt", "estimated_upper_bdt", "fairness_status", "model_route",
    "model_version", "target_strategy", "checked_at", "input_snapshot",
}


def seed_definitions():
    tree = ast.parse((ROOT / SOURCE).read_text(encoding="utf-8"))
    constants = {}

    def literal(node):
        if isinstance(node, ast.Name):
            return constants[node.id]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sorted":
            if len(node.args) != 1 or node.keywords:
                raise ValueError("Unsupported seed expression.")
            return sorted(literal(node.args[0]))
        if isinstance(node, ast.List):
            return [literal(item) for item in node.elts]
        if isinstance(node, ast.Dict):
            return {literal(k): literal(v) for k, v in zip(node.keys, node.values)}
        return ast.literal_eval(node)

    for node in tree.body:
        names = ([t.id for t in node.targets if isinstance(t, ast.Name)]
                 if isinstance(node, ast.Assign) else
                 [node.target.id] if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) else [])
        for name in names:
            if name in {"CANONICAL_AMENITIES", "SEED_LISTINGS"}:
                constants[name] = literal(node.value)
    return constants["SEED_LISTINGS"]


def reconstruct_seed_fixtures():
    """Freeze dates/status as fixture assumptions, not claims about live records."""
    result = []
    for definition in seed_definitions():
        row = {k: v for k, v in definition.items() if k in FIELDS}
        row.update(
            id=definition["seed_key"], status="approved", is_available=True,
            available_from=(date(2026, 10, 25) + timedelta(days=definition["available_offset_days"])).isoformat(),
            rent_assessment=None,
            provenance={
                "source_type": "evaluation_fixture", "source_reference": SOURCE,
                "source_sha256": hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
                "coordinate_precision": "area_anchor_not_property_geocode",
                "coordinate_source": "Repository seed: OSM Nominatim, claimed verified 2026-08-26; not independently reverified",
                "observed_at": None, "license_or_basis": "Repository development fixtures; not market observations",
                "transformations": "Exclude address/contact data; set fixture base date 2026-10-25 plus seed offset; assume approved/available; no assessment invented",
            },
        )
        result.append(row)
    return result


def import_export(rows):
    """Allowlist fields and hash source identifiers. No names or contacts survive."""
    result = []
    for item in rows:
        provenance = item.get("provenance", {})
        if provenance.get("source_type") not in TYPES:
            raise ValueError("Every exported listing needs explicit provenance classification.")
        for field in ("source_reference", "coordinate_precision", "coordinate_source", "license_or_basis"):
            if not isinstance(provenance.get(field), str) or not provenance[field].strip():
                raise ValueError(f"Missing provenance field: {field}")
        if provenance["source_type"] == "real_market_observation" and not provenance.get("observed_at"):
            raise ValueError("Real observations require observation timestamp and verifiable source.")
        identifier = item.get("id", item.get("_id"))
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("Expected exported string listing ID.")
        assessment = item.get("rent_assessment")
        if assessment is not None and not isinstance(assessment, dict):
            raise ValueError("Invalid assessment object.")
        row = {k: v for k, v in item.items() if k in FIELDS}
        row.update(id="listing-" + hashlib.sha256(identifier.encode()).hexdigest()[:24],
                   provenance={key: provenance.get(key) for key in (
                       "source_type", "source_reference", "coordinate_precision", "coordinate_source",
                       "license_or_basis", "observed_at", "source_sha256", "transformations")},
                   rent_assessment={k: v for k, v in assessment.items() if k in ASSESSMENT_FIELDS} if assessment else None)
        # Nested snapshots have an explicit structural allowlist as well.
        if row["rent_assessment"] and "input_snapshot" in row["rent_assessment"]:
            snapshot = row["rent_assessment"]["input_snapshot"]
            if not isinstance(snapshot, dict):
                raise ValueError("Invalid assessment input snapshot.")
            row["rent_assessment"]["input_snapshot"] = {k: snapshot[k] for k in (
                "broad_area", "model_micro_area", "area_sqft", "bedrooms", "bathrooms", "asking_rent_bdt") if k in snapshot}
        result.append(row)
    from .validate_properties import validate_properties
    validate_properties(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Authorized de-identified JSON listing array")
    parser.add_argument("output", help="New path under research/; never overwrite benchmark_v1")
    args = parser.parse_args()
    write_once(args.output, import_export(read(args.input)))


if __name__ == "__main__":
    main()
