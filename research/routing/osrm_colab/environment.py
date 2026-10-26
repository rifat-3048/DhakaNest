"""Select an explicit research environment; never loosen production pins.

This module is stdlib-only so the Colab kernel can select a specification before
creating the isolated venv. Actual installed versions are checked in that venv.
"""

import argparse
from importlib import metadata, import_module
import json
from pathlib import Path
import platform
import re
import sys

from .storage import sha

HERE = Path(__file__).resolve().parent
SPEC = HERE / "environment-spec-v2.json"


def select_environment(version=None):
    text = platform.python_version() if version is None else version
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        raise ValueError(f"Unsupported Python version {text!r}; a stable CPython 3.12.x or 3.13.x is required")
    minor = ".".join(match.groups()[:2])
    specification = json.loads(SPEC.read_text(encoding="utf-8"))
    if minor not in specification["environments"]:
        raise ValueError(f"Python {text} is unsupported; use CPython 3.12.x or 3.13.x. "
                         "3.11 cannot install pinned XGBoost 3.3.0; 3.14 lacks the frozen scikit-learn 1.6.1 wheel")
    entry = dict(specification["environments"][minor])
    requirements = HERE / entry["requirements"]
    if sha(requirements) != entry["requirements_sha256"]:
        raise ValueError("Research requirements checksum differs from its environment specification")
    installation = HERE / entry.get("installation_lock", entry["requirements"])
    if "installation_lock_sha256" in entry and sha(installation) != entry["installation_lock_sha256"]:
        raise ValueError("Research installation lock checksum differs from its specification")
    return {**entry, "python_minor": minor, "requirements_path": str(requirements),
            "installation_path": str(installation),
            "specification_sha256": sha(SPEC)}


def pinned_packages(path):
    # This is a deliberately small lock grammar, not a general pip-file parser.
    packages = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)(?: --hash=sha256:[a-f0-9]{64})?", line)
        if not match or match[1] in packages:
            raise ValueError("Environment specifications require unique exact package pins")
        packages[match[1]] = match[2]
    return packages


def check_resume(previous_inputs, selected):
    """Do not install a different interpreter's freeze into the new venv."""
    previous = previous_inputs.get("research_environment")
    if not previous or any(previous.get(key) != selected[key] for key in
                           ("id", "python_minor", "requirements_sha256", "specification_sha256")):
        raise ValueError("Previous inputs use a different/unspecified research environment; select a new run_id and local_root")


def installed_environment():
    if platform.python_implementation() != "CPython":
        raise ValueError("The validated wheels require CPython, not an alternate implementation")
    selected = select_environment()
    direct = pinned_packages(selected["requirements_path"])
    expected = pinned_packages(selected["installation_path"])
    actual = {name: metadata.version(name) for name in expected}
    if actual != expected:
        raise ValueError(f"Installed environment differs from exact pins: expected {expected}; got {actual}")
    # Imports check binary extension/ABI loading without instantiating a model,
    # generating predictions, connecting to MongoDB or making routing requests.
    imports = {"pydantic-settings": "pydantic_settings", "python-dotenv": "dotenv", "pymongo": "pymongo",
               "email-validator": "email_validator", "python-jose": "jose", "scikit-learn": "sklearn"}
    for name in direct:
        import_module(imports.get(name, name))
    return {key: value for key, value in selected.items() if key not in {"requirements_path", "installation_path"}} | {
        "python": platform.python_version(), "implementation": platform.python_implementation(),
        "architecture": platform.machine(), "packages": actual, "import_smoke": "passed",
        "prediction_generated": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-installed", action="store_true")
    args = parser.parse_args()
    print(json.dumps(installed_environment() if args.verify_installed else select_environment(), indent=2))
