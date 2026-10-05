# Technical Report Update Notes

No report source file is stored in this repository. Apply these corrections to
the university report:

- Tenant location input is 1-3 important destinations, not residential areas.
- Destination importance is 1-5; maximum commute is optional per destination.
- Household size is descriptive and affects no filter, KNN feature, WSM score,
  or rank.
- Preferred floor size is a soft target used by KNN structural similarity and
  the WSM space component; it is not a minimum/maximum hard filter.
- Complete new searches estimate monthly travel from OSRM road distance, one
  round trip per travel day, and a configurable fixed BDT/km academic rate.
- Estimated monthly spend is advertised rent plus estimated travel cost and is
  used inside Budget; destination importance is not travel frequency.
- Legacy requests with missing frequency remain rent-only and never show a
  misleading partial travel total.
- OSRM provides traffic-free road estimates, not live Dhaka traffic.
- XGBoost is the final rent model and uses five features with a `log1p` target.
- Property similarity chooses the content-based KNN candidate set; it is not a
  sixth WSM criterion.
- The five WSM criteria are location, budget, space, amenities, and rent fairness.
- Recommendation reasons are deterministic, rule-based, and non-LLM.
- Evaluation uses Precision@K and NDCG@K on 8 profiles, 12 listings per profile,
  and 96 manually assigned development judgments.
- History stores immutable snapshots; opening one reruns no ranking service.
- Route geometry is visualization only and never changes commute values or rank.
- The supported project mode is local academic execution without Docker/cloud.
- The optional local inventory contains 2,500 recommendation-ready and 100
  lifecycle synthetic records generated with default seed `20261005`.
- Seed coordinates use 12 repository-verified anchors with small deterministic
  jitter, not arbitrary bounding-box coordinates or runtime geocoding.
- Seed rent starts from production XGBoost output; deterministic advertised-rent
  bands then pass through the standard stored assessment builder.
- Coverage validation includes all amenities, all 45 amenity pairs, canonical
  cross-feature combinations, and 25 hard-filter profiles.
- Seed records are academic/demo data, not current market observations.
- Travel costs remain recommendation-time values and are not stored in listings.
