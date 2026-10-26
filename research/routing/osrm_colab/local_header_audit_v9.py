"""Inspect exact Git blobs and run HOST focused probes; never a Linux OSRM build."""

import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import uuid

from .headers_v9 import SUFFIX, ORIGINAL_SHA, PATCHED_SHA, compile_probe, disposable_source, inventory
from .storage import put_json, sha
from .workflow import HERE, ROOT, OSRM_COMMIT


def main():
    checkout = HERE / "runtime/osrm_v9_audit"
    git = ["git", "-c", "safe.directory=" + checkout.as_posix(), "-C", str(checkout)]
    if subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip() != OSRM_COMMIT:
        raise ValueError("Audit checkout is not pinned")
    if subprocess.check_output(git + ["status", "--porcelain"], text=True).strip():
        raise ValueError("Audit checkout is dirty")
    # Git archive otherwise honors the Windows checkout EOL configuration.
    archive = subprocess.check_output(git[:1] + ["-c", "core.autocrlf=false", "-c", "core.eol=lf"] + git[1:] + ["archive", "--format=tar", "HEAD"])
    work = HERE / "runtime" / ("header-audit-v9-" + uuid.uuid4().hex)
    pristine = work / "pristine"
    omitted = []
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        for member in source.getmembers():
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or "\\" in member.name:
                raise ValueError("Unsafe source archive path")
            if not member.isfile():
                if not member.isdir():
                    omitted.append(member.name)
                continue
            destination = pristine / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.extractfile(member).read())
    if sha(pristine / SUFFIX) != ORIGINAL_SHA:
        raise ValueError("Frozen Git blob differs from expected suffix hash")
    evidence = ROOT / "research/results/phase_3d_colab/header_audit_v9"
    evidence.mkdir(parents=True, exist_ok=False)
    manifest = disposable_source(pristine, work / "build_source", evidence)
    hints = inventory(pristine)
    put_json(evidence / "candidate-inventory.json", hints)
    compiler = shutil.which("g++")
    if not compiler:
        raise RuntimeError("No existing host compiler; do not fabricate focused probe results")
    # Exact known member declaration and standard includes, isolating Boost from this proof.
    blob = (pristine / SUFFIX).read_text()
    declaration = next(line.strip() for line in blob.splitlines() if "std::vector<std::string> suffixes;" in line)
    standard = "#include <string>\n#include <unordered_set>\nstruct KnownSuffixReproduction { " + declaration + " };\n"
    command = [compiler, "-std=c++17", "-fsyntax-only", "-x", "c++", "-"]
    negative = compile_probe(command, standard, work, "isolated-original-suffix-declaration", True)
    positive = compile_probe(command, "#include <vector>\n" + standard, work, "isolated-corrected-suffix-declaration")
    put_json(evidence / "focused-probes.json", {"negative": negative, "corrected": positive,
                                               "scope": "Known frozen declaration with its standard includes; Boost omitted explicitly"})
    if negative["exit_code"] == 0 or positive["exit_code"] != 0 or "vector" not in negative["stderr"]:
        raise RuntimeError("Required focused negative/positive reproduction did not establish the correction")
    original_full = compile_probe(command[:-1] + ["-I", str(pristine / "include"), "-"],
                                  '#include "extractor/suffix_table.hpp"\n', work, "host-full-original-header", True)
    corrected_full = compile_probe(command[:-1] + ["-I", str(work / "build_source/include"), "-"],
                                   '#include "extractor/suffix_table.hpp"\n', work, "host-full-corrected-header")
    put_json(evidence / "host-full-header-probes.json", {"original": original_full, "corrected": corrected_full,
              "passed": corrected_full["exit_code"] == 0,
              "note": "Missing host Boost is a blocked full-header probe, NOT proof that the vector correction failed or passed"})
    version = subprocess.check_output([compiler, "--version"], text=True).strip()
    macros = compile_probe([compiler, "-std=c++17", "-E", "-dM", "-x", "c++", "-"],
                           "#include <vector>\n#include <cstdint>\n", work, "host-compiler-and-stdlib")
    put_json(evidence / "host-stdlib.json", macros)
    report = {"source_commit": OSRM_COMMIT, "git_archive_sha256": hashlib.sha256(archive).hexdigest(),
              "omitted_nonregular_archive_members": omitted, "candidate_headers": len(hints),
              "inventory_is_not_verified_defect_count": True, "original_suffix_sha256": ORIGINAL_SHA,
              "corrected_suffix_sha256": PATCHED_SHA, "patch_sha256": manifest["patch_sha256"],
              "host_compiler": version, "focused_negative_failed_and_corrected_passed": True,
              "full_header_host_probe_passed": corrected_full["exit_code"] == 0,
              "full_linux_compilation_executed": False, "routing_executed": False,
              "pristine_path": str(pristine), "disposable_source_path": str(work / "build_source")}
    put_json(evidence / "verification.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
