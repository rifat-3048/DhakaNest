"""Real HOST CMake File API/scope check on a small fixture, not an OSRM build."""

import json
from pathlib import Path
import shutil
import subprocess
import uuid

from .compatibility_v2 import WARNING_HOOK
from .compatibility_v3 import verify_compile_commands
from .headers_v9 import TARGETS, file_api_sources
from .storage import copy_once, put_json, sha, tree_copy
from .workflow import HERE, ROOT


def main():
    cmake = HERE / "runtime/cmake_scope_tools/unpacked/cmake/data/bin/cmake.exe"
    if sha(cmake) != "3c05de86fbc0ec0610bbee201588e4fc1017347ec61b0f8080981fc6bfe93681":
        raise ValueError("Prior approved private CMake tool changed")
    compiler = shutil.which("g++")
    make = Path(compiler).parent / "mingw32-make.exe"
    work = HERE / "runtime" / ("file-api-v9-" + uuid.uuid4().hex)
    source = work / "source"
    names = ["src/extractor/scripting_environment_lua.cpp", "src/extractor/suffix_table.cpp", "src/extractor/other.cpp", "src/osrm/osrm.cpp"]
    names += ["src/tools/" + name + ".cpp" for name in TARGETS]
    for name in names:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("int fixture;\n", encoding="ascii")
    (source / "CMakeLists.txt").write_text('''cmake_minimum_required(VERSION 3.16)
project(OSRM LANGUAGES CXX)
if(TEST_GCC11_BRANCH)
  set(CMAKE_CXX_COMPILER_VERSION "11.4.0")
endif()
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Werror -include cstdint")
include("@HOOK@")
add_library(EXTRACTOR OBJECT src/extractor/scripting_environment_lua.cpp src/extractor/suffix_table.cpp src/extractor/other.cpp)
add_library(osrm OBJECT src/osrm/osrm.cpp)
foreach(name osrm-extract osrm-partition osrm-customize osrm-routed)
  add_executable(${name} src/tools/${name}.cpp)
  target_link_libraries(${name} PRIVATE EXTRACTOR osrm)
endforeach()
'''.replace("@HOOK@", WARNING_HOOK.as_posix()), encoding="ascii")
    evidence = ROOT / "research/results/phase_3d_colab/header_file_api_v9"
    report = {"fixture_only": True, "linux_osrm_build_executed": False, "cases": {}}
    host_version = subprocess.check_output([compiler, "-dumpversion"], text=True).strip()
    for name, major, simulated in (("host", host_version.split(".")[0], False), ("gcc11_branch", "11", True)):
        binary = work / name
        query = binary / ".cmake/api/v1/query"
        query.mkdir(parents=True)
        (query / "codemodel-v2").touch()
        command = [str(cmake), "-S", str(source), "-B", str(binary), "-G", "MinGW Makefiles",
                   "-DCMAKE_CXX_COMPILER=" + compiler, "-DCMAKE_MAKE_PROGRAM=" + str(make),
                   "-DTEST_GCC11_BRANCH=" + ("ON" if simulated else "OFF")]
        result = subprocess.run(command, capture_output=True, text=True)
        put_json(evidence / f"{name}-configure.json", {"command": command, "exit_code": result.returncode,
                                                     "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            raise RuntimeError(result.stderr)
        files, targets = file_api_sources(binary, source)
        proof = verify_compile_commands(binary / "compile_commands.json", major, source)
        copy_once(binary / "compile_commands.json", evidence / f"{name}-compile-commands.json")
        tree_copy(binary / ".cmake/api/v1/reply", evidence / name / "cmake-file-api")
        report["cases"][name] = {"compiler_version_branch_simulated": simulated, "host_compiler_version": host_version,
                                 "target_closure": targets, "source_count": len(files), "scope_proof": proof}
    put_json(evidence / "verification.json", report)
    print(json.dumps({name: {"sources": row["source_count"], "targets": row["target_closure"]}
                      for name, row in report["cases"].items()}, indent=2))


if __name__ == "__main__":
    main()
