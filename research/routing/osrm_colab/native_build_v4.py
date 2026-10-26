"""Versioned compatibility adapter retaining v6 authorization and binary validation."""

import argparse
import json
from pathlib import Path

from . import native_build_v3 as base
from .compatibility_v1 import POLICY, WARNING_HOOK, summarize_log, verify_compile_commands
from .storage import copy_once, sha
from .workflow import read


class Workflow(base.Workflow):
    def __init__(self, config):
        config = dict(config)
        # New immutable identity: a v6 run can never be silently reused as v7.
        config["compatibility_policy_sha256"] = sha(POLICY)
        super().__init__(config)

    def command(self, command, stage, timeout=7200):
        if "research.routing.osrm_colab.build_v3" not in command:
            return super().command(command, stage, timeout)
        command = ["research.routing.osrm_colab.build_v4" if part == "research.routing.osrm_colab.build_v3"
                   else part for part in command]
        attempt = Path(command[command.index("--attempt") + 1])
        before = set(self.work.glob("setup-*.log"))
        try:
            result = super().command(command, stage, timeout)
            # Validate the override BEFORE the inherited action publishes binaries.
            override = read(attempt / "build-override.json")
            expected = read(POLICY)["warning_overrides"] if override["compiler_major"] == "11" else []
            if (override["policy_sha256"] != sha(POLICY) or override["warning_overrides"] != expected
                    or override["warning_hook_sha256"] != sha(WARNING_HOOK)):
                raise ValueError("Unapproved build compatibility policy")
            result["compatibility"] = verify_compile_commands(attempt / "build/compile_commands.json", override["compiler_major"])
            return result
        finally:
            for log in sorted(set(self.work.glob("setup-*.log")) - before):
                self.record(f"{log.stem}.compatibility-diagnostics.json", {
                    "log_sha256": sha(log), "diagnostics": summarize_log(log.read_text(errors="replace"))})
            patch = attempt / "coordinate-cstdint.patch"
            if patch.is_file():
                copy_once(patch, self.drive / "native_attempts" / attempt.name / patch.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("inputs", "runtime", "setup", "download", "preprocess", "acquire", "offline"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    workflow = Workflow(read(args.config))
    method = {"acquire": workflow.acquire_and_finalize}.get(args.stage, getattr(workflow, args.stage, None))
    value = method()
    if value is not None:
        print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
