"""Frozen-header inventory and compiler-backed preflight; no inferred auto-patches."""

import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

from .compatibility_v2 import command_arguments
from .storage import put_json, sha

SUFFIX = "include/extractor/suffix_table.hpp"
ORIGINAL_SHA = "4035f945b7507677586cab639971293d34ea8f526df66dedf01ff23887af7945"
PATCHED_SHA = "7c1dc301eaf255452ec05b994bf6026dfc61a567554d6cdb4f549a1cfe3d9203"
TARGETS = ("osrm-extract", "osrm-partition", "osrm-customize", "osrm-routed")
STANDARD = {"vector": "vector", "string": "string", "array": "array", "string_view": "string_view",
            "unordered_map": "unordered_map", "unordered_set": "unordered_set", "map": "map", "set": "set",
            "unique_ptr": "memory", "shared_ptr": "memory", "weak_ptr": "memory", "function": "functional",
            "optional": "optional", "tuple": "tuple", "pair": "utility", "numeric_limits": "limits",
            "size_t": "cstddef", "int32_t": "cstdint", "uint32_t": "cstdint", "uint64_t": "cstdint",
            "int64_t": "cstdint", "uint16_t": "cstdint", "uint8_t": "cstdint"}
QUOTE_INCLUDE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.M)


def vector_patch(contents):
    if hashlib.sha256(contents).hexdigest() != ORIGINAL_SHA:
        raise ValueError("Unexpected frozen suffix header bytes; refuse guessed correction")
    corrected = contents.replace(b"#include <string>", b"#include <vector>\n#include <string>", 1)
    if hashlib.sha256(corrected).hexdigest() != PATCHED_SHA:
        raise ValueError("Suffix correction checksum differs")
    return corrected


def tree_manifest(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob("*"))
            if ".git" not in p.relative_to(root).parts and p.is_file()}


def disposable_source(pristine, destination, evidence):
    before = tree_manifest(pristine)
    shutil.copytree(pristine, destination, ignore=shutil.ignore_patterns(".git"))
    original = (pristine / SUFFIX).read_bytes()
    (destination / SUFFIX).write_bytes(vector_patch(original))
    after = tree_manifest(destination)
    verify_source_copy(before, after)
    difference = "".join(difflib.unified_diff(original.decode().splitlines(keepends=True),
                 (destination / SUFFIX).read_text().splitlines(keepends=True), fromfile="a/" + SUFFIX, tofile="b/" + SUFFIX))
    path = evidence / "suffix-vector.patch"
    path.write_text(difference, encoding="utf-8", newline="\n")
    record = {"pristine_files": before, "build_files": after, "only_modified_file": SUFFIX,
              "original_sha256": ORIGINAL_SHA, "corrected_sha256": PATCHED_SHA, "patch_sha256": sha(path)}
    put_json(evidence / "header-source-manifest.json", record)
    return record


def verify_source_copy(before, after):
    if set(before) != set(after) or [name for name in before if before[name] != after[name]] != [SUFFIX]:
        raise ValueError("Disposable source differs beyond the one justified header include")
    if before[SUFFIX] != ORIGINAL_SHA or after[SUFFIX] != PATCHED_SHA:
        raise ValueError("Unexpected header correction hashes")


def inventory(source):
    """Lexical hints ONLY. A missing direct include is not a proven compiler defect."""
    result = []
    for path in sorted((source / "include").rglob("*.hpp")):
        raw = path.read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/|//[^\n]*", "", raw, flags=re.S)
        declared = set(re.findall(r"#\s*include\s*<([^>]+)>", text))
        used = set(re.findall(r"\bstd::([A-Za-z_][A-Za-z_0-9]*)", text))
        missing = sorted({STANDARD[name] for name in used if name in STANDARD and STANDARD[name] not in declared})
        if missing:
            result.append({"header": path.relative_to(source / "include").as_posix(),
                           "missing_direct_include_candidates": missing, "status": "lexical_candidate_not_a_verified_defect"})
    return result


def file_api_sources(binary, source):
    """Use CMake's structured target dependency graph, not guessed library names."""
    reply = binary / ".cmake/api/v1/reply"
    indexes = sorted(reply.glob("index-*.json"))
    if len(indexes) != 1:
        raise ValueError("Clean CMake File API codemodel reply required")
    index = json.loads(indexes[0].read_text())
    model = json.loads((reply / index["reply"]["codemodel-v2"]["jsonFile"]).read_text())
    configurations = model["configurations"]
    if len(configurations) != 1:
        raise ValueError("Single Release configuration required")
    targets = {row["id"]: row for row in configurations[0]["targets"]}
    names = {row["name"]: row["id"] for row in targets.values()}
    if not set(TARGETS).issubset(names):
        raise ValueError("Required executable missing from CMake target graph")
    pending, visited, paths = [names[name] for name in TARGETS], set(), set()
    while pending:
        key = pending.pop()
        if key in visited:
            continue
        visited.add(key)
        target = json.loads((reply / targets[key]["jsonFile"]).read_text())
        pending.extend(row["id"] for row in target.get("dependencies", []))
        for row in target.get("sources", []):
            path = Path(row["path"])
            paths.add((path if path.is_absolute() else source / path).resolve())
    return paths, sorted(targets[key]["name"] for key in visited)


