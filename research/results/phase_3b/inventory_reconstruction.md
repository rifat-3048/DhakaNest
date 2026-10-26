# Inventory Reconstruction

Supporting frozen evidence: research/datasets/benchmark_v1_1/. Status: partially complete; genuine routing remains missing. No final ranking benchmark, human labels or Phase 4 work was performed.

Reused original generate_inventory unchanged with seed 20261005, generator 1.0.0,
2500 active plus 100 lifecycle records. Generation of all 2600 preserves original
group allocation and random sequence before selecting the active subset.
Recovered 2500 approved/available synthetic records; retained
100 separate lifecycle audit records. IDs hash deterministic
academic seed keys. This is equivalent configured reconstruction, NOT a live DB
snapshot or confirmation of the current application's records. No MongoDB access.

Property types: {'apartment': 1490, 'house': 430, 'room': 310, 'sublet': 270}. Furnishing: {'furnished': 833, 'semi_furnished': 834, 'unfurnished': 833}.
Advertised rents BDT 6,000-198,000.
Unique amenity combinations: 483.
All records are academic_synthetic; none are real market observations. Contacts,
private addresses, administrator IDs and authentication details are excluded.
Full independent replay reproduced active/lifecycle records exactly. Genuine
routes remain missing; inventory alone does not enable final evaluation.

Evidence: properties.json, lifecycle_properties.json, generation_config.json,
inventory_coverage.json, dataset_manifest.json and verification_results.json.
