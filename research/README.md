# DhakaNest Research Workspace

This directory isolates reproducible research work from the production
application. Phase 0 audits the existing implementation and evidence; it does
not run recommendations, contact MongoDB or OSRM, retrain models, or alter any
production artifact.

## Layout

- `protocols/`: explicit experiment configurations.
- `datasets/`: inventories and future research-only dataset references.
- `experiments/`: small, reusable experiment metadata utilities.
- `reproducibility/`: safe workspace setup helpers.
- `results/`: immutable outputs grouped by phase.
- `tests/`: research-infrastructure tests that require no live services.

Later phases may use `literature/`, `annotation/`, `baselines/`, `ablations/`,
`metrics/`, `statistics/`, `xgboost_analysis/`, `user_study/`, and `figures/`.
The initializer creates these directories when needed without adding
placeholder files.

## Record an experiment

From the repository root:

```powershell
backend\.venv\Scripts\python.exe -m research.experiments.manifest `
  research\protocols\phase_0_audit.json `
  --output results\phase_0\phase_0_manifest.json
```

The output path is relative to `research/`. Manifest creation uses exclusive
file creation and refuses to overwrite an existing result. Configurations may
declare only `none` or `read_only` database access.

## Run checks

```powershell
backend\.venv\Scripts\python.exe -m unittest discover -s research\tests -v
```

The Phase 0 reports are in `results/phase_0/`. Status labels used there are:
`Verified`, `Unresolved`, and `Requires external evidence`.
