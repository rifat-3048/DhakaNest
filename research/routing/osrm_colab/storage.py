"""Immutable, checksum-verified local/Drive copies and safe repository bundles.

Acquisition stays inside research/ because the existing validator deliberately
rejects capture references outside it. Drive receives a durable second copy.
"""

from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def copy_once(source, destination):
    """Never replace different evidence; publish only a complete verified copy."""
    source, destination = Path(source), Path(destination)
    expected = sha(source)
    if destination.exists():
        if sha(destination) != expected:
            raise ValueError(f"Immutable copy conflict: {destination}")
        return expected
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".copy-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as target, source.open("rb") as origin:
            shutil.copyfileobj(origin, target)
            target.flush()
            os.fsync(target.fileno())
        if sha(temporary) != expected:
            raise IOError("Copy checksum mismatch")
        # This workflow is single-writer. Existing conflicting evidence is refused.
        if destination.exists():
            raise FileExistsError(destination)
        os.replace(temporary, destination)
        if sha(destination) != expected:
            raise IOError("Published copy checksum mismatch")
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()
    return expected


def put_json(path, value):
    path = Path(path)
    contents = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "value.json"
        source.write_bytes(contents)
        copy_once(source, path)
    return value


def tree_copy(source, target):
    source, target = Path(source), Path(target)
    if source.exists():
        for path in sorted(source.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlinks are not evidence: {path}")
            if path.is_file() and not path.name.startswith(".copy-"):
                copy_once(path, target / path.relative_to(source))


@contextmanager
def durable_acquisition(local, persistent):
    """Persist reservations BEFORE HTTP; abort rather than run without Drive.

    Only the imported write helper in the research acquisition module is scoped
    temporarily. No historical source or production module is modified.
    """
    engine = importlib.import_module("research.benchmark.phase3c.acquire")
    local, persistent = Path(local).resolve(), Path(persistent).resolve()
    tree_copy(persistent, local)
    tree_copy(local, persistent)
    original = engine.write_once

    def durable(path, value):
        path = Path(path).resolve()
        if not path.is_relative_to(local):
            raise ValueError("Acquisition write escaped its capture directory")
        result = original(path, value)
        try:
            copy_once(path, persistent / path.relative_to(local))
        except Exception as error:
            # The old engine retries OSError. Persistence loss MUST stop the run.
            raise RuntimeError("Drive persistence failed; acquisition stopped") from error
        return result

    engine.write_once = durable
    try:
        yield
    finally:
        engine.write_once = original


EXCLUDED = {".git", ".venv", "node_modules", "__pycache__", "runtime", "exports", ".pytest_cache"}


def bundle_files(root):
    """Allowlist research inputs; never package real .env or user databases."""
    root = Path(root)
    for base in ("research", "backend/app", "backend/tests", "backend/evaluation", "backend/data", "backend/scripts"):
        for path in sorted((root / base).rglob("*")):
            relative = path.relative_to(root)
            if path.is_symlink():
                raise ValueError("Bundle cannot contain symlinks")
            if (path.is_file() and not EXCLUDED.intersection(relative.parts)
                    and not (path.name.startswith(".env") and path.name != ".env.example")
                    and not path.name.startswith(".copy-") and path.suffix not in {".pyc", ".zip", ".pbf"}
                    and ".osrm" not in path.name):
                yield path
    if (root / "backend/requirements.txt").is_file():
        yield root / "backend/requirements.txt"


def create_bundle(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    files = list(bundle_files(root))
    checksums = {p.relative_to(root).as_posix(): sha(p) for p in files}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
        archive.writestr("COLAB_INPUT_MANIFEST.json", json.dumps(checksums, sort_keys=True))
    return {"path": str(output), "sha256": sha(output), "files": len(files)}


def extract_bundle(archive_path, target, expected_sha256, maximum_bytes=4 * 1024**3):
    if len(expected_sha256) != 64 or sha(archive_path) != expected_sha256:
        raise ValueError("Input ZIP checksum is missing or incorrect")
    target = Path(target).resolve()
    with zipfile.ZipFile(archive_path) as archive:
        names = [item.filename for item in archive.infolist()]
        if len(names) != len(set(names)) or sum(i.file_size for i in archive.infolist()) > maximum_bytes:
            raise ValueError("Duplicate ZIP members or oversized repository bundle")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            if (path.is_absolute() or ".." in path.parts or "\\" in item.filename
                    or ":" in item.filename or stat.S_ISLNK(mode)):
                raise ValueError("Unsafe ZIP member")
        metadata = {"COLAB_INPUT_MANIFEST.json"}
        manifest_name = "COLAB_INPUT_MANIFEST.json"
        if "COLAB_EVIDENCE_MANIFEST.json" in names:
            manifest_name = "COLAB_EVIDENCE_MANIFEST.json"
            metadata.add(manifest_name)
        manifest = json.loads(archive.read(manifest_name))
        if set(names) != set(manifest) | metadata:
            raise ValueError("ZIP inventory differs from its manifest")
        for name, expected in manifest.items():
            body = archive.read(name)
            if hashlib.sha256(body).hexdigest() != expected:
                raise ValueError(f"ZIP member checksum mismatch: {name}")
            destination = target / name
            if destination.is_symlink() or not destination.resolve().is_relative_to(target):
                raise ValueError("ZIP destination escapes through an existing symlink")
            if destination.exists():
                if sha(destination) != expected:
                    raise ValueError(f"Existing import conflict: {name}")
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as stream:
                    stream.write(body)
    return target


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create a byte-preserving Colab input ZIP without private environments")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if not args.output.resolve().is_relative_to(root / "research"):
        parser.error("Place generated bundles inside research/exports/")
    print(json.dumps(create_bundle(root, args.output), indent=2))
