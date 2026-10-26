"""Diagnosed, isolated environment creation with an ensurepip-specific fallback.

Failed directories created by this call are quarantined, not recursively deleted.
Pre-existing invalid environments are refused without changing their contents.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .storage import put_json, sha

HERE = Path(__file__).resolve().parent
SPEC = HERE / "virtualenv-bootstrap-v1.json"
OWNER = ".dhakanest-creation-owner.json"
COMPLETE = ".dhakanest-environment-ready.json"
PROBE = """import json, sys, site, pip, platform
print(json.dumps(dict(prefix=sys.prefix, base_prefix=sys.base_prefix,
    python_minor=str(sys.version_info.major)+'.'+str(sys.version_info.minor),
    implementation=platform.python_implementation(), pip_file=pip.__file__,
    pip_version=pip.__version__, user_site_enabled=site.ENABLE_USER_SITE,
    paths=sys.path)))
"""


class EnvironmentCreationError(RuntimeError):
    pass


def clean_process_environment():
    # Subprocess-only: leave the Colab kernel's os.environ/sys.path untouched.
    result = {key: value for key, value in os.environ.items() if not key.upper().startswith(("PYTHON", "PIP_", "VIRTUALENV"))
              and key != "VIRTUAL_ENV"}
    result.update(VIRTUALENV_CONFIG_FILE=os.devnull, PYTHONNOUSERSITE="1", PIP_CONFIG_FILE=os.devnull)
    return result


def child_python(directory):
    return Path(directory) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def validate_environment(directory, minor, invoke):
    directory = Path(directory).resolve()
    config = directory / "pyvenv.cfg"
    if not config.is_file() or config.is_symlink():
        raise EnvironmentCreationError("Missing/unsafe pyvenv.cfg; interpreter existence is insufficient")
    fields = dict(line.split("=", 1) for line in config.read_text(encoding="utf-8").splitlines() if "=" in line)
    fields = {key.strip().lower(): value.strip().lower() for key, value in fields.items()}
    if fields.get("include-system-site-packages") != "false":
        raise EnvironmentCreationError("System site-packages must be disabled")
    result = invoke("validate-python-and-pip", [str(child_python(directory)), "-I", "-c", PROBE])
    if result.returncode:
        raise EnvironmentCreationError("Environment Python/pip validation failed:\n" + result.stdout + result.stderr)
    try:
        evidence = json.loads(result.stdout)
        prefix = Path(evidence["prefix"]).resolve()
        if (prefix != directory or prefix == Path(evidence["base_prefix"]).resolve()
                or evidence["python_minor"] != minor or evidence["implementation"] != "CPython"
                or evidence["user_site_enabled"] is not False
                or not Path(evidence["pip_file"]).resolve().is_relative_to(directory)):
            raise ValueError("Prefix, interpreter or pip escaped the isolated environment")
        for entry in evidence["paths"]:
            path = Path(entry).resolve()
            if any(part in {"site-packages", "dist-packages"} for part in path.parts) and not path.is_relative_to(directory):
                raise ValueError("External site-packages leaked into the environment")
    except (KeyError, TypeError, ValueError) as error:
        raise EnvironmentCreationError(f"Invalid environment probe: {error}") from error
    pip = invoke("validate-pip-cli", [str(child_python(directory)), "-I", "-m", "pip", "--version"])
    if pip.returncode:
        raise EnvironmentCreationError("Environment pip CLI unavailable:\n" + pip.stdout + pip.stderr)
    return {**evidence, "pyvenv_cfg_sha256": sha(config)}


def create_environment(workspace, selected, *, runner=subprocess.run, emit=print):
    workspace = Path(workspace)
    if workspace.is_symlink():
        raise EnvironmentCreationError("Compute workspace cannot be a symlink")
    workspace = workspace.resolve()
    if workspace == workspace.parent:
        raise EnvironmentCreationError("Refusing filesystem root as a compute workspace")
    minor = selected["python_minor"]
    if minor not in {"3.12", "3.13"}:
        raise EnvironmentCreationError("Only CPython 3.12/3.13 environments are supported")
    directory = workspace / ("research_venv_cp" + minor.replace(".", ""))
    if directory.is_symlink() or directory.resolve().parent != workspace:
        raise EnvironmentCreationError("Unsafe environment destination")
    attempt = uuid.uuid4().hex
    logs = workspace / "venv_diagnostics" / attempt
    logs.mkdir(parents=True)
    environment = clean_process_environment()

    def invoke(label, command):
        try:
            result = runner(command, capture_output=True, text=True, check=False, env=environment, timeout=600)
        except subprocess.TimeoutExpired as error:
            put_json(logs / f"{label}.json", {"command": command, "timeout": True,
                     "stdout": str(error.stdout or ""), "stderr": str(error.stderr or "")})
            raise EnvironmentCreationError(f"{label} timed out; diagnostics: {logs}") from error
        put_json(logs / f"{label}.json", {"command": command, "returncode": result.returncode,
                                        "stdout": result.stdout, "stderr": result.stderr})
        emit(f"{label}: exit {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        return result

    binding = {"python_minor": minor, "research_specification_sha256": selected["specification_sha256"],
               "bootstrap_specification_sha256": sha(SPEC)}
    if directory.exists():
        marker = directory / COMPLETE
        if not marker.is_file() or marker.is_symlink():
            raise EnvironmentCreationError("Pre-existing partial/unowned environment rejected. Use a new local_root; nothing was deleted")
        ready = json.loads(marker.read_text())
        if ready.get("binding") != binding:
            raise EnvironmentCreationError("Existing environment belongs to a different specification")
        verified = validate_environment(directory, minor, invoke)
        if verified["pyvenv_cfg_sha256"] != ready["validation"]["pyvenv_cfg_sha256"]:
            raise EnvironmentCreationError("Existing environment configuration changed")
        return {"python": str(child_python(directory)), "method": ready["method"], "reused": True,
                "validation": verified, "diagnostics": str(logs)}

    def own_destination():
        directory.mkdir()
        put_json(directory / OWNER, {"attempt": attempt, "workspace": str(workspace)})

    def quarantine():
        # Rename ONLY the exact directory created by this invocation. No rmtree.
        if not directory.exists():
            return
        marker = directory / OWNER
        if directory.is_symlink() or not marker.is_file() or marker.is_symlink() or json.loads(marker.read_text()).get("attempt") != attempt:
            raise EnvironmentCreationError("Refusing cleanup of an unowned environment")
        destination = workspace / "failed_environments" / f"{directory.name}-{time.time_ns()}"
        destination.parent.mkdir(exist_ok=True)
        if not destination.parent.resolve().is_relative_to(workspace) or directory.resolve().parent != workspace:
            raise EnvironmentCreationError("Cleanup destination escaped compute workspace")
        directory.rename(destination)
        emit(f"Failed environment quarantined: {destination}")

    own_destination()
    try:
        ensurepip = invoke("ensurepip-preflight", [sys.executable, "-I", "-m", "ensurepip", "--version"])
        standard = invoke("stdlib-venv", [sys.executable, "-I", "-m", "venv", str(directory)])
        method = "stdlib-venv"
        if standard.returncode:
            diagnostic = (ensurepip.stdout + ensurepip.stderr).lower()
            missing = ensurepip.returncode != 0 and any(message in diagnostic for message in (
                "no module named ensurepip", "ensurepip is disabled", "ensurepip is not available"))
            if not missing or "ensurepip" not in (standard.stdout + standard.stderr).lower():
                raise EnvironmentCreationError("venv failed for an unconfirmed/non-ensurepip cause; no fallback attempted:\n" + standard.stdout + standard.stderr)
            quarantine()
            own_destination()
            bootstrap = json.loads(SPEC.read_text())
            lock = HERE / bootstrap["requirements"]
            if sha(lock) != bootstrap["requirements_sha256"]:
                raise EnvironmentCreationError("Bootstrap lock checksum mismatch")
            kernel_pip = invoke("kernel-pip-preflight", [sys.executable, "-I", "-m", "pip", "--version"])
            if kernel_pip.returncode:
                raise EnvironmentCreationError("Kernel pip unavailable; will not install pip into system Python")
            tools = workspace / "venv_bootstrap_tools" / attempt
            tools.mkdir(parents=True)
            install = invoke("install-private-bootstrap", [sys.executable, "-I", "-m", "pip", "--isolated", "install",
                "--target", str(tools), "--ignore-installed", "--no-deps", "--require-hashes", "--only-binary=:all:",
                "--index-url", "https://pypi.org/simple", "--no-compile", "--report", str(logs / "bootstrap-install-report.json"), "-r", str(lock)])
            if install.returncode:
                raise EnvironmentCreationError("Private virtualenv bootstrap installation failed:\n" + install.stdout + install.stderr)
            # -I -S prevents host/user site-packages from supplying bootstrap code.
            program = "import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); import virtualenv; assert virtualenv.__version__ == sys.argv.pop(1); runpy.run_module('virtualenv',run_name='__main__')"
            # A Windows venv launcher can redirect to its parent environment.
            # Select the real base executable when this helper itself runs in a venv.
            base_python = getattr(sys, "_base_executable", None) or sys.executable
            fallback = invoke("virtualenv-fallback", [sys.executable, "-I", "-S", "-c", program, str(tools), bootstrap["virtualenv_version"],
                "--python", base_python, "--no-download", "--no-periodic-update", "--pip", "embed", "--setuptools", "none",
                "--activators", "", "--app-data", str(workspace / "venv_bootstrap_cache" / attempt), str(directory)])
            if fallback.returncode:
                raise EnvironmentCreationError("Isolated virtualenv fallback failed:\n" + fallback.stdout + fallback.stderr)
            method = "pinned-virtualenv-ensurepip-unavailable"
        validation = validate_environment(directory, minor, invoke)
        ready = {"binding": binding, "method": method, "validation": validation, "attempt": attempt}
        put_json(directory / COMPLETE, ready)
        put_json(logs / "creation-result.json", ready)
        return {"python": str(child_python(directory)), "method": method, "reused": False,
                "validation": validation, "diagnostics": str(logs)}
    except BaseException:
        quarantine()
        raise
