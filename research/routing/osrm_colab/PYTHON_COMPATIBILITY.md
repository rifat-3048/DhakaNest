# Colab Python compatibility revision

## Diagnosis

The affected Colab kernel reports CPython **3.13.16**, x86_64, GCC 13.3.0.
The original guard deliberately accepted 3.12 only. Its wording was imprecise:
NumPy 2.0.2 and pandas 2.2.2 individually support several older Python versions,
not just 3.12, but neither publishes a compatible CPython 3.13 wheel. XGBoost
3.3.0 requires Python >=3.12. The original complete binary environment therefore
has a supported intersection of CPython 3.12. Removing that guard would only move
the failure to installation; it would not make the original pins work on 3.13.

## New specification

`environment-spec-v2.json` selects a checksum-bound environment by interpreter:

| Interpreter | Specification | NumPy | pandas |
|---|---|---|---|
| CPython 3.12.x | Original `requirements-colab.txt`, unchanged | 2.0.2 | 2.2.2 |
| CPython 3.13.x | `requirements-colab-py313-v1.txt` | 2.1.3 | 2.2.3 |

The 3.13 installation uses `requirements-colab-py313-v1.lock.txt`: all 33 direct
and transitive dependencies are exactly pinned, with the SHA-256 of each selected
Linux wheel. XGBoost 3.3.0, scikit-learn 1.6.1, joblib 1.5.3 and SciPy 1.16.3 are
unchanged. No production requirement or model artifact is edited. No inference,
retraining or regeneration of frozen predictions occurs.

Python <=3.11, 3.14+, prerelease/malformed versions and alternate implementations
remain rejected. There is no silent source-build or dependency-upgrade fallback.
Resource, architecture, source, map and dataset integrity checks are retained.

## Evidence and Validation Limits

The evidence directory is `research/results/phase_3d_colab/python_compatibility_v1/`.
The PyPI audit records release metadata, its response checksum, Requires-Python,
compatible Linux wheel filenames and artifact hashes for every direct pin.
The original 3.13 environment fails wheel checks specifically for NumPy/pandas.
The new 3.13 and unchanged 3.12 pins pass those checks.

Pip's cross-platform dry run selects target wheel tags but can still evaluate
dependency markers on its Windows host. The first report is retained as evidence,
not mislabeled as a complete Linux environment. A second report explicitly adds
XGBoost's mandatory Linux `nvidia-nccl-cu12` dependency. An independent marker
evaluation using Linux / x86_64 / CPython 3.13.16 validates the full 33-package
dependency closure, including Python-version specifiers. The lock includes the
NCCL wheel because the unchanged upstream XGBoost distribution requires it; this
does NOT request a GPU runtime or run GPU computation.

No packages were installed locally for this fix. Metadata/wheel availability,
target dependency closure and local CPython 3.12 tests are NOT a substitute for
actual CPython 3.13 Colab imports or numerical-equivalence tests. These remain
mandatory notebook gates. The research environment is recorded explicitly rather
than claiming the two environments are identical. No final KNN/WSM experiment,
quality metric, traffic measurement or model calibration is part of this fix.

## Run the Corrected Notebook

1. Upload `research/exports/dhakanest_colab_input_v3.zip` to
   `MyDrive/DhakaNestResearch`. Use its newly reported SHA-256, not the v2 hash.
2. Upload `research/notebooks/DhakaNest_Phase3D_Colab_OSRM_v3.ipynb` into Colab.
   The original notebook and previous ZIP are preserved.
3. Select CPU. Enter the new archive checksum in the one config cell. The v3
   defaults already use a NEW run ID and local_root so old snapshots are not mixed.
4. Run through import, guard and isolated Python setup. The guard now accepts
   CPython 3.13.16 without weakening RAM/disk/architecture checks. A dedicated
   `research_venv_cp313` is created with the selected hashed lock, followed by
   `pip check`, exact installed-version verification and binary import smoke.
5. `stage('inputs')` verifies the immutable benchmark and records interpreter,
   environment/requirements checksums, installed versions and import results.
   Actual pip installation reports are saved separately to Drive. Existing map,
   preprocessing, smoke, routing, freeze and regression stages are unchanged.

The notebook can then proceed to its next stage. Do not call Phase 3D complete
until actual Colab runtime/build/routing/finalization and tests succeed. This fix
does not start OSRM or make live routing requests on your computer.

## Resume Integrity

Resume within the same selected environment only. Python 3.13 always reuses the
complete hashed lock. Python 3.12 retains the saved full pip freeze, but only after
its environment identity is checked. A different/unspecified environment in prior
inputs causes a stop and requests a new run ID/local_root. Environment provenance
is also included in the routing scope identity, preventing cross-environment mixing.

## Sources

- [NumPy 2.0.2 metadata](https://pypi.org/pypi/numpy/2.0.2/json)
- [pandas 2.2.2 metadata](https://pypi.org/pypi/pandas/2.2.2/json)
- [NumPy 2.1.3 metadata](https://pypi.org/pypi/numpy/2.1.3/json)
- [pandas 2.2.3 metadata](https://pypi.org/pypi/pandas/2.2.3/json)
- All other package-specific PyPI URLs/hashes are in the saved wheel audit.
