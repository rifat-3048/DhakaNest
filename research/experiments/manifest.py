"""Create immutable, machine-readable manifests for research experiments."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "experiment_id",
    "purpose",
    "dataset",
    "input_configuration",
    "random_seed",
    "versions",
    "dependencies",
    "output_paths",
    "database_access",
    "execution_status",
}
ALLOWED_DATABASE_ACCESS = {"none", "read_only"}


def sha256_file(path: Path) -> str:
    """Return a stable SHA-256 checksum without modifying the input file."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{field}' must be a non-empty string.")
    return value.strip()


def validate_config(
    config: dict[str, Any], *, repo_root: Path, research_root: Path
) -> None:
    """Validate explicit inputs and reject unsafe output or database settings."""
    missing = sorted(REQUIRED_FIELDS - set(config))
    if missing:
        raise ValueError(f"Missing required configuration fields: {missing}")

    _required_text(config["experiment_id"], "experiment_id")
    _required_text(config["purpose"], "purpose")
    if not isinstance(config["random_seed"], int) or isinstance(
        config["random_seed"], bool
    ):
        raise ValueError("'random_seed' must be an integer.")

    dataset = config["dataset"]
    if not isinstance(dataset, dict):
        raise ValueError("'dataset' must be an object.")
    _required_text(dataset.get("identifier"), "dataset.identifier")
    dataset_path = repo_root / _required_text(dataset.get("path"), "dataset.path")
    if not _inside(dataset_path, repo_root) or not dataset_path.is_file():
        raise ValueError("The dataset path must be an existing file in the repository.")

    if not isinstance(config["input_configuration"], dict):
        raise ValueError("'input_configuration' must be an object.")
    if not isinstance(config["versions"], dict) or not config["versions"]:
        raise ValueError("'versions' must be a non-empty object.")
    if not isinstance(config["dependencies"], list) or not all(
        isinstance(item, str) and item.strip() for item in config["dependencies"]
    ):
        raise ValueError("'dependencies' must be a list of package names.")

    outputs = config["output_paths"]
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("'output_paths' must be a non-empty list.")
    for output in outputs:
        output_path = research_root / _required_text(output, "output_paths item")
        if not _inside(output_path, research_root):
            raise ValueError("Every output path must remain inside research/.")

    if config["database_access"] not in ALLOWED_DATABASE_ACCESS:
        raise ValueError("Research database access must be 'none' or 'read_only'.")
    _required_text(config["execution_status"], "execution_status")


def _git_commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={repo_root.as_posix()}",
                "rev-parse",
                "HEAD",
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _dependency_versions(names: list[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in names:
        if name.lower() == "python":
            versions[name] = platform.python_version()
            continue
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def build_manifest(
    config: dict[str, Any], *, repo_root: Path, research_root: Path
) -> dict[str, Any]:
    """Build metadata only after every declared input and output is verified."""
    validate_config(config, repo_root=repo_root, research_root=research_root)
    dataset_path = repo_root / config["dataset"]["path"]
    outputs: list[dict[str, Any]] = []
    for relative_path in config["output_paths"]:
        output_path = research_root / relative_path
        if not output_path.is_file():
            raise ValueError(f"Declared output does not exist: {relative_path}")
        outputs.append(
            {
                "path": relative_path,
                "sha256": sha256_file(output_path),
                "bytes": output_path.stat().st_size,
            }
        )

    return {
        "manifest_schema_version": "1.0",
        "experiment_id": config["experiment_id"],
        "purpose": config["purpose"],
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(repo_root),
        "dataset": {
            "identifier": config["dataset"]["identifier"],
            "path": config["dataset"]["path"],
            "sha256": sha256_file(dataset_path),
            "bytes": dataset_path.stat().st_size,
        },
        "input_configuration": config["input_configuration"],
        "random_seed": config["random_seed"],
        "versions": config["versions"],
        "dependencies": _dependency_versions(config["dependencies"]),
        "outputs": outputs,
        "execution_status": config["execution_status"],
        "safety": {
            "database_access": config["database_access"],
            "production_writes": False,
        },
    }


def write_manifest_exclusive(
    manifest: dict[str, Any], destination: Path, *, research_root: Path
) -> None:
    """Write once, refusing traversal and accidental replacement."""
    if not _inside(destination, research_root):
        raise ValueError("Manifest destination must remain inside research/.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(manifest, output, indent=2, sort_keys=True)
        output.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    research_root = Path(__file__).resolve().parents[1]
    repo_root = research_root.parent
    config = json.loads(args.config.read_text(encoding="utf-8"))
    manifest = build_manifest(
        config, repo_root=repo_root, research_root=research_root
    )
    write_manifest_exclusive(
        manifest, research_root / args.output, research_root=research_root
    )
    print(f"Created immutable manifest: {research_root / args.output}")


if __name__ == "__main__":
    main()
