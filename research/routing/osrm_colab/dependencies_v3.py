"""Detect existing dependencies; simulate and freeze additive APT transactions.

This module is executed only inside an explicitly authorized native setup stage.
No installed package may be removed, downgraded or upgraded by this strategy.
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from .storage import put_json

COMPONENTS = ("date-time", "chrono", "filesystem", "iostreams", "program-options",
              "regex", "system", "thread", "test")
BASE = ("git", "cmake", "make", "pkg-config", "libbz2-dev", "libxml2-dev",
        "libexpat1-dev", "zlib1g-dev", "libzip-dev", "lua5.2", "liblua5.2-dev",
        "libtbb-dev", "osmium-tool", "ca-certificates")


def capture(command):
    result = subprocess.run(command, text=True, capture_output=True)
    print("COMMAND:", command, "\nEXIT:", result.returncode, "\nSTDOUT:\n", result.stdout,
          "\nSTDERR:\n", result.stderr, flush=True)
    return result


def checked(command):
    result = capture(command)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command}; inspect full setup log")
    return result.stdout.strip()


def inventory():
    text = checked(["dpkg-query", "-W", "-f=${binary:Package}\t${db:Status-Status}\t${Version}\n"])
    return {name: version for line in text.splitlines()
            for name, state, version in [line.split("\t")]
            if state == "installed"}


def boost_version(header):
    match = re.search(r"^#define BOOST_VERSION (\d+)$", header, re.M)
    value = int(match[1]) if match else 0
    # These are the two target Ubuntu runtimes, not a claim of full compatibility.
    if value not in {107400, 108300}:
        raise RuntimeError(f"Detected Boost macro {value}; expected existing 1.74 or 1.83. Stop for review; do not replace headers")
    return f"{value // 100000}.{value // 100 % 1000}"


def missing_packages(installed, boost):
    names = {name.split(":")[0] for name in installed}
    desired = BASE + tuple(f"libboost-{component}{boost}-dev" for component in COMPONENTS)
    return [name for name in desired if name not in names]


def parse_simulation(text, returncode, installed):
    """Fail closed on solver errors, removals, existing-package changes or unknown output."""
    if returncode or re.search(r"^E:|unmet dependencies|held broken packages|unresolved", text, re.M | re.I):
        raise RuntimeError("APT simulation failed. Inspect apt-*.json; keep existing libraries and resolve the package candidates before retrying")
    summary = re.search(r"(\d+) upgraded, (\d+) newly installed, (?:(\d+) downgraded, )?(\d+) to remove", text)
    if not summary:
        raise RuntimeError("APT simulation summary missing; refusing an unrecognized transaction")
    if (int(summary[1]) or int(summary[3] or 0) or int(summary[4])
            or re.search(r"^Remv\s|will be REMOVED|will be DOWNGRADED", text, re.M)):
        raise RuntimeError("APT plan changes existing packages. No installation authorized; retain Colab's Boost and dependent libraries")
    known = {name.split(":")[0] for name in installed}
    plan = {}
    for line in text.splitlines():
        if not line.startswith("Inst "):
            continue
        match = re.match(r"Inst (\S+)\s+\((\S+)\s", line)
        if not match or match[1].split(":")[0] in known:
            raise RuntimeError(f"APT attempts to change an existing/unknown package: {line}")
        if match[1] in plan:
            raise RuntimeError("Duplicate APT installation action")
        plan[match[1]] = match[2]
    if len(plan) != int(summary[2]):
        raise RuntimeError("APT action count differs from summary; refusing installation")
    return plan


def verify_preserved(before, after):
    changed = [name for name, version in before.items() if after.get(name) != version]
    if changed:
        raise RuntimeError(f"Existing package inventory changed: {changed}. Stop; do not build or repair automatically")


def install_additive(packages, directory, label):
    """Persist both simulation passes. Install only the exact new versions simulated."""
    before = inventory()
    if not packages:
        put_json(directory / f"apt-{label}.json", {"status": "no missing packages", "plan": {}})
        return
    if checked(["dpkg", "--audit"]):
        raise RuntimeError("dpkg reports incomplete packages; stop for operator review")
    first = capture(["apt-get", "--simulate", "--no-install-recommends", "install", *packages])
    put_json(directory / f"apt-{label}.json", {"requested": packages, "returncode": first.returncode,
                                             "stdout": first.stdout, "stderr": first.stderr})
    plan = parse_simulation(first.stdout + "\n" + first.stderr, first.returncode, before)
    pinned = [f"{name}={version}" for name, version in sorted(plan.items())]
    if not pinned:
        return
    second = capture(["apt-get", "--simulate", "--no-install-recommends", "install", *pinned])
    put_json(directory / f"apt-{label}-pinned.json", {"requested": pinned, "returncode": second.returncode,
                                                    "stdout": second.stdout, "stderr": second.stderr})
    if parse_simulation(second.stdout + "\n" + second.stderr, second.returncode, before) != plan:
        raise RuntimeError("APT plan changed while pinning; stop for review")
    verify_preserved(before, inventory())
    checked(["apt-get", "install", "-y", "--no-remove", "--no-upgrade", "--no-install-recommends", *pinned])
    after = inventory()
    verify_preserved(before, after)
    for name, version in plan.items():
        actual = after.get(name, after.get(name + ":amd64"))
        if actual != version:
            raise RuntimeError(f"Installed package differs from simulated pin: {name}")
    put_json(directory / f"apt-{label}-verified.json", {"new_packages": plan, "existing_packages_preserved": len(before)})


def select_compiler(source, directory):
    """Prefer the existing GNU compiler. GCC 11 is conditional, never presumed necessary."""
    from .workflow import HERE
    attempts = []
    candidates = [(shutil.which("g++"), shutil.which("gcc")),
                  (shutil.which("g++-11"), shutil.which("gcc-11"))]
    seen = set()
    for index in range(3):
        if index == 2:
            if shutil.which("g++-11") and shutil.which("gcc-11"):
                break
            # Only after an actual default-compiler header failure, use a safe APT plan.
            install_additive(["gcc-11", "g++-11"], directory, "compiler-fallback")
            candidates.append((shutil.which("g++-11"), shutil.which("gcc-11")))
        cxx, cc = candidates[index]
        if not cxx or not cc or str(Path(cxx).resolve()) in seen:
            continue
        seen.add(str(Path(cxx).resolve()))
        version = checked([cxx, "--version"])
        major = checked([cxx, "-dumpversion"]).split(".")[0]
        if not major.isdigit() or int(major) < 11 or "clang" in version.lower():
            attempts.append({"compiler": cxx, "rejected": "GNU >=11 required for this build specification"})
            continue
        result = capture([cxx, "-std=c++17", "-fdiagnostics-color=never", "-I", str(source / "include"),
                          "-fsyntax-only", "-x", "c++", str(HERE / "coordinate_probe.cpp")])
        attempts.append({"compiler": cxx, "version": version, "exit_code": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode == 0:
            selected = {"cxx": cxx, "cc": cc, "compiler_version": version, "header_probe": "passed",
                        "attempts": attempts}
            put_json(directory / "compiler-selection.json", selected)
            return selected
    put_json(directory / "compiler-selection.json", {"attempts": attempts, "selected": None})
    raise RuntimeError("No compiler passed the unmodified OSRM coordinate-header probe; inspect compiler-selection.json, no C++ patches applied")


def prepare(directory):
    os.environ.update(LC_ALL="C", DEBIAN_FRONTEND="noninteractive")
    system = Path("/etc/os-release").read_text()
    if not re.search(r'^ID=\"?ubuntu\"?$', system, re.M) or not re.search(r'^VERSION_ID="(?:22\.04|24\.04)"$', system, re.M):
        raise RuntimeError("This specification targets Ubuntu 22.04/24.04 only")
    if checked(["dpkg", "--print-architecture"]) != "amd64":
        raise RuntimeError("Native build requires amd64")
    before = inventory()
    put_json(directory / "packages-before.json", before)
    boost = boost_version(Path("/usr/include/boost/version.hpp").read_text())
    detected = {"boost": boost, "os_release": system,
                "tools": {name: shutil.which(name) for name in ("g++", "gcc", "g++-11", "gcc-11", "cmake")}}
    detected["tool_versions"] = {}
    for name, path in detected["tools"].items():
        if path:
            result = capture([path, "--version"])
            detected["tool_versions"][name] = {"exit_code": result.returncode,
                                                "stdout": result.stdout, "stderr": result.stderr}
    put_json(directory / "detected-environment.json", detected)
    print("Detected environment:", json.dumps(detected), flush=True)
    # Updating indexes changes no installed package; every install is simulated first.
    checked(["apt-get", "update"])
    install_additive(missing_packages(before, boost), directory, "dependencies")
    verify_preserved(before, inventory())
    if boost_version(Path("/usr/include/boost/version.hpp").read_text()) != boost:
        raise RuntimeError("Boost header version changed")
    return boost, before