def reachable_headers(source, source_files):
    pending = list(source_files)
    seen, headers = set(), set()
    root = source.resolve()
    while pending:
        path = pending.pop().resolve()
        if path in seen or not path.is_relative_to(root) or not path.is_file():
            continue
        seen.add(path)
        if path.is_relative_to(root / "include"):
            headers.add(path.relative_to(root / "include").as_posix())
        for include in QUOTE_INCLUDE.findall(path.read_text(encoding="utf-8", errors="replace")):
            candidates = [path.parent / include, root / "include" / include, root / include]
            pending.extend([next((p for p in candidates if p.is_file()), root / "__not_found__")])
    return headers


def syntax_arguments(row):
    original = command_arguments(row)
    result, skip = [], False
    for argument in original:
        if skip:
            skip = False
            continue
        if argument in {"-o", "-MF", "-MT", "-MQ", "-c"}:
            skip = True
            continue
        if argument in {"-MD", "-MMD", "-MP"} or argument.startswith("-Wno-error="):
            continue
        result.append(argument)
    return result + ["-fsyntax-only", "-x", "c++", "-"]


def compile_probe(command, code, directory, label, expected_negative=False):
    marker = "EXPECTED NEGATIVE PROBE" if expected_negative else "PREFLIGHT REQUIRED PROBE"
    print(f"=== {marker}: {label} ===", flush=True)
    try:
        result = subprocess.run(command, input=code, cwd=directory, capture_output=True, text=True, timeout=45)
        value = {"command": command, "input": code, "exit_code": result.returncode,
                 "stdout": result.stdout, "stderr": result.stderr, "expected_negative": expected_negative}
    except subprocess.TimeoutExpired as error:
        value = {"command": command, "input": code, "exit_code": None, "timeout": True,
                 "stdout": str(error.stdout or ""), "stderr": str(error.stderr or ""), "expected_negative": expected_negative}
    print(json.dumps({"label": label, "exit_code": value["exit_code"], "expected_negative": expected_negative,
                      "diagnostic_preview": value.get("stderr", "").splitlines()[:6]}), flush=True)
    return value


def preflight(pristine, source, binary, evidence):
    rows = json.loads((binary / "compile_commands.json").read_text())
    files, targets = file_api_sources(binary, source)
    selected = [row for row in rows if Path(row["file"]).resolve() in files]
    if not selected:
        raise ValueError("No generated compile commands for the required target closure")
    representative = next(row for row in selected if Path(row["file"]).resolve() == (source / "src/extractor/suffix_table.cpp").resolve())
    command = syntax_arguments(representative)
    compiler_info = compile_probe([command[0], "-std=c++17", "-E", "-dM", "-x", "c++", "-"],
                                 "#include <cstdint>\n#include <vector>\n", source, "compiler-and-stdlib")
    put_json(evidence / "compiler-stdlib.json", compiler_info)
    if compiler_info["exit_code"] != 0:
        raise RuntimeError("Compiler/standard library readiness failed")
    negative = compile_probe(command, f'#include "{(pristine / SUFFIX).as_posix()}"\n', source, "original-suffix", True)
    put_json(evidence / "suffix-negative-probe.json", negative)
    corrected = compile_probe(command, '#include "extractor/suffix_table.hpp"\n', source, "corrected-suffix")
    put_json(evidence / "suffix-corrected-probe.json", corrected)
    if corrected["exit_code"] != 0:
        raise RuntimeError("Corrected suffix header still fails; no full build")
    hints = inventory(pristine)
    relevant = reachable_headers(source, files)
    candidates = [row for row in hints if row["header"] in relevant]
    report = {"inventory": hints, "target_closure": targets, "reachable_owned_headers": sorted(relevant),
              "candidate_count": len(candidates), "probes": [], "full_build_permitted": False}
    start = time.monotonic()
    try:
        if len(candidates) > 256:
            raise RuntimeError("Header audit exceeds reviewed 256-candidate cap; inspect inventory before expanding")
        for row in candidates:
            if time.monotonic() - start > 300:
                raise RuntimeError("Header preflight time budget reached; no partial pass or automatic retry")
            value = compile_probe(command, '#include "' + row["header"] + '"\n', source, row["header"])
            report["probes"].append(dict(row, result=value))
        failures = [row["header"] for row in report["probes"] if row["result"]["exit_code"] != 0]
        if failures:
            raise RuntimeError(f"Header preflight blocked: {failures}. No speculative includes added; inspect diagnostics before full build")
        report["full_build_permitted"] = True
    finally:
        put_json(evidence / "header-preflight.json", report)
    return report
