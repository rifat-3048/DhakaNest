"""V9 delegates unchanged warning scope validation, then rejects extra forced headers."""

import json
from pathlib import Path

from . import compatibility_v2 as previous
from .storage import sha
from .workflow import HERE

POLICY = HERE / "compatibility-v3.json"


def verify_compile_commands(path, major, source):
    proof = previous.verify_compile_commands(path, major, source)
    for row in json.loads(path.read_text()):
        if Path(row["file"]).suffix not in {".cpp", ".cc", ".cxx"}:
            continue
        arguments = previous.command_arguments(row)
        includes = []
        for index, flag in enumerate(arguments):
            if flag == "-include":
                includes.append(arguments[index + 1] if index + 1 < len(arguments) else None)
            elif flag.startswith("-include"):
                raise ValueError("Unapproved joined/extra forced include")
        if includes != ["cstdint"] or any(flag.startswith("-imacros") for flag in arguments):
            raise ValueError("Only the evidence-backed inherited cstdint forced include is allowed")
    proof["header_policy_sha256"] = sha(POLICY)
    return proof
