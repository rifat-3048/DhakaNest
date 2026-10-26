# Benchmark Feasibility

Supporting frozen evidence: research/datasets/benchmark_v1_1/. Status: partially complete; genuine routing remains missing. No final ranking benchmark, human labels or Phase 4 work was performed.

Structural diversity is present across all four types, canonical furnishings,
many amenity combinations and BDT 6,000-
198,000 model-linked synthetic rents. Twelve area-anchor
regions and 200 distinct scenario profiles are retained. Hard-filter coverage
supports ten-way competition for 200 profiles
before commuting. Difficult/sparse cases stay in the dataset and are reported.

| Future comparison | Current support |
|---|---|
| Structural eligibility / candidate coverage | Supported offline; measured, not recommendation performance |
| KNN selection experiment | Structurally prepared; full pipeline partially supported until routing/labels |
| Five-criterion WSM v4 | Assessments and inputs prepared; ranking evaluation unsupported until routes/labels |
| Destination importance / max commute | Unsupported as an experiment without genuine frozen OSRM |
| Rent Fairness | Arithmetic/inference integrity supported; market validity limited by model-rent circularity |
| Area-first comparison | Structural/area inputs prepared; common routing/labels missing for full comparison |
| Single-destination control | Frozen request definitions prepared; experiments not executed, routing/labels missing |
| Journey-aware baseline | Protocol specified; not implemented, needs routes and independent labels |

Geographic coordinates are approximate synthetic offsets, not real property
observations; destinations are area proxies, not verified hospitals/workplaces.
Profile families are held out together but share inventory/geographic scope.
No real-market or IID generalization, causal component benefit, statistical
superiority, or actual commute variation has been demonstrated. Near-boundary
rent/size and random pool selection is a design feature, not human relevance.

Next evidence gate: separately authorized OSRM capture, new integrated version,
repeat commute competition, expert/pilot review of scenarios and workload,
then explicit Phase 4 authorization. No comparative outcomes were examined.
