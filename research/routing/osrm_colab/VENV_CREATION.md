# Colab virtual environment repair (v4)

## Established Cause

The supplied Colab diagnostics establish the actual cause, not just exit status 1:

```text
/usr/bin/python3 -m ensurepip --version
/usr/bin/python3: No module named ensurepip
```

Python is 3.13.16 on x86_64. Base pip 26.2.2 exists under
`/usr/local/lib/python3.13/dist-packages`, but standard `venv` tries to seed its
own pip by invoking `ensurepip` in the child interpreter. That module is absent.
Having pip in the kernel does not supply the missing standard-library module.
The supplied venv stderr explicitly identifies the child ensurepip invocation.

## Corrected Creation

The new `venv_setup.py` helper first captures the ensurepip preflight and standard
venv attempt, including complete stdout, stderr, command and return code. It does
not replace an unknown failure with an unconditional workaround. A fallback is
permitted only when ensurepip is confirmed missing/disabled and the failed venv
output identifies ensurepip. Disk/permission/unrelated failures stop with logs.

For that specific failure, kernel pip installs a separately locked bootstrap into
a NEW private `venv_bootstrap_tools/<attempt>` target. All six tool packages and
wheel hashes are pinned. No `pip install virtualenv` into system/user/kernel site
packages occurs. The unchanged research requirements are not installed there.

The tool process runs with `-I -S` and an explicitly inserted private helper path;
host/user site-packages cannot supply its virtualenv dependencies. Virtualenv
21.14.5 creates the research environment with embedded pip only, downloads and
periodic seed updates disabled. Activators are disabled; no activation script is
sourced. The notebook always invokes the environment's Python by absolute path.
The base executable is selected explicitly when the creator itself runs inside a
venv, avoiding Windows launcher redirection to its parent environment.

## Acceptance and Cleanup

`bin/python` (or Windows `Scripts/python.exe`) alone is NOT accepted. Creation and
every reuse validate all of the following:

- `pyvenv.cfg` exists and disables system site-packages.
- CPython minor version matches the selected 3.12/3.13 specification.
- The child's `sys.prefix` is the requested environment, not `sys.base_prefix`.
- Pip imports from inside that environment and `python -m pip --version` succeeds.
- User site-packages are disabled and no external site/dist-packages leak in.
- Reuse requires a completion marker bound to research/bootstrap specification
  checksums and an unchanged environment configuration checksum.

A pre-existing partial/unowned environment is refused without changing its files.
Failed directories created by this invocation are moved to `failed_environments/`
after checking ownership and workspace containment. They are not reused. No
recursive deletion, forced overwrite or removal of user environments is used.
Unrelated files are untouched. Diagnostics live OUTSIDE failed environments and
are copied to Drive by the notebook on both success and failure.

## Use v4

1. Upload `research/exports/dhakanest_colab_input_v4.zip` to
   `MyDrive/DhakaNestResearch`, without replacing previous ZIPs.
2. Upload `research/notebooks/DhakaNest_Phase3D_Colab_OSRM_v4.ipynb` to Colab.
3. Enter the v4 ZIP SHA-256 in its config cell. Keep its new run ID and local_root
   defaults so a partial v3 environment is not silently reused.
4. Run the cells in order. The Python setup cell displays the precise diagnostics,
   uses the fallback only when justified, then retains the existing research
   `--require-hashes`, 33-package lock, version verification, `pip check`, imports,
   checksum verification, resume checks and input-provenance steps.

The research requirements/environment spec, historical notebooks/ZIPs, benchmarks,
models and production files are unchanged. No OSM data or OSRM measurement is
downloaded during this repair. Phase 3D remains incomplete until real Colab work
and the existing acceptance checks finish.

## Validation

Offline tests cover both supported Python minors, successful creation, missing
ensurepip, non-ensurepip failures, conditional fallback, private bootstrap target,
pip import/CLI failures, isolation leaks, invalid existing environments, reuse,
timeouts and ownership-scoped quarantine. Ordinary tests never install packages.

An explicitly approved real Windows CPython 3.12 smoke validates standard creation,
the actual pinned virtualenv creator with simulated missing ensurepip, embedded
pip availability/isolation and reuse. It does NOT establish Colab 3.13 execution.
Initial local attempts caught a Windows path-length issue and a parent-launcher
redirection; failed attempts were rejected/quarantined, and the successful final
smoke uses a short test path and the actual base interpreter. No backend or system
packages were changed. The only new packages are in private ignored tool targets.

Evidence: `research/results/phase_3d_colab/venv_repair_v1/`.

## Primary References

- [Python 3.13 venv and ensurepip](https://docs.python.org/3.13/library/venv.html)
- [Official virtualenv installation guidance](https://virtualenv.pypa.io/en/latest/how-to/install.html)
- [Virtualenv CLI isolation and seed options](https://virtualenv.pypa.io/en/latest/reference/cli.html)
- [Pinned virtualenv release metadata](https://pypi.org/pypi/virtualenv/21.14.5/json)
