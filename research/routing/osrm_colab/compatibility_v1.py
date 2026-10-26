"""Auditable cstdint correction and separate probe/build warning diagnostics."""

import difflib
from pathlib import Path
import re
import shutil

from .dependencies_v3 import capture, checked
from .storage import put_json, sha
from .workflow import HERE

POLICY = HERE / "compatibility-v1.json"
CXX_FLAGS = ["-fdiagnostics-color=never", "-include", "cstdint"]
BUILD_MARKER = "=== Full OSRM build (all four targets; global Werror retained) ==="
WARNING_HOOK = HERE / "gcc11_compat.cmake"


def include_cstdint(original):
    """The candidate patch adds one include; no types or algorithms are changed."""
    if b"#include <cstdint>" in original or original.count(b"#include <cstddef>") != 1:
        raise ValueError("Unexpected coordinate header; stop rather than guess a patch")
    ending = b"\r\n" if b"\r\n" in original else b"\n"
    return original.replace(b"#include <cstddef>", b"#include <cstdint>" + ending + b"#include <cstddef>", 1)


def disposable_patch(source, directory):
    target = directory / "probe_source/include"
    shutil.copytree(source / "include", target)  # Never patch the pinned checkout.
    original = source / "include/util/coordinate.hpp"
    patched = target / "util/coordinate.hpp"
    before = original.read_bytes()
    patched.write_bytes(include_cstdint(before))
    difference = "".join(difflib.unified_diff(before.decode().splitlines(keepends=True),
                       patched.read_text().splitlines(keepends=True),
                       fromfile="a/include/util/coordinate.hpp", tofile="b/include/util/coordinate.hpp"))
    patch = directory / "coordinate-cstdint.patch"
    patch.write_text(difference, encoding="utf-8", newline="\n")
    return target, {"original_header_sha256": sha(original), "candidate_header_sha256": sha(patched),
                    "candidate_patch_sha256": sha(patch), "applied_to_build_source": False}


def select_compiler(source, directory):
    """Compare original, disposable patch and forced include with the same compiler."""
    includes, patch = disposable_patch(source, directory)
    attempts = []
    candidates = [(shutil.which("g++"), shutil.which("gcc")),
                  (shutil.which("g++-11"), shutil.which("gcc-11"))]
    seen = set()
    for cxx, cc in candidates:
        if not cxx or not cc or str(Path(cxx).resolve()) in seen:
            continue
        seen.add(str(Path(cxx).resolve()))
        version = checked([cxx, "--version"])
        major = checked([cxx, "-dumpversion"]).split(".")[0]
        if not major.isdigit() or int(major) < 11 or "clang" in version.lower():
            continue
        record = {"compiler": cxx, "version": version, "probes": {}}
        for label, include, flags in (("original", source / "include", []),
                                      ("explicit_header_patch", includes, []),
                                      ("forced_cstdint", source / "include", CXX_FLAGS)):
            command = [cxx, "-std=c++17", "-fdiagnostics-color=never", *flags, "-I", str(include),
                       "-fsyntax-only", "-x", "c++", str(HERE / "coordinate_probe.cpp")]
            result = capture(command)
            record["probes"][label] = {"command": command, "exit_code": result.returncode,
                                       "stdout": result.stdout, "stderr": result.stderr}
        attempts.append(record)
        if all(record["probes"][name]["exit_code"] == 0 for name in ("explicit_header_patch", "forced_cstdint")):
            if sha(source / "include/util/coordinate.hpp") != patch["original_header_sha256"]:
                raise ValueError("Original header changed during probes")
            selection = {"cxx": cxx, "cc": cc, "compiler_version": version, "header_probe": "passed",
                         "attempts": attempts, "cxx_flags": CXX_FLAGS, "patch_comparison": patch,
                         "compatibility_policy_sha256": sha(POLICY),
                         "selected_correction": "build-only forced include; original source remains unchanged"}
            put_json(directory / "compiler-selection.json", selection)
            return selection
    put_json(directory / "compiler-selection.json", {"attempts": attempts, "patch_comparison": patch, "selected": None})
    raise RuntimeError("Corrected probes failed; inspect compiler-selection.json. No errors suppressed and no compiler packages installed automatically")


def summarize_log(text):
    """A recovered probe error is not automatically the terminal build failure."""
    lines = text.splitlines()
    build_line = next((i for i, line in enumerate(lines) if BUILD_MARKER in line), None)
    errors, warnings, option_notes = [], [], []
    pattern = re.compile(r"^(.*?):(\d+)(?::(\d+))?:\s+(?:fatal )?error:\s*(.*)")
    for i, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            location = match[1]
            origin = ("dependency" if "/usr/include/" in location or "/third_party/" in location
                      else "osrm" if "/source/" in location else "unknown")
            value = {"line": i + 1, "diagnostic": line, "origin": origin,
                     "stage": "build" if build_line is not None and i > build_line else "probe_or_configure",
                     "context": lines[max(0, i - 4):i + 6]}
            errors.append(value)
            category = re.search(r"\[(-Werror(?:=[^\]]+)?)\]", line)
            if category:
                warnings.append(dict(value, warning_flag=category[1]))
        if "unrecognized command-line option" in line:
            option_notes.append(line)
    build_errors = [row for row in errors if row["stage"] == "build"]
    return {"first_compiler_error": errors[0] if errors else None,
            "first_build_error": build_errors[0] if build_errors else None,
            "warnings_as_errors": warnings, "unsupported_option_notes": option_notes,
            "warning_policy": "Only a recorded GCC 11 osrm.cpp free-nonheap-object demotion is permitted",
            "full_log_required": True}


def verify_compile_commands(path, compiler_major=None):
    """Prove that the forced include reached every generated C++ compilation."""
    import json
    import shlex
    commands = json.loads(path.read_text())
    count = 0
    for row in commands:
        if Path(row["file"]).suffix not in {".cpp", ".cc", ".cxx"}:
            continue
        arguments = row.get("arguments") or shlex.split(row["command"])
        if not any(arguments[i:i + 2] == ["-include", "cstdint"] for i in range(len(arguments) - 1)):
            raise ValueError(f"Missing recorded cstdint include: {row['file']}")
        allowed = compiler_major == "11" and row["file"].replace("\\", "/").endswith("/src/osrm/osrm.cpp")
        demotions = [flag for flag in arguments if flag in {"-w", "-Wno-error"} or flag.startswith("-Wno-error=")]
        if any(flag != "-Wno-error=free-nonheap-object" or not allowed for flag in demotions):
            raise ValueError(f"Unapproved warning suppression: {row['file']}")
        if allowed and "-Wno-error=free-nonheap-object" not in arguments:
            raise ValueError("Recorded GCC 11 source-specific compatibility flag is missing")
        if "-Werror" not in arguments and "/source/src/" in row["file"].replace("\\", "/"):
            raise ValueError("Upstream OSRM Werror policy disappeared")
        count += 1
    if not count:
        raise ValueError("No C++ compile commands found")
    return {"cpp_commands_verified": count, "compile_commands_sha256": sha(path),
            "compatibility_policy_sha256": sha(POLICY)}
