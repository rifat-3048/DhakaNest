"""V9 changes only build-source preparation/preflight, reusing all v8 safeguards."""

import argparse
import json
from pathlib import Path
import subprocess

from . import compatibility_v2 as base
from .compatibility_v3 import POLICY, verify_compile_commands
from .dependencies_v3 import checked, inventory, prepare, verify_preserved
from .headers_v9 import disposable_source, preflight, tree_manifest, verify_source_copy
from .storage import put_json, sha
from .workflow import HERE, OSRM_COMMIT


def build(attempt):
    attempt.mkdir(parents=True, exist_ok=False)
    boost, packages_before = prepare(attempt)
    pristine, source, binary = attempt / "source", attempt / "build_source", attempt / "build"
    checked(["git", "init", str(pristine)])
    git = ["git", "-C", str(pristine)]
    checked(git + ["remote", "add", "origin", "https://github.com/Project-OSRM/osrm-backend.git"])
    checked(git + ["fetch", "--depth", "1", "origin", "refs/tags/v5.27.1"])
    if checked(git + ["rev-parse", "FETCH_HEAD^{commit}"]) != OSRM_COMMIT:
        raise RuntimeError("Official source ref differs from pinned commit")
    checked(git + ["checkout", "--detach", OSRM_COMMIT])
    checked(git + ["submodule", "update", "--init", "--recursive", "--depth", "1"])
    checked(git + ["fsck", "--no-dangling"])
    if checked(git + ["status", "--porcelain", "--untracked-files=all"]):
        raise RuntimeError("Pristine source is dirty")
    inherited_policy = json.loads(base.POLICY.read_text())
    for relative, key in (("include/util/coordinate.hpp", "original_coordinate_header_sha256"),
                          ("cmake/warnings.cmake", "original_warning_configuration_sha256"),
                          ("third_party/sol2-3.3.0/include/sol/sol.hpp", "original_sol2_header_sha256")):
        if sha(pristine / relative) != inherited_policy[key]:
            raise RuntimeError(f"Pristine source hash differs: {relative}")
    manifest = disposable_source(pristine, source, attempt)
    selection = base.select_compiler(pristine, attempt)
    major = checked([selection["cxx"], "-dumpversion"]).split(".")[0]
    cmake = "/usr/bin/cmake"
    version = checked([cmake, "--version"])
    if not version.startswith("cmake version 3."):
        raise RuntimeError("Existing system CMake 3.x required")
    checked([selection["cxx"], "-std=c++17", *base.CXX_FLAGS,
             f"-DEXPECTED_BOOST={100000 + int(boost.split('.')[1]) * 100}", str(HERE / "boost_probe.cpp"),
             "-o", str(attempt / "boost-probe"), "-lboost_filesystem", "-lboost_program_options"])
    checked([str(attempt / "boost-probe")])
    query = binary / ".cmake/api/v1/query"
    query.mkdir(parents=True)
    (query / "codemodel-v2").touch(exist_ok=False)
    command = [cmake, "-S", str(source), "-B", str(binary),
               "-DCMAKE_C_COMPILER=" + selection["cc"], "-DCMAKE_CXX_COMPILER=" + selection["cxx"],
               "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_VERBOSE_MAKEFILE=ON", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
               "-DCMAKE_CXX_FLAGS=" + " ".join(base.CXX_FLAGS), "-DCMAKE_PROJECT_OSRM_INCLUDE=" + str(base.WARNING_HOOK),
               "-DBoost_NO_BOOST_CMAKE=ON", "-DBOOST_ROOT=/usr", "-DBOOST_INCLUDEDIR=/usr/include",
               "-DBoost_ADDITIONAL_VERSIONS=" + boost + ".0", "-DBUILD_SHARED_LIBS=OFF",
               "-DENABLE_CCACHE=OFF", "-DENABLE_NODE_BINDINGS=OFF", "-DENABLE_LTO=OFF", "-DENABLE_GOLD_LINKER=OFF"]
    put_json(attempt / "build-override.json", {"policy_sha256": sha(POLICY), "inherited_policy_sha256": sha(base.POLICY),
             "cmake_command": command, "compiler_major": major, "cxx_flags": base.CXX_FLAGS,
             "warning_overrides": base.overrides(major), "warning_hook_sha256": sha(base.WARNING_HOOK),
             "source_patch_sha256": manifest["patch_sha256"]})
    checked(command)
    put_json(attempt / "compile-compatibility.json", verify_compile_commands(binary / "compile_commands.json", major, source))
    preflight(pristine, source, binary, attempt)  # Failure stops before any expensive target build.
    put_json(attempt / "compatibility-probes.json", {"boost": boost, "compiler": selection, "cmake": version,
             "header_preflight": "passed", "full_build_accepted": False, "header_policy_sha256": sha(POLICY)})
    print(base.BUILD_MARKER, flush=True)
    subprocess.run([cmake, "--build", str(binary), "--verbose", "--parallel", "1", "--target",
                    "osrm-extract", "osrm-partition", "osrm-customize", "osrm-routed"], check=True)
    verify_source_copy(manifest["pristine_files"], tree_manifest(source))
    if checked(git + ["status", "--porcelain", "--untracked-files=all"]):
        raise RuntimeError("Pristine source changed during build")
    after = inventory()
    verify_preserved(packages_before, after)
    put_json(attempt / "packages-after.json", after)
    (attempt / "system-packages.txt").write_text(checked(["dpkg-query", "-W"]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=Path, required=True)
    build(parser.parse_args().attempt)
