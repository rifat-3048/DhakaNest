# Python Compatibility Correction

Status: compatibility implementation complete; actual Colab setup/imports and
Phase 3D execution remain outstanding. No OSRM request was made for this fix.

The user confirmed CPython 3.13.16 / Linux x86_64, GCC 13.3.0. The original
NumPy 2.0.2 and pandas 2.2.2 pins do not publish CPython 3.13 wheels. The old
guard was not safely removable: the original complete binary environment is
restricted to Python 3.12 because XGBoost 3.3.0 also requires Python >=3.12.

The research-only guard now selects a validated specification for stable CPython
3.12.x or 3.13.x. Python 3.12 retains its original pins. Python 3.13 uses NumPy
2.1.3 and pandas 2.2.3, with all other direct pins unchanged. A full 33-package
Linux wheel lock adds exact versions and wheel hashes for transitive dependencies.

Validation performed:

- All 15 direct pins have compatible binary wheels in their selected environments.
- The original 3.13 pin set fails specifically for NumPy and pandas.
- Pip dry-run selected compatible Linux wheel distributions without installing.
- Linux/3.13.16 dependency markers were independently checked because cross-target
  pip still reports/evaluates some host Windows markers. The incomplete first
  resolver report is retained. The complete report includes XGBoost's mandatory
  Linux NCCL dependency; all 33 selected dependencies satisfy target constraints.
- 177 research tests passed, no skips. 104 backend regression tests passed.
- Local CPython 3.12.10 installed-version/import verification passed.
- The exact reported 3.13.16 version passes the guard in automated tests without
  reducing RAM/disk/CPU/architecture requirements.
- V3 notebook code cells compile and preserve checksum, venv, pip check, import,
  checkpoint, scope and regression gates. Actual 3.13 imports were NOT executed
  locally. No numerical equivalence between different environments is assumed.
- Original notebook and v2 ZIP hashes are unchanged. Historical phase/recovery
  seals pass. Production Git diff is empty, and no database/model/data changes ran.

Modified source files:

- `research/routing/osrm_colab/workflow.py`
- `research/tests/test_colab_setup.py`

Added source/artifact files:

- `research/routing/osrm_colab/environment.py`
- `research/routing/osrm_colab/environment-spec-v2.json`
- `research/routing/osrm_colab/requirements-colab-py313-v1.txt`
- `research/routing/osrm_colab/requirements-colab-py313-v1.lock.txt`
- `research/routing/osrm_colab/audit_python_compatibility.py`
- `research/routing/osrm_colab/notebook_compat.py`
- `research/routing/osrm_colab/PYTHON_COMPATIBILITY.md`
- `research/notebooks/DhakaNest_Phase3D_Colab_OSRM_v3.ipynb`
- `research/tests/test_colab_python_compatibility.py`

New evidence is appended under this directory and `local_verification_v5/`.
The new archive is `research/exports/dhakanest_colab_input_v3.zip`; its separate
post-packaging record gives the final SHA-256 without a circular self-hash.

Next: upload the v3 ZIP and v3 notebook, enter the new hash, and run the import
and isolated Python setup cells. The notebook requires exact installed versions,
binary imports and pip check to pass before continuing. Use its new run ID/local
root defaults. Phase 3D is NOT complete; no live routing was acquired here.
