"""Production hard-filter reuse with per-listing sequential exclusion reasons."""

from .common import backend, request_schema

STAGES = ["after_budget", "after_property_type", "after_bedrooms", "after_bathrooms",
          "after_area", "after_furnishing", "after_move_in", "after_must_have_amenities"]


def construct_candidates(profile, properties, routes):
    service = backend()
    from app.services.listing_eligibility import is_recommendation_eligible
    request = request_schema().model_validate(profile["request"])
    base = [r for r in properties if is_recommendation_eligible(r)]
    result = service.filter_recommendation_candidates(base, request)
    hard = [r.id for r in result.candidates]
    exclusions = {r["id"]: "base_eligibility" for r in properties if not is_recommendation_eligible(r)}
    # Reuse the production predicates via singleton calls instead of duplicating
    # budget, move-in or amenity semantics in research code.
    for row in base:
        if row["id"] not in hard:
            summary = service.filter_recommendation_candidates([row], request).filter_summary.model_dump()
            exclusions[row["id"]] = next(stage for stage in STAGES if summary[stage] == 0)
    from app.services.routing_service import RouteMatrix, RouteMeasurement
    index = {(r["listing_id"], r["destination_id"]): r for r in routes}
    matrix = RouteMatrix(routes={
        key: (RouteMeasurement(key[0], key[1], row["distance_meters"], row["duration_seconds"])
              if row["status"] == "valid" else None)
        for key, row in index.items() if row["status"] in {"valid", "unreachable"}
    })
    production_commutes = service.apply_commute_routes(part_one=result, preferences=request, route_matrix=matrix)
    production_feasible = {row.id for row in production_commutes.candidates}
    accounted, complete, feasible, unavailable, unreachable, over_limit = [], [], [], [], [], []
    available_pairs = 0
    for identifier in hard:
        cells = [index.get((identifier, d.id)) for d in request.important_destinations]
        available_pairs += sum(c is not None and c["status"] in {"valid", "unreachable"} for c in cells)
        if any(c is None or c["status"] in {"missing", "error"} for c in cells):
            unavailable.append(identifier)
            continue
        accounted.append(identifier)
        if any(c["status"] == "unreachable" for c in cells):
            unreachable.append(identifier)
            continue
        complete.append(identifier)
        if identifier in production_feasible:
            feasible.append(identifier)
        else:
            over_limit.append(identifier)
    return dict(
        profile_id=profile["id"], pre_filter_ids=[r["id"] for r in properties],
        base_eligible_ids=[r["id"] for r in base], hard_filter_ids=hard,
        exclusions=exclusions, filter_summary=result.filter_summary.model_dump(),
        required_route_pairs=len(hard) * len(request.important_destinations), available_route_pairs=available_pairs,
        routing_accounted_ids=accounted, routing_complete_ids=complete, commute_feasible_ids=feasible,
        missing_route_ids=unavailable, unreachable_ids=unreachable, over_commute_limit_ids=over_limit,
        feasibility_status="verified" if not unavailable else "unknown_missing_routes",
        knn_selected_ids=None, wsm_ranked_ids=None,
        end_to_end_universe="pre_filter_ids; apply method-declared constraints independently",
        controlled_ranking_pool="commute_feasible_ids only when feasibility_status=verified; never KNN-selected",
    )
