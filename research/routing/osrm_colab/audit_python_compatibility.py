"""Explicit online PyPI wheel audit. Ordinary unit tests never call the network."""

import argparse
import json
from pathlib import Path
import time
from urllib.request import urlopen

from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.tags import cpython_tags, compatible_tags
from pip._vendor.packaging.utils import parse_wheel_filename
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.requirements import Requirement

from .environment import pinned_packages, HERE
from .storage import put_json, sha


def audit():
    configurations = (("3.12", HERE / "requirements-colab.txt"),
                      ("3.13", HERE / "requirements-colab-py313-v1.txt"),
                      ("3.13-original", HERE / "requirements-colab.txt"))
    releases, checks = {}, {}
    for label, path in configurations:
        minor = "3.12" if label == "3.12" else "3.13"
        version = tuple(map(int, minor.split(".")))
        platforms = ["manylinux_2_28_x86_64", "manylinux_2_17_x86_64", "manylinux2014_x86_64",
                     "manylinux_2_24_x86_64", "manylinux_2_27_x86_64"]
        tags = set(cpython_tags(version, platforms=platforms)) | set(compatible_tags(version, interpreter="cp" + minor.replace(".", ""), platforms=platforms))
        rows = []
        for name, pin in pinned_packages(path).items():
            key = name + "==" + pin
            if key not in releases:
                url = f"https://pypi.org/pypi/{name}/{pin}/json"
                with urlopen(url, timeout=60) as response:
                    raw = response.read()
                import hashlib
                releases[key] = {"url": url, "response_sha256": hashlib.sha256(raw).hexdigest(), "metadata": json.loads(raw)}
            release = releases[key]
            metadata = release["metadata"]
            available = []
            for item in metadata["urls"]:
                if item["packagetype"] != "bdist_wheel" or item.get("yanked"):
                    continue
                if item.get("requires_python") and not SpecifierSet(item["requires_python"]).contains(minor + ".16"):
                    continue
                if parse_wheel_filename(item["filename"])[3] & tags:
                    available.append({k: item[k] for k in ("filename", "url", "digests", "requires_python")})
            rows.append({"package": name, "version": pin, "requires_python": metadata["info"]["requires_python"],
                         "compatible_linux_wheels": available})
        checks[label] = {"requirements_sha256": sha(path), "packages": rows,
                         "all_pins_have_compatible_wheels": all(r["compatible_linux_wheels"] for r in rows)}
    return {"checked_at_unix": time.time(), "source": "PyPI release JSON and PEP 425 wheel tags; not a Colab runtime test",
            "checks": checks, "releases": releases}


def validate_resolution(report):
    """Cross-target pip still evaluates some markers on its Windows host.

    Re-evaluate every dependency using Linux/3.13 markers, including XGBoost's
    mandatory Linux NCCL package. This does not assert runtime import success.
    """
    environment = {"implementation_name": "cpython", "implementation_version": "3.13.16",
                   "os_name": "posix", "platform_machine": "x86_64", "platform_release": "",
                   "platform_system": "Linux", "platform_version": "", "python_full_version": "3.13.16",
                   "platform_python_implementation": "CPython", "python_version": "3.13", "sys_platform": "linux", "extra": ""}
    items = {canonicalize_name(p["metadata"]["name"]): p for p in report["install"]}
    problems = []
    for name, item in items.items():
        data = item["metadata"]
        if data.get("requires_python") and not SpecifierSet(data["requires_python"]).contains("3.13.16"):
            problems.append(f"{name}: Python requirement not met")
        for text in data.get("requires_dist", []):
            requirement = Requirement(text)
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            dependency = items.get(canonicalize_name(requirement.name))
            if dependency is None or not requirement.specifier.contains(dependency["metadata"]["version"]):
                problems.append(f"{name}: unresolved {text}")
    if problems:
        raise ValueError("Linux target closure invalid: " + "; ".join(problems))
    return {"target": environment, "resolved_packages": len(items), "dependency_closure": "passed",
            "runtime_imports_executed": False, "pip_resolver_host": report["environment"]}


def write_lock(report, path):
    validated = validate_resolution(report)
    lines = ["# CPython 3.13 Linux x86_64 only. All direct/transitive packages and wheel hashes frozen.",
             "# Generated from the validated PyPI resolver report; no packages installed during generation."]
    for item in sorted(report["install"], key=lambda p: p["metadata"]["name"].lower()):
        metadata = item["metadata"]
        digest = item["download_info"]["archive_info"]["hashes"]["sha256"]
        lines.append(f"{metadata['name']}=={metadata['version']} --hash=sha256:{digest}")
    with Path(path).open("x", encoding="utf-8", newline="\n") as output:
        output.write("\n".join(lines) + "\n")
    return validated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resolver-report", type=Path)
    parser.add_argument("--lock-output", type=Path)
    args = parser.parse_args()
    if args.resolver_report:
        if args.lock_output is None:
            parser.error("Provide a new --lock-output with the resolver report")
        report = json.loads(args.resolver_report.read_text(encoding="utf-8"))
        result = write_lock(report, args.lock_output)
        put_json(args.output, result)
        print(json.dumps(result, indent=2))
        raise SystemExit(0)
    result = audit()
    put_json(args.output, result)
    print(json.dumps({key: {"all_pins_have_compatible_wheels": value["all_pins_have_compatible_wheels"],
                            "missing_wheels": [r["package"] for r in value["packages"] if not r["compatible_linux_wheels"]]}
                      for key, value in result["checks"].items()}, indent=2))
