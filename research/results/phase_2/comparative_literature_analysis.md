# Comparative Literature Analysis

`P` means present and verified in the cited source. `N` means absent in the
examined defined method or experiment, with that boundary stated. `U` means
unknown/not reported or inaccessible. `D` describes implemented DhakaNest
behavior, not an empirical advantage. Abstract omissions never become `N`.

## Closest housing systems

| Study | Inputs and strategy | Journey treatment | Evidence and boundary |
|---|---|---|---|
| P04 HomeFinder Revisited | Daily routines, property attributes, interactive criteria | Reachability constraints and trajectory-derived travel | Full text; task/user evaluation; strongest conceptual comparator |
| P31 journey-aware housing | Home features and user-specified destinations | Multihop journey calculator and MCDM | Author abstract only; experimental details require retrieval |
| P01 RE-RecSys | Search locality and historical interactions | Commute mechanism unknown | Full text; temporal engagement metrics and deployment |
| P03 cold-start properties | User/property content, multiple behaviors | Road commute mechanism unknown | Full text; query and stage comparisons; ranks users for new listings |
| P05 Dynamic HomeFinder | Sliders, property facts and map markers | Physical-distance filters; excluded from user comparison | Full text; counterbalanced task study |
| P06 CFRecs | Listing/user graphs and preferences | Explicit destination treatment unknown | Preprint; counterfactual graph validity, not housing decisions |

These six are relevant at different levels. P04 and P31 directly precede the
destination/commute formulation; P01/P03 are algorithmic property comparators;
P05 is a housing-interaction comparator; P06 concerns actionable graph
explanations. No claim is made that all can be reproduced as ranking baselines
without their proprietary data or missing implementation details.

## Feature evidence

| Characteristic | P01 | P03 | P04 | P05 | P06 | P31 | DhakaNest |
|---|---|---|---|---|---|---|---|
| Neighborhood/locality inputs | P | P | P | P | U | U | D |
| Important places/routines as inputs | U | U | P | P | U | P | D |
| Multiple places | U | U | P | P (two markers) | U | P (plural locations; exact count unverified) | D (1-3) |
| Road/trajectory travel evidence | U | U | P | N (physical distance method) | U | P (journeys) | D (OSRM) |
| Explicit commute constraints | U | U | P | U | U | U | D |
| Content-based candidate selection | P | P | U | N (query filters) | U | U | D |
| Multi-criteria ranking/choice | U | U | P | P (filters) | U | P | D |
| Rent prediction | U | U | U | U | U | U | D |
| Predicted-rent reasonableness criterion | U | U | U | U | U | U | D |
| Explanations/decision visualization | U | U | P | P | P | U | D |
| Independent graded relevance evaluation | U | U | U | U | U | U | Planned |
| Statistical testing/intervals | U | U | P (user intervals) | P (task study) | U | U | Planned |
| Real-user evaluation | U (behavior logs) | U (behavior logs) | P | P | U | P (abstract states study) | Planned |
| Reusable complete dataset/code verified here | U | U | U | U | U | U | Partial |

`U` entries are evidence gaps, not inferred weaknesses. P04's richer routine and
probabilistic reachability formulation may model travel conditions that static
OSRM estimates omit. DhakaNest's distinctive rent-assessment integration must
earn its value through H4C and model-reliability tests.

## Recommended later protocol revisions

Do not change Phase 1 without approval. Record these as prospective revisions:

1. Add a journey-aware MCDM/Pareto comparator informed by P31 and P04, after
   obtaining sufficient primary methods. Area-first alone is too weak a
   location-aware comparison.
2. Add a highest-priority single-destination control, holding original routes
   and evaluation destinations fixed; Phase 1 H2 names this idea but its JSON
   has no operational baseline for it.
3. Split the current no-location ablation into criterion-only reranking on
   identical commute-valid candidates and a distinct end-to-end no-routing
   intervention. Current A_NO_DESTINATION_LOCATION removes constraints too.
4. Declare pooled-universe NDCG explicitly, audit missing judgments, and add
   pool-sensitivity checks. A 20-30-item annotation pool is not a fully judged
   property universe.
5. Test whether showing model rent assessments anchors independent relevance
   labels; use blinded rating conditions or a separate annotation sensitivity
   study before adopting them as ground truth for H4C.

Evidence: P02 Section 4.4; P04 architecture/user study; P23 baseline audit;
P24-P25 sampling analyses; P26 user-experience framework. Direct links and exact
locations are in the registry.
