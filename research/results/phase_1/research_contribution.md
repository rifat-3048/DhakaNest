# DhakaNest Research Contribution

## Problem

Rental portals commonly begin with a neighborhood selected by the user. That
area-first workflow assumes the renter already knows which neighborhood best
balances work, education, health care, family, and other recurring destinations.
In Dhaka, road travel does not map cleanly to straight-line distance. A home in
a familiar area may satisfy property filters while producing poor journeys to
one or more important destinations.

DhakaNest addresses a different decision problem: given a tenant's mandatory
housing needs, one to three important destinations, destination priorities, and
commute limits, which eligible homes form the most suitable ranked set?

## Proposed contribution

The proposed research object is a **destination-first, multi-destination,
commute-constrained, rent-reasonableness-aware hybrid rental recommendation
framework**. Its implemented pipeline is:

1. Validate tenant requirements and destination coordinates.
2. Keep approved, available properties satisfying mandatory budget, property,
   room, size, furnishing, move-in, and must-have amenity rules.
3. Obtain road-network time and distance from OSRM.
4. Enforce expressed maximum commutes and calculate importance-weighted
   destination accessibility.
5. Use Content-Based KNN to select structurally similar candidates.
6. Rank the shortlist with WSM v4 over Location, Budget, Space, Amenities, and
   Rent Fairness according to normalized tenant priorities.
7. Explain the strongest candidate-specific reasons and retain an auditable
   recommendation snapshot.

WSM v4 Budget Suitability is
`clamp(1 - advertised_rent / maximum_budget, 0, 1)`. Travel cost and estimated
monthly spending are displayed information, not ranking criteria.

## Why this is more than filtering

Mandatory filters only decide eligibility. Destination scoring quantifies
road-network access across several places; KNN reduces the eligible universe to
properties resembling expressed housing needs; WSM then makes tradeoffs among
five interpretable criteria. A property can therefore be eligible yet rank
below another because the second better reflects the tenant's priorities.

Multiple destinations matter because optimizing only the closest or most
important destination can shift travel burden to every other recurring trip.
The research must test whether representing those tradeoffs improves relevance
and decisions rather than assuming that it does.

KNN and WSM are intentionally separate. KNN is a candidate-selection stage in
a content feature space. Its cosine similarity is not a sixth WSM criterion.
WSM is a preference-sensitive reranker over the selected candidates. Separate
KNN-only, WSM-only, no-KNN, and full conditions are required to identify their
respective effects.

## Role of XGBoost

XGBoost predicts a reference monthly rent from property and location features.
Administrators store a rent assessment when approving a listing; recommendation
ranking reads the stored percentage difference and never reruns prediction.
Rent Fairness therefore means model-based rent reasonableness, not demographic
fairness and not a guarantee of market value. Its usefulness depends on model
error, subgroup reliability, data freshness, and empirical ranking contribution.

## Implementation versus research claims

| Status | Claim |
|---|---|
| Implemented and verified in code | Hard filtering, OSRM adapters, commute constraints, destination scoring, KNN, five-factor WSM v4, stored rent assessment, explanations, and history |
| Existing preliminary evidence | Eight profiles, twelve listings, and 96 labels with historical NDCG values tied to older scoring periods |
| Potential contribution requiring evidence | Destination-first multi-destination formulation improves relevance or user decisions over fair area-first and simpler controls |
| Potential contribution requiring evidence | KNN plus personalized WSM is more useful than either stage alone |
| Potential contribution requiring evidence | Stored rent reasonableness improves recommendations without introducing unacceptable model-error effects |
| Scientifically unproven | Current WSM v4 recommendation quality, robustness, independent human relevance, user benefit, external generalization, and subgroup rent-model reliability |

Combining known algorithms is not itself novelty. A defensible contribution
requires a precise problem formulation, fair operational baselines, component
ablations, independent labels, statistical uncertainty, and evidence that the
integrated destination-first design produces useful effects under declared
conditions.
