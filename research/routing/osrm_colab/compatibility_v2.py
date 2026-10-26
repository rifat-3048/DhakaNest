"""V8 audits actual exported C++ commands, not merely CMake property text."""

import json
import os
from pathlib import Path
import re
import shlex

from .compatibility_v1 import CXX_FLAGS, BUILD_MARKER, select_compiler, summarize_log
from .storage import sha
from .workflow import HERE

POLICY = HERE / "compatibility-v2.json"
WARNING_HOOK = HERE / "sol2_compat.cmake"
LUA_SOURCE = "src/extractor/scripting_environment_lua.cpp"
OSRM_SOURCE = "src/osrm/osrm.cpp"


def command_arguments(row):
    if row.get("arguments"):
        return row["arguments"]
    command = row["command"]
    if os.name == "nt" and (re.match(r"^[A-Za-z]:", row.get("directory", "")) or re.match(r'^"?[A-Za-z]:', command)):
        # shlex's POSIX escaping destroys Windows backslashes. Use the native parser.
        import ctypes
        from ctypes import wintypes
        split = ctypes.windll.shell32.CommandLineToArgvW
        split.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
        split.restype = ctypes.POINTER(wintypes.LPWSTR)
        count = ctypes.c_int()
        values = split(command, ctypes.byref(count))
        if not values:
            raise ctypes.WinError()
        try:
            return [values[i] for i in range(count.value)]
        finally:
            free = ctypes.windll.kernel32.LocalFree
            free.argtypes = [ctypes.c_void_p]
            free.restype = ctypes.c_void_p
            free(ctypes.cast(values, ctypes.c_void_p))
    return shlex.split(command)


def overrides(major):
    return [row for row in json.loads(POLICY.read_text())["warning_overrides"]
            if row["compiler"] == "GNU" or major == "11"]


def verify_compile_commands(path, compiler_major, source_root):
    root = Path(source_root).resolve()
    expected_sources = {name: (root / name).resolve() for name in (LUA_SOURCE, OSRM_SOURCE)}
    scoped = {name: [] for name in expected_sources}
    count = 0
    for row in json.loads(path.read_text()):
        filename = Path(row["file"])
        if not filename.is_absolute():
            filename = Path(row.get("directory", root)) / filename
        filename = filename.resolve()
        if filename.suffix not in {".cpp", ".cc", ".cxx"}:
            continue
        arguments = command_arguments(row)
        if not any(arguments[i:i + 2] == ["-include", "cstdint"] for i in range(len(arguments) - 1)):
            raise ValueError(f"Missing cstdint correction: {filename}")
        relative = next((name for name, target in expected_sources.items() if target == filename), None)
        allowed = ({"-Wno-error=array-bounds"} if relative == LUA_SOURCE else
                   {"-Wno-error=free-nonheap-object"} if relative == OSRM_SOURCE and compiler_major == "11" else set())
        actual = {flag for flag in arguments if flag.startswith("-Wno-error=")}
        if actual != allowed:
            raise ValueError(f"Wrong warning exception scope: {filename}; expected {allowed}, got {actual}")
        if any(flag in {"-w", "-Wno-error", "-Warray-bounds=0", "-Wno-free-nonheap-object"}
               or flag.startswith("-Wno-array-bounds") for flag in arguments):
            raise ValueError(f"Disabled diagnostic or global suppression: {filename}")
        if filename.is_relative_to(root / "src") and "-Werror" not in arguments:
            raise ValueError(f"Global Werror missing: {filename}")
        if relative:
            output = row.get("output", "")
            target_paths = [output] if output else arguments
            if relative == LUA_SOURCE and not any("CMakeFiles/EXTRACTOR.dir/" in arg.replace("\\", "/") for arg in target_paths):
                raise ValueError("Sol2 source is not in the expected EXTRACTOR object compilation")
            scoped[relative].append({"file": str(filename), "arguments": arguments, "command": row.get("command"),
                                     "output": output,
                                     "visible_warning_exceptions": sorted(actual)})
        count += 1
    if not all(scoped.values()):
        raise ValueError("Both intended source files must appear in exported compilation commands")
    return {"cpp_commands_verified": count, "source_scopes": scoped,
            "compile_commands_sha256": sha(path), "compatibility_policy_sha256": sha(POLICY),
            "warning_hook_sha256": sha(WARNING_HOOK)}
