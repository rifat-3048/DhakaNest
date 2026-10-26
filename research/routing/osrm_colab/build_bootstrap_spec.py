"""Generate a separate trusted tool lock from an explicit PyPI dry-run report."""

import json
from pathlib import Path
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name
from .storage import put_json, sha


def build(report_path, directory):
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    items = {canonicalize_name(p["metadata"]["name"]): p for p in report["install"]}
    if items["virtualenv"]["metadata"]["version"] != "21.14.5":
        raise ValueError("Unexpected bootstrap tool version")
    for minor in ("3.12", "3.13"):
        env = {**report["environment"], "python_version": minor, "python_full_version": minor + ".16",
               "implementation_version": minor + ".16", "sys_platform": "linux", "os_name": "posix",
               "platform_system": "Linux", "platform_machine": "x86_64", "extra": ""}
        for item in items.values():
            meta = item["metadata"]
            if not SpecifierSet(meta.get("requires_python", "")).contains(minor + ".16"):
                raise ValueError("Bootstrap Python incompatibility")
            if not item["download_info"]["url"].endswith(("py3-none-any.whl", "py2.py3-none-any.whl")):
                raise ValueError("Bootstrap must use universal Python wheels")
            for text in meta.get("requires_dist", []):
                req = Requirement(text)
                if req.marker and not req.marker.evaluate(env):
                    continue
                dependency = items.get(canonicalize_name(req.name))
                if dependency is None or not req.specifier.contains(dependency["metadata"]["version"]):
                    raise ValueError(f"Unresolved bootstrap dependency: {text}")
    directory = Path(directory)
    lock = directory / "virtualenv-bootstrap-v1.lock.txt"
    with lock.open("x", encoding="utf-8", newline="\n") as output:
        output.write("# Private bootstrap tools ONLY; never install into system or research site-packages.\n")
        for key in sorted(items):
            item = items[key]
            digest = item["download_info"]["archive_info"]["hashes"]["sha256"]
            output.write(f"{item['metadata']['name']}=={item['metadata']['version']} --hash=sha256:{digest}\n")
    spec = {"id": "virtualenv-bootstrap-v1", "virtualenv_version": "21.14.5", "python_minors": ["3.12", "3.13"],
            "requirements": lock.name, "requirements_sha256": sha(lock),
            "packages": {key: item["metadata"]["version"] for key, item in items.items()},
            "source_report_sha256": sha(report_path), "seed_policy": "embedded pip only; no periodic updates/downloads; no activators",
            "isolation": "pip --target private helper directory; execute with -I -S; never system site-packages"}
    put_json(directory / "virtualenv-bootstrap-v1.json", spec)
    return spec


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.report, Path(__file__).resolve().parent), indent=2))
