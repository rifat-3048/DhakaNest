"""Clean native attempt, called under the workflow's bounded resource monitor."""

import argparse
from pathlib import Path
import re

from .dependencies_v3 import checked, inventory, prepare, select_compiler, verify_preserved
from .storage import put_json, sha
from .workflow import HERE, OSRM_COMMIT


def build(attempt):
    # A failed attempt is evidence, not a directory to clean and reuse.
    attempt.mkdir(parents=True, exist_ok=False)
    boost, before = prepare(attempt)
    source, binary = attempt / "source", attempt / "build"
    checked(["git", "init", str(source)])
    git = ["git", "-C", str(source)]
    checked(git + ["remote", "add", "origin", "https://github.com/Project-OSRM/osrm-backend.git"])
    checked(git + ["fetch", "--depth", "1", "origin", "refs/tags/v5.27.1"])
    if checked(git + ["rev-parse", "FETCH_HEAD^{commit}"]) != OSRM_COMMIT:
        raise RuntimeError("Official tag does not match the pinned OSRM commit")
    checked(git + ["checkout", "--detach", OSRM_COMMIT])
    checked(git + ["submodule", "update", "--init", "--recursive", "--depth", "1"])
    checked(git + ["fsck", "--no-dangling"])
    if checked(git + ["status", "--porcelain", "--untracked-files=all"]):
        raise RuntimeError("Official source checkout is not clean")
    selection = select_compiler(source, attempt)
    cmake = "/usr/bin/cmake"
    version = checked([cmake, "--version"])
    if not re.match(r"cmake version 3\.", version):
        raise RuntimeError("System CMake 3.x required; do not use an unvalidated pip CMake 4")
    # Separate link probe checks actual installed headers and compiled libraries.
    macro = 100000 + int(boost.split(".")[1]) * 100
    checked([selection["cxx"], "-std=c++17", f"-DEXPECTED_BOOST={macro}",
             str(HERE / "boost_probe.cpp"), "-o", str(attempt / "boost-probe"),
             "-lboost_filesystem", "-lboost_program_options"])
    checked([str(attempt / "boost-probe")])
    checked([cmake, "-S", str(source), "-B", str(binary),
             "-DCMAKE_C_COMPILER=" + selection["cc"], "-DCMAKE_CXX_COMPILER=" + selection["cxx"],
             "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_VERBOSE_MAKEFILE=ON",
             "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON", "-DCMAKE_CXX_FLAGS=-fdiagnostics-color=never",
             "-DBoost_NO_BOOST_CMAKE=ON", "-DBOOST_ROOT=/usr", "-DBOOST_INCLUDEDIR=/usr/include",
             "-DBoost_ADDITIONAL_VERSIONS=" + boost + ".0", "-DBUILD_SHARED_LIBS=OFF",
             "-DENABLE_CCACHE=OFF", "-DENABLE_NODE_BINDINGS=OFF", "-DENABLE_LTO=OFF",
             "-DENABLE_GOLD_LINKER=OFF"])
    put_json(attempt / "compatibility-probes.json", {
        "boost": boost, "compiler": selection, "cmake": version,
        "coordinate_header_probe": "passed", "boost_link_and_execution_probe": "passed",
        "official_cmake_dependency_resolution": "passed", "full_build_accepted": False,
        "coordinate_header_sha256": sha(source / "include/util/coordinate.hpp"),
        "boost_header_sha256": sha(Path("/usr/include/boost/version.hpp"))})
    # Stream verbose compilation directly into the monitored parent's full log.
    import subprocess
    subprocess.run([cmake, "--build", str(binary), "--verbose", "--parallel", "1", "--target",
                    "osrm-extract", "osrm-partition", "osrm-customize", "osrm-routed"], check=True)
    if checked(git + ["rev-parse", "HEAD"]) != OSRM_COMMIT or checked(git + ["status", "--porcelain", "--untracked-files=all"]):
        raise RuntimeError("OSRM source integrity changed")
    after = inventory()
    verify_preserved(before, after)
    put_json(attempt / "packages-after.json", after)
    # Keep the canonical package inventory used by existing downstream evidence.
    (attempt / "system-packages.txt").write_text(checked(["dpkg-query", "-W"]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=Path, required=True)
    build(parser.parse_args().attempt)
