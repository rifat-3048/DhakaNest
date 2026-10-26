"""Generate real CMake compile commands for a minimal HOST fixture, never OSRM.

The GCC-11 case simulates the CMake version branch, not an installed GCC 11.
The approved portable tool is unpacked privately; nothing is pip-installed.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import uuid
import zipfile

from .compatibility_v2 import WARNING_HOOK, verify_compile_commands
from .storage import copy_once, put_json, sha
from .workflow import HERE, ROOT

WHEEL_SHA = "f1ea1fe826355560e8976c3d5794d9357444209bc0e0d56676c71e6a571fd474"


def main():
    directory = HERE / "runtime/cmake_scope_tools"
    wheel = directory / "cmake-3.31.10-py3-none-win_amd64.whl"
    if sha(wheel) != WHEEL_SHA:
        raise ValueError("Private portable CMake wheel checksum differs from approved PyPI artifact")
    unpacked = directory / "unpacked"
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.infolist():
            name = PurePosixPath(member.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in member.filename or ":" in member.filename:
                raise ValueError("Unsafe tool wheel member")
            if member.is_dir():
                continue
            destination = unpacked / member.filename
            body = archive.read(member)
            if destination.exists():
                if sha(destination) != hashlib.sha256(body).hexdigest():
                    raise ValueError("Existing private CMake tool changed")
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(body)
    cmake = unpacked / "cmake/data/bin/cmake.exe"
    compiler = shutil.which("g++")
    make = Path(compiler).parent / "mingw32-make.exe" if compiler else None
    if not compiler or not make.is_file():
        raise RuntimeError("Existing Windows MinGW compiler/make required; this runner installs neither")
    actual_version = subprocess.check_output([compiler, "-dumpversion"], text=True).strip()
    actual_major = actual_version.split(".")[0]
    work = HERE / "runtime" / ("scope-v8-" + uuid.uuid4().hex)
    source = work / "source"
    for name in ("src/extractor/scripting_environment_lua.cpp", "src/extractor/other.cpp", "src/osrm/osrm.cpp"):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("int fixture_value;\n", encoding="ascii")
    cmake_source = '''cmake_minimum_required(VERSION 3.16)
project(OSRM LANGUAGES CXX)
if(TEST_GCC11_BRANCH)
  set(CMAKE_CXX_COMPILER_VERSION "11.4.0")
endif()
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Werror -include cstdint")
include("@HOOK@")
add_library(EXTRACTOR OBJECT src/extractor/scripting_environment_lua.cpp src/extractor/other.cpp)
add_library(osrm OBJECT src/osrm/osrm.cpp)
'''.replace("@HOOK@", WARNING_HOOK.as_posix())
    (source / "CMakeLists.txt").write_text(cmake_source, encoding="ascii")
    cases = {}
    evidence = ROOT / "research/results/phase_3d_colab/sol2_scope_v4"
    for case, major, simulated in (("host_actual", actual_major, False), ("gcc11_cmake_branch", "11", True)):
        binary = work / case
        command = [str(cmake), "-S", str(source), "-B", str(binary), "-G", "MinGW Makefiles",
                   "-DCMAKE_CXX_COMPILER=" + compiler, "-DCMAKE_MAKE_PROGRAM=" + str(make),
                   "-DTEST_GCC11_BRANCH=" + ("ON" if simulated else "OFF")]
        result = subprocess.run(command, capture_output=True, text=True)
        put_json(evidence / f"{case}-configure.json", {"command": command, "exit_code": result.returncode,
                                                       "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise RuntimeError(f"CMake fixture generation failed: {result.stderr}")
        path = binary / "compile_commands.json"
        proof = verify_compile_commands(path, major, source)
        copy_once(path, evidence / f"{case}-compile-commands.json")
        cases[case] = {"branch_simulated": simulated, "verified_scope": proof}
    copy_once(source / "CMakeLists.txt", evidence / "fixture-CMakeLists.txt")
    report = {"host": "Windows MinGW", "actual_compiler_version": actual_version,
              "portable_cmake_version": subprocess.check_output([str(cmake), "--version"], text=True).strip(),
              "portable_wheel_sha256": WHEEL_SHA, "cmake_executable_sha256": sha(cmake),
              "scope_fixture_only": True, "osrm_compiled": False, "linux_executed": False, "cases": cases}
    put_json(evidence / "verification.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
