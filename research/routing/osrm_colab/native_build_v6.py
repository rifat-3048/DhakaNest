"""Small v9 adapter: reuse v8 runtime/auth controls; add source/preflight acceptance."""

import argparse
import json
from pathlib import Path

from . import native_build_v5 as previous
from . import compatibility_v2 as inherited
from .compatibility_v3 import POLICY, verify_compile_commands
from .headers_v9 import tree_manifest, verify_source_copy
from .storage import copy_once, sha, tree_copy
from .workflow import read


class Workflow(previous.Workflow):
    def __init__(self, config):
        config = dict(config)
        config["header_policy_sha256"] = sha(POLICY)
        super().__init__(config)

    def command(self, command, stage, timeout=7200):
        if "research.routing.osrm_colab.build_v3" not in command:
            return super().command(command, stage, timeout)
        command = ["research.routing.osrm_colab.build_v6" if part == "research.routing.osrm_colab.build_v3" else part
                   for part in command]
        attempt = Path(command[command.index("--attempt") + 1])
        before = set(self.work.glob("setup-*.log"))
        try:
            result = super().command(command, stage, timeout)
            override = read(attempt / "build-override.json")
            if (override["policy_sha256"] != sha(POLICY) or override["inherited_policy_sha256"] != sha(inherited.POLICY)
                    or override["warning_overrides"] != inherited.overrides(override["compiler_major"])
                    or override["warning_hook_sha256"] != sha(inherited.WARNING_HOOK)):
                raise ValueError("Unapproved v9 source/header policy")
            if read(attempt / "header-preflight.json")["full_build_permitted"] is not True:
                raise ValueError("Incomplete/failed header preflight cannot publish binaries")
            manifest = read(attempt / "header-source-manifest.json")
            verify_source_copy(manifest["pristine_files"], tree_manifest(attempt / "build_source"))
            if override["source_patch_sha256"] != sha(attempt / "suffix-vector.patch"):
                raise ValueError("Header patch checksum changed")
            result["compatibility"] = verify_compile_commands(attempt / "build/compile_commands.json",
                                                              override["compiler_major"], attempt / "build_source")
            return result
        finally:
            for log in sorted(set(self.work.glob("setup-*.log")) - before):
                diagnostic = inherited.summarize_log(log.read_text(errors="replace"))
                diagnostic["warning_policy"] = read(inherited.POLICY)["warning_policy"]
                diagnostic["negative_probe_note"] = "Original coordinate/suffix probes are intentional baselines; required header failures block full build. See structured probe JSON."
                self.record(f"{log.stem}.header-diagnostics.json", {"log_sha256": sha(log), "diagnostics": diagnostic})
            for name in ("suffix-vector.patch", "coordinate-cstdint.patch"):
                path = attempt / name
                if path.is_file():
                    copy_once(path, self.drive / "native_attempts" / attempt.name / name)
            tree_copy(attempt / "build/.cmake/api/v1/reply", self.drive / "native_attempts" / attempt.name / "cmake-file-api")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("inputs", "runtime", "setup", "download", "preprocess", "runtime-smoke", "acquire", "offline"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    workflow = Workflow(read(args.config))
    method = {"acquire": workflow.acquire_and_finalize, "runtime-smoke": workflow.runtime_smoke}.get(
        args.stage, getattr(workflow, args.stage.replace("-", "_"), None))
    value = method()
    if value is not None:
        print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
