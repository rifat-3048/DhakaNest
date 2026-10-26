"""Coverage-driven synthetic scenarios; no claims of real tenant elicitation."""

from collections import Counter
import random

from .common import SEED, digest, request_schema

# Each family encodes a substantive need. Contexts rotate existing area anchors;
# they do not claim that an anchor is a particular university/hospital/workplace.
FAMILIES = [
    {"id": "student", "need": "University student: private room or sublet, modest rent", "types": ["room", "sublet"], "budget": 16000, "beds": 1, "baths": 1, "area": 550, "priorities": [5, 5, 2, 2, 3]},
    {"id": "professional", "need": "Young professional: furnished compact home", "types": ["apartment", "sublet"], "budget": 35000, "beds": 1, "baths": 1, "area": 850, "priorities": [5, 3, 2, 3, 3]},
    {"id": "family", "need": "Family with children: multiple bedrooms and reliable building services", "types": ["apartment", "house"], "budget": 50000, "beds": 3, "baths": 2, "area": 1450, "priorities": [4, 3, 5, 4, 3]},
    {"id": "hospital_access", "need": "Healthcare-access household; destinations are area proxies, not verified hospital POIs", "types": ["apartment", "sublet"], "budget": 40000, "beds": 2, "baths": 2, "area": 1000, "priorities": [5, 3, 3, 4, 3]},
    {"id": "multi_worker", "need": "Two-worker household: competing workplace-area journeys", "types": ["apartment", "house"], "budget": 45000, "beds": 2, "baths": 2, "area": 1200, "priorities": [5, 4, 3, 2, 3]},
    {"id": "budget_constrained", "need": "Strictly budget-constrained tenant accepting compact homes", "types": ["room", "sublet", "apartment"], "budget": 12500, "beds": 1, "baths": 1, "area": 500, "priorities": [3, 5, 1, 1, 4]},
    {"id": "flexible_budget", "need": "Flexible-budget household seeking larger homes", "types": ["apartment", "house"], "budget": 70000, "beds": 3, "baths": 3, "area": 1900, "priorities": [4, 2, 4, 4, 3]},
    {"id": "strict_commute", "need": "Strict commute limits with modest structural requirements", "types": ["apartment", "sublet", "room"], "budget": 30000, "beds": 1, "baths": 1, "area": 800, "priorities": [5, 3, 2, 2, 2]},
    {"id": "size_amenities", "need": "Space and amenities prioritized over low rent", "types": ["house", "apartment"], "budget": 65000, "beds": 3, "baths": 2, "area": 2000, "priorities": [2, 2, 5, 5, 3]},
    {"id": "rent_reasonableness", "need": "Tenant prioritizing rent reasonableness over premium features", "types": ["apartment", "house", "sublet"], "budget": 40000, "beds": 2, "baths": 1, "area": 1100, "priorities": [3, 4, 3, 2, 5]},
]


def destinations_from_properties(properties):
    return [dict(
        id=f"destination-{i + 1:02d}", destination=f"{p['broad_area']} / {p['model_micro_area']} area anchor",
        latitude=p["latitude"], longitude=p["longitude"], broad_area=p["broad_area"], model_micro_area=p["model_micro_area"],
        provenance={"coordinate_source": p["provenance"]["coordinate_source"],
                    "coordinate_precision": "area_anchor_not_verified_institution",
                    "source_reference": p["provenance"]["source_reference"]},
    ) for i, p in enumerate(properties)]


