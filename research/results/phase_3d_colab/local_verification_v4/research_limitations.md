# Research Limitations

The 2,500 active listings are synthetic academic records; property coordinates
are generated around area anchors. Destinations are area anchors, not verified
institution addresses. OSRM routes use a frozen OSM road network and car profile,
not observed Dhaka traffic. Snapping may move synthetic coordinates to roads.
Frozen XGBoost assessments are model outputs, not independent market truth.
These controlled synthetic data cannot establish real-market generalization.
Colab does not remove these limitations. No human labels, final ranking metrics,
baseline comparisons or ablation experiments are produced in this phase.
