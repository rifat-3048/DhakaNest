# Technical Report Update Notes

No report source file is stored in this repository. Apply these corrections to
the university report:

- Tenant location input is 1-3 important destinations, not residential areas.
- Destination importance is 1-5; maximum commute is optional per destination.
- Household size is descriptive and affects no filter, KNN feature, WSM score,
  or rank.
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
