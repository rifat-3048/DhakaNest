# Colab venv Repair

Status: creation repair implemented and locally validated. Actual Colab 3.13
execution remains outstanding. Phase 3D is not complete.

## Confirmed Cause

User-supplied diagnostics show `/usr/bin/python3` is CPython 3.13.16 and
`python -m ensurepip --version` exits 1 with `No module named ensurepip`.
Base pip 26.2.2 works, but standard venv's child `-m ensurepip --upgrade
--default-pip` invocation fails. Kernel pip and ensurepip are distinct; kernel
pip availability does not make standard venv's pip-seeding step work.

## Repair

New v4 creation code captures stdout/stderr and return codes for preflight,
stdlib creation, fallback and validation. It first attempts standard venv.
Only confirmed missing/disabled ensurepip plus a matching venv failure enables
the pinned fallback. Unrelated failures are not silently bypassed.

The fallback installs six hash-locked bootstrap tools into a private target,
executes pinned virtualenv 21.14.5 with isolated imports, seeds embedded pip
without periodic/network updates, and generates no activators. It never installs
virtualenv or research dependencies into system/user site-packages. The unchanged
33-package research lock and all downstream pip/version/import gates remain.

An existing interpreter alone is insufficient: prefix, Python minor version,
pyvenv.cfg, pip origin/CLI, user-site isolation, external-site exclusion and a
specification-bound completion marker are checked. Newly created failed paths
are ownership-checked and quarantined. Existing partial/unowned paths are refused
unchanged. Logs remain outside failed environments and are persisted to Drive.

## Validation

- 191 research tests passed, zero skips (14 new creation tests).
- 104 applicable backend regression tests passed.
- New Python modules compile and v4 notebook JSON/code checks pass.
- Real Windows CPython 3.12 standard creation passed.
- Real pinned virtualenv creation/embedded pip/isolation/reuse passed, with
  ensurepip absence simulated only to exercise the real fallback branch.
- Initial Windows-only smoke failures (long test path and parent venv launcher
  redirection) were rejected/quarantined. The final smoke uses a short test path
  and the real base executable. These are not Colab execution claims.
- Historical phase/recovery checksums pass; production diff is empty.
- Original v3 sources/notebook/archive and research dependency locks are retained.
- No OSM download, OSRM acquisition, model change, inference or DB change occurred.

Source additions are under `research/routing/osrm_colab/`: `venv_setup.py`,
`build_bootstrap_spec.py`, `virtualenv-bootstrap-v1.json`, its hashed lock,
`notebook_venv.py`, `venv_smoke.py`, and `VENV_CREATION.md`. Also added the
v4 notebook, `research/tests/test_colab_venv_creation.py`, and this new evidence.
No historical source file needed modification.

Upload `DhakaNest_Phase3D_Colab_OSRM_v4.ipynb` with
`research/exports/dhakanest_colab_input_v4.zip`, use the new checksum and keep the
v4 run ID/local_root defaults. Post-packaging evidence records the ZIP hash.
