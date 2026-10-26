"""V8 pristine build, additive APT and exact source-scoped Sol2 compatibility."""

import argparse
import json
from pathlib import Path
import re
import subprocess

from .compatibility_v2 import BUILD_MARKER, CXX_FLAGS, POLICY, WARNING_HOOK, overrides, select_compiler, verify_compile_commands
from .dependencies_v3 import checked, inventory, prepare, verify_preserved
from .storage import put_json, sha
from .workflow import HERE, OSRM_COMMIT


def build(attempt):
    attempt.mkdir(parents=True, exist_ok=False)
    boost, before = prepare(attempt)
    source, binary = attempt / "source", attempt / "build"
    checked(["git", "init", str(source)])
    git = ["git", "-C", str(source)]
    checked(git + ["remote", "add", "origin", "https://github.com/Project-OSRM/osrm-backend.git"])
    checked(git + ["fetch", "--depth", "1", "origin", "refs/tags/v5.27.1"])
    if checked(git + ["rev-parse", "FETCH_HEAD^{commit}"]) != OSRM_COMMIT:
        raise RuntimeError("Official tag differs from pinned OSRM revision")
    checked(git + ["checkout", "--detach", OSRM_COMMIT])
    checked(git + ["submodule", "update", "--init", "--recursive", "--depth", "1"])
    checked(git + ["fsck", "--no-dangling"])
    if checked(git + ["status", "--porcelain", "--untracked-files=all"]):
        raise RuntimeError("Source checkout is not clean")
    policy = json.loads(POLICY.read_text())
    for relative, key in (("include/util/coordinate.hpp", "original_coordinate_header_sha256"),
                          ("cmake/warnings.cmake", "original_warning_configuration_sha256"),
                          ("third_party/sol2-3.3.0/include/sol/sol.hpp", "original_sol2_header_sha256")):
        if sha(source / relative) != policy[key]:
            raise RuntimeError(f"Pinned source bytes differ: {relative}")
    selection = select_compiler(source, attempt)
    cmake = "/usr/bin/cmake"
    version = checked([cmake, "--version"])
    if not re.match(r"cmake version 3\.", version):
        raise RuntimeError("System CMake 3.x required")
    checked([selection["cxx"], "-std=c++17", *CXX_FLAGS,
             f"-DEXPECTED_BOOST={100000 + int(boost.split('.')[1]) * 100}", str(HERE / "boost_probe.cpp"),
             "-o", str(attempt / "boost-probe"), "-lboost_filesystem", "-lboost_program_options"])
    checked([str(attempt / "boost-probe")])
    command = [cmake, "-S", str(source), "-B", str(binary),
               "-DCMAKE_C_COMPILER=" + selection["cc"], "-DCMAKE_CXX_COMPILER=" + selection["cxx"],
               "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_VERBOSE_MAKEFILE=ON", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
               "-DCMAKE_CXX_FLAGS=" + " ".join(CXX_FLAGS), "-DCMAKE_PROJECT_OSRM_INCLUDE=" + str(WARNING_HOOK),
               "-DBoost_NO_BOOST_CMAKE=ON", "-DBOOST_ROOT=/usr", "-DBOOST_INCLUDEDIR=/usr/include",
               "-DBoost_ADDITIONAL_VERSIONS=" + boost + ".0", "-DBUILD_SHARED_LIBS=OFF",
               "-DENABLE_CCACHE=OFF", "-DENABLE_NODE_BINDINGS=OFF", "-DENABLE_LTO=OFF", "-DENABLE_GOLD_LINKER=OFF"]
    major = checked([selection["cxx"], "-dumpversion"]).split(".")[0]
    put_json(attempt / "build-override.json", {"policy_sha256": sha(POLICY), "cmake_command": command,
             "cxx_flags": CXX_FLAGS, "compiler_major": major, "warning_hook_sha256": sha(WARNING_HOOK),
             "inherited_warning_hook_sha256": sha(HERE / "gcc11_compat.cmake"), "warning_overrides": overrides(major)})
    checked(command)
    put_json(attempt / "compile-compatibility.json", verify_compile_commands(binary / "compile_commands.json", major, source))
    put_json(attempt / "compatibility-probes.json", {"boost": boost, "compiler": selection, "cmake": version,
             "coordinate_header_probe": "passed with inherited recorded correction", "boost_link_and_execution_probe": "passed",
             "official_cmake_dependency_resolution": "passed", "full_build_accepted": False,
             "sol2_header_sha256": sha(source / "third_party/sol2-3.3.0/include/sol/sol.hpp"),
             "compatibility_policy_sha256": sha(POLICY), "build_override_sha256": sha(attempt / "build-override.json")})
    print(BUILD_MARKER, flush=True)
    subprocess.run([cmake, "--build", str(binary), "--verbose", "--parallel", "1", "--target",
                    "osrm-extract", "osrm-partition", "osrm-customize", "osrm-routed"], check=True)
    if checked(git + ["rev-parse", "HEAD"]) != OSRM_COMMIT or checked(git + ["status", "--porcelain", "--untracked-files=all"]):
        raise RuntimeError("Original OSRM source changed")
    after = inventory()
    verify_preserved(before, after)
    put_json(attempt / "packages-after.json", after)
    (attempt / "system-packages.txt").write_text(checked(["dpkg-query", "-W"]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=Path, required=True)
    build(parser.parse_args().attempt)