def generate_profiles(destinations, seed=SEED):
    if len(destinations) < 3:
        raise ValueError("At least three evidenced destination anchors are required.")
    schema = request_schema()
    rng = random.Random(seed)
    family_order = [f["id"] for f in FAMILIES]
    rng.shuffle(family_order)
    dev_families = set(family_order[:3])
    profiles = []
    for family_index, family in enumerate(FAMILIES):
        # Five need conditions x four geographic contexts per scenario family.
        for condition in range(5):
            for context in range(4):
                index = condition * 4 + context
                count = 2 + index % 2 if family["id"] == "multi_worker" else 1 + (index + family_index) % 3
                places = []
                for d in range(count):
                    anchor = destinations[(family_index + context * 3 + d * 5) % len(destinations)]
                    places.append({k: anchor[k] for k in ("id", "destination", "latitude", "longitude")})
                    places[-1].update(
                        preference=1 + (condition + d) % 5,
                        max_commute_minutes=(15, 20, 25, 30, 35)[condition] if family["id"] == "strict_commute" else (30, 45, 60, 90, None)[condition],
                        travel_days_per_month=(8, 12, 20, 22, 26)[(condition + d) % 5],
                    )
                budget = family["budget"] + (0, 2500, 5000, 7500, 10000)[condition]
                furnishing = (["furnished", "semi_furnished"] if family["id"] == "professional"
                              else [[], ["unfurnished"], ["semi_furnished"], ["furnished"], []][condition])
                must = (["Lift", "Generator"] if family["id"] == "size_amenities" else
                        [[], ["CCTV"], ["Balcony"], [], ["Backup Water Supply"]][condition])
                request = dict(
                    important_destinations=places, minimum_rent_bdt=None if condition % 2 == 0 else 4000,
                    maximum_rent_bdt=budget,
                    over_budget_percent=0 if family["id"] == "budget_constrained" else (0, 5, 10, 0, 10)[condition],
                    property_types=family["types"], minimum_bedrooms=family["beds"], minimum_bathrooms=family["baths"],
                    preferred_area_sqft=family["area"] + (0, 100, 200, 300, 400)[condition],
                    minimum_area_sqft=None if condition < 3 else family["area"] * 0.6,
                    maximum_area_sqft=None if condition != 4 else family["area"] * 2,
                    furnishing_statuses=furnishing, desired_move_in_date=("2026-11-01", "2026-11-15", "2026-12-01", None, "2027-01-01")[condition],
                    household_size=1 if family["beds"] == 1 else family["beds"] + 1,
                    must_have_amenities=must, nice_to_have_amenities=[a for a in ["Lift", "Parking", "CCTV"] if a not in must],
                    priorities=dict(zip(("location", "budget", "space", "amenities", "rent_fairness"), family["priorities"])),
                )
                request = schema.model_validate(request).model_dump(mode="json")
                profiles.append(dict(
                    id=f"tenant-{family_index + 1:02d}-{index + 1:02d}", family=family["id"],
                    source_type="synthetic_scenario", scenario=family["need"],
                    condition=condition, geographic_context=context, group_id=family["id"],
                    partition="development" if family["id"] in dev_families else "final_held_out",
                    preferred_broad_area=places[0]["destination"].split(" / ")[0],
                    preferred_micro_area=destinations[(family_index + context * 3) % len(destinations)]["model_micro_area"],
                    request=request,
                ))
    validate_profiles(profiles, destinations)
    return profiles


def validate_profiles(profiles, destinations, expected=200):
    if len(profiles) != expected or len({p["id"] for p in profiles}) != expected:
        raise ValueError("Unexpected profile count or duplicate IDs.")
    schema = request_schema()
    anchors = {d["id"]: d for d in destinations}
    if len(anchors) != len(destinations) or any(not key for key in anchors):
        raise ValueError("Missing or duplicate destination IDs.")
    signatures, group_folds = set(), {}
    for p in profiles:
        request = schema.model_validate(p["request"])
        signature = digest(p["request"])
        if signature in signatures:
            raise ValueError("Duplicate tenant request.")
        signatures.add(signature)
        if p["partition"] not in {"development", "final_held_out"}:
            raise ValueError("Invalid partition.")
        previous = group_folds.setdefault(p["group_id"], p["partition"])
        if previous != p["partition"]:
            raise ValueError("Related scenario families leak across partitions.")
        if len({d.id for d in request.important_destinations}) != len(request.important_destinations):
            raise ValueError("Repeated destination in tenant request.")
        for d in request.important_destinations:
            a = anchors.get(d.id)
            if not a or (d.latitude, d.longitude) != (a["latitude"], a["longitude"]):
                raise ValueError("Destination reference or coordinates mismatch.")
        if set(request.must_have_amenities) & set(request.nice_to_have_amenities):
            raise ValueError("Conflicting amenity groups.")
    return profile_coverage(profiles)


def profile_coverage(profiles):
    def count(values):
        return dict(sorted(Counter(str(v) for v in values).items()))
    requests = [p["request"] for p in profiles]
    ds = [d for r in requests for d in r["important_destinations"]]
    return dict(
        count=len(profiles), family=count(p["family"] for p in profiles),
        partition=count(p["partition"] for p in profiles), destination_count=count(len(r["important_destinations"]) for r in requests),
        destination_importance=count(d["preference"] for d in ds), commute_limits=count(d["max_commute_minutes"] for d in ds),
        travel_days=count(d["travel_days_per_month"] for d in ds), budgets=count(r["maximum_rent_bdt"] for r in requests),
        flexibility=count(r["over_budget_percent"] for r in requests), property_types=count(t for r in requests for t in r["property_types"]),
        bedrooms=count(r["minimum_bedrooms"] for r in requests), bathrooms=count(r["minimum_bathrooms"] for r in requests),
        furnishing=count(t for r in requests for t in r["furnishing_statuses"]),
        preferred_area=count(r["preferred_area_sqft"] for r in requests),
        move_in=count(r["desired_move_in_date"] for r in requests),
        priorities={k: count(r["priorities"][k] for r in requests) for k in requests[0]["priorities"]},
        destination_references=count(d["id"] for d in ds),
        must_have=count(a for r in requests for a in r["must_have_amenities"]),
        nice_to_have=count(a for r in requests for a in r["nice_to_have_amenities"]),
        limitation="Grouped family split prevents near-copy leakage but holds entire need families out; this is scenario transfer, not IID or geographic holdout.",
    )
